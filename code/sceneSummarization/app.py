#!/usr/bin/env python3
"""Scene Summarization Service

This Flask service ingests still images or video clips, extracts rich scene
metadata with a cloud vision API, composes natural-language recaps with a
managed language model, and renders voiceover audio with a neural speech engine.
"""
from __future__ import annotations

import json
import math
import os
import shutil
import subprocess
import tempfile
import uuid
from collections import Counter, defaultdict
from datetime import datetime
from typing import Any, Dict, List

from flask import Flask, jsonify, request, send_file
from flask_cors import CORS
from werkzeug.utils import secure_filename
from shared.env_loader import load_environment

load_environment()

import boto3
from botocore.exceptions import BotoCoreError, ClientError

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOAD_FOLDER = os.path.join(BASE_DIR, "uploads")
OUTPUT_FOLDER = os.path.join(BASE_DIR, "outputs")
AUDIO_FOLDER = os.path.join(OUTPUT_FOLDER, "audio")
METADATA_FOLDER = os.path.join(OUTPUT_FOLDER, "metadata")
FRAME_CACHE = os.path.join(BASE_DIR, "frames")

for folder in [UPLOAD_FOLDER, OUTPUT_FOLDER, AUDIO_FOLDER, METADATA_FOLDER, FRAME_CACHE]:
    os.makedirs(folder, exist_ok=True)

MAX_CONTENT_LENGTH = 2 * 1024 * 1024 * 1024  # 2GB
ALLOWED_EXTENSIONS = {
    "jpg",
    "jpeg",
    "png",
    "bmp",
    "webp",
    "tiff",
    "heic",
    "gif",
    "mp4",
    "mov",
    "avi",
    "mkv",
    "m4v",
    "webm",
}

AWS_REGION = os.getenv("AWS_REGION")
BEDROCK_REGION = os.getenv("BEDROCK_REGION") or AWS_REGION
if not BEDROCK_REGION:
    raise RuntimeError("Set BEDROCK_REGION or AWS_REGION before starting scene summarization service")

REKOGNITION_REGION = os.getenv("REKOGNITION_REGION", BEDROCK_REGION)
POLLY_REGION = os.getenv("POLLY_REGION", BEDROCK_REGION)
SCENE_MODEL_ID = os.getenv("SCENE_SUMMARY_MODEL_ID", "meta.llama3-70b-instruct-v1:0")
DEFAULT_VOICE_ID = os.getenv("SCENE_SUMMARY_VOICE_ID", "Joanna")
SUMMARY_MAX_TOKENS = int(os.getenv("SCENE_SUMMARY_MAX_TOKENS", "600"))
SUMMARY_TEMPERATURE = float(os.getenv("SCENE_SUMMARY_TEMPERATURE", "0.4"))
SUMMARY_TOP_P = float(os.getenv("SCENE_SUMMARY_TOP_P", "0.9"))
SCENE_S3_BUCKET = os.getenv("SCENE_SUMMARY_S3_BUCKET") or os.getenv("AWS_S3_BUCKET")
SCENE_S3_PREFIX = os.getenv("SCENE_SUMMARY_S3_PREFIX", "scene-summaries/")
FRAME_STRIDE_SECONDS = float(os.getenv("SCENE_SUMMARY_FRAME_STRIDE_SECONDS", "1.7"))
MAX_SCENE_FRAMES = int(os.getenv("SCENE_SUMMARY_MAX_FRAMES", "120"))
VIDEO_ENGINE_MODE = "ffmpeg"

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = MAX_CONTENT_LENGTH


def _resolve_binary(
    default_name: str,
    env_keys: tuple[str, ...],
    extra_paths: tuple[str, ...] = (),
) -> str | None:
    """Resolve an executable path from environment overrides and common install locations."""

    for key in env_keys:
        candidate = os.getenv(key)
        if not candidate:
            continue
        candidate = candidate.strip()
        if not candidate:
            continue
        if os.path.isfile(candidate) and os.access(candidate, os.X_OK):
            return candidate
        resolved = shutil.which(candidate)
        if resolved:
            return resolved

    resolved_default = shutil.which(default_name)
    if resolved_default:
        return resolved_default

    for candidate in extra_paths:
        if os.path.isfile(candidate) and os.access(candidate, os.X_OK):
            return candidate

    return None


FFMPEG_BINARY = _resolve_binary(
    "ffmpeg",
    ("SCENE_SUMMARY_FFMPEG", "FFMPEG_BINARY", "FFMPEG_PATH"),
    (
        "/opt/homebrew/bin/ffmpeg",
        "/usr/local/bin/ffmpeg",
        "/usr/bin/ffmpeg",
    ),
)


def _derive_ffprobe() -> str | None:
    explicit = _resolve_binary(
        "ffprobe",
        ("SCENE_SUMMARY_FFPROBE", "FFPROBE_BINARY", "FFPROBE_PATH"),
        (
            "/opt/homebrew/bin/ffprobe",
            "/usr/local/bin/ffprobe",
            "/usr/bin/ffprobe",
        ),
    )
    if explicit:
        return explicit
    if FFMPEG_BINARY:
        sibling = os.path.join(os.path.dirname(FFMPEG_BINARY), "ffprobe")
        if os.path.isfile(sibling) and os.access(sibling, os.X_OK):
            return sibling
    return None


FFPROBE_BINARY = _derive_ffprobe()


def _cors_origins() -> List[str] | str:
    configured = os.getenv("CORS_ALLOWED_ORIGINS") or os.getenv("CORS_ALLOWED_ORIGIN")
    if configured:
        configured = configured.strip()
        if configured == "*":
            return "*"
        origins = [origin.strip().rstrip("/") for origin in configured.split(",") if origin.strip()]
        return origins or ["http://localhost:3000", "https://localhost:3000"]

    defaults = ["http://localhost:3000", "http://127.0.0.1:3000", "http://0.0.0.0:3000"]
    https_defaults = [origin.replace("http://", "https://", 1) for origin in defaults]
    derived = defaults + https_defaults

    frontend_url = os.getenv("FRONTEND_URL")
    if frontend_url:
        cleaned = frontend_url.strip().rstrip("/")
        derived.append(cleaned)
        if cleaned.startswith("http://"):
            derived.append(cleaned.replace("http://", "https://", 1))

    return derived


cors_origins = _cors_origins()
if cors_origins == "*":
    CORS(app, resources={r"/*": {"origins": "*"}}, supports_credentials=False)
else:
    CORS(app, resources={r"/*": {"origins": cors_origins}}, supports_credentials=False)


def _safe_client(service_name: str, region: str | None):
    try:
        return boto3.client(service_name, region_name=region)  # type: ignore[call-arg]
    except Exception as exc:  # pragma: no cover - depends on env
        app.logger.warning("Unable to create %s client: %s", service_name, exc)
        return None


rekognition = _safe_client("rekognition", REKOGNITION_REGION)
bedrock_runtime = _safe_client("bedrock-runtime", BEDROCK_REGION)
polly = _safe_client("polly", POLLY_REGION)
s3 = _safe_client("s3", os.getenv("S3_REGION") or BEDROCK_REGION)


def _service_ready() -> bool:
    return bool(rekognition and bedrock_runtime and polly)


def allowed_file(filename: str) -> bool:
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def _s3_key_for_video(file_id: str, original_name: str) -> str:
    prefix = (SCENE_S3_PREFIX or "").strip("/")
    safe_name = secure_filename(original_name) or "upload"
    key = f"{file_id}/{safe_name}"
    if prefix:
        return f"{prefix}/{key}"
    return key


def _upload_video_to_s3(local_path: str, key: str) -> str | None:
    if not (s3 and SCENE_S3_BUCKET):
        return None
    try:
        extra_args: Dict[str, Any] = {"ACL": "private"}
        s3.upload_file(local_path, SCENE_S3_BUCKET, key, ExtraArgs=extra_args)
        return key
    except Exception as exc:  # pragma: no cover - depends on env
        app.logger.error("Failed to upload %s to s3://%s/%s: %s", local_path, SCENE_S3_BUCKET, key, exc)
        return None


def _analyse_image_bytes(image_bytes: bytes) -> Dict[str, Any]:
    if not rekognition:
        raise RuntimeError("Vision analysis client is not configured")

    frame_result: Dict[str, Any] = {
        "labels": [],
        "faces": [],
        "celebrities": [],
        "text": [],
    }

    try:
        label_response = rekognition.detect_labels(
            Image={"Bytes": image_bytes},
            MaxLabels=25,
            MinConfidence=55.0,
        )
        for label in label_response.get("Labels", []):
            frame_result["labels"].append(
                {
                    "name": label.get("Name"),
                    "confidence": label.get("Confidence"),
                    "parents": [parent.get("Name") for parent in label.get("Parents", []) if parent.get("Name")],
                }
            )
    except (BotoCoreError, ClientError) as error:
        frame_result.setdefault("errors", []).append(f"detect_labels: {error}")

    try:
        face_response = rekognition.detect_faces(Image={"Bytes": image_bytes}, Attributes=["ALL"])
        for face in face_response.get("FaceDetails", []):
            emotions = [
                {
                    "type": emotion.get("Type"),
                    "confidence": emotion.get("Confidence"),
                }
                for emotion in face.get("Emotions", [])
            ]
            frame_result["faces"].append(
                {
                    "gender": face.get("Gender", {}).get("Value"),
                    "ageRange": face.get("AgeRange"),
                    "emotions": emotions,
                    "faceConfidence": face.get("Confidence"),
                    "beard": face.get("Beard", {}).get("Value"),
                    "mustache": face.get("Mustache", {}).get("Value"),
                    "sunglasses": face.get("Sunglasses", {}).get("Value"),
                    "smile": face.get("Smile", {}).get("Value"),
                }
            )
    except (BotoCoreError, ClientError) as error:
        frame_result.setdefault("errors", []).append(f"detect_faces: {error}")

    try:
        celeb_response = rekognition.recognize_celebrities(Image={"Bytes": image_bytes})
        for celeb in celeb_response.get("CelebrityFaces", []):
            frame_result["celebrities"].append(
                {
                    "name": celeb.get("Name"),
                    "confidence": celeb.get("MatchConfidence"),
                    "urls": celeb.get("Urls", [])[:3],
                }
            )
    except (BotoCoreError, ClientError) as error:
        frame_result.setdefault("errors", []).append(f"recognize_celebrities: {error}")

    try:
        text_response = rekognition.detect_text(Image={"Bytes": image_bytes})
        unique_lines = []
        seen = set()
        for detection in text_response.get("TextDetections", []):
            if detection.get("Type") != "LINE":
                continue
            text = detection.get("DetectedText")
            if text and text not in seen:
                unique_lines.append(text)
                seen.add(text)
        frame_result["text"] = unique_lines
    except (BotoCoreError, ClientError) as error:
        frame_result.setdefault("errors", []).append(f"detect_text: {error}")

    return frame_result


def _probe_video_duration(video_path: str) -> float | None:
    probe_binary = FFPROBE_BINARY or shutil.which("ffprobe")
    if not probe_binary:
        app.logger.error("ffprobe binary not found; cannot probe video duration.")
        return None
    command = [
        probe_binary,
        "-v",
        "error",
        "-select_streams",
        "v:0",
        "-show_entries",
        "stream=duration",
        "-of",
        "default=noprint_wrappers=1:nokey=1",
        video_path,
    ]
    try:
        output = subprocess.check_output(command, stderr=subprocess.STDOUT)
        value = output.decode("utf-8", errors="ignore").strip()
        return float(value)
    except (subprocess.CalledProcessError, FileNotFoundError, ValueError):
        return None


def _extract_frames_local(video_path: str) -> List[str]:
    """Extract frames using the local ffmpeg binary."""

    extracted: List[str] = []
    tmp_dir = tempfile.mkdtemp(prefix="frames_", dir=FRAME_CACHE)
    duration = _probe_video_duration(video_path)
    stride = max(0.5, FRAME_STRIDE_SECONDS)

    if duration and duration > 0:
        estimated_frames = int(math.ceil(duration / stride))
        frame_count = max(1, min(MAX_SCENE_FRAMES, estimated_frames))
    else:
        frame_count = max(1, min(MAX_SCENE_FRAMES, 60))

    try:
        ffmpeg_binary = FFMPEG_BINARY or shutil.which("ffmpeg")
        if not ffmpeg_binary:
            error_message = (
                "ffmpeg binary not found; set SCENE_SUMMARY_FFMPEG or ensure ffmpeg is installed."
            )
            app.logger.error("%s (input=%s)", error_message, video_path)
            raise RuntimeError(error_message)
        for index in range(frame_count):
            output_path = os.path.join(tmp_dir, f"frame_{index:04d}.jpg")
            if duration and duration > 0:
                time_offset = min(index * stride, max(duration - 0.5, 0.0))
            else:
                time_offset = index * stride

            command = [
                ffmpeg_binary,
                "-y",
                "-hide_banner",
                "-loglevel",
                "error",
                "-ss",
                str(time_offset),
                "-i",
                video_path,
                "-frames:v",
                "1",
                "-q:v",
                "2",
                output_path,
            ]
            try:
                subprocess.run(command, check=True)
            except (subprocess.CalledProcessError, FileNotFoundError) as exc:
                app.logger.error("ffmpeg failed while extracting frame %s: %s", index, exc)
                continue
            if os.path.exists(output_path):
                extracted.append(output_path)

        return extracted
    finally:
        if not extracted:
            shutil.rmtree(tmp_dir, ignore_errors=True)


def _extract_frames(
    video_path: str,
    *,
    file_id: str,
    s3_key: str | None,
) -> List[str]:
    """Extract frames from the video using the local ffmpeg binary."""

    try:
        return _extract_frames_local(video_path)
    except RuntimeError as exc:
        raise RuntimeError(str(exc))


def _analyse_media(
    file_path: str,
    media_type: str,
    *,
    file_id: str,
    s3_key: str | None = None,
) -> Dict[str, Any]:
    frame_results: List[Dict[str, Any]] = []
    if media_type == "video":
        frames = _extract_frames(file_path, file_id=file_id, s3_key=s3_key)
        if not frames:
            raise RuntimeError("Unable to extract frames from the provided video")
        for frame in frames:
            with open(frame, "rb") as fp:
                frame_results.append(_analyse_image_bytes(fp.read()))
        # Clean up temporary frame directory
        parent_dir = os.path.dirname(frames[0])
        shutil.rmtree(parent_dir, ignore_errors=True)
    else:
        with open(file_path, "rb") as fp:
            frame_results.append(_analyse_image_bytes(fp.read()))

    return _aggregate_results(frame_results, media_type)


INDOOR_HINTS = {"indoors", "interior", "room", "office", "studio", "kitchen", "living room"}
OUTDOOR_HINTS = {"outdoors", "outdoor", "nature", "urban", "street", "forest", "beach", "stadium"}
ACTION_HINTS = {"action", "fight", "battle", "sports", "running", "explosion", "car chase", "race"}
DIALOGUE_HINTS = {"conversation", "talk", "speech", "interview", "meeting", "discussion", "lecture", "press conference"}
LIGHTING_HINTS = {"spotlight", "stage", "dark", "night", "day", "sunset", "sunrise", "shadow"}
CROWD_HINTS = {"crowd", "audience", "group", "team", "people"}


def _aggregate_results(frame_results: List[Dict[str, Any]], media_type: str) -> Dict[str, Any]:
    label_buckets: Dict[str, Dict[str, float]] = {
        "objects": defaultdict(float),
        "scenes": defaultdict(float),
        "activities": defaultdict(float),
    }
    label_counts: Dict[str, Dict[str, int]] = {
        "objects": defaultdict(int),
        "scenes": defaultdict(int),
        "activities": defaultdict(int),
    }
    text_lines: set[str] = set()
    celebrity_scores: Dict[str, float] = defaultdict(float)
    emotions_counter: Counter[str] = Counter()
    people_summaries: List[Dict[str, Any]] = []
    context_flags: Dict[str, Counter[str]] = {
        "environment": Counter(),
        "lighting": Counter(),
        "crowd": Counter(),
        "activity": Counter(),
    }

    for frame in frame_results:
        for label in frame.get("labels", []):
            name = (label.get("name") or "").strip()
            if not name:
                continue
            name_lower = name.lower()
            parents = {str(parent).lower() for parent in label.get("parents", []) if parent}
            confidence = float(label.get("confidence") or 0.0)

            bucket_key = "objects"
            if parents & {"activity", "activities"} or name_lower in ACTION_HINTS | DIALOGUE_HINTS:
                bucket_key = "activities"
            elif parents & {"scene"} or name_lower in OUTDOOR_HINTS | INDOOR_HINTS:
                bucket_key = "scenes"

            if name_lower in INDOOR_HINTS:
                context_flags["environment"]["indoor"] += 1
            if name_lower in OUTDOOR_HINTS:
                context_flags["environment"]["outdoor"] += 1
            if name_lower in ACTION_HINTS:
                context_flags["activity"]["action"] += 1
            if name_lower in DIALOGUE_HINTS:
                context_flags["activity"]["dialogue"] += 1
            if name_lower in LIGHTING_HINTS:
                context_flags["lighting"][name_lower] += 1
            if name_lower in CROWD_HINTS:
                context_flags["crowd"][name_lower] += 1

            label_buckets[bucket_key][name] = max(label_buckets[bucket_key][name], confidence)
            label_counts[bucket_key][name] += 1

        for text in frame.get("text", []):
            cleaned = text.strip()
            if cleaned:
                text_lines.add(cleaned)

        for celeb in frame.get("celebrities", []):
            name = celeb.get("name")
            confidence = float(celeb.get("confidence") or 0.0)
            if name:
                celebrity_scores[name] = max(celebrity_scores[name], confidence)

        for face in frame.get("faces", []):
            emotions = [
                (emotion.get("type"), float(emotion.get("confidence") or 0.0))
                for emotion in face.get("emotions", [])
                if emotion.get("type")
            ]
            for emotion_type, confidence in emotions:
                if confidence >= 20.0:
                    emotions_counter[emotion_type] += confidence
            if emotions:
                top_emotions = sorted(emotions, key=lambda item: item[1], reverse=True)[:3]
            else:
                top_emotions = []
            summary = {
                "gender": face.get("gender"),
                "ageRange": face.get("ageRange"),
                "dominantEmotions": [emotion for emotion, _ in top_emotions],
                "faceConfidence": face.get("faceConfidence"),
                "smile": face.get("smile"),
                "sunglasses": face.get("sunglasses"),
            }
            people_summaries.append(summary)

    def _sorted_bucket(bucket_key: str, limit: int = 10) -> List[Dict[str, Any]]:
        bucket = label_buckets[bucket_key]
        counts = label_counts[bucket_key]
        ranked = sorted(bucket.items(), key=lambda item: item[1], reverse=True)
        return [
            {
                "label": name,
                "confidence": round(confidence, 2),
                "frameOccurrences": counts[name],
            }
            for name, confidence in ranked[:limit]
        ]

    emotions_overview = [
        {"emotion": emotion, "score": round(score, 2)}
        for emotion, score in emotions_counter.most_common(5)
    ]

    celebrities = [
        {"name": name, "confidence": round(score, 2)}
        for name, score in sorted(celebrity_scores.items(), key=lambda item: item[1], reverse=True)
    ]

    environment = "unknown"
    env_counts = context_flags["environment"]
    if env_counts:
        if env_counts["indoor"] > env_counts["outdoor"]:
            environment = "indoor"
        elif env_counts["outdoor"] > env_counts["indoor"]:
            environment = "outdoor"

    if environment == "unknown" and env_counts:
        environment = env_counts.most_common(1)[0][0]

    activity_focus = "unclear"
    activity_counts = context_flags["activity"]
    if activity_counts:
        activity_focus = activity_counts.most_common(1)[0][0]

    lighting = None
    lighting_counts = context_flags["lighting"]
    if lighting_counts:
        lighting = lighting_counts.most_common(1)[0][0]

    crowd_indicator = None
    crowd_counts = context_flags["crowd"]
    if crowd_counts:
        crowd_indicator = crowd_counts.most_common(1)[0][0]

    return {
        "mediaType": media_type,
        "framesAnalysed": len(frame_results),
        "objects": _sorted_bucket("objects"),
        "activities": _sorted_bucket("activities", limit=6),
        "scenes": _sorted_bucket("scenes", limit=6),
        "textDetections": sorted(text_lines),
        "celebrities": celebrities,
        "people": people_summaries[:10],
        "dominantEmotions": emotions_overview,
        "context": {
            "environment": environment,
            "activityFocus": activity_focus,
            "lighting": lighting,
            "crowdIndicator": crowd_indicator,
        },
    }


def _invoke_bedrock(prompt: str) -> Dict[str, Any]:
    if not bedrock_runtime:
        raise RuntimeError("Language generation client is not configured")
    body = {
        "prompt": prompt,
        "max_gen_len": SUMMARY_MAX_TOKENS,
        "temperature": SUMMARY_TEMPERATURE,
        "top_p": SUMMARY_TOP_P,
    }
    response = bedrock_runtime.invoke_model(
        modelId=SCENE_MODEL_ID,
        body=json.dumps(body),
        accept="application/json",
        contentType="application/json",
    )
    raw_body = response["body"].read()
    return json.loads(raw_body)


def _extract_text_from_bedrock_response(response_body: Dict[str, Any]) -> str:
    if not response_body:
        return ""

    def _from_content(value: Any) -> str:
        if isinstance(value, list):
            return "".join(_from_content(item) for item in value)
        if isinstance(value, dict):
            candidates = []
            if value.get("text"):
                candidates.append(str(value["text"]))
            if value.get("result"):
                candidates.append(str(value["result"]))
            if value.get("content"):
                candidates.append(_from_content(value["content"]))
            return "".join(candidates)
        return str(value)

    for key in ("output", "generation", "result", "message"):
        if key in response_body and isinstance(response_body[key], str):
            return response_body[key]

    if "outputs" in response_body:
        return "".join(_from_content(item) for item in response_body["outputs"])

    if "content" in response_body:
        return _from_content(response_body["content"])

    if "messages" in response_body:
        for message in response_body["messages"]:
            if isinstance(message, dict) and message.get("role") == "assistant":
                return _from_content(message.get("content"))

    return ""


def _parse_summary_payload(raw_text: str) -> Dict[str, Any]:
    candidate = raw_text.strip()
    if not candidate:
        return {}

    # Strip markdown fences if present
    if candidate.startswith("```") and candidate.endswith("```"):
        candidate = candidate.strip("`").split("\n", 1)[-1]

    # Attempt to locate JSON object boundaries
    start = candidate.find("{")
    end = candidate.rfind("}")
    if start != -1 and end != -1 and end > start:
        candidate = candidate[start : end + 1]

    try:
        return json.loads(candidate)
    except json.JSONDecodeError:
        return {}


def _fallback_summary(metadata: Dict[str, Any]) -> Dict[str, Any]:
    context = metadata.get("context", {})
    environment = context.get("environment") or "unknown surroundings"
    activity = context.get("activityFocus") or "mixed activity"
    dominant_emotions = metadata.get("dominantEmotions", [])
    emotion_phrase = "balanced"
    if dominant_emotions:
        emotion_phrase = ", ".join(item["emotion"].lower() for item in dominant_emotions[:2])

    key_objects = [item["label"] for item in metadata.get("objects", [])[:3]]
    object_phrase = ", ".join(key_objects) if key_objects else "several visual details"

    summary_text = (
        f"A {environment} scene shows {object_phrase}. The mood leans toward {emotion_phrase}, "
        f"with {activity} elements shaping the moment."
    )
    highlights = []
    if key_objects:
        highlights.append(f"Prominent visuals: {', '.join(key_objects)}")
    if dominant_emotions:
        highlights.append(
            "Emotional tone: "
            + ", ".join(f"{item['emotion'].title()} ({item['score']:.0f})" for item in dominant_emotions[:3])
        )
    if metadata.get("textDetections"):
        highlights.append("Text on screen: " + "; ".join(metadata["textDetections"][:3]))

    ssml = (
        "<speak><p>"
        f"In this {environment} moment, {object_phrase} fill the frame. "
        f"The atmosphere feels {emotion_phrase}, and we sense {activity} energy."
        "</p></speak>"
    )

    return {
        "summary": summary_text,
        "highlights": highlights,
        "ssml": ssml,
    }


def _build_bedrock_prompt(metadata: Dict[str, Any]) -> str:
    structured_json = json.dumps(metadata, ensure_ascii=False, indent=2)
    return (
        "You are a senior story editor building highlight recaps for post-production teams. "
        "Given the structured scene analysis JSON, craft a concise natural-language summary.\n"
        "Return ONLY valid JSON with keys: summary (string), highlights (array of 3 short bullet strings), "
        "and ssml (string with a <speak> root). Keep the summary under 120 words and ensure the SSML is expressive, "
        "using <p>, <emphasis>, and <break> tags sparingly.\n\n"
        f"Scene metadata:\n{structured_json}\n"
    )


def _generate_summary(metadata: Dict[str, Any]) -> Dict[str, Any]:
    try:
        prompt = _build_bedrock_prompt(metadata)
        response = _invoke_bedrock(prompt)
        generation_text = _extract_text_from_bedrock_response(response)
        parsed = _parse_summary_payload(generation_text)
        if parsed.get("summary") and parsed.get("ssml"):
            return parsed
    except Exception as exc:  # pragma: no cover - depends on external service
        app.logger.error("Language summarization failed: %s", exc)
    return _fallback_summary(metadata)


def _synth_audio(file_id: str, ssml: str, voice_id: str) -> str | None:
    if not polly:
        raise RuntimeError("Speech synthesis client is not configured")
    try:
        response = polly.synthesize_speech(
            Text=ssml,
            TextType="ssml",
            VoiceId=voice_id,
            OutputFormat="mp3",
        )
    except (BotoCoreError, ClientError) as error:
        app.logger.error("Speech synthesis request failed: %s", error)
        return None

    audio_path = os.path.join(AUDIO_FOLDER, f"{file_id}.mp3")
    audio_stream = response.get("AudioStream")
    if audio_stream:
        with open(audio_path, "wb") as output:
            output.write(audio_stream.read())
        return audio_path
    return None


def _store_result(file_id: str, payload: Dict[str, Any]) -> None:
    metadata_path = os.path.join(METADATA_FOLDER, f"{file_id}.json")
    with open(metadata_path, "w", encoding="utf-8") as fp:
        json.dump(payload, fp, ensure_ascii=False, indent=2)


def _detect_media_type(filename: str) -> str:
    ext = filename.rsplit(".", 1)[1].lower()
    if ext in {"mp4", "mov", "avi", "mkv", "m4v", "webm"}:
        return "video"
    return "image"


@app.route("/health", methods=["GET"])
def health() -> Any:
    return jsonify(
        {
            "status": "ok" if _service_ready() else "degraded",
            "bedrockRegion": BEDROCK_REGION,
            "rekognitionRegion": REKOGNITION_REGION,
            "pollyRegion": POLLY_REGION,
            "model": SCENE_MODEL_ID,
        }
    )


@app.route("/summarize", methods=["POST"])
def summarize_scene() -> Any:
    if not _service_ready():
        return (
            jsonify({"error": "Scene summarization service is not fully configured. Verify service credentials and regions."}),
            503,
        )

    if "media" not in request.files:
        return jsonify({"error": "A media file is required."}), 400

    media_file = request.files["media"]
    if media_file.filename == "":
        return jsonify({"error": "Uploaded media is missing a filename."}), 400

    if not allowed_file(media_file.filename):
        return jsonify({"error": "Unsupported file type."}), 400

    file_id = str(uuid.uuid4())
    filename = secure_filename(media_file.filename)
    extension = filename.rsplit(".", 1)[1].lower()
    saved_filename = f"{file_id}.{extension}"
    saved_path = os.path.join(UPLOAD_FOLDER, saved_filename)
    media_file.save(saved_path)

    media_type = _detect_media_type(filename)
    s3_video_key: str | None = None

    if media_type == "video":
        s3_key_candidate = _s3_key_for_video(file_id, filename)
        uploaded_key = _upload_video_to_s3(saved_path, s3_key_candidate)
        if uploaded_key:
            s3_video_key = uploaded_key

    try:
        structured_metadata = _analyse_media(
            saved_path,
            media_type,
            file_id=file_id,
            s3_key=s3_video_key,
        )
    except Exception as exc:
        app.logger.exception("Scene analysis failed: %s", exc)
        return jsonify({"error": f"Scene analysis failed: {exc}"}), 500

    summary_payload = _generate_summary(structured_metadata)
    summary_text = summary_payload.get("summary") or ""
    ssml_text = summary_payload.get("ssml") or ""
    highlights = summary_payload.get("highlights") or []

    if not ssml_text:
        ssml_text = "<speak><p>Scene summary is currently unavailable.</p></speak>"

    voice_id = request.form.get("voice_id") or DEFAULT_VOICE_ID
    audio_path = _synth_audio(file_id, ssml_text, voice_id)

    response_body = {
        "file_id": file_id,
        "created_at": datetime.utcnow().isoformat() + "Z",
        "media_type": media_type,
        "summary": summary_text,
        "highlights": highlights,
        "ssml": ssml_text,
        "voice_id": voice_id,
        "metadata": structured_metadata,
        "audio_url": f"/audio/{file_id}" if audio_path else None,
    }

    if s3_video_key:
        response_body["source_video"] = {
            "bucket": SCENE_S3_BUCKET,
            "key": s3_video_key,
            "uri": f"s3://{SCENE_S3_BUCKET}/{s3_video_key}" if SCENE_S3_BUCKET else None,
        }

    _store_result(file_id, response_body)
    return jsonify(response_body)


@app.route("/result/<file_id>", methods=["GET"])
def get_result(file_id: str) -> Any:
    metadata_path = os.path.join(METADATA_FOLDER, f"{file_id}.json")
    if not os.path.exists(metadata_path):
        return jsonify({"error": "Result not found."}), 404
    with open(metadata_path, "r", encoding="utf-8") as fp:
        data = json.load(fp)
    return jsonify(data)


@app.route("/audio/<file_id>", methods=["GET"])
def get_audio(file_id: str) -> Any:
    audio_path = os.path.join(AUDIO_FOLDER, f"{file_id}.mp3")
    if not os.path.exists(audio_path):
        return jsonify({"error": "Audio not found."}), 404
    return send_file(audio_path, mimetype="audio/mpeg", conditional=True)


if __name__ == "__main__":  # pragma: no cover - script entry point
    port = int(os.getenv("PORT", "5004"))
    app.run(host="0.0.0.0", port=port, debug=os.getenv("DEBUG", "false").lower() == "true")
