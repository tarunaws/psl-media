from __future__ import annotations

import os
import json
import base64
import tempfile
import shutil
import subprocess
import threading
from pathlib import Path
from typing import Any, Dict, List, Tuple, Optional
from datetime import datetime
import uuid
import io
import re
import mimetypes
from PIL import Image

try:
    import numpy as np  # type: ignore
except Exception:  # pragma: no cover
    np = None  # type: ignore

from flask import Flask, jsonify, request, send_file
from werkzeug.exceptions import RequestEntityTooLarge
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

def _max_upload_bytes() -> int | None:
    """Return max upload bytes for Flask/werkzeug.

    Default is generous for local dev demos. Set `METADATA_MAX_UPLOAD_GB` (or
    `METADATA_MAX_UPLOAD_BYTES`) to tune.
    """

    raw_bytes = os.getenv("METADATA_MAX_UPLOAD_BYTES")
    if raw_bytes:
        try:
            v = int(raw_bytes)
            return v if v > 0 else None
        except ValueError:
            pass

    raw_gb = os.getenv("METADATA_MAX_UPLOAD_GB", "25")
    try:
        gb = float(raw_gb)
    except ValueError:
        gb = 25.0
    if gb <= 0:
        return None
    return int(gb * 1024 * 1024 * 1024)


# Configure for large file uploads (local dev). Set to None for unlimited.
app.config["MAX_CONTENT_LENGTH"] = _max_upload_bytes()
app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0


@app.errorhandler(RequestEntityTooLarge)
def _handle_request_too_large(_: RequestEntityTooLarge) -> Any:
    limit = app.config.get("MAX_CONTENT_LENGTH")
    if isinstance(limit, int) and limit > 0:
        limit_gb = limit / (1024 * 1024 * 1024)
        return jsonify({"error": f"Upload too large. Max allowed is {limit_gb:.1f} GB."}), 413
    return jsonify({"error": "Upload too large."}), 413


JOBS_LOCK = threading.Lock()
JOBS: Dict[str, Dict[str, Any]] = {}


def _job_update(job_id: str, **updates: Any) -> None:
    with JOBS_LOCK:
        job = JOBS.get(job_id)
        if not job:
            return
        job.update(updates)
        job["updated_at"] = datetime.utcnow().isoformat()


def _job_init(job_id: str, *, title: str) -> None:
    with JOBS_LOCK:
        JOBS[job_id] = {
            "id": job_id,
            "title": title,
            "status": "queued",  # queued | processing | completed | failed
            "progress": 0,
            "message": "Queued",
            "error": None,
            "result": None,
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat(),
        }


def _process_video_job(
    *,
    job_id: str,
    temp_dir: Path,
    video_path: Path,
    video_title: str,
    video_description: str,
    original_filename: str,
    frame_interval_seconds: int,
    max_frames_to_analyze: int,
    face_recognition_mode: Optional[str],
    collection_id: Optional[str],
) -> None:
    try:
        _job_update(job_id, status="processing", progress=3, message="Extracting frames")

        frames_dir = temp_dir / "frames"
        frames_dir.mkdir(exist_ok=True)
        frames = _extract_video_frames(video_path, frames_dir, interval=frame_interval_seconds)
        duration_seconds = _probe_video_duration_seconds(video_path)

        _job_update(
            job_id,
            progress=15,
            message=f"Analyzing frames ({min(len(frames), max_frames_to_analyze)} of {len(frames)})",
        )

        all_emotions: List[str] = []
        label_stats: Dict[str, Dict[str, float]] = {}
        text_stats: Dict[str, int] = {}
        celeb_stats: Dict[str, float] = {}
        moderation_stats: Dict[str, float] = {}
        gender_counts: Dict[str, int] = {}
        age_ranges: List[Tuple[int, int]] = []
        frames_metadata: List[Dict[str, Any]] = []

        frames_to_process = frames[:max_frames_to_analyze]
        total = max(1, len(frames_to_process))
        for i, frame in enumerate(frames_to_process):
            analysis = _analyze_frame_with_rekognition(
                frame,
                collection_id=collection_id if (face_recognition_mode == "aws_collection") else None,
                local_face_mode=bool(face_recognition_mode == "local"),
            )
            timestamp = _frame_timestamp_seconds(frame)

            for label in analysis.get("labels", []):
                name = (label.get("name") or "").strip()
                if not name:
                    continue
                confidence = float(label.get("confidence") or 0.0)
                stat = label_stats.setdefault(name, {"count": 0.0, "max": 0.0, "sum": 0.0})
                stat["count"] += 1.0
                stat["sum"] += confidence
                stat["max"] = max(stat["max"], confidence)

            for txt in analysis.get("text", []):
                value = (txt.get("text") or "").strip()
                if not value:
                    continue
                if txt.get("type") != "LINE":
                    continue
                text_stats[value] = text_stats.get(value, 0) + 1

            for face in analysis.get("faces", []):
                for e in (face.get("emotions") or []):
                    et = (e.get("type") or "").strip()
                    if et:
                        all_emotions.append(et)
                gender = (face.get("gender") or "").strip()
                if gender:
                    gender_counts[gender] = gender_counts.get(gender, 0) + 1
                age = face.get("age_range") or {}
                try:
                    low = int(age.get("Low"))
                    high = int(age.get("High"))
                    age_ranges.append((low, high))
                except Exception:
                    pass

            for c in (analysis.get("celebrities") or []):
                name = (c.get("name") or "").strip()
                if not name:
                    continue
                try:
                    conf = float(c.get("confidence") or 0.0)
                except (TypeError, ValueError):
                    conf = 0.0
                celeb_stats[name] = max(celeb_stats.get(name, 0.0), conf)

            for m in (analysis.get("moderation") or []):
                name = (m.get("name") or "").strip()
                if not name:
                    continue
                try:
                    conf = float(m.get("confidence") or 0.0)
                except (TypeError, ValueError):
                    conf = 0.0
                moderation_stats[name] = max(moderation_stats.get(name, 0.0), conf)

            frames_metadata.append(
                {
                    "timestamp": timestamp,
                    "labels": (analysis.get("labels") or [])[:12],
                    "text": [t for t in (analysis.get("text") or []) if t.get("type") == "LINE"][:12],
                    "faces": (analysis.get("faces") or [])[:12],
                    "celebrities": (analysis.get("celebrities") or [])[:12],
                    "moderation": (analysis.get("moderation") or [])[:12],
                    "custom_faces": (analysis.get("custom_faces") or [])[:12],
                    "local_faces": (analysis.get("local_faces") or [])[:12],
                }
            )

            if i % 3 == 0 or i == total - 1:
                pct = 15 + int(((i + 1) / total) * 45)
                _job_update(job_id, progress=pct, message=f"Analyzing frames ({i + 1}/{total})")

        emotions_unique = sorted(list(set(all_emotions)))
        labels_ranked = sorted(
            (
                (
                    name,
                    int(stats.get("count", 0.0) or 0),
                    float(stats.get("max", 0.0) or 0.0),
                    float(stats.get("sum", 0.0) or 0.0) / max(1.0, float(stats.get("count", 0.0) or 1.0)),
                )
                for name, stats in label_stats.items()
            ),
            key=lambda row: (row[1], row[2], row[0]),
            reverse=True,
        )
        labels_detailed = [
            {
                "name": name,
                "occurrences": count,
                "max_confidence": max_conf,
                "avg_confidence": avg_conf,
            }
            for (name, count, max_conf, avg_conf) in labels_ranked[:50]
        ]
        text_detailed = [
            {"text": text, "occurrences": count}
            for text, count in sorted(text_stats.items(), key=lambda kv: (kv[1], kv[0]), reverse=True)[:50]
        ]
        celebs_detailed = [
            {"name": name, "max_confidence": conf}
            for name, conf in sorted(celeb_stats.items(), key=lambda kv: (kv[1], kv[0]), reverse=True)[:50]
        ]
        moderation_detailed = [
            {"name": name, "max_confidence": conf}
            for name, conf in sorted(moderation_stats.items(), key=lambda kv: (kv[1], kv[0]), reverse=True)[:50]
        ]

        _job_update(job_id, progress=65, message="Transcribing audio")
        transcribe_rich = _extract_audio_and_transcribe_rich(video_path, temp_dir, job_id)
        transcript = transcribe_rich.get("text") or ""
        transcript_words = transcribe_rich.get("words") or []
        transcript_segments = transcribe_rich.get("segments") or []
        transcript_language_code = (transcribe_rich.get("language_code") or "").strip() or None
        languages_detected = _detect_dominant_languages_from_text(transcript)

        _job_update(job_id, progress=78, message="Generating embedding")
        metadata_parts = [video_title, video_description]
        if transcript:
            metadata_parts.append(f"Transcript: {transcript}")
        if labels_detailed:
            metadata_parts.append("Visual elements: " + ", ".join([l["name"] for l in labels_detailed[:50] if l.get("name")]))
        if text_detailed:
            metadata_parts.append("Text in video: " + ", ".join([t["text"] for t in text_detailed[:20] if t.get("text")]))
        if emotions_unique:
            metadata_parts.append(f"Emotions detected: {', '.join(emotions_unique)}")
        if celebs_detailed:
            metadata_parts.append("Celebrities detected: " + ", ".join([c["name"] for c in celebs_detailed[:25] if c.get("name")]))
        if moderation_detailed:
            metadata_parts.append("Moderation labels: " + ", ".join([m["name"] for m in moderation_detailed[:30] if m.get("name")]))

        metadata_text = " ".join(metadata_parts)
        embedding = _generate_embedding(metadata_text)

        _job_update(job_id, progress=88, message="Saving & indexing")
        thumbnail_path = frames[len(frames) // 2] if frames else None
        thumbnail_base64 = None
        if thumbnail_path and thumbnail_path.exists():
            with open(thumbnail_path, "rb") as f:
                thumbnail_base64 = base64.b64encode(f.read()).decode("utf-8")

        file_extension = Path(original_filename).suffix or ".mp4"
        stored_filename = f"{job_id}{file_extension}"
        stored_video_path = VIDEOS_DIR / stored_filename
        shutil.copy2(video_path, stored_video_path)

        video_entry = {
            "id": job_id,
            "title": video_title,
            "description": video_description,
            "original_filename": original_filename,
            "stored_filename": stored_filename,
            "file_path": _relative_video_path(stored_filename),
            "transcript": transcript,
            "language_code": transcript_language_code,
            "languages_detected": languages_detected,
            "transcript_words": transcript_words,
            "transcript_segments": transcript_segments,
            "labels": [l["name"] for l in labels_detailed if l.get("name")][:50],
            "labels_detailed": labels_detailed,
            "text_detected": [t["text"] for t in text_detailed if t.get("text")][:20],
            "text_detailed": text_detailed,
            "emotions": emotions_unique,
            "celebrities": [c["name"] for c in celebs_detailed if c.get("name")][:50],
            "celebrities_detailed": celebs_detailed,
            "moderation_labels": [m["name"] for m in moderation_detailed if m.get("name")][:50],
            "moderation_detailed": moderation_detailed,
            "faces_summary": {
                "count": sum(gender_counts.values()),
                "genders": gender_counts,
                "age_ranges": age_ranges[:200],
            },
            "embedding": embedding,
            "thumbnail": thumbnail_base64,
            "metadata_text": metadata_text,
            "frame_count": len(frames),
            "frames_analyzed": len(frames_metadata),
            "frame_interval_seconds": frame_interval_seconds,
            "duration_seconds": duration_seconds,
            "frames": frames_metadata,
            "uploaded_at": datetime.utcnow().isoformat(),
        }

        VIDEO_INDEX.append(video_entry)
        _save_video_index()

        result = {
            "id": job_id,
            "title": video_title,
            "message": "Video uploaded and indexed successfully",
            "labels_count": len(label_stats),
            "celebrities_count": len(celeb_stats),
            "transcript_length": len(transcript),
            "frame_count": len(frames),
            "language_code": transcript_language_code,
        }
        _job_update(job_id, status="completed", progress=100, message="Completed", result=result)
    except Exception as exc:
        app.logger.error("Job %s failed: %s", job_id, exc)
        import traceback

        app.logger.error(traceback.format_exc())
        _job_update(job_id, status="failed", message="Failed", error=str(exc))
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)

DEFAULT_AWS_REGION = os.environ.get("AWS_REGION")
if not DEFAULT_AWS_REGION:
    raise RuntimeError("Set AWS_REGION before starting semantic search service")

# AWS clients
rekognition = boto3.client("rekognition", region_name=DEFAULT_AWS_REGION)
transcribe = boto3.client("transcribe", region_name=DEFAULT_AWS_REGION)
comprehend = boto3.client("comprehend", region_name=DEFAULT_AWS_REGION)
bedrock_runtime = boto3.client("bedrock-runtime", region_name=DEFAULT_AWS_REGION)
s3 = boto3.client("s3", region_name=DEFAULT_AWS_REGION)


LOCAL_FACE_GALLERY_FILE: Path | None = None
_INSIGHTFACE_ANALYZER = None


def _safe_json_load(path: Path, default_value: Any) -> Any:
    try:
        if not path.exists():
            return default_value
        with open(path, "r") as f:
            return json.load(f)
    except Exception:
        return default_value


def _safe_json_save(path: Path, value: Any) -> None:
    tmp_path = path.with_suffix(path.suffix + ".tmp")
    with open(tmp_path, "w") as f:
        json.dump(value, f, indent=2, default=str)
    os.replace(tmp_path, path)


def _rekognition_collection_id_normalize(raw: str | None) -> str:
    return (raw or "").strip()


def _rekognition_external_image_id_normalize(raw: str | None) -> str:
    # ExternalImageId: keep simple (avoid very long ids); Rekognition accepts Unicode,
    # but we keep it compact for UI display.
    value = (raw or "").strip()
    value = re.sub(r"\s+", " ", value)
    return value[:128]


def _pil_crop_bbox_to_jpeg_bytes(image_bytes: bytes, bbox: Dict[str, Any] | None, *, min_size_px: int = 40) -> bytes | None:
    if not bbox:
        return None
    try:
        left = float(bbox.get("Left", 0.0) or 0.0)
        top = float(bbox.get("Top", 0.0) or 0.0)
        width = float(bbox.get("Width", 0.0) or 0.0)
        height = float(bbox.get("Height", 0.0) or 0.0)
    except (TypeError, ValueError):
        return None
    if width <= 0.0 or height <= 0.0:
        return None

    try:
        with Image.open(io.BytesIO(image_bytes)) as img:
            img = img.convert("RGB")
            w, h = img.size
            x1 = max(0, min(w - 1, int(left * w)))
            y1 = max(0, min(h - 1, int(top * h)))
            x2 = max(0, min(w, int((left + width) * w)))
            y2 = max(0, min(h, int((top + height) * h)))
            if x2 <= x1 or y2 <= y1:
                return None
            if (x2 - x1) < min_size_px or (y2 - y1) < min_size_px:
                return None

            crop = img.crop((x1, y1, x2, y2))
            out = io.BytesIO()
            crop.save(out, format="JPEG", quality=85)
            return out.getvalue()
    except Exception:
        return None


def _pil_crop_bbox_thumbnail_base64(image_bytes: bytes, bbox: Dict[str, Any] | None, *, size_px: int = 96) -> str | None:
    if not bbox:
        return None
    try:
        left = float(bbox.get("Left", 0.0) or 0.0)
        top = float(bbox.get("Top", 0.0) or 0.0)
        width = float(bbox.get("Width", 0.0) or 0.0)
        height = float(bbox.get("Height", 0.0) or 0.0)
    except (TypeError, ValueError):
        return None
    if width <= 0.0 or height <= 0.0:
        return None

    try:
        with Image.open(io.BytesIO(image_bytes)) as img:
            img = img.convert("RGB")
            w, h = img.size
            x1 = max(0, min(w - 1, int(left * w)))
            y1 = max(0, min(h - 1, int(top * h)))
            x2 = max(0, min(w, int((left + width) * w)))
            y2 = max(0, min(h, int((top + height) * h)))
            if x2 <= x1 or y2 <= y1:
                return None

            crop = img.crop((x1, y1, x2, y2))
            crop.thumbnail((size_px, size_px))
            out = io.BytesIO()
            crop.save(out, format="JPEG", quality=80)
            return base64.b64encode(out.getvalue()).decode("utf-8")
    except Exception:
        return None


def _insightface_available() -> tuple[bool, str | None]:
    if np is None:
        return False, "numpy not available"
    try:
        import insightface  # type: ignore
        from insightface.app import FaceAnalysis  # noqa: F401
    except Exception as exc:
        return False, f"insightface not installed ({exc})"
    return True, None


def _get_insightface_analyzer():
    global _INSIGHTFACE_ANALYZER
    if _INSIGHTFACE_ANALYZER is not None:
        return _INSIGHTFACE_ANALYZER

    ok, reason = _insightface_available()
    if not ok:
        raise RuntimeError(reason or "insightface not available")

    from insightface.app import FaceAnalysis  # type: ignore

    analyzer = FaceAnalysis(name=os.environ.get("INSIGHTFACE_MODEL", "buffalo_l"))
    analyzer.prepare(ctx_id=0, det_size=(640, 640))
    _INSIGHTFACE_ANALYZER = analyzer
    return analyzer


def _local_gallery_load() -> Dict[str, Any]:
    if not isinstance(LOCAL_FACE_GALLERY_FILE, Path):
        return {"version": 1, "actors": {}}
    gallery = _safe_json_load(LOCAL_FACE_GALLERY_FILE, default_value={"version": 1, "actors": {}})
    if not isinstance(gallery, dict):
        return {"version": 1, "actors": {}}
    if "actors" not in gallery or not isinstance(gallery.get("actors"), dict):
        gallery["actors"] = {}
    if "version" not in gallery:
        gallery["version"] = 1
    return gallery


def _local_gallery_save(gallery: Dict[str, Any]) -> None:
    if not isinstance(LOCAL_FACE_GALLERY_FILE, Path):
        raise RuntimeError("Local face gallery path is not configured")
    LOCAL_FACE_GALLERY_FILE.parent.mkdir(exist_ok=True)
    _safe_json_save(LOCAL_FACE_GALLERY_FILE, gallery)


def _cosine_similarity(a: "np.ndarray", b: "np.ndarray") -> float:
    # Normalize defensively
    denom = float(np.linalg.norm(a) * np.linalg.norm(b))  # type: ignore
    if denom <= 0:
        return -1.0
    return float(np.dot(a, b) / denom)  # type: ignore


def _local_match_embedding(embedding: "np.ndarray", gallery: Dict[str, Any], *, threshold: float) -> Dict[str, Any] | None:
    best = None
    best_score = float("-inf")
    actors = (gallery.get("actors") or {}) if isinstance(gallery, dict) else {}
    for actor_name, samples in actors.items():
        if not isinstance(samples, list):
            continue
        for sample in samples:
            vec = sample.get("embedding") if isinstance(sample, dict) else None
            if not isinstance(vec, list) or not vec:
                continue
            try:
                v = np.asarray(vec, dtype=np.float32)  # type: ignore
            except Exception:
                continue
            score = _cosine_similarity(embedding, v)
            if score > best_score:
                best_score = score
                best = {"name": str(actor_name), "similarity": score}

    if best is None:
        return None
    if best_score < float(threshold):
        return None
    return best

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

LOCAL_FACE_GALLERY_FILE = INDICES_DIR / "local_face_gallery.json"


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
        "service": "metadata",
        "region": DEFAULT_AWS_REGION
    })


@app.route("/rekognition-check", methods=["GET"])
def rekognition_check() -> Any:
    """Validate AWS Rekognition connectivity and permissions.

    This does not prove celebrity detection will happen for a given video; it only verifies
    that the AWS call to RecognizeCelebrities can be executed successfully.
    """

    def _call(fn_name: str, fn) -> Dict[str, Any]:
        try:
            resp = fn()
            return {
                "ok": True,
                "fn": fn_name,
                "status": "success",
                "summary": {
                    "keys": list(resp.keys()) if isinstance(resp, dict) else None,
                },
            }
        except (BotoCoreError, ClientError) as exc:
            return {
                "ok": False,
                "fn": fn_name,
                "status": "error",
                "error": str(exc),
            }
        except Exception as exc:  # pragma: no cover
            return {
                "ok": False,
                "fn": fn_name,
                "status": "error",
                "error": str(exc),
            }

    # Generate a small, valid JPEG in-memory so Rekognition accepts Image bytes.
    img = Image.new("RGB", (64, 64), color=(0, 0, 0))
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=80)
    image_bytes = buf.getvalue()

    checks: List[Dict[str, Any]] = []
    checks.append(
        _call(
            "recognize_celebrities",
            lambda: rekognition.recognize_celebrities(Image={"Bytes": image_bytes}),
        )
    )

    # Optional: also validate a basic Rekognition call, useful for diagnosing IAM.
    checks.append(
        _call(
            "detect_labels",
            lambda: rekognition.detect_labels(Image={"Bytes": image_bytes}, MaxLabels=5),
        )
    )

    ok = all(c.get("ok") for c in checks)
    return jsonify(
        {
            "ok": ok,
            "service": "rekognition",
            "region": DEFAULT_AWS_REGION,
            "checks": checks,
            "note": "This validates AWS calls; celebrity detection still depends on the video content.",
        }
    ), (200 if ok else 500)


@app.route("/face-collection/create", methods=["POST"])
def face_collection_create() -> Any:
    payload = request.get_json(silent=True) or {}
    collection_id = _rekognition_collection_id_normalize(payload.get("collection_id"))
    if not collection_id:
        return jsonify({"error": "collection_id is required"}), 400

    try:
        resp = rekognition.create_collection(CollectionId=collection_id)
        return jsonify({"ok": True, "collection_id": collection_id, "status": "created", "response": resp}), 200
    except rekognition.exceptions.ResourceAlreadyExistsException:
        return jsonify({"ok": True, "collection_id": collection_id, "status": "exists"}), 200
    except (BotoCoreError, ClientError) as exc:
        return jsonify({"ok": False, "error": str(exc)}), 500


@app.route("/face-collection/<collection_id>/faces", methods=["GET"])
def face_collection_list_faces(collection_id: str) -> Any:
    collection_id = _rekognition_collection_id_normalize(collection_id)
    if not collection_id:
        return jsonify({"error": "collection_id is required"}), 400

    faces: List[Dict[str, Any]] = []
    next_token = None
    try:
        while True:
            kwargs: Dict[str, Any] = {"CollectionId": collection_id, "MaxResults": 100}
            if next_token:
                kwargs["NextToken"] = next_token
            resp = rekognition.list_faces(**kwargs)
            for f in resp.get("Faces", []) or []:
                faces.append(
                    {
                        "face_id": f.get("FaceId"),
                        "image_id": f.get("ImageId"),
                        "external_image_id": f.get("ExternalImageId"),
                        "confidence": f.get("Confidence"),
                    }
                )
            next_token = resp.get("NextToken")
            if not next_token:
                break
        return jsonify({"ok": True, "collection_id": collection_id, "faces": faces, "total": len(faces)}), 200
    except (BotoCoreError, ClientError) as exc:
        return jsonify({"ok": False, "error": str(exc)}), 500


@app.route("/face-collection/enroll", methods=["POST"])
def face_collection_enroll() -> Any:
    if "image" not in request.files:
        return jsonify({"error": "image file is required"}), 400
    collection_id = _rekognition_collection_id_normalize(request.form.get("collection_id"))
    actor_name = _rekognition_external_image_id_normalize(request.form.get("actor_name"))
    if not collection_id:
        return jsonify({"error": "collection_id is required"}), 400
    if not actor_name:
        return jsonify({"error": "actor_name is required"}), 400

    image_bytes = request.files["image"].read()
    if not image_bytes:
        return jsonify({"error": "empty image"}), 400

    try:
        resp = rekognition.index_faces(
            CollectionId=collection_id,
            Image={"Bytes": image_bytes},
            ExternalImageId=actor_name,
            MaxFaces=1,
            QualityFilter="AUTO",
            DetectionAttributes=[],
        )
        face_records = resp.get("FaceRecords") or []
        return jsonify(
            {
                "ok": True,
                "collection_id": collection_id,
                "actor_name": actor_name,
                "faces_indexed": len(face_records),
                "face_records": face_records,
                "unindexed_faces": resp.get("UnindexedFaces") or [],
            }
        ), 200
    except rekognition.exceptions.ResourceNotFoundException:
        return jsonify({"ok": False, "error": f"collection not found: {collection_id}"}), 404
    except (BotoCoreError, ClientError) as exc:
        return jsonify({"ok": False, "error": str(exc)}), 500


@app.route("/local-faces", methods=["GET"])
def local_faces_list() -> Any:
    ok, reason = _insightface_available()
    gallery = _local_gallery_load()
    actors = gallery.get("actors") if isinstance(gallery, dict) else {}
    if not isinstance(actors, dict):
        actors = {}
    summary = [{"name": name, "samples": len(samples) if isinstance(samples, list) else 0} for name, samples in actors.items()]
    summary.sort(key=lambda x: (-(x.get("samples") or 0), x.get("name") or ""))
    return jsonify(
        {
            "ok": True,
            "engine": {"available": ok, "reason": reason},
            "actors": summary,
            "total_actors": len(summary),
        }
    ), 200


@app.route("/local-faces/enroll", methods=["POST"])
def local_faces_enroll() -> Any:
    if "image" not in request.files:
        return jsonify({"error": "image file is required"}), 400
    actor_name = (request.form.get("actor_name") or "").strip()
    actor_name = re.sub(r"\s+", " ", actor_name)
    if not actor_name:
        return jsonify({"error": "actor_name is required"}), 400

    ok, reason = _insightface_available()
    if not ok:
        return jsonify(
            {
                "error": "Local face engine not available",
                "detail": reason,
                "hint": "Install optional dependencies (insightface, onnxruntime, numpy) to enable local matching.",
            }
        ), 501

    image_bytes = request.files["image"].read()
    if not image_bytes:
        return jsonify({"error": "empty image"}), 400

    try:
        analyzer = _get_insightface_analyzer()
        img = np.asarray(Image.open(io.BytesIO(image_bytes)).convert("RGB"))  # type: ignore
        faces = analyzer.get(img)
        if not faces:
            return jsonify({"error": "No face detected in image"}), 400

        # Choose the largest detected face
        def _area(face_obj) -> float:
            bbox = getattr(face_obj, "bbox", None)
            if bbox is None:
                return 0.0
            x1, y1, x2, y2 = [float(v) for v in list(bbox)]
            return max(0.0, (x2 - x1)) * max(0.0, (y2 - y1))

        face_obj = max(faces, key=_area)
        emb = getattr(face_obj, "embedding", None)
        if emb is None:
            return jsonify({"error": "Face embedding unavailable"}), 500
        emb_vec = np.asarray(emb, dtype=np.float32)  # type: ignore

        gallery = _local_gallery_load()
        gallery.setdefault("actors", {})
        gallery["actors"].setdefault(actor_name, [])
        gallery["actors"][actor_name].append(
            {
                "embedding": emb_vec.tolist(),
                "added_at": datetime.utcnow().isoformat(),
                "filename": request.files["image"].filename,
            }
        )
        _local_gallery_save(gallery)
        return jsonify({"ok": True, "actor_name": actor_name, "samples": len(gallery["actors"][actor_name])}), 200
    except Exception as exc:
        app.logger.error("Local enroll failed: %s", exc)
        return jsonify({"error": f"Local enroll failed: {exc}"}), 500


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


def _probe_video_duration_seconds(video_path: Path) -> float | None:
    probe_cmd = [
        FFPROBE_PATH,
        "-v",
        "error",
        "-show_entries",
        "format=duration",
        "-of",
        "default=noprint_wrappers=1:nokey=1",
        str(video_path),
    ]
    try:
        duration_result = subprocess.run(probe_cmd, capture_output=True, text=True, timeout=10)
        raw = (duration_result.stdout or "").strip()
        if not raw:
            return None
        return float(raw)
    except Exception:
        return None


def _frame_timestamp_seconds(frame_path: Path) -> int | None:
    # Expected: frame_0010.jpg -> 10
    match = re.search(r"frame_(\d+)", frame_path.name)
    if not match:
        return None
    try:
        return int(match.group(1))
    except ValueError:
        return None


def _speaker_by_start_time(transcript_data: Dict[str, Any]) -> Dict[str, str]:
    results = ((transcript_data or {}).get("results") or {})
    speaker_labels = results.get("speaker_labels") or {}
    segments = speaker_labels.get("segments") or []
    mapping: Dict[str, str] = {}
    for seg in segments:
        for it in (seg.get("items") or []):
            start_time = it.get("start_time")
            speaker = it.get("speaker_label")
            if start_time and speaker:
                mapping[str(start_time)] = str(speaker)
    return mapping


def _parse_transcribe_words(
    transcript_data: Dict[str, Any],
    *,
    max_words: int = 5000,
    speaker_map: Dict[str, str] | None = None,
) -> List[Dict[str, Any]]:
    items = (((transcript_data or {}).get("results") or {}).get("items") or [])
    words: List[Dict[str, Any]] = []
    for item in items:
        itype = item.get("type")
        alt = (item.get("alternatives") or [{}])[0] or {}
        content = alt.get("content")
        if not content:
            continue

        if itype == "punctuation":
            # Attach punctuation to the previous word so segments read naturally.
            if words:
                words[-1]["word"] = f"{words[-1].get('word', '')}{content}"
            continue

        if itype != "pronunciation":
            continue

        raw_start = item.get("start_time")
        try:
            start_time = float(item.get("start_time"))
            end_time = float(item.get("end_time"))
        except (TypeError, ValueError):
            continue
        word: Dict[str, Any] = {
            "start": start_time,
            "end": end_time,
            "word": content,
        }
        if speaker_map and raw_start:
            speaker = speaker_map.get(str(raw_start))
            if speaker:
                word["speaker"] = speaker
        confidence = alt.get("confidence")
        try:
            if confidence is not None:
                word["confidence"] = float(confidence)
        except (TypeError, ValueError):
            pass
        words.append(word)
        if len(words) >= max_words:
            break
    return words


def _transcript_segments_from_words(
    words: List[Dict[str, Any]],
    *,
    window_seconds: float = 8.0,
    gap_seconds: float = 1.25,
    min_confidence: float = 0.45,
    max_segments: int = 250,
) -> List[Dict[str, Any]]:
    if not words:
        return []

    segments: List[Dict[str, Any]] = []
    current: List[str] = []
    current_speaker = words[0].get("speaker")
    seg_start = float(words[0].get("start", 0.0) or 0.0)
    seg_end = float(words[0].get("end", seg_start) or seg_start)

    last_end = seg_end
    for w in words:
        w_start = float(w.get("start", seg_end) or seg_end)
        w_end = float(w.get("end", w_start) or w_start)
        token = (w.get("word") or "").strip()
        speaker = w.get("speaker")
        conf = w.get("confidence")
        try:
            conf_value = float(conf) if conf is not None else None
        except (TypeError, ValueError):
            conf_value = None

        # Split when speaker changes.
        if current and (speaker is not None) and (speaker != current_speaker):
            text = " ".join(current).strip()
            if text:
                seg_obj: Dict[str, Any] = {"start": seg_start, "end": seg_end, "text": text}
                if current_speaker is not None:
                    seg_obj["speaker"] = current_speaker
                segments.append(seg_obj)
            current = []
            seg_start = w_start
            seg_end = w_end
            current_speaker = speaker

        # If there's a large pause, close the current segment early.
        if current and (w_start - last_end) >= gap_seconds:
            text = " ".join(current).strip()
            if text:
                seg_obj = {"start": seg_start, "end": seg_end, "text": text}
                if current_speaker is not None:
                    seg_obj["speaker"] = current_speaker
                segments.append(seg_obj)
            current = []
            seg_start = w_start

        if token:
            if conf_value is None or conf_value >= min_confidence:
                current.append(token)
        seg_end = max(seg_end, w_end)
        last_end = w_end

        if (seg_end - seg_start) >= window_seconds:
            text = " ".join(current).strip()
            if text:
                seg_obj = {"start": seg_start, "end": seg_end, "text": text}
                if current_speaker is not None:
                    seg_obj["speaker"] = current_speaker
                segments.append(seg_obj)
            current = []
            seg_start = seg_end
            if len(segments) >= max_segments:
                break

    if current and len(segments) < max_segments:
        text = " ".join(current).strip()
        if text:
            seg_obj = {"start": seg_start, "end": seg_end, "text": text}
            if current_speaker is not None:
                seg_obj["speaker"] = current_speaker
            segments.append(seg_obj)

    # Merge tiny trailing segments (often a single garbled word).
    if len(segments) >= 2:
        last = segments[-1]
        prev = segments[-2]
        last_words = (last.get("text") or "").split()
        if len(last_words) <= 2 and (float(last.get("end") or 0.0) - float(last.get("start") or 0.0)) <= 3.0:
            merged = (prev.get("text") or "").rstrip()
            tail = (last.get("text") or "").strip()
            if tail:
                prev["text"] = (merged + " " + tail).strip()
                prev["end"] = last.get("end")
                segments.pop()

    return segments


def _analyze_frame_with_rekognition(
    frame_path: Path,
    *,
    collection_id: str | None = None,
    local_face_mode: bool = False,
    local_similarity_threshold: float = 0.35,
) -> Dict[str, Any]:
    """Analyze a single frame using Amazon Rekognition (plus optional face matching modes)."""
    with open(frame_path, "rb") as image_file:
        image_bytes = image_file.read()
    
    analysis = {
        "labels": [],
        "text": [],
        "faces": [],
        "celebrities": [],
        "moderation": [],
        "custom_faces": [],
        "local_faces": [],
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
            {
                "text": item.get("DetectedText"),
                "type": item.get("Type"),
                "confidence": item.get("Confidence"),
            }
            for item in text_response.get("TextDetections", [])
            if item.get("Type") in {"LINE", "WORD"} and item.get("DetectedText")
        ]
    except Exception as e:
        app.logger.error(f"Text detection failed: {e}")
    
    try:
        # Detect faces and emotions
        face_response = rekognition.detect_faces(
            Image={"Bytes": image_bytes},
            Attributes=["ALL"]
        )
        face_details = face_response.get("FaceDetails", []) or []
        analysis["faces"] = [
            {
                "gender": (face.get("Gender") or {}).get("Value"),
                "gender_confidence": (face.get("Gender") or {}).get("Confidence"),
                "age_range": face.get("AgeRange"),
                "smile": (face.get("Smile") or {}).get("Value"),
                "eyeglasses": (face.get("Eyeglasses") or {}).get("Value"),
                "sunglasses": (face.get("Sunglasses") or {}).get("Value"),
                "beard": (face.get("Beard") or {}).get("Value"),
                "mustache": (face.get("Mustache") or {}).get("Value"),
                "bounding_box": (face.get("BoundingBox") if isinstance(face.get("BoundingBox"), dict) else None),
                "emotions": [
                    {"type": e["Type"], "confidence": e["Confidence"]}
                    for e in face.get("Emotions", [])
                ][:3]  # Top 3 emotions
            }
            for face in face_details
        ]
    except Exception as e:
        app.logger.error(f"Face detection failed: {e}")
        face_details = []

    # Optional: AWS Rekognition Custom Face Collection matching
    collection_id_norm = _rekognition_collection_id_normalize(collection_id)
    if collection_id_norm:
        try:
            matches: List[Dict[str, Any]] = []
            for face in face_details:
                bbox = face.get("BoundingBox") if isinstance(face.get("BoundingBox"), dict) else None
                face_jpeg = _pil_crop_bbox_to_jpeg_bytes(image_bytes, bbox)
                if not face_jpeg:
                    continue
                try:
                    sr = rekognition.search_faces_by_image(
                        CollectionId=collection_id_norm,
                        Image={"Bytes": face_jpeg},
                        FaceMatchThreshold=80,
                        MaxFaces=1,
                    )
                except Exception as exc:
                    app.logger.warning("search_faces_by_image failed: %s", exc)
                    continue

                face_matches = sr.get("FaceMatches") or []
                if not face_matches:
                    continue
                best_match = face_matches[0]
                face_obj = best_match.get("Face") or {}
                actor_name = face_obj.get("ExternalImageId") or face_obj.get("ImageId") or "Actor"
                similarity = best_match.get("Similarity")
                matches.append(
                    {
                        "name": actor_name,
                        "similarity": similarity,
                        "face_id": face_obj.get("FaceId"),
                        "collection_id": collection_id_norm,
                        "bounding_box": bbox,
                        "thumbnail": _pil_crop_bbox_thumbnail_base64(image_bytes, bbox),
                    }
                )
            analysis["custom_faces"] = matches
        except Exception as e:
            app.logger.error("Custom collection matching failed: %s", e)

    # Optional: local/open-source face matching (InsightFace)
    if local_face_mode:
        ok, reason = _insightface_available()
        if not ok:
            # Keep response shape stable; put a hint in logs only.
            app.logger.warning("Local face mode requested but unavailable: %s", reason)
        else:
            try:
                analyzer = _get_insightface_analyzer()
                gallery = _local_gallery_load()
                if isinstance(gallery.get("actors"), dict) and len(gallery.get("actors")) > 0:
                    img = np.asarray(Image.open(io.BytesIO(image_bytes)).convert("RGB"))  # type: ignore
                    faces = analyzer.get(img)
                    results: List[Dict[str, Any]] = []
                    for f in faces:
                        emb = getattr(f, "embedding", None)
                        bbox = getattr(f, "bbox", None)
                        if emb is None or bbox is None:
                            continue
                        try:
                            emb_vec = np.asarray(emb, dtype=np.float32)  # type: ignore
                        except Exception:
                            continue
                        best = _local_match_embedding(emb_vec, gallery, threshold=float(local_similarity_threshold))
                        if not best:
                            continue

                        # Convert bbox pixels to fractional for UI consistency
                        try:
                            h, w = img.shape[0], img.shape[1]
                            x1, y1, x2, y2 = [float(v) for v in list(bbox)]
                            frac_bbox = {
                                "Left": max(0.0, min(1.0, x1 / max(1.0, w))),
                                "Top": max(0.0, min(1.0, y1 / max(1.0, h))),
                                "Width": max(0.0, min(1.0, (x2 - x1) / max(1.0, w))),
                                "Height": max(0.0, min(1.0, (y2 - y1) / max(1.0, h))),
                            }
                        except Exception:
                            frac_bbox = None

                        results.append(
                            {
                                "name": best.get("name"),
                                "similarity": best.get("similarity"),
                                "bounding_box": frac_bbox,
                                "thumbnail": _pil_crop_bbox_thumbnail_base64(image_bytes, frac_bbox),
                            }
                        )
                    analysis["local_faces"] = results
            except Exception as e:
                app.logger.error("Local face matching failed: %s", e)

    try:
        celeb_response = rekognition.recognize_celebrities(Image={"Bytes": image_bytes})
        analysis["celebrities"] = [
            {
                "name": celeb.get("Name"),
                "confidence": celeb.get("MatchConfidence"),
                "urls": (celeb.get("Urls") or [])[:3],
                "bounding_box": ((celeb.get("Face") or {}).get("BoundingBox") if isinstance(celeb.get("Face"), dict) else None),
                "thumbnail": _pil_crop_bbox_thumbnail_base64(
                    image_bytes,
                    (celeb.get("Face") or {}).get("BoundingBox") if isinstance(celeb.get("Face"), dict) else None,
                ),
            }
            for celeb in celeb_response.get("CelebrityFaces", [])
            if celeb.get("Name")
        ]
    except Exception as e:
        app.logger.error(f"Celebrity detection failed: {e}")

    try:
        # Detect moderation labels (violence, gore, drugs, etc.)
        moderation_response = rekognition.detect_moderation_labels(
            Image={"Bytes": image_bytes},
            MinConfidence=30
        )
        analysis["moderation"] = [
            {"name": label["Name"], "confidence": label["Confidence"]}
            for label in moderation_response.get("ModerationLabels", [])
        ]
    except Exception as e:
        app.logger.error(f"Moderation label detection failed: {e}")
    
    return analysis


def _list_matches_terms(values: List[str], query_terms: List[str]) -> bool:
    """Return True if all query terms match as word-prefixes in the provided list of strings."""
    if not query_terms:
        return True
    if not values:
        return False
    haystack = " ".join(values)
    return _chunk_matches_terms(haystack, query_terms)


def _extract_audio_and_transcribe(video_path: Path, temp_dir: Path, job_id: str) -> str:
    """Extract audio and transcribe using AWS Transcribe."""
    # Extract audio
    audio_path = temp_dir / "audio.wav"
    extract_cmd = [
        FFMPEG_PATH, "-i", str(video_path),
        "-vn",
        "-ac", "1",
        "-ar", "16000",
        "-af", "loudnorm",
        "-acodec", "pcm_s16le",
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
    s3_key = f"transcribe/{job_id}/audio.wav"
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
    lang_opts_raw = (os.getenv("TRANSCRIBE_LANGUAGE_OPTIONS") or "").strip()
    if not lang_opts_raw:
        # Default tuned for common demo content; override in .env.local if needed.
        # NOTE: must be valid Transcribe language codes.
        lang_opts_raw = "en-US,en-IN,hi-IN"
    language_options = [x.strip() for x in lang_opts_raw.split(",") if x.strip()]

    transcribe_kwargs: Dict[str, Any] = {
        "TranscriptionJobName": transcribe_job_name,
        "Media": {"MediaFileUri": s3_uri},
        "MediaFormat": "wav",
    }
    if len(language_options) == 1:
        transcribe_kwargs["LanguageCode"] = language_options[0]
    else:
        transcribe_kwargs["IdentifyLanguage"] = True
        transcribe_kwargs["LanguageOptions"] = language_options

    try:
        transcribe_client.start_transcription_job(**transcribe_kwargs)
    except Exception as exc:
        # If language options contain an unsupported code, Transcribe throws a BadRequest.
        # Retry with a small safe set.
        safe_options = ["en-US", "en-IN", "hi-IN"]
        if transcribe_kwargs.get("IdentifyLanguage") and transcribe_kwargs.get("LanguageOptions"):
            app.logger.warning("Transcribe start failed; retrying with safe language options: %s", exc)
            transcribe_kwargs["LanguageOptions"] = safe_options
            transcribe_client.start_transcription_job(**transcribe_kwargs)
        else:
            raise
    
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


def _extract_audio_and_transcribe_rich(
    video_path: Path,
    temp_dir: Path,
    job_id: str,
    *,
    max_words: int = 5000,
) -> Dict[str, Any]:
    """Like _extract_audio_and_transcribe but also returns word timestamps for UI preview."""
    # We re-run the same Transcribe flow, but keep the JSON for timestamps.
    # NOTE: Kept separate to avoid breaking older callers.
    # Extract audio
    audio_path = temp_dir / "audio.wav"
    extract_cmd = [
        FFMPEG_PATH, "-i", str(video_path),
        "-vn",
        "-ac", "1",
        "-ar", "16000",
        "-af", "loudnorm",
        "-acodec", "pcm_s16le",
        str(audio_path), "-y"
    ]
    subprocess.run(extract_cmd, capture_output=True, check=True)

    bucket_region = _detect_bucket_region(SEMANTIC_SEARCH_BUCKET)
    s3_region = bucket_region or DEFAULT_AWS_REGION
    s3_client = boto3.client("s3", region_name=s3_region)
    transcribe_region = _resolve_transcribe_region(bucket_region)
    transcribe_client = boto3.client("transcribe", region_name=transcribe_region)

    s3_key = f"transcribe/{job_id}/audio.wav"
    try:
        s3_client.head_bucket(Bucket=SEMANTIC_SEARCH_BUCKET)
    except ClientError:
        create_kwargs: Dict[str, Any] = {"Bucket": SEMANTIC_SEARCH_BUCKET}
        if s3_region != "us-east-1":
            create_kwargs["CreateBucketConfiguration"] = {"LocationConstraint": s3_region}
        s3_client.create_bucket(**create_kwargs)

    s3_client.upload_file(str(audio_path), SEMANTIC_SEARCH_BUCKET, s3_key)
    s3_uri = f"s3://{SEMANTIC_SEARCH_BUCKET}/{s3_key}"

    transcribe_job_name = f"semantic-search-{job_id}"
    lang_opts_raw = (os.getenv("TRANSCRIBE_LANGUAGE_OPTIONS") or "").strip()
    if not lang_opts_raw:
        lang_opts_raw = "en-US,en-IN,hi-IN"
    language_options = [x.strip() for x in lang_opts_raw.split(",") if x.strip()]

    transcribe_kwargs: Dict[str, Any] = {
        "TranscriptionJobName": transcribe_job_name,
        "Media": {"MediaFileUri": s3_uri},
        "MediaFormat": "wav",
    }
    if len(language_options) == 1:
        transcribe_kwargs["LanguageCode"] = language_options[0]
    else:
        transcribe_kwargs["IdentifyLanguage"] = True
        transcribe_kwargs["LanguageOptions"] = language_options

    # Speaker diarization (best-effort). Works for many multi-speaker clips.
    try:
        max_speakers = int(os.getenv("TRANSCRIBE_MAX_SPEAKERS", "5"))
    except ValueError:
        max_speakers = 5
    transcribe_kwargs["Settings"] = {
        "ShowSpeakerLabels": True,
        "MaxSpeakerLabels": max(2, min(10, max_speakers)),
    }

    try:
        transcribe_client.start_transcription_job(**transcribe_kwargs)
    except Exception as exc:
        safe_options = ["en-US", "en-IN", "hi-IN"]
        if transcribe_kwargs.get("IdentifyLanguage") and transcribe_kwargs.get("LanguageOptions"):
            app.logger.warning("Transcribe start failed; retrying with safe language options: %s", exc)
            transcribe_kwargs["LanguageOptions"] = safe_options
            transcribe_client.start_transcription_job(**transcribe_kwargs)
        else:
            raise

    import time
    max_wait = 300
    start_time = time.time()
    import requests

    while time.time() - start_time < max_wait:
        status = transcribe_client.get_transcription_job(TranscriptionJobName=transcribe_job_name)
        job_status = status["TranscriptionJob"]["TranscriptionJobStatus"]
        if job_status == "COMPLETED":
            transcript_uri = status["TranscriptionJob"]["Transcript"]["TranscriptFileUri"]
            detected_language_code = status["TranscriptionJob"].get("LanguageCode")
            transcript_data = requests.get(transcript_uri).json()
            transcript_text = transcript_data.get("results", {}).get("transcripts", [{}])[0].get("transcript", "")
            speaker_map = _speaker_by_start_time(transcript_data)
            words = _parse_transcribe_words(transcript_data, max_words=max_words, speaker_map=speaker_map)
            segments = _transcript_segments_from_words(words)

            transcribe_client.delete_transcription_job(TranscriptionJobName=transcribe_job_name)
            s3_client.delete_object(Bucket=SEMANTIC_SEARCH_BUCKET, Key=s3_key)

            return {
                "text": transcript_text,
                "words": words,
                "segments": segments,
                "language_code": detected_language_code or (language_options[0] if language_options else "en-US"),
            }

        if job_status == "FAILED":
            break
        time.sleep(5)

    fallback_lang = (language_options[0] if ("language_options" in locals() and language_options) else "en-US")
    return {"text": "", "words": [], "segments": [], "language_code": fallback_lang}


def _detect_dominant_languages_from_text(text: str) -> List[Dict[str, Any]]:
    t = (text or "").strip()
    if not t:
        return []
    # Comprehend's Text limit is small; keep a short prefix.
    snippet = t[:4500]
    try:
        resp = comprehend.detect_dominant_language(Text=snippet)
        langs = resp.get("Languages") or []
        parsed: List[Dict[str, Any]] = []
        for l in langs:
            code = (l.get("LanguageCode") or "").strip()
            try:
                score = float(l.get("Score") or 0.0)
            except (TypeError, ValueError):
                score = 0.0
            if not code:
                continue
            parsed.append({"language_code": code, "score": score})
        parsed.sort(key=lambda x: (x.get("score") or 0.0), reverse=True)
        return parsed[:5]
    except Exception as exc:
        app.logger.warning("Language detection failed: %s", exc)
        return []


def _top_n_by_score(items: List[Tuple[str, float]], *, limit: int) -> List[Dict[str, Any]]:
    ranked = sorted(items, key=lambda pair: (pair[1], pair[0]), reverse=True)
    return [{"name": name, "score": score} for name, score in ranked[: max(0, limit)]]


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


def _normalize_similarity(cosine_similarity: float) -> float:
    """Normalize cosine similarity (-1..1) to a 0..1 score."""
    try:
        value = (float(cosine_similarity) + 1.0) / 2.0
    except (TypeError, ValueError):
        return 0.0
    if value < 0.0:
        return 0.0
    if value > 1.0:
        return 1.0
    return value


def _chunk_text_for_indexing(text: str, *, max_chars: int = 800, overlap: int = 120, max_chunks: int = 400) -> List[str]:
    """Split extracted document text into reasonably sized chunks for embedding."""
    if not text:
        return []

    # Prefer paragraph boundaries when available.
    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
    if not paragraphs:
        paragraphs = [text.strip()]

    chunks: List[str] = []
    step = max(1, max_chars - max(0, overlap))

    for paragraph in paragraphs:
        if len(paragraph) <= max_chars:
            chunks.append(paragraph)
        else:
            start = 0
            while start < len(paragraph):
                piece = paragraph[start:start + max_chars].strip()
                if piece:
                    chunks.append(piece)
                start += step

        if len(chunks) >= max_chunks:
            break

    return chunks[:max_chunks]


def _extract_match_snippet(text: str, query_terms: List[str], *, window: int = 160) -> str | None:
    """Return a short snippet around the first literal match of any query term."""
    if not text or not query_terms:
        return None

    positions: List[int] = []
    for term in query_terms:
        term = (term or "").strip()
        if not term:
            continue
        # Match word prefixes (e.g., 'amit' should match 'amitabh').
        pattern = re.compile(rf"\b{re.escape(term)}\w*", re.IGNORECASE)
        match = pattern.search(text)
        if match:
            positions.append(match.start())

    if not positions:
        return None

    match_pos = min(positions)
    start = max(0, match_pos - window)
    end = min(len(text), match_pos + window)
    prefix = "…" if start > 0 else ""
    suffix = "…" if end < len(text) else ""
    return f"{prefix}{text[start:end].strip()}{suffix}"


def _chunk_matches_terms(text: str, query_terms: List[str]) -> bool:
    """Return True if all query terms appear as word prefixes in text (case-insensitive)."""
    if not query_terms:
        return True
    if not text:
        return False

    for term in query_terms:
        term = (term or "").strip()
        if not term:
            continue
        if not re.search(rf"\b{re.escape(term)}\w*", text, flags=re.IGNORECASE):
            return False
    return True


def _chunk_matches_any_terms(text: str, query_terms: List[str]) -> bool:
    """Return True if any query term appears as a word prefix in text (case-insensitive)."""
    if not query_terms:
        return True
    if not text:
        return False

    for term in query_terms:
        term = (term or "").strip()
        if not term:
            continue
        if re.search(rf"\b{re.escape(term)}\w*", text, flags=re.IGNORECASE):
            return True
    return False


def _list_matches_any_terms(values: List[str], query_terms: List[str]) -> bool:
    """Return True if any query term matches as a word-prefix in the provided list of strings."""
    if not query_terms:
        return True
    if not values:
        return False
    haystack = " ".join(values)
    return _chunk_matches_any_terms(haystack, query_terms)


def _video_intent_expansion_terms(raw_query_terms: List[str]) -> List[str]:
    """Return expanded terms for certain single-intent video queries (e.g., song/music/dance).

    This is used for keyword gating with OR-semantics (any-term), so semantic noise doesn't
    surface unrelated results when we have good lexical signals.
    """
    lowered = [(t or "").strip().lower() for t in (raw_query_terms or []) if (t or "").strip()]
    if not lowered:
        return []

    music_intent = {
        "song", "songs", "music", "dance", "dancing", "singer", "singers", "sing", "singing", "lyrics", "lyric",
    }

    # Only expand when the user's query is strongly a single intent word.
    if len(lowered) == 1 and lowered[0] in music_intent:
        # Use stems/prefixes where helpful (e.g., perform -> performer/performance).
        return [
            lowered[0],
            "music",
            "dance",
            "sing",
            "lyric",
            "melod",
            "rhythm",
            "beat",
            "perform",
            "stage",
            "show",
            "finalist",
            "judge",
        ]

    return []


def _extract_movie_titles_by_actor(full_text: str, query_terms: List[str], *, max_titles: int = 50) -> List[str]:
    """Extract movie titles from "Title — actors" style lists where actors match query terms.

    Designed for PDF-extracted content where line breaks can be messy.
    """
    if not full_text or not query_terms:
        return []

    # Normalize whitespace so wrapped PDF lines don't break patterns.
    normalized = re.sub(r"\s+", " ", full_text)

    # Common pattern: "12. Movie Title — Actor1, Actor2".
    # Use a lookahead for the next numbered item boundary.
    pattern = re.compile(
        r"\b\d{1,3}\.\s+([^—]{2,120}?)\s+—\s+(.+?)(?=\s+\d{1,3}\.\s+|$)",
        re.UNICODE,
    )

    # Build prefix matchers for each term (e.g., 'amit' matches 'Amitabh').
    term_patterns = [re.compile(rf"\b{re.escape(term)}\w*", re.IGNORECASE) for term in query_terms if term.strip()]
    if not term_patterns:
        return []

    titles: List[str] = []
    seen = set()

    for match in pattern.finditer(normalized):
        raw_title = (match.group(1) or "").strip()
        actors = (match.group(2) or "").strip()

        # Clean up title noise.
        title = re.sub(r"\s+", " ", raw_title)
        title = title.strip("-–— ")
        if not title:
            continue

        if not all(p.search(actors) for p in term_patterns):
            continue

        key = title.lower()
        if key in seen:
            continue
        seen.add(key)
        titles.append(title)

        if len(titles) >= max_titles:
            break

    return titles


def _parse_int_param(
    raw_value: Any,
    *,
    default: int,
    min_value: int,
    max_value: int,
) -> int:
    try:
        value = int(str(raw_value).strip())
    except Exception:
        return default
    return max(min_value, min(max_value, value))


def _parse_float_param(
    raw_value: Any,
    *,
    default: float,
    min_value: float,
    max_value: float,
) -> float:
    try:
        value = float(str(raw_value).strip())
    except Exception:
        return default
    return max(min_value, min(max_value, value))


def _process_stored_video(
    *,
    video_id: str,
    stored_video_path: Path,
    video_title: str,
    video_description: str,
    original_filename: str,
    frame_interval_seconds: int = 10,
    max_frames_to_analyze: int = 1000,
    face_recognition_mode: str | None = None,
    collection_id: str | None = None,
    local_similarity_threshold: float = 0.35,
) -> Dict[str, Any]:
    """Re-process a video already stored on disk and return updated fields."""
    temp_dir = Path(tempfile.mkdtemp(prefix=f"metadata_reprocess_{video_id}_"))
    try:
        working_video_path = temp_dir / "video.mp4"
        shutil.copy2(stored_video_path, working_video_path)

        # Extract frames
        frames_dir = temp_dir / "frames"
        frames_dir.mkdir()
        frame_interval_seconds = _parse_int_param(
            frame_interval_seconds,
            default=10,
            min_value=1,
            max_value=30,
        )
        frames = _extract_video_frames(working_video_path, frames_dir, interval=frame_interval_seconds)
        duration_seconds = _probe_video_duration_seconds(working_video_path)

        # Analyze frames with Rekognition
        all_emotions: List[str] = []

        label_stats: Dict[str, Dict[str, float]] = {}
        text_stats: Dict[str, int] = {}
        celeb_stats: Dict[str, float] = {}
        custom_face_stats: Dict[str, float] = {}
        local_face_stats: Dict[str, float] = {}
        moderation_stats: Dict[str, float] = {}
        gender_counts: Dict[str, int] = {}
        age_ranges: List[Tuple[int, int]] = []

        frames_metadata: List[Dict[str, Any]] = []

        max_frames_to_analyze = _parse_int_param(
            max_frames_to_analyze,
            default=1000,
            min_value=1,
            max_value=10000,
        )
        for frame in frames[:max_frames_to_analyze]:  # Limit to save API calls
            analysis = _analyze_frame_with_rekognition(
                frame,
                collection_id=collection_id if (face_recognition_mode == "aws_collection") else None,
                local_face_mode=bool(face_recognition_mode == "local"),
                local_similarity_threshold=local_similarity_threshold,
            )
            timestamp = _frame_timestamp_seconds(frame)

            # Aggregate labels with confidence
            for label in analysis.get("labels", []):
                name = (label.get("name") or "").strip()
                if not name:
                    continue
                confidence = float(label.get("confidence") or 0.0)
                stat = label_stats.setdefault(name, {"count": 0.0, "max": 0.0, "sum": 0.0})
                stat["count"] += 1.0
                stat["sum"] += confidence
                stat["max"] = max(stat["max"], confidence)

            # Aggregate text (prefer LINE)
            for txt in analysis.get("text", []):
                value = (txt.get("text") or "").strip()
                if not value:
                    continue
                if txt.get("type") != "LINE":
                    continue
                text_stats[value] = text_stats.get(value, 0) + 1

            # Aggregate faces
            for face in analysis.get("faces", []):
                for e in (face.get("emotions") or []):
                    et = (e.get("type") or "").strip()
                    if et:
                        all_emotions.append(et)
                gender = (face.get("gender") or "").strip()
                if gender:
                    gender_counts[gender] = gender_counts.get(gender, 0) + 1
                age = face.get("age_range") or {}
                try:
                    low = int(age.get("Low"))
                    high = int(age.get("High"))
                    age_ranges.append((low, high))
                except Exception:
                    pass

            # Aggregate celebrities
            for c in (analysis.get("celebrities") or []):
                name = (c.get("name") or "").strip()
                if not name:
                    continue
                try:
                    conf = float(c.get("confidence") or 0.0)
                except (TypeError, ValueError):
                    conf = 0.0
                celeb_stats[name] = max(celeb_stats.get(name, 0.0), conf)

            # Aggregate custom collection matches
            for c in (analysis.get("custom_faces") or []):
                name = (c.get("name") or "").strip()
                if not name:
                    continue
                try:
                    sim = float(c.get("similarity") or 0.0)
                except (TypeError, ValueError):
                    sim = 0.0
                custom_face_stats[name] = max(custom_face_stats.get(name, 0.0), sim)

            # Aggregate local matches
            for c in (analysis.get("local_faces") or []):
                name = (c.get("name") or "").strip()
                if not name:
                    continue
                try:
                    sim = float(c.get("similarity") or 0.0)
                except (TypeError, ValueError):
                    sim = 0.0
                local_face_stats[name] = max(local_face_stats.get(name, 0.0), sim)

            # Aggregate moderation
            for m in (analysis.get("moderation") or []):
                name = (m.get("name") or "").strip()
                if not name:
                    continue
                try:
                    conf = float(m.get("confidence") or 0.0)
                except (TypeError, ValueError):
                    conf = 0.0
                moderation_stats[name] = max(moderation_stats.get(name, 0.0), conf)

            frames_metadata.append(
                {
                    "timestamp": timestamp,
                    "labels": (analysis.get("labels") or [])[:12],
                    "text": [t for t in (analysis.get("text") or []) if t.get("type") == "LINE"][:12],
                    "faces": (analysis.get("faces") or [])[:12],
                    "celebrities": (analysis.get("celebrities") or [])[:12],
                    "custom_faces": (analysis.get("custom_faces") or [])[:12],
                    "local_faces": (analysis.get("local_faces") or [])[:12],
                    "moderation": (analysis.get("moderation") or [])[:12],
                }
            )

        emotions_unique = sorted(list(set(all_emotions)))
        labels_ranked = sorted(
            (
                (
                    name,
                    int(stats.get("count", 0.0) or 0),
                    float(stats.get("max", 0.0) or 0.0),
                    float(stats.get("sum", 0.0) or 0.0) / max(1.0, float(stats.get("count", 0.0) or 1.0)),
                )
                for name, stats in label_stats.items()
            ),
            key=lambda row: (row[1], row[2], row[0]),
            reverse=True,
        )
        labels_detailed = [
            {
                "name": name,
                "occurrences": count,
                "max_confidence": max_conf,
                "avg_confidence": avg_conf,
            }
            for (name, count, max_conf, avg_conf) in labels_ranked[:50]
        ]
        text_detailed = [
            {"text": text, "occurrences": count}
            for text, count in sorted(text_stats.items(), key=lambda kv: (kv[1], kv[0]), reverse=True)[:50]
        ]
        celebs_detailed = [
            {"name": name, "max_confidence": conf}
            for name, conf in sorted(celeb_stats.items(), key=lambda kv: (kv[1], kv[0]), reverse=True)[:50]
        ]

        custom_faces_detailed = [
            {"name": name, "max_similarity": conf}
            for name, conf in sorted(custom_face_stats.items(), key=lambda kv: (kv[1], kv[0]), reverse=True)[:50]
        ]
        local_faces_detailed = [
            {"name": name, "max_similarity": conf}
            for name, conf in sorted(local_face_stats.items(), key=lambda kv: (kv[1], kv[0]), reverse=True)[:50]
        ]
        moderation_detailed = [
            {"name": name, "max_confidence": conf}
            for name, conf in sorted(moderation_stats.items(), key=lambda kv: (kv[1], kv[0]), reverse=True)[:50]
        ]

        # Extract and transcribe audio (rich)
        transcribe_rich = _extract_audio_and_transcribe_rich(working_video_path, temp_dir, video_id)
        transcript = transcribe_rich.get("text") or ""
        transcript_words = transcribe_rich.get("words") or []
        transcript_segments = transcribe_rich.get("segments") or []
        transcript_language_code = (transcribe_rich.get("language_code") or "").strip() or None
        languages_detected = _detect_dominant_languages_from_text(transcript)

        # Extract and transcribe audio
        # Build metadata text for embedding
        metadata_parts = [video_title, video_description]
        if transcript:
            metadata_parts.append(f"Transcript: {transcript}")
        if labels_detailed:
            metadata_parts.append(
                "Visual elements: " + ", ".join([l["name"] for l in labels_detailed[:50] if l.get("name")])
            )
        if text_detailed:
            metadata_parts.append(
                "Text in video: " + ", ".join([t["text"] for t in text_detailed[:20] if t.get("text")])
            )
        if emotions_unique:
            metadata_parts.append(f"Emotions detected: {', '.join(emotions_unique)}")
        if celebs_detailed:
            metadata_parts.append(
                "Celebrities detected: " + ", ".join([c["name"] for c in celebs_detailed[:25] if c.get("name")])
            )
        if custom_faces_detailed:
            metadata_parts.append(
                "Cast detected (custom collection): "
                + ", ".join([c["name"] for c in custom_faces_detailed[:25] if c.get("name")])
            )
        if local_faces_detailed:
            metadata_parts.append(
                "Cast detected (local): " + ", ".join([c["name"] for c in local_faces_detailed[:25] if c.get("name")])
            )
        if moderation_detailed:
            metadata_parts.append(
                "Moderation labels: " + ", ".join([m["name"] for m in moderation_detailed[:30] if m.get("name")])
            )
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
            "language_code": transcript_language_code,
            "languages_detected": languages_detected,
            "transcript_words": transcript_words,
            "transcript_segments": transcript_segments,
            "labels": [l["name"] for l in labels_detailed if l.get("name")][:50],
            "labels_detailed": labels_detailed,
            "text_detected": [t["text"] for t in text_detailed if t.get("text")][:20],
            "text_detailed": text_detailed,
            "emotions": emotions_unique,
            "celebrities": [c["name"] for c in celebs_detailed if c.get("name")][:50],
            "celebrities_detailed": celebs_detailed,
            "custom_faces": [c["name"] for c in custom_faces_detailed if c.get("name")][:50],
            "custom_faces_detailed": custom_faces_detailed,
            "custom_collection_id": _rekognition_collection_id_normalize(collection_id) if face_recognition_mode == "aws_collection" else None,
            "local_faces": [c["name"] for c in local_faces_detailed if c.get("name")][:50],
            "local_faces_detailed": local_faces_detailed,
            "face_recognition_mode": face_recognition_mode,
            "local_similarity_threshold": float(local_similarity_threshold) if face_recognition_mode == "local" else None,
            "moderation_labels": [m["name"] for m in moderation_detailed if m.get("name")][:50],
            "moderation_detailed": moderation_detailed,
            "faces_summary": {
                "count": sum(gender_counts.values()),
                "genders": gender_counts,
                "age_ranges": age_ranges[:200],
            },
            "embedding": embedding,
            "thumbnail": thumbnail_base64,
            "metadata_text": metadata_text,
            "frame_count": len(frames),
            "frames_analyzed": len(frames_metadata),
            "frame_interval_seconds": frame_interval_seconds,
            "duration_seconds": duration_seconds,
            "frames": frames_metadata,
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
    original_filename = video_file.filename
    temp_dir = Path(tempfile.mkdtemp(prefix=f"metadata_{job_id}_"))

    frame_interval_seconds = _parse_int_param(
        request.form.get("frame_interval_seconds"),
        default=10,
        min_value=1,
        max_value=30,
    )
    max_frames_to_analyze = _parse_int_param(
        request.form.get("max_frames_to_analyze"),
        default=1000,
        min_value=1,
        max_value=10000,
    )
    face_recognition_mode = (request.form.get("face_recognition_mode") or "").strip().lower() or None
    collection_id = (request.form.get("collection_id") or None)

    try:
        video_path = temp_dir / "video.mp4"
        video_file.save(str(video_path))
    except Exception as exc:
        shutil.rmtree(temp_dir, ignore_errors=True)
        return jsonify({"error": f"Failed to save upload: {str(exc)}"}), 500

    _job_init(job_id, title=video_title)
    _job_update(job_id, status="processing", progress=1, message="Upload received")

    thread = threading.Thread(
        target=_process_video_job,
        kwargs={
            "job_id": job_id,
            "temp_dir": temp_dir,
            "video_path": video_path,
            "video_title": video_title,
            "video_description": video_description,
            "original_filename": original_filename,
            "frame_interval_seconds": frame_interval_seconds,
            "max_frames_to_analyze": max_frames_to_analyze,
            "face_recognition_mode": face_recognition_mode,
            "collection_id": collection_id,
        },
        daemon=True,
    )
    thread.start()

    with JOBS_LOCK:
        job = JOBS.get(job_id)
    return jsonify({"job_id": job_id, "job": job}), 202


@app.route("/jobs/<job_id>", methods=["GET"])
def get_job(job_id: str) -> Any:
    with JOBS_LOCK:
        job = JOBS.get(job_id)
    if not job:
        return jsonify({"error": "Job not found"}), 404
    return jsonify(job), 200


@app.route("/search", methods=["POST"])
def search_videos() -> Any:
    """Search videos using semantic similarity."""
    payload = request.get_json(silent=True) or {}
    query = payload.get("query", "").strip()
    top_k = int(payload.get("top_k", 5))
    min_similarity = payload.get("min_similarity")
    if min_similarity is None:
        min_similarity = os.getenv("SEMANTIC_VIDEO_MIN_SIMILARITY", "0.5")
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
        
        raw_query_terms = [t for t in query.split() if t]
        raw_query_terms_count = len(raw_query_terms)
        query_terms = list(raw_query_terms)

        # Intent-based expansion for better relevance on short queries like "song".
        intent_terms = _video_intent_expansion_terms(raw_query_terms)

        # Small synonym expansion for common safety-related queries.
        lowered = {t.lower() for t in query_terms}
        if "blood" in lowered:
            # Rekognition moderation labels tend to use categories like "Violence" / "Graphic Violence Or Gore".
            query_terms = list(dict.fromkeys(query_terms + ["violence", "gore", "graphic"]))

        def moderation_match(v: Dict[str, Any]) -> bool:
            return _list_matches_terms([str(x) for x in (v.get("moderation_labels") or [])], query_terms)

        def label_match(v: Dict[str, Any]) -> bool:
            return _list_matches_terms([str(x) for x in (v.get("labels") or [])], query_terms)

        def text_match(v: Dict[str, Any]) -> bool:
            combined = " ".join([
                str(v.get("title") or ""),
                str(v.get("description") or ""),
                str(v.get("transcript") or ""),
                " ".join([str(x) for x in (v.get("text_detected") or [])]),
            ])
            return _chunk_matches_terms(combined, query_terms)

        def label_match_any(v: Dict[str, Any]) -> bool:
            if not intent_terms:
                return False
            return _list_matches_any_terms([str(x) for x in (v.get("labels") or [])], intent_terms)

        def text_match_any(v: Dict[str, Any]) -> bool:
            if not intent_terms:
                return False
            combined = " ".join([
                str(v.get("title") or ""),
                str(v.get("description") or ""),
                str(v.get("transcript") or ""),
                " ".join([str(x) for x in (v.get("text_detected") or [])]),
            ])
            return _chunk_matches_any_terms(combined, intent_terms)

        has_moderation_hits = any(moderation_match(v) for v in VIDEO_INDEX)
        has_label_hits = any(label_match(v) for v in VIDEO_INDEX)
        has_text_hits = any(text_match(v) for v in VIDEO_INDEX)

        # For certain intent queries (e.g., "song"), prefer OR-based gating on expanded terms.
        has_intent_label_hits = any(label_match_any(v) for v in VIDEO_INDEX) if intent_terms else False
        has_intent_text_hits = any(text_match_any(v) for v in VIDEO_INDEX) if intent_terms else False

        def include_video(v: Dict[str, Any]) -> bool:
            if has_intent_label_hits:
                return label_match_any(v)
            if has_intent_text_hits:
                return text_match_any(v)
            if has_moderation_hits:
                return moderation_match(v)
            if has_label_hits:
                return label_match(v)
            if has_text_hits:
                return text_match(v)
            return True

        # Compute similarities (with keyword-aware filtering first)
        all_results = []
        for video in VIDEO_INDEX:
            if not video.get("embedding"):
                continue
            if not include_video(video):
                continue

            cosine_similarity = _compute_similarity(query_embedding, video["embedding"])
            similarity = _normalize_similarity(cosine_similarity)

            labels = [str(x) for x in (video.get("labels") or [])]
            moderation_labels = [str(x) for x in (video.get("moderation_labels") or [])]
            if intent_terms:
                matched_labels = [l for l in labels if _chunk_matches_any_terms(l, intent_terms)]
            else:
                matched_labels = [l for l in labels if _chunk_matches_terms(l, query_terms)] if query_terms else labels[:10]
            matched_moderation = [m for m in moderation_labels if _chunk_matches_terms(m, query_terms)] if query_terms else moderation_labels[:10]

            all_results.append({
                "id": video["id"],
                "video_id": video["id"],
                "title": video["title"],
                "description": video["description"],
                "transcript_snippet": video["transcript"][:200] if video["transcript"] else "",
                "labels": labels[:10],
                "matched_labels": matched_labels[:10],
                "moderation_labels": moderation_labels[:10],
                "matched_moderation_labels": matched_moderation[:10],
                "emotions": video["emotions"],
                "thumbnail": _as_data_uri_jpeg(video.get("thumbnail")),
                "similarity_score": round(similarity, 4),
                "cosine_similarity": round(cosine_similarity, 4),
                "uploaded_at": video["uploaded_at"]
            })
        
        # Sort by similarity
        all_results.sort(key=lambda x: x["similarity_score"], reverse=True)

        # Filter results.
        # - Always apply min_similarity.
        # - If this search is semantic-only (no keyword hits), additionally keep only results
        #   within a small margin of the best score to avoid unrelated matches.
        semantic_only = not (has_intent_label_hits or has_intent_text_hits or has_moderation_hits or has_label_hits or has_text_hits)
        effective_min_similarity = min_similarity_value
        if semantic_only and all_results:
            # Single-word queries tend to be more specific; use a tighter margin by default.
            default_margin = "0.02" if raw_query_terms_count == 1 else "0.03"
            margin = float(os.getenv("SEMANTIC_VIDEO_TOP_SCORE_MARGIN", default_margin))
            top_score = all_results[0]["similarity_score"]
            effective_min_similarity = max(effective_min_similarity, top_score - margin)

        results = [r for r in all_results if r["similarity_score"] >= effective_min_similarity]
        
        # Log for debugging
        app.logger.info(f"Query: {query}")
        app.logger.info(f"Top scores: {[r['similarity_score'] for r in all_results[:5]]}")
        app.logger.info(
            f"Results after min_similarity={effective_min_similarity:.2f} filter: {len(results)}/{len(all_results)}"
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
            "frame_count": int(v.get("frame_count", 0) or 0),
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

    include_frames_raw = (request.args.get("include_frames") or "").strip().lower()
    include_words_raw = (request.args.get("include_words") or "").strip().lower()
    include_frames = include_frames_raw in {"1", "true", "yes", "y", "on"}
    include_words = include_words_raw in {"1", "true", "yes", "y", "on"}

    # Opportunistic backfill for older index entries.
    if (video.get("languages_detected") is None or (isinstance(video.get("languages_detected"), list) and len(video.get("languages_detected") or []) == 0)) and (video.get("transcript") or "").strip():
        try:
            detected = _detect_dominant_languages_from_text(video.get("transcript") or "")
            if detected:
                video["languages_detected"] = detected
                # Prefer detected top language for language_code if missing.
                if not (video.get("language_code") or "").strip():
                    video["language_code"] = detected[0].get("language_code")
                _save_video_index()
        except Exception as exc:
            app.logger.warning("Language backfill failed for %s: %s", video_id, exc)

    response: Dict[str, Any] = {
        "id": video["id"],
        "title": video["title"],
        "description": video["description"],
        "thumbnail": video.get("thumbnail"),
        "uploaded_at": video.get("uploaded_at"),

        # Core metadata (backwards compatible keys)
        "transcript": video.get("transcript") or "",
        "language_code": video.get("language_code"),
        "languages_detected": video.get("languages_detected") or [],
        "labels": video.get("labels") or [],
        "text_detected": video.get("text_detected") or [],
        "emotions": video.get("emotions") or [],
        "celebrities": video.get("celebrities") or [],

        # Optional face recognition modes
        "custom_faces": video.get("custom_faces") or [],
        "custom_faces_detailed": video.get("custom_faces_detailed") or [],
        "custom_collection_id": video.get("custom_collection_id"),
        "local_faces": video.get("local_faces") or [],
        "local_faces_detailed": video.get("local_faces_detailed") or [],

        # Enriched aggregates
        "duration_seconds": video.get("duration_seconds"),
        "frame_interval_seconds": video.get("frame_interval_seconds"),
        "frame_count": int(video.get("frame_count", 0) or 0),
        "frames_analyzed": int(video.get("frames_analyzed", 0) or 0),

        "labels_detailed": video.get("labels_detailed") or [],
        "text_detailed": video.get("text_detailed") or [],
        "celebrities_detailed": video.get("celebrities_detailed") or [],
        "moderation_labels": video.get("moderation_labels") or [],
        "moderation_detailed": video.get("moderation_detailed") or [],
        "faces_summary": video.get("faces_summary") or {},

        # Timed transcript
        "transcript_segments": video.get("transcript_segments") or [],
        "transcript_words_count": int(len(video.get("transcript_words") or [])),

        "reprocessed_at": video.get("reprocessed_at"),
    }

    if include_frames:
        response["frames"] = video.get("frames") or []
    if include_words:
        response["transcript_words"] = video.get("transcript_words") or []

    return jsonify(response), 200


@app.route("/video-file/<video_id>", methods=["GET"])
def get_video_file(video_id: str) -> Any:
    """Stream the original uploaded video file for playback in the UI."""
    video = next((v for v in VIDEO_INDEX if v.get("id") == video_id), None)
    if not video:
        return jsonify({"error": "Video not found"}), 404

    stored_filename = video.get("stored_filename")
    if not stored_filename:
        file_path_value = (video.get("file_path") or "").strip()
        stored_filename = Path(file_path_value).name if file_path_value else ""
    if not stored_filename:
        return jsonify({"error": "Video is missing stored_filename"}), 400

    video_path = _absolute_video_path(stored_filename)
    if not video_path.exists():
        legacy_path_value = (video.get("file_path") or "").strip()
        legacy_path = (STORAGE_BASE_DIR / legacy_path_value) if legacy_path_value else None
        if legacy_path and legacy_path.exists():
            video_path = legacy_path
        else:
            return jsonify({"error": "Video file not found on disk"}), 404

    mimetype = mimetypes.guess_type(str(video_path))[0] or "application/octet-stream"
    return send_file(str(video_path), mimetype=mimetype, conditional=True)


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

    frame_interval_seconds = _parse_int_param(
        request.args.get("frame_interval_seconds"),
        default=int(video.get("frame_interval_seconds") or 10),
        min_value=1,
        max_value=30,
    )
    max_frames_to_analyze = _parse_int_param(
        request.args.get("max_frames_to_analyze"),
        default=int(video.get("max_frames_to_analyze") or 1000),
        min_value=1,
        max_value=10000,
    )

    face_recognition_mode = (request.args.get("face_recognition_mode") or "").strip().lower() or None
    if face_recognition_mode == "none":
        face_recognition_mode = None
    allowed_modes = {None, "aws_collection", "local"}
    if face_recognition_mode not in allowed_modes:
        return jsonify({"error": "Invalid face_recognition_mode. Use aws_collection, local, or none."}), 400

    collection_id = request.args.get("collection_id")
    if face_recognition_mode == "aws_collection" and not _rekognition_collection_id_normalize(collection_id):
        return jsonify({"error": "collection_id is required when face_recognition_mode=aws_collection"}), 400

    local_similarity_threshold = _parse_float_param(
        request.args.get("local_similarity_threshold"),
        default=float(video.get("local_similarity_threshold") or 0.35),
        min_value=0.0,
        max_value=1.0,
    )

    try:
        updated_fields = _process_stored_video(
            video_id=video_id,
            stored_video_path=stored_path,
            video_title=video.get("title") or video_id,
            video_description=video.get("description") or "",
            original_filename=video.get("original_filename") or stored_filename,
            frame_interval_seconds=frame_interval_seconds,
            max_frames_to_analyze=max_frames_to_analyze,
            face_recognition_mode=face_recognition_mode,
            collection_id=collection_id,
            local_similarity_threshold=local_similarity_threshold,
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
        
        # Split into chunks (bounded-size chunking so search results aren't whole-file dumps)
        chunks = _chunk_text_for_indexing(content)
        if not chunks:
            chunks = [content[:1000]]
        
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
        query_terms = [t for t in query.split() if t]

        # If the document looks like a Movie — Actors list, return titles-only matches.
        # This gives users the expected UX for queries like "amit".
        movie_results: List[Dict[str, Any]] = []
        for doc in DOCUMENT_INDEX:
            full_text = doc.get("full_text") or ""
            titles = _extract_movie_titles_by_actor(full_text, query_terms)
            if not titles:
                continue

            # Return a compact list of titles; keep response shape stable with "text".
            movie_results.append({
                "document_id": doc.get("id"),
                "document_title": doc.get("title"),
                "text": "\n".join(titles[: min(len(titles), 25)]),
                "matches_count": len(titles),
                "similarity_score": 1.0,
                "cosine_similarity": 1.0,
            })

        if movie_results:
            movie_results.sort(key=lambda r: (r.get("matches_count", 0), r.get("document_title") or ""), reverse=True)
            return jsonify({
                "query": query,
                "results": movie_results[:top_k]
            }), 200

        # Otherwise, fall back to semantic snippet search.
        query_embedding = _generate_embedding(query)

        if not query_embedding:
            return jsonify({"error": "Failed to generate query embedding"}), 500
        
        # Search across all chunks in all documents.
        # Enforce prefix-term containment (see _chunk_matches_terms) and return only the best hit per document.
        best_by_document: Dict[str, Dict[str, Any]] = {}
        for doc in DOCUMENT_INDEX:
            doc_id = doc.get("id")
            if not doc_id:
                continue

            best_hit: Dict[str, Any] | None = None
            for chunk in doc.get("chunks", []):
                chunk_text = (chunk or {}).get("text", "")
                if query_terms and not _chunk_matches_terms(chunk_text, query_terms):
                    continue

                cosine_similarity = _compute_similarity(query_embedding, (chunk or {}).get("embedding", []))
                similarity = _normalize_similarity(cosine_similarity)
                snippet = _extract_match_snippet(chunk_text, query_terms) or chunk_text[:400]

                candidate = {
                    "document_id": doc_id,
                    "document_title": doc.get("title") or doc_id,
                    "text": snippet,
                    "similarity_score": round(similarity, 4),
                    "cosine_similarity": round(cosine_similarity, 4),
                }

                if best_hit is None or candidate["similarity_score"] > best_hit["similarity_score"]:
                    best_hit = candidate

            if best_hit is not None:
                best_by_document[doc_id] = best_hit

        results = list(best_by_document.values())
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
    port = int(os.getenv("METADATA_PORT", "5014"))
    debug_raw = (os.getenv("DEBUG") or "false").strip().lower()
    reloader_raw = (os.getenv("RELOADER") or "false").strip().lower()
    debug = debug_raw in {"1", "true", "yes", "y", "on"}
    use_reloader = reloader_raw in {"1", "true", "yes", "y", "on"}
    app.run(host="0.0.0.0", port=port, debug=debug, use_reloader=use_reloader)
