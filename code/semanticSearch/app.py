from __future__ import annotations

import os
import json
import base64
import tempfile
import shutil
import subprocess
from pathlib import Path
from typing import Any, Dict, List
from datetime import datetime
import uuid
import io

from flask import Flask, jsonify, request
from flask_cors import CORS
import boto3
from botocore.exceptions import BotoCoreError, ClientError
try:
    from PyPDF2 import PdfReader
except ImportError:  # Prefer PyPDF2, fall back to pypdf if only modern package exists
    from pypdf import PdfReader
from docx import Document as DocxDocument
from shared.env_loader import load_environment

load_environment()

app = Flask(__name__)
CORS(app)

# Configure for large file uploads
app.config['MAX_CONTENT_LENGTH'] = 500 * 1024 * 1024  # 500MB max file size
app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0

DEFAULT_AWS_REGION = os.environ.get("AWS_REGION")
if not DEFAULT_AWS_REGION:
    raise RuntimeError("Set AWS_REGION before starting semantic search service")

# AWS clients
rekognition = boto3.client("rekognition", region_name=DEFAULT_AWS_REGION)
transcribe = boto3.client("transcribe", region_name=DEFAULT_AWS_REGION)
comprehend = boto3.client("comprehend", region_name=DEFAULT_AWS_REGION)
bedrock_runtime = boto3.client("bedrock-runtime", region_name=DEFAULT_AWS_REGION)
s3 = boto3.client("s3", region_name=DEFAULT_AWS_REGION)

# S3 bucket for video storage
DEFAULT_MEDIA_BUCKET = os.environ.get("MEDIA_S3_BUCKET")
SEMANTIC_SEARCH_BUCKET = os.environ.get("SEMANTIC_SEARCH_BUCKET") or DEFAULT_MEDIA_BUCKET

if not SEMANTIC_SEARCH_BUCKET:
    raise RuntimeError("Set SEMANTIC_SEARCH_BUCKET or MEDIA_S3_BUCKET before starting semantic search service")


def _normalise_bucket_region(region: str | None) -> str:
    """Convert S3 location constraint into a concrete region name."""
    if not region:
        return "us-east-1"
    if region == "EU":
        return "eu-west-1"
    return region


def _detect_bucket_region(bucket_name: str) -> str | None:
    """Best-effort detection of the S3 bucket's region."""
    try:
        probe_client = boto3.client("s3", region_name=DEFAULT_AWS_REGION)
        response = probe_client.get_bucket_location(Bucket=bucket_name)
        return _normalise_bucket_region(response.get("LocationConstraint"))
    except Exception as exc:  # pragma: no cover - network failures tolerated
        app.logger.warning("Unable to determine region for bucket %s: %s", bucket_name, exc)
        return None


def _resolve_transcribe_region(bucket_region: str | None) -> str:
    """Determine which region AWS Transcribe should use."""
    override = os.environ.get("TRANSCRIBE_REGION")
    if override:
        if bucket_region and bucket_region != override:
            app.logger.warning(
                "TRANSCRIBE_REGION override (%s) differs from bucket region %s",
                override,
                bucket_region,
            )
        return override
    return bucket_region or DEFAULT_AWS_REGION

# FFmpeg paths
FFMPEG_PATH = os.environ.get("FFMPEG_PATH")
if not FFMPEG_PATH:
    for path in ["/opt/homebrew/bin/ffmpeg", "/usr/local/bin/ffmpeg", "/usr/bin/ffmpeg", "ffmpeg"]:
        try:
            result = subprocess.run([path, "-version"], capture_output=True, timeout=2)
            if result.returncode == 0:
                FFMPEG_PATH = path
                break
        except (FileNotFoundError, subprocess.TimeoutExpired):
            continue
    if not FFMPEG_PATH:
        FFMPEG_PATH = "ffmpeg"

FFPROBE_PATH = FFMPEG_PATH.replace("ffmpeg", "ffprobe") if "ffmpeg" in FFMPEG_PATH else "ffprobe"

# Local storage directories
STORAGE_BASE_DIR = Path(__file__).parent
DOCUMENTS_DIR = STORAGE_BASE_DIR / "documents"
VIDEOS_DIR = STORAGE_BASE_DIR / "videos"
INDICES_DIR = STORAGE_BASE_DIR / "indices"

# Ensure directories exist
DOCUMENTS_DIR.mkdir(exist_ok=True)
VIDEOS_DIR.mkdir(exist_ok=True)
INDICES_DIR.mkdir(exist_ok=True)


def _as_data_uri_jpeg(base64_value: str | None) -> str | None:
    if not base64_value:
        return None
    if base64_value.startswith("data:"):
        return base64_value
    return f"data:image/jpeg;base64,{base64_value}"


def _relative_video_path(stored_filename: str) -> str:
    """Return the relative storage path for a video."""
    return str(Path("videos") / stored_filename)


def _relative_document_path(stored_filename: str) -> str:
    """Return the relative storage path for a document."""
    return str(Path("documents") / stored_filename)


def _absolute_video_path(stored_filename: str) -> Path:
    """Return the absolute storage path for a video."""
    return VIDEOS_DIR / stored_filename


def _absolute_document_path(stored_filename: str) -> Path:
    """Return the absolute storage path for a document."""
    return DOCUMENTS_DIR / stored_filename

# Index file paths
VIDEO_INDEX_FILE = INDICES_DIR / "video_index.json"
DOCUMENT_INDEX_FILE = INDICES_DIR / "document_index.json"

# In-memory indices (loaded from disk on startup)
VIDEO_INDEX = []
DOCUMENT_INDEX = []


def _save_video_index():
    """Save video index to JSON file."""
    try:
        serialized_index = []
        for entry in VIDEO_INDEX:
            entry_copy = entry.copy()
            stored_filename = entry_copy.get("stored_filename")
            if stored_filename:
                entry_copy["file_path"] = _relative_video_path(stored_filename)
            serialized_index.append(entry_copy)

        with open(VIDEO_INDEX_FILE, 'w') as f:
            json.dump(serialized_index, f, indent=2, default=str)
    except Exception as e:
        print(f"Error saving video index: {e}")


def _load_video_index():
    """Load video index from JSON file."""
    global VIDEO_INDEX
    if VIDEO_INDEX_FILE.exists():
        try:
            with open(VIDEO_INDEX_FILE, 'r') as f:
                raw_index = json.load(f)

            VIDEO_INDEX = []
            for entry in raw_index:
                entry_copy = entry.copy()
                stored_filename = entry_copy.get("stored_filename")
                if not stored_filename:
                    file_path_value = entry_copy.get("file_path", "")
                    stored_filename = Path(file_path_value).name if file_path_value else ""
                if stored_filename:
                    entry_copy["stored_filename"] = stored_filename
                    entry_copy["file_path"] = _relative_video_path(stored_filename)
                VIDEO_INDEX.append(entry_copy)
            print(f"Loaded {len(VIDEO_INDEX)} videos from index")
        except Exception as e:
            print(f"Error loading video index: {e}")
            VIDEO_INDEX = []


def _save_document_index():
    """Save document index to JSON file."""
    try:
        serialized_index = []
        for entry in DOCUMENT_INDEX:
            entry_copy = entry.copy()
            stored_filename = entry_copy.get("stored_filename")
            if stored_filename:
                entry_copy["file_path"] = _relative_document_path(stored_filename)
            serialized_index.append(entry_copy)

        with open(DOCUMENT_INDEX_FILE, 'w') as f:
            json.dump(serialized_index, f, indent=2, default=str)
    except Exception as e:
        print(f"Error saving document index: {e}")


def _load_document_index():
    """Load document index from JSON file."""
    global DOCUMENT_INDEX
    if DOCUMENT_INDEX_FILE.exists():
        try:
            with open(DOCUMENT_INDEX_FILE, 'r') as f:
                raw_index = json.load(f)

            DOCUMENT_INDEX = []
            for entry in raw_index:
                entry_copy = entry.copy()
                stored_filename = entry_copy.get("stored_filename")
                if not stored_filename:
                    file_path_value = entry_copy.get("file_path", "")
                    stored_filename = Path(file_path_value).name if file_path_value else ""
                if stored_filename:
                    entry_copy["stored_filename"] = stored_filename
                    entry_copy["file_path"] = _relative_document_path(stored_filename)
                DOCUMENT_INDEX.append(entry_copy)
            print(f"Loaded {len(DOCUMENT_INDEX)} documents from index")
        except Exception as e:
            print(f"Error loading document index: {e}")
            DOCUMENT_INDEX = []


# Load indices on startup
_load_video_index()
_load_document_index()


@app.route("/health", methods=["GET"])
def health() -> Any:
    return jsonify({
        "status": "ok",
        "service": "semantic-search",
        "region": DEFAULT_AWS_REGION
    })


def _extract_video_frames(video_path: Path, output_dir: Path, interval: int = 5) -> List[Path]:
    """Extract frames from video at specified interval (in seconds)."""
    frames = []
    
    # Get video duration
    probe_cmd = [
        FFPROBE_PATH, "-v", "error",
        "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1",
        str(video_path)
    ]
    duration_result = subprocess.run(probe_cmd, capture_output=True, text=True)
    duration = float(duration_result.stdout.strip())
    
    # Extract frames at intervals
    for timestamp in range(0, int(duration), interval):
        frame_path = output_dir / f"frame_{timestamp:04d}.jpg"
        extract_cmd = [
            FFMPEG_PATH, "-ss", str(timestamp),
            "-i", str(video_path),
            "-vframes", "1",
            "-q:v", "2",
            str(frame_path), "-y"
        ]
        result = subprocess.run(extract_cmd, capture_output=True)
        if result.returncode == 0:
            frames.append(frame_path)
    
    return frames


def _analyze_frame_with_rekognition(frame_path: Path) -> Dict[str, Any]:
    """Analyze a single frame using Amazon Rekognition."""
    with open(frame_path, "rb") as image_file:
        image_bytes = image_file.read()
    
    analysis = {
        "labels": [],
        "text": [],
        "faces": [],
        "moderation": []
    }
    
    try:
        # Detect labels (objects, scenes, activities)
        label_response = rekognition.detect_labels(
            Image={"Bytes": image_bytes},
            MaxLabels=20,
            MinConfidence=70
        )
        analysis["labels"] = [
            {"name": label["Name"], "confidence": label["Confidence"]}
            for label in label_response.get("Labels", [])
        ]
    except Exception as e:
        app.logger.error(f"Label detection failed: {e}")
    
    try:
        # Detect text in image
        text_response = rekognition.detect_text(Image={"Bytes": image_bytes})
        analysis["text"] = [
            item["DetectedText"]
            for item in text_response.get("TextDetections", [])
            if item.get("Type") == "LINE"
        ]
    except Exception as e:
        app.logger.error(f"Text detection failed: {e}")
    
    try:
        # Detect faces and emotions
        face_response = rekognition.detect_faces(
            Image={"Bytes": image_bytes},
            Attributes=["ALL"]
        )
        analysis["faces"] = [
            {
                "emotions": [
                    {"type": e["Type"], "confidence": e["Confidence"]}
                    for e in face.get("Emotions", [])
                ][:3]  # Top 3 emotions
            }
            for face in face_response.get("FaceDetails", [])
        ]
    except Exception as e:
        app.logger.error(f"Face detection failed: {e}")
    
    return analysis


def _extract_audio_and_transcribe(video_path: Path, temp_dir: Path, job_id: str) -> str:
    """Extract audio and transcribe using AWS Transcribe."""
    # Extract audio
    audio_path = temp_dir / "audio.mp3"
    extract_cmd = [
        FFMPEG_PATH, "-i", str(video_path),
        "-vn", "-acodec", "libmp3lame", "-ar", "16000", "-ac", "1", "-b:a", "64k",
        str(audio_path), "-y"
    ]
    subprocess.run(extract_cmd, capture_output=True, check=True)
    
    # Resolve regions for S3 and Transcribe
    bucket_region = _detect_bucket_region(SEMANTIC_SEARCH_BUCKET)
    if not bucket_region:
        app.logger.warning(
            "Could not detect region for bucket %s; falling back to AWS_REGION %s",
            SEMANTIC_SEARCH_BUCKET,
            DEFAULT_AWS_REGION,
        )
    s3_region = bucket_region or DEFAULT_AWS_REGION
    s3_client = boto3.client("s3", region_name=s3_region)
    transcribe_region = _resolve_transcribe_region(bucket_region)
    transcribe_client = boto3.client("transcribe", region_name=transcribe_region)
    app.logger.info(
        "Semantic search using S3 region %s and Transcribe region %s",
        s3_region,
        transcribe_region,
    )

    # Upload to S3
    s3_key = f"transcribe/{job_id}/audio.mp3"
    try:
        s3_client.head_bucket(Bucket=SEMANTIC_SEARCH_BUCKET)
    except ClientError:
        create_kwargs: Dict[str, Any] = {"Bucket": SEMANTIC_SEARCH_BUCKET}
        if s3_region != "us-east-1":
            create_kwargs["CreateBucketConfiguration"] = {"LocationConstraint": s3_region}
        s3_client.create_bucket(**create_kwargs)
        bucket_region = bucket_region or s3_region
    
    s3_client.upload_file(str(audio_path), SEMANTIC_SEARCH_BUCKET, s3_key)
    s3_uri = f"s3://{SEMANTIC_SEARCH_BUCKET}/{s3_key}"
    
    # Start transcription job
    transcribe_job_name = f"semantic-search-{job_id}"
    transcribe_client.start_transcription_job(
        TranscriptionJobName=transcribe_job_name,
        Media={"MediaFileUri": s3_uri},
        MediaFormat="mp3",
        LanguageCode="en-US"
    )
    
    # Wait for completion
    import time
    max_wait = 300  # 5 minutes
    start_time = time.time()
    
    while time.time() - start_time < max_wait:
        status = transcribe_client.get_transcription_job(TranscriptionJobName=transcribe_job_name)
        job_status = status["TranscriptionJob"]["TranscriptionJobStatus"]
        
        if job_status == "COMPLETED":
            transcript_uri = status["TranscriptionJob"]["Transcript"]["TranscriptFileUri"]
            import requests
            transcript_data = requests.get(transcript_uri).json()
            transcript_text = transcript_data.get("results", {}).get("transcripts", [{}])[0].get("transcript", "")
            
            # Cleanup
            transcribe_client.delete_transcription_job(TranscriptionJobName=transcribe_job_name)
            s3_client.delete_object(Bucket=SEMANTIC_SEARCH_BUCKET, Key=s3_key)
            
            return transcript_text
        elif job_status == "FAILED":
            break
        
        time.sleep(5)
    
    return ""


def _generate_embedding(text: str) -> List[float]:
    """Generate embedding using Amazon Bedrock Titan Embeddings."""
    try:
        response = bedrock_runtime.invoke_model(
            modelId="amazon.titan-embed-text-v1",
            contentType="application/json",
            accept="application/json",
            body=json.dumps({"inputText": text})
        )
        
        response_body = json.loads(response["body"].read())
        embedding = response_body.get("embedding", [])
        return embedding
    except Exception as e:
        app.logger.error(f"Embedding generation failed: {e}")
        return []


def _compute_similarity(embedding1: List[float], embedding2: List[float]) -> float:
    """Compute cosine similarity between two embeddings."""
    if not embedding1 or not embedding2:
        return 0.0
    
    import math
    
    dot_product = sum(a * b for a, b in zip(embedding1, embedding2))
    magnitude1 = math.sqrt(sum(a * a for a in embedding1))
    magnitude2 = math.sqrt(sum(b * b for b in embedding2))
    
    if magnitude1 == 0 or magnitude2 == 0:
        return 0.0
    
    return dot_product / (magnitude1 * magnitude2)


def _process_stored_video(
    *,
    video_id: str,
    stored_video_path: Path,
    video_title: str,
    video_description: str,
    original_filename: str,
) -> Dict[str, Any]:
    """Re-process a video already stored on disk and return updated fields."""
    temp_dir = Path(tempfile.mkdtemp(prefix=f"semantic_search_reprocess_{video_id}_"))
    try:
        working_video_path = temp_dir / "video.mp4"
        shutil.copy2(stored_video_path, working_video_path)

        # Extract frames
        frames_dir = temp_dir / "frames"
        frames_dir.mkdir()
        frames = _extract_video_frames(working_video_path, frames_dir, interval=10)

        # Analyze frames with Rekognition
        all_labels: List[str] = []
        all_text: List[str] = []
        all_emotions: List[str] = []

        for frame in frames[:30]:  # Limit to 30 frames to save API calls
            analysis = _analyze_frame_with_rekognition(frame)
            all_labels.extend([label["name"] for label in analysis["labels"]])
            all_text.extend(analysis["text"])
            for face in analysis["faces"]:
                all_emotions.extend([e["type"] for e in face["emotions"]])

        unique_labels = list(set(all_labels))
        unique_text = list(set(all_text))
        unique_emotions = list(set(all_emotions))

        # Extract and transcribe audio
        transcript = _extract_audio_and_transcribe(working_video_path, temp_dir, video_id)

        # Build metadata text for embedding
        metadata_parts = [video_title, video_description]
        if transcript:
            metadata_parts.append(f"Transcript: {transcript}")
        if unique_labels:
            metadata_parts.append(f"Visual elements: {', '.join(unique_labels[:50])}")
        if unique_text:
            metadata_parts.append(f"Text in video: {', '.join(unique_text[:20])}")
        if unique_emotions:
            metadata_parts.append(f"Emotions detected: {', '.join(unique_emotions)}")
        metadata_text = " ".join([part for part in metadata_parts if part])

        embedding = _generate_embedding(metadata_text)

        # Create thumbnail
        thumbnail_path = frames[len(frames) // 2] if frames else None
        thumbnail_base64 = None
        if thumbnail_path and thumbnail_path.exists():
            with open(thumbnail_path, "rb") as f:
                thumbnail_base64 = base64.b64encode(f.read()).decode("utf-8")

        return {
            "title": video_title,
            "description": video_description,
            "original_filename": original_filename,
            "transcript": transcript,
            "labels": unique_labels[:50],
            "text_detected": unique_text[:20],
            "emotions": unique_emotions,
            "embedding": embedding,
            "thumbnail": thumbnail_base64,
            "metadata_text": metadata_text,
            "reprocessed_at": datetime.utcnow().isoformat(),
        }
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


@app.route("/upload-video", methods=["POST"])
def upload_video() -> Any:
    """Upload and index a video for semantic search."""
    if "video" not in request.files:
        return jsonify({"error": "No video file provided"}), 400
    
    video_file = request.files["video"]
    if not video_file.filename:
        return jsonify({"error": "Empty filename"}), 400
    
    video_title = request.form.get("title", video_file.filename)
    video_description = request.form.get("description", "")
    
    job_id = str(uuid.uuid4())
    temp_dir = Path(tempfile.mkdtemp(prefix=f"semantic_search_{job_id}_"))
    
    try:
        app.logger.info(f"Job {job_id}: Processing video: {video_title}")
        
        # Save video
        video_path = temp_dir / "video.mp4"
        video_file.save(str(video_path))
        
        # Extract frames
        app.logger.info(f"Job {job_id}: Extracting frames...")
        frames_dir = temp_dir / "frames"
        frames_dir.mkdir()
        frames = _extract_video_frames(video_path, frames_dir, interval=10)
        
        # Analyze frames with Rekognition
        app.logger.info(f"Job {job_id}: Analyzing {len(frames)} frames...")
        all_labels = []
        all_text = []
        all_emotions = []
        
        for frame in frames[:30]:  # Limit to 30 frames to save API calls
            analysis = _analyze_frame_with_rekognition(frame)
            all_labels.extend([label["name"] for label in analysis["labels"]])
            all_text.extend(analysis["text"])
            for face in analysis["faces"]:
                all_emotions.extend([e["type"] for e in face["emotions"]])
        
        # Get unique labels and text
        unique_labels = list(set(all_labels))
        unique_text = list(set(all_text))
        unique_emotions = list(set(all_emotions))
        
        # Extract and transcribe audio
        app.logger.info(f"Job {job_id}: Transcribing audio...")
        transcript = _extract_audio_and_transcribe(video_path, temp_dir, job_id)
        
        # Build metadata text for embedding
        metadata_parts = [video_title, video_description]
        if transcript:
            metadata_parts.append(f"Transcript: {transcript}")
        if unique_labels:
            metadata_parts.append(f"Visual elements: {', '.join(unique_labels[:50])}")
        if unique_text:
            metadata_parts.append(f"Text in video: {', '.join(unique_text[:20])}")
        if unique_emotions:
            metadata_parts.append(f"Emotions detected: {', '.join(unique_emotions)}")
        
        metadata_text = " ".join(metadata_parts)
        
        # Generate embedding
        app.logger.info(f"Job {job_id}: Generating embedding...")
        embedding = _generate_embedding(metadata_text)
        
        # Create thumbnail
        thumbnail_path = frames[len(frames)//2] if frames else None
        thumbnail_base64 = None
        if thumbnail_path and thumbnail_path.exists():
            with open(thumbnail_path, "rb") as f:
                thumbnail_base64 = base64.b64encode(f.read()).decode('utf-8')
        
        # Save video to local storage
        original_filename = video_file.filename
        file_extension = Path(original_filename).suffix or '.mp4'
        stored_filename = f"{job_id}{file_extension}"
        stored_video_path = VIDEOS_DIR / stored_filename
        shutil.copy2(video_path, stored_video_path)
        
        app.logger.info(f"Job {job_id}: Video saved to: {stored_video_path}")
        
        # Store in index
        video_entry = {
            "id": job_id,
            "title": video_title,
            "description": video_description,
            "original_filename": original_filename,
            "stored_filename": stored_filename,
            "file_path": _relative_video_path(stored_filename),
            "transcript": transcript,
            "labels": unique_labels[:50],
            "text_detected": unique_text[:20],
            "emotions": unique_emotions,
            "embedding": embedding,
            "thumbnail": thumbnail_base64,
            "metadata_text": metadata_text,
            "uploaded_at": datetime.utcnow().isoformat()
        }
        
        VIDEO_INDEX.append(video_entry)
        
        # Save index to disk
        _save_video_index()
        
        app.logger.info(f"Job {job_id}: Video indexed successfully")
        
        return jsonify({
            "id": job_id,
            "title": video_title,
            "message": "Video uploaded and indexed successfully",
            "labels_count": len(unique_labels),
            "transcript_length": len(transcript),
            "frame_count": len(frames)
        }), 200
        
    except Exception as e:
        app.logger.error(f"Job {job_id}: Error processing video: {str(e)}")
        import traceback
        app.logger.error(traceback.format_exc())
        return jsonify({"error": f"Failed to process video: {str(e)}"}), 500
    
    finally:
        try:
            shutil.rmtree(temp_dir, ignore_errors=True)
        except:
            pass


@app.route("/search", methods=["POST"])
def search_videos() -> Any:
    """Search videos using semantic similarity."""
    payload = request.get_json(silent=True) or {}
    query = payload.get("query", "").strip()
    top_k = int(payload.get("top_k", 5))
    min_similarity = payload.get("min_similarity")
    if min_similarity is None:
        min_similarity = os.getenv("SEMANTIC_VIDEO_MIN_SIMILARITY", "0.51")
    try:
        min_similarity_value = float(min_similarity)
    except (TypeError, ValueError):
        return jsonify({"error": "min_similarity must be a number"}), 400
    
    if not query:
        return jsonify({"error": "Query is required"}), 400
    
    if not VIDEO_INDEX:
        return jsonify({"error": "No videos indexed yet. Please upload videos first."}), 400
    
    try:
        # Generate query embedding
        app.logger.info(f"Searching for: {query}")
        query_embedding = _generate_embedding(query)
        
        if not query_embedding:
            return jsonify({"error": "Failed to generate query embedding"}), 500
        
        # Compute similarities
        all_results = []
        for video in VIDEO_INDEX:
            if not video.get("embedding"):
                continue
            
            similarity = _compute_similarity(query_embedding, video["embedding"])
            
            all_results.append({
                "id": video["id"],
                "video_id": video["id"],
                "title": video["title"],
                "description": video["description"],
                "transcript_snippet": video["transcript"][:200] if video["transcript"] else "",
                "labels": video["labels"][:10],
                "matched_labels": video["labels"][:10],
                "emotions": video["emotions"],
                "thumbnail": _as_data_uri_jpeg(video.get("thumbnail")),
                "similarity_score": round(similarity, 4),
                "uploaded_at": video["uploaded_at"]
            })
        
        # Sort by similarity
        all_results.sort(key=lambda x: x["similarity_score"], reverse=True)
        
        # Filter results with minimum similarity threshold (configurable).
        results = [r for r in all_results if r["similarity_score"] >= min_similarity_value]
        
        # Log for debugging
        app.logger.info(f"Query: {query}")
        app.logger.info(f"Top scores: {[r['similarity_score'] for r in all_results[:5]]}")
        app.logger.info(
            f"Results after min_similarity={min_similarity_value:.2f} filter: {len(results)}/{len(all_results)}"
        )
        
        return jsonify({
            "query": query,
            "results": results[:top_k],
            "total_videos": len(VIDEO_INDEX)
        }), 200
        
    except Exception as e:
        app.logger.error(f"Search failed: {str(e)}")
        import traceback
        app.logger.error(traceback.format_exc())
        return jsonify({"error": f"Search failed: {str(e)}"}), 500


@app.route("/videos", methods=["GET"])
def list_videos() -> Any:
    """List all indexed videos."""
    videos = [
        {
            "id": v["id"],
            "title": v["title"],
            "description": v["description"],
            "labels_count": len(v["labels"]),
            "has_transcript": bool(v["transcript"]),
            "uploaded_at": v["uploaded_at"],
            "thumbnail": v["thumbnail"]
        }
        for v in VIDEO_INDEX
    ]
    
    return jsonify({
        "videos": videos,
        "total": len(videos)
    }), 200


@app.route("/video/<video_id>", methods=["GET"])
def get_video_details(video_id: str) -> Any:
    """Get details of a specific video."""
    video = next((v for v in VIDEO_INDEX if v["id"] == video_id), None)
    
    if not video:
        return jsonify({"error": "Video not found"}), 404
    
    return jsonify({
        "id": video["id"],
        "title": video["title"],
        "description": video["description"],
        "transcript": video["transcript"],
        "labels": video["labels"],
        "text_detected": video["text_detected"],
        "emotions": video["emotions"],
        "thumbnail": video["thumbnail"],
        "uploaded_at": video["uploaded_at"]
    }), 200


@app.route("/video/<video_id>", methods=["DELETE"])
def delete_video(video_id: str) -> Any:
    """Delete a video and its associated files."""
    global VIDEO_INDEX
    
    # Find the video
    video = next((v for v in VIDEO_INDEX if v["id"] == video_id), None)
    
    if not video:
        return jsonify({"error": "Video not found"}), 404
    
    try:
        # Delete the video file from storage
        stored_filename = video.get("stored_filename")
        video_path = _absolute_video_path(stored_filename) if stored_filename else None

        if video_path and video_path.exists():
            video_path.unlink()
            print(f"Deleted video file: {video_path}")
        else:
            legacy_path_value = video.get("file_path")
            if legacy_path_value:
                legacy_path = Path(legacy_path_value)
                if legacy_path.exists():
                    legacy_path.unlink()
                    print(f"Deleted legacy video file: {legacy_path}")
        
        # Remove from index
        VIDEO_INDEX = [v for v in VIDEO_INDEX if v["id"] != video_id]
        
        # Save updated index
        _save_video_index()
        
        print(f"Video {video_id} deleted successfully")
        
        return jsonify({
            "status": "success",
            "message": f"Video '{video['title']}' deleted successfully",
            "video_id": video_id
        }), 200
        
    except Exception as e:
        print(f"Error deleting video {video_id}: {str(e)}")
        return jsonify({"error": f"Failed to delete video: {str(e)}"}), 500


@app.route("/reprocess-video/<video_id>", methods=["POST"])
def reprocess_video(video_id: str) -> Any:
    """Re-process an already-indexed video using the stored file on disk."""
    video = next((v for v in VIDEO_INDEX if v.get("id") == video_id), None)
    if not video:
        return jsonify({"error": "Video not found"}), 404

    stored_filename = video.get("stored_filename")
    if not stored_filename:
        return jsonify({"error": "Video is missing stored_filename; cannot reprocess"}), 400

    stored_path = _absolute_video_path(stored_filename)
    if not stored_path.exists():
        return jsonify({"error": f"Stored video file not found: {stored_filename}"}), 404

    try:
        updated_fields = _process_stored_video(
            video_id=video_id,
            stored_video_path=stored_path,
            video_title=video.get("title") or video_id,
            video_description=video.get("description") or "",
            original_filename=video.get("original_filename") or stored_filename,
        )
        video.update(updated_fields)
        _save_video_index()
        return jsonify({
            "message": "Video reprocessed successfully",
            "id": video_id,
            "labels_count": len(video.get("labels") or []),
            "has_transcript": bool(video.get("transcript")),
            "reprocessed_at": video.get("reprocessed_at"),
        }), 200
    except Exception as exc:
        app.logger.error("Reprocess failed for video %s: %s", video_id, exc)
        import traceback
        app.logger.error(traceback.format_exc())
        return jsonify({"error": f"Reprocess failed: {exc}"}), 500


@app.route("/reprocess-videos", methods=["POST"])
def reprocess_videos() -> Any:
    """Re-process all indexed videos (best-effort)."""
    payload = request.get_json(silent=True) or {}
    requested_ids = payload.get("video_ids")
    if requested_ids is not None and not isinstance(requested_ids, list):
        return jsonify({"error": "video_ids must be a list when provided"}), 400

    targets = VIDEO_INDEX
    if isinstance(requested_ids, list):
        requested_set = {str(v) for v in requested_ids}
        targets = [v for v in VIDEO_INDEX if str(v.get("id")) in requested_set]

    results: List[Dict[str, Any]] = []
    for video in targets:
        vid = str(video.get("id"))
        stored_filename = video.get("stored_filename")
        stored_path = _absolute_video_path(stored_filename) if stored_filename else None

        if not stored_filename or not stored_path or not stored_path.exists():
            results.append({"id": vid, "status": "skipped", "reason": "missing stored file"})
            continue

        try:
            updated_fields = _process_stored_video(
                video_id=vid,
                stored_video_path=stored_path,
                video_title=video.get("title") or vid,
                video_description=video.get("description") or "",
                original_filename=video.get("original_filename") or stored_filename,
            )
            video.update(updated_fields)
            results.append({"id": vid, "status": "ok", "reprocessed_at": video.get("reprocessed_at")})
        except Exception as exc:
            app.logger.error("Reprocess failed for video %s: %s", vid, exc)
            results.append({"id": vid, "status": "error", "error": str(exc)})

    _save_video_index()
    ok_count = sum(1 for r in results if r.get("status") == "ok")
    return jsonify({"message": "Reprocess complete", "total": len(results), "ok": ok_count, "results": results}), 200


def _extract_text_from_file(file_content: bytes, filename: str) -> str:
    """Extract text from different file formats."""
    file_extension = Path(filename).suffix.lower()
    
    try:
        if file_extension == '.pdf':
            # Extract text from PDF
            pdf_reader = PdfReader(io.BytesIO(file_content))
            text_parts = []
            for page in pdf_reader.pages:
                text = page.extract_text()
                if text:
                    text_parts.append(text)
            return '\n\n'.join(text_parts)
        
        elif file_extension in ['.docx', '.doc']:
            # Extract text from DOCX
            doc = DocxDocument(io.BytesIO(file_content))
            text_parts = []
            for paragraph in doc.paragraphs:
                if paragraph.text.strip():
                    text_parts.append(paragraph.text)
            return '\n\n'.join(text_parts)
        
        elif file_extension == '.txt':
            # Plain text file
            return file_content.decode('utf-8', errors='ignore')
        
        else:
            # Try decoding as text for unknown file types
            return file_content.decode('utf-8', errors='ignore')
    
    except Exception as e:
        app.logger.error(f"Error extracting text from {filename}: {str(e)}")
        # Fallback: try to decode as text
        try:
            return file_content.decode('utf-8', errors='ignore')
        except:
            return ""


@app.route("/upload-document", methods=["POST"])
def upload_document() -> Any:
    """Upload and index a document for semantic search and Q&A."""
    if "document" not in request.files:
        return jsonify({"error": "No document file provided"}), 400
    
    doc_file = request.files["document"]
    if not doc_file.filename:
        return jsonify({"error": "Empty filename"}), 400
    
    doc_title = request.form.get("title", doc_file.filename)
    doc_id = str(uuid.uuid4())
    
    try:
        # Read document file content
        file_content = doc_file.read()
        original_filename = doc_file.filename
        
        # Extract text based on file type
        content = _extract_text_from_file(file_content, original_filename)
        
        if not content or len(content.strip()) < 10:
            return jsonify({"error": "Could not extract text from document or document is too short"}), 400
        
        # Save document to local storage
        original_filename = doc_file.filename
        file_extension = Path(original_filename).suffix or '.txt'
        stored_filename = f"{doc_id}{file_extension}"
        doc_file_path = DOCUMENTS_DIR / stored_filename
        
        with open(doc_file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        app.logger.info(f"Document saved to: {doc_file_path}")
        
        # Split into chunks (simple chunking by paragraphs)
        chunks = [chunk.strip() for chunk in content.split('\n\n') if chunk.strip()]
        
        if not chunks:
            chunks = [content[:1000]]  # Fallback: first 1000 chars
        
        # Generate embeddings for each chunk
        chunk_embeddings = []
        for chunk in chunks:
            embedding = _generate_embedding(chunk)
            if embedding:
                chunk_embeddings.append({
                    "text": chunk,
                    "embedding": embedding
                })
        
        # Create document entry
        doc_entry = {
            "id": doc_id,
            "title": doc_title,
            "original_filename": original_filename,
            "stored_filename": stored_filename,
            "file_path": _relative_document_path(stored_filename),
            "chunks": chunk_embeddings,
            "chunks_count": len(chunk_embeddings),
            "full_text": content,
            "uploaded_at": datetime.utcnow().isoformat()
        }
        
        DOCUMENT_INDEX.append(doc_entry)
        
        # Save index to disk
        _save_document_index()
        
        app.logger.info(f"Document {doc_id} indexed successfully with {len(chunk_embeddings)} chunks")
        
        return jsonify({
            "id": doc_id,
            "title": doc_title,
            "message": "Document uploaded and indexed successfully",
            "chunks_count": len(chunk_embeddings)
        }), 200
        
    except Exception as e:
        app.logger.error(f"Error processing document: {str(e)}")
        import traceback
        app.logger.error(traceback.format_exc())
        return jsonify({"error": f"Failed to process document: {str(e)}"}), 500


@app.route("/documents", methods=["GET"])
def list_documents() -> Any:
    """List all indexed documents."""
    documents = [
        {
            "id": d["id"],
            "title": d["title"],
            "chunks_count": d["chunks_count"],
            "uploaded_at": d["uploaded_at"]
        }
        for d in DOCUMENT_INDEX
    ]
    
    return jsonify({
        "documents": documents,
        "total": len(documents)
    }), 200


@app.route("/documents/<document_id>", methods=["DELETE"])
def delete_document(document_id: str) -> Any:
    """Delete a document and all its chunks."""
    global DOCUMENT_INDEX
    
    # Find document index
    doc_idx = None
    for idx, doc in enumerate(DOCUMENT_INDEX):
        if doc["id"] == document_id:
            doc_idx = idx
            break
    
    if doc_idx is None:
        return jsonify({"error": "Document not found"}), 404
    
    # Remove document from index
    deleted_doc = DOCUMENT_INDEX.pop(doc_idx)
    
    # Delete stored document file
    stored_filename = deleted_doc.get("stored_filename")
    doc_path = _absolute_document_path(stored_filename) if stored_filename else None
    if doc_path and doc_path.exists():
        doc_path.unlink()
        app.logger.info(f"Deleted document file: {doc_path}")
    else:
        legacy_path_value = deleted_doc.get("file_path")
        if legacy_path_value:
            legacy_path = Path(legacy_path_value)
            if legacy_path.exists():
                legacy_path.unlink()
                app.logger.info(f"Deleted legacy document file: {legacy_path}")
    
    app.logger.info(f"Deleted document: {deleted_doc['title']} (ID: {document_id})")
    
    return jsonify({
        "message": "Document deleted successfully",
        "deleted_document": {
            "id": deleted_doc["id"],
            "title": deleted_doc["title"]
        }
    }), 200


@app.route("/search-text", methods=["POST"])
def search_text() -> Any:
    """Search documents using text/semantic similarity."""
    payload = request.get_json(silent=True) or {}
    query = payload.get("query", "").strip()
    top_k = int(payload.get("top_k", 5))
    
    if not query:
        return jsonify({"error": "Query is required"}), 400
    
    if not DOCUMENT_INDEX:
        return jsonify({"error": "No documents indexed yet"}), 400
    
    try:
        # Generate query embedding
        query_embedding = _generate_embedding(query)
        
        if not query_embedding:
            return jsonify({"error": "Failed to generate query embedding"}), 500
        
        # Search across all chunks in all documents
        results = []
        for doc in DOCUMENT_INDEX:
            for chunk in doc["chunks"]:
                similarity = _compute_similarity(query_embedding, chunk["embedding"])
                results.append({
                    "document_id": doc["id"],
                    "document_title": doc["title"],
                    "text": chunk["text"],
                    "similarity_score": round(similarity, 4)
                })
        
        # Sort by similarity
        results.sort(key=lambda x: x["similarity_score"], reverse=True)
        
        return jsonify({
            "query": query,
            "results": results[:top_k]
        }), 200
        
    except Exception as e:
        app.logger.error(f"Text search failed: {str(e)}")
        import traceback
        app.logger.error(traceback.format_exc())
        return jsonify({"error": f"Search failed: {str(e)}"}), 500


@app.route("/ask-question", methods=["POST"])
def ask_question() -> Any:
    """Ask a question about a document using Meta Llama via Bedrock."""
    payload = request.get_json(silent=True) or {}
    document_id = payload.get("document_id", "").strip()
    question = payload.get("question", "").strip()
    
    if not document_id or not question:
        return jsonify({"error": "Both document_id and question are required"}), 400
    
    # Find the document
    doc = next((d for d in DOCUMENT_INDEX if d["id"] == document_id), None)
    if not doc:
        return jsonify({"error": "Document not found"}), 404
    
    try:
        # Generate query embedding
        query_embedding = _generate_embedding(question)
        
        # Find most relevant chunks
        chunk_scores = []
        for chunk in doc["chunks"]:
            similarity = _compute_similarity(query_embedding, chunk["embedding"])
            chunk_scores.append((chunk["text"], similarity))
        
        # Sort and get top 3 chunks
        chunk_scores.sort(key=lambda x: x[1], reverse=True)
        relevant_chunks = [chunk[0] for chunk in chunk_scores[:3]]
        
        # Build prompt for Llama
        context = "\n\n".join(relevant_chunks)
        prompt = f"""Based on the following context from the document, please answer the question.

Context:
{context}

Question: {question}

Answer:"""
        
        # Call Bedrock with Meta Llama
        response = bedrock_runtime.invoke_model(
            modelId="meta.llama3-70b-instruct-v1:0",
            contentType="application/json",
            accept="application/json",
            body=json.dumps({
                "prompt": prompt,
                "max_gen_len": 512,
                "temperature": 0.7,
                "top_p": 0.9
            })
        )
        
        response_body = json.loads(response["body"].read())
        answer = response_body.get("generation", "").strip()
        
        return jsonify({
            "question": question,
            "answer": answer,
            "context": relevant_chunks,
            "document_title": doc["title"]
        }), 200
        
    except Exception as e:
        app.logger.error(f"Q&A failed: {str(e)}")
        import traceback
        app.logger.error(traceback.format_exc())
        return jsonify({"error": f"Question answering failed: {str(e)}"}), 500


@app.route("/askme", methods=["POST"])
def askme_chatbot():
    """
    AskMe chatbot endpoint - answers questions about MediaGenAI use cases and documentation.
    This endpoint reads from documentation files and uses Bedrock Llama to provide answers.
    """
    try:
        data = request.get_json()
        question = data.get("question", "").strip()
        
        if not question:
            return jsonify({"error": "Question is required"}), 400
        
        # Load documentation content
        docs_dir = Path(__file__).parent.parent / "Documentation"
        readme_file = Path(__file__).parent.parent / "SERVICES_README.md"
        
        context_docs = []
        
        # Read SERVICES_README.md
        if readme_file.exists():
            try:
                with open(readme_file, 'r', encoding='utf-8') as f:
                    context_docs.append({
                        "filename": "SERVICES_README.md",
                        "content": f.read()
                    })
            except Exception as e:
                print(f"Error reading SERVICES_README.md: {e}")
        
        # Read documentation files
        if docs_dir.exists():
            for doc_file in docs_dir.glob("*.md"):
                try:
                    with open(doc_file, 'r', encoding='utf-8') as f:
                        context_docs.append({
                            "filename": doc_file.name,
                            "content": f.read()
                        })
                except Exception as e:
                    print(f"Error reading {doc_file}: {e}")
        
        if not context_docs:
            return jsonify({
                "error": "No documentation available"
            }), 500
        
        # Build context from documentation
        context_text = "\n\n---\n\n".join([
            f"Document: {doc['filename']}\n\n{doc['content'][:3000]}"  # Limit each doc to 3000 chars
            for doc in context_docs[:5]  # Use top 5 documents
        ])
        
        # Create prompt for Llama
        prompt = f"""You are AskMe, a helpful chatbot assistant for MediaGenAI platform. You help users understand the various AI-powered media generation use cases available in the platform.

Documentation Context:
{context_text}

User Question: {question}

Provide a helpful, accurate, and concise answer based on the documentation above. If the question is about a specific use case or feature, explain what it does and how it works. If you're not sure about something, say so.

Answer:"""
        
        # Call Bedrock Llama
        response = bedrock_runtime.invoke_model(
            modelId="meta.llama3-70b-instruct-v1:0",
            contentType="application/json",
            accept="application/json",
            body=json.dumps({
                "prompt": prompt,
                "max_gen_len": 512,
                "temperature": 0.7,
                "top_p": 0.9
            })
        )
        
        response_body = json.loads(response["body"].read())
        answer = response_body.get("generation", "").strip()
        
        return jsonify({
            "question": question,
            "answer": answer,
            "sources": [doc["filename"] for doc in context_docs[:5]]
        }), 200
        
    except Exception as e:
        app.logger.error(f"AskMe chatbot failed: {str(e)}")
        import traceback
        app.logger.error(traceback.format_exc())
        return jsonify({"error": f"Chatbot request failed: {str(e)}"}), 500


if __name__ == "__main__":
    _load_video_index()
    _load_document_index()
    app.run(host="0.0.0.0", port=5008, debug=True)
