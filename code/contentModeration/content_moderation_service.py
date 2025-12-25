#!/usr/bin/env python3
"""Content Moderation Service

Accepts short-form video uploads, routes them to AWS video moderation APIs,
and returns the timestamps for each moderation label that crosses the
configured confidence threshold.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import time
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Set

from flask import Flask, jsonify, request
from flask_cors import CORS
from werkzeug.utils import secure_filename
from shared.env_loader import load_environment

load_environment()

import boto3
from botocore.exceptions import BotoCoreError, ClientError

BASE_DIR = Path(__file__).resolve().parent
UPLOAD_DIR = BASE_DIR / "uploads"
REPORT_DIR = BASE_DIR / "reports"
ALLOWED_EXTENSIONS = {"mp4", "mov", "mkv", "m4v", "avi", "webm"}

for directory in (UPLOAD_DIR, REPORT_DIR):
    directory.mkdir(parents=True, exist_ok=True)

MAX_CONTENT_LENGTH = int(
    os.getenv("CONTENT_MODERATION_MAX_UPLOAD_BYTES", str(2 * 1024 * 1024 * 1024))
)
DEFAULT_MIN_CONFIDENCE = float(os.getenv("CONTENT_MODERATION_MIN_CONFIDENCE", "75"))
POLL_INTERVAL_SECONDS = float(os.getenv("CONTENT_MODERATION_POLL_INTERVAL", "2"))
MAX_WAIT_SECONDS = int(os.getenv("CONTENT_MODERATION_MAX_WAIT_SECONDS", "900"))
TRANSCODE_ON_UNSUPPORTED = os.getenv("CONTENT_MODERATION_TRANSCODE", "1") not in {"0", "false", "False"}
AWS_REGION = os.getenv("CONTENT_MODERATION_REGION") or os.getenv("AWS_REGION")
if not AWS_REGION:
    raise RuntimeError("Set CONTENT_MODERATION_REGION or AWS_REGION before starting content moderation service")


def _which(binary_name: str) -> Optional[str]:
    try:
        return shutil.which(binary_name)
    except Exception:  # pragma: no cover
        return None


FFMPEG_BINARY = _which("ffmpeg")
FFPROBE_BINARY = _which("ffprobe")


def _probe_media(local_path: Path) -> Dict[str, Any]:
    if not FFPROBE_BINARY:
        raise RuntimeError(
            "ffprobe is required to validate/transcode uploads. Ensure ffmpeg is installed and on PATH."
        )
    cmd = [
        FFPROBE_BINARY,
        "-v",
        "error",
        "-show_streams",
        "-show_format",
        "-of",
        "json",
        str(local_path),
    ]
    try:
        out = subprocess.check_output(cmd, stderr=subprocess.STDOUT, text=True)
    except subprocess.CalledProcessError as exc:
        raise RuntimeError(f"ffprobe failed: {exc.output}") from exc
    try:
        return json.loads(out)
    except json.JSONDecodeError as exc:
        raise RuntimeError("ffprobe returned invalid JSON") from exc


def _extract_codec_info(probe: Dict[str, Any]) -> Dict[str, Optional[str]]:
    fmt = (probe.get("format") or {})
    format_name = fmt.get("format_name")
    video_codec = None
    audio_codec = None

    for stream in probe.get("streams") or []:
        if not isinstance(stream, dict):
            continue
        if stream.get("codec_type") == "video" and not video_codec:
            video_codec = stream.get("codec_name")
        if stream.get("codec_type") == "audio" and not audio_codec:
            audio_codec = stream.get("codec_name")

    return {
        "format": format_name,
        "video_codec": video_codec,
        "audio_codec": audio_codec,
    }


def _is_rekognition_compatible(codec_info: Dict[str, Optional[str]]) -> bool:
    """Best-effort checks for Rekognition StartContentModeration compatibility.

    Rekognition is generally happiest with MP4/MOV containers and H.264 video.
    We'll accept MPEG-4 Part 2 (`mpeg4`) as a best-effort pass-through too.
    """
    format_name = (codec_info.get("format") or "").lower()
    video_codec = (codec_info.get("video_codec") or "").lower()
    audio_codec = (codec_info.get("audio_codec") or "").lower()

    container_ok = any(token in format_name for token in ("mov,mp4", "mp4", "mov"))
    video_ok = video_codec in {"h264", "mpeg4"}
    audio_ok = (not audio_codec) or audio_codec in {"aac", "mp3"}
    return container_ok and video_ok and audio_ok


def _transcode_to_rekognition_mp4(input_path: Path, output_path: Path) -> None:
    if not FFMPEG_BINARY:
        raise RuntimeError(
            "ffmpeg is required to transcode unsupported uploads. Ensure ffmpeg is installed and on PATH."
        )

    cmd = [
        FFMPEG_BINARY,
        "-y",
        "-i",
        str(input_path),
        "-c:v",
        "libx264",
        "-pix_fmt",
        "yuv420p",
        "-preset",
        "veryfast",
        "-crf",
        "23",
        "-c:a",
        "aac",
        "-b:a",
        "128k",
        "-movflags",
        "+faststart",
        str(output_path),
    ]

    try:
        subprocess.check_output(cmd, stderr=subprocess.STDOUT, text=True)
    except subprocess.CalledProcessError as exc:
        raise RuntimeError(f"ffmpeg transcode failed: {exc.output}") from exc


def _ensure_rekognition_ready_video(local_path: Path) -> tuple[Path, Dict[str, Any]]:
    """Return a Rekognition-compatible file path (possibly transcoded) and codec metadata."""
    probe = _probe_media(local_path)
    codec_info = _extract_codec_info(probe)
    result: Dict[str, Any] = {
        "detected": codec_info,
        "transcoded": False,
    }

    if _is_rekognition_compatible(codec_info):
        return local_path, result

    if not TRANSCODE_ON_UNSUPPORTED:
        raise RuntimeError(
            "Unsupported codec/format. Enable CONTENT_MODERATION_TRANSCODE=1 or upload an MP4 (H.264/AAC)."
        )

    output_path = local_path.with_suffix("")
    output_path = output_path.with_name(f"{output_path.name}-rekognition.mp4")
    _transcode_to_rekognition_mp4(local_path, output_path)

    transcoded_probe = _probe_media(output_path)
    transcoded_codec_info = _extract_codec_info(transcoded_probe)
    result["transcoded"] = True
    result["transcoded_detected"] = transcoded_codec_info
    return output_path, result
def _normalise_env_value(raw: Optional[str]) -> Optional[str]:
    if raw is None:
        return None
    cleaned = raw.strip()
    if not cleaned:
        return None
    if cleaned.lower() in {"none", "null", "undefined"}:
        return None
    return cleaned


MODERATION_BUCKET = os.getenv("CONTENT_MODERATION_BUCKET") or os.getenv("AWS_S3_BUCKET")
MODERATION_PREFIX = os.getenv("CONTENT_MODERATION_PREFIX", "content-moderation")
SNS_TOPIC_ARN = _normalise_env_value(os.getenv("CONTENT_MODERATION_SNS_TOPIC_ARN"))
SNS_ROLE_ARN = _normalise_env_value(os.getenv("CONTENT_MODERATION_SNS_ROLE_ARN"))

MODERATION_CATEGORY_OPTIONS: List[Dict[str, str]] = [
    {"key": "Explicit Nudity", "label": "Explicit Nudity"},
    {"key": "Suggestive", "label": "Suggestive"},
    {"key": "Violence", "label": "Violence"},
    {"key": "Visually Disturbing", "label": "Visually Disturbing"},
    {"key": "Rude Gestures", "label": "Rude Gestures"},
    {"key": "Tobacco", "label": "Tobacco / Smoking"},
    {"key": "Drugs", "label": "Drugs"},
    {"key": "Alcohol", "label": "Alcohol"},
    {"key": "Hate Symbols", "label": "Hate Symbols"},
    {"key": "Weapons", "label": "Weapons"},
    {"key": "Gambling", "label": "Gambling"},
]

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = MAX_CONTENT_LENGTH


def _resolve_cors_origins() -> Iterable[str] | str:
    configured = os.getenv("CONTENT_MODERATION_ALLOWED_ORIGINS")
    if configured:
        configured = configured.strip()
        if configured == "*":
            return "*"
        origins = [origin.strip() for origin in configured.split(",") if origin.strip()]
        return origins or [
            "http://localhost:3000",
            "https://localhost:3000",
        ]

    defaults = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://0.0.0.0:3000",
    ]
    https_defaults = [origin.replace("http://", "https://", 1) for origin in defaults]
    derived = defaults + https_defaults
    frontend_url = os.getenv("FRONTEND_URL")
    if frontend_url:
        cleaned = frontend_url.strip().rstrip("/")
        derived.append(cleaned)
        if cleaned.startswith("http://"):
            derived.append(cleaned.replace("http://", "https://", 1))
    return derived


cors_origins = _resolve_cors_origins()
if cors_origins == "*":
    CORS(app, resources={r"/*": {"origins": "*"}}, supports_credentials=False)
else:
    CORS(app, resources={r"/*": {"origins": cors_origins}}, supports_credentials=False)


def _create_client(service_name: str):
    try:
        return boto3.client(service_name, region_name=AWS_REGION)
    except Exception as exc:  # pragma: no cover - depends on environment
        app.logger.warning("Unable to create %s client: %s", service_name, exc)
        return None


rekognition = _create_client("rekognition")
s3 = _create_client("s3")


def _service_ready() -> bool:
    return bool(rekognition and s3 and MODERATION_BUCKET)


def allowed_file(filename: str) -> bool:
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def _build_s3_key(file_id: str, filename: str) -> str:
    safe_name = secure_filename(filename) or "upload"
    prefix = (MODERATION_PREFIX or "").strip("/")
    key = f"{file_id}/{safe_name}"
    if prefix:
        return f"{prefix}/{key}"
    return key


def _upload_to_s3(local_path: Path, s3_key: str) -> None:
    if not (s3 and MODERATION_BUCKET):
        raise RuntimeError("S3 client or bucket is not configured")
    extra_args: Dict[str, Any] = {"ACL": "private"}
    s3.upload_file(str(local_path), MODERATION_BUCKET, s3_key, ExtraArgs=extra_args)


def _start_content_moderation_job(s3_key: str, min_confidence: float, job_tag: str) -> str:
    if not rekognition:
        raise RuntimeError("Rekognition client is not configured")
    notification_channel: Optional[Dict[str, str]] = None
    if SNS_TOPIC_ARN and SNS_ROLE_ARN:
        notification_channel = {
            "SNSTopicArn": SNS_TOPIC_ARN,
            "RoleArn": SNS_ROLE_ARN,
        }
    elif SNS_TOPIC_ARN or SNS_ROLE_ARN:
        app.logger.warning(
            "Partial SNS configuration detected. Provide both CONTENT_MODERATION_SNS_TOPIC_ARN and "
            "CONTENT_MODERATION_SNS_ROLE_ARN or leave them unset. Skipping notification channel."
        )
    kwargs: Dict[str, Any] = {
        "Video": {
            "S3Object": {
                "Bucket": MODERATION_BUCKET,
                "Name": s3_key,
            }
        },
        "MinConfidence": min_confidence,
        "JobTag": job_tag,
    }
    if notification_channel:
        kwargs["NotificationChannel"] = notification_channel
    app.logger.debug(
        "Starting moderation job %s with NotificationChannel=%s (topic configured=%s, role configured=%s)",
        job_tag,
        "present" if "NotificationChannel" in kwargs else "absent",
        bool(SNS_TOPIC_ARN),
        bool(SNS_ROLE_ARN),
    )
    response = rekognition.start_content_moderation(**kwargs)
    return response["JobId"]


def _format_timestamp(timestamp_ms: int) -> Dict[str, Any]:
    seconds = timestamp_ms / 1000.0
    minutes, sec = divmod(seconds, 60)
    hours, minutes = divmod(minutes, 60)
    timecode = f"{int(hours):02d}:{int(minutes):02d}:{sec:06.3f}"
    return {
        "milliseconds": timestamp_ms,
        "seconds": round(seconds, 3),
        "timecode": timecode,
    }


def _normalise_selected_categories(raw: Optional[str]) -> Set[str]:
    if not raw:
        return set()
    return {token.strip().lower() for token in raw.split(",") if token.strip()}


def _category_matches(selection: Set[str], category: Optional[str], name: Optional[str]) -> bool:
    if not selection:
        return True
    normalized_category = (category or "").lower()
    normalized_name = (name or "").lower()
    if normalized_category and normalized_category in selection:
        return True
    if normalized_name and normalized_name in selection:
        return True
    return False


def _poll_moderation_results(job_id: str) -> List[Dict[str, Any]]:
    if not rekognition:
        raise RuntimeError("Rekognition client is not configured")

    start_time = time.time()
    collected: List[Dict[str, Any]] = []
    pagination_token: Optional[str] = None

    while True:
        if (time.time() - start_time) > MAX_WAIT_SECONDS:
            raise TimeoutError(
                f"Content moderation exceeded {MAX_WAIT_SECONDS}s timeout"
            )

        request_kwargs: Dict[str, Any] = {"JobId": job_id}
        if pagination_token:
            request_kwargs["NextToken"] = pagination_token

        response = rekognition.get_content_moderation(**request_kwargs)
        status = response.get("JobStatus")
        if status == "FAILED":
            status_message = (
                response.get("StatusMessage")
                or response.get("ErrorMessage")
                or response.get("ErrorCode")
                or "Unknown failure"
            )
            app.logger.error(
                "Content moderation job %s failed: %s",
                job_id,
                status_message,
            )
            raise RuntimeError(f"Content moderation job failed: {status_message}")

        collected.extend(response.get("ModerationLabels", []))
        pagination_token = response.get("NextToken")

        if status == "SUCCEEDED" and not pagination_token:
            break

        if status == "SUCCEEDED" and pagination_token:
            # continue fetching remaining pages without sleeping
            continue

        time.sleep(POLL_INTERVAL_SECONDS)

    return collected


def _summarise_events(events: List[Dict[str, Any]]) -> Dict[str, Any]:
    summary = {
        "totalFindings": len(events),
        "categories": {},
        "labels": {},
    }
    for event in events:
        category = event.get("category") or "Uncategorized"
        label = event.get("label") or "Unknown"
        summary["categories"].setdefault(category, 0)
        summary["categories"][category] += 1
        summary["labels"].setdefault(label, 0)
        summary["labels"][label] += 1
    return summary


def _store_report(job_id: str, payload: Dict[str, Any]) -> None:
    report_path = REPORT_DIR / f"{job_id}.json"
    with report_path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2)


@app.route("/health", methods=["GET"])
def health() -> Any:
    return jsonify(
        {
            "status": "ok" if _service_ready() else "degraded",
            "region": AWS_REGION,
            "bucket": MODERATION_BUCKET,
            "services": {
                "rekognition": bool(rekognition),
                "s3": bool(s3),
            },
        }
    )


@app.route("/moderation-options", methods=["GET"])
def list_moderation_options() -> Any:
    return jsonify({"options": MODERATION_CATEGORY_OPTIONS})


@app.route("/moderate", methods=["POST"])
def moderate_video() -> Any:
    if not _service_ready():
        return (
            jsonify(
                {
                    "error": "Content moderation service is not fully configured. Verify AWS credentials and S3 bucket settings.",
                }
            ),
            503,
        )

    if "video" not in request.files:
        return jsonify({"error": "Video file is required."}), 400

    uploaded_file = request.files["video"]
    if uploaded_file.filename == "":
        return jsonify({"error": "Uploaded video is missing a filename."}), 400

    if not allowed_file(uploaded_file.filename):
        return (
            jsonify(
                {
                    "error": "Unsupported file type. Please provide MP4, MOV, MKV, M4V, AVI, or WEBM.",
                }
            ),
            400,
        )

    file_id = str(uuid.uuid4())
    filename = secure_filename(uploaded_file.filename)
    saved_path = UPLOAD_DIR / f"{file_id}-{filename}"
    uploaded_file.save(saved_path)
    file_size = saved_path.stat().st_size if saved_path.exists() else 0

    transcoded_path: Optional[Path] = None
    codec_metadata: Dict[str, Any] = {}
    upload_path = saved_path
    upload_filename = filename
    try:
        upload_path, codec_metadata = _ensure_rekognition_ready_video(saved_path)
        if upload_path != saved_path:
            transcoded_path = upload_path
            upload_filename = upload_path.name
            file_size = upload_path.stat().st_size if upload_path.exists() else file_size
    except Exception as exc:
        app.logger.exception("Failed to validate/transcode upload: %s", exc)
        try:
            saved_path.unlink(missing_ok=True)
        except Exception:  # pragma: no cover
            pass
        return jsonify({"error": f"Failed to prepare video for moderation: {exc}"}), 500

    selected_categories = _normalise_selected_categories(request.form.get("categories"))
    min_confidence = request.form.get("min_confidence") or request.form.get("confidence")
    try:
        confidence_threshold = max(0.0, min(100.0, float(min_confidence))) if min_confidence else DEFAULT_MIN_CONFIDENCE
    except ValueError:
        confidence_threshold = DEFAULT_MIN_CONFIDENCE

    s3_key = _build_s3_key(file_id, upload_filename)

    try:
        _upload_to_s3(upload_path, s3_key)
    except Exception as exc:
        app.logger.exception("Failed to upload video to S3: %s", exc)
        return jsonify({"error": f"Failed to upload video to S3: {exc}"}), 500
    finally:
        try:
            saved_path.unlink(missing_ok=True)
        except Exception:  # pragma: no cover - best effort cleanup
            pass
        if transcoded_path and transcoded_path != saved_path:
            try:
                transcoded_path.unlink(missing_ok=True)
            except Exception:  # pragma: no cover
                pass

    started_at = time.time()
    try:
        job_id = _start_content_moderation_job(
            s3_key=s3_key,
            min_confidence=confidence_threshold,
            job_tag=file_id,
        )
    except Exception as exc:
        app.logger.exception("Failed to start content moderation job: %s", exc)
        return jsonify({"error": f"Failed to start content moderation job: {exc}"}), 500

    try:
        raw_results = _poll_moderation_results(job_id)
    except TimeoutError as timeout_exc:
        app.logger.warning("Content moderation timed out: %s", timeout_exc)
        return jsonify({"error": str(timeout_exc), "jobId": job_id}), 504
    except Exception as exc:
        app.logger.exception("Failed to retrieve moderation results: %s", exc)
        return jsonify({"error": f"Failed to retrieve moderation results: {exc}"}), 500

    events: List[Dict[str, Any]] = []
    lowest_confidence = None
    for item in raw_results:
        label = item.get("ModerationLabel", {})
        confidence = float(label.get("Confidence") or 0.0)
        name = label.get("Name")
        parent = label.get("ParentName")
        category = parent or name

        if confidence < confidence_threshold:
            continue

        if not _category_matches(selected_categories, parent, name):
            continue

        timestamp_ms = int(item.get("Timestamp") or 0)
        formatted_ts = _format_timestamp(timestamp_ms)

        lowest_confidence = confidence if lowest_confidence is None else min(lowest_confidence, confidence)

        events.append(
            {
                "timestamp": formatted_ts,
                "label": name,
                "parent": parent,
                "category": category,
                "confidence": round(confidence, 2),
            }
        )

    events.sort(key=lambda evt: evt["timestamp"]["milliseconds"])

    summary = _summarise_events(events)
    analysis_duration = round(time.time() - started_at, 2)

    response_payload: Dict[str, Any] = {
        "jobId": job_id,
        "fileId": file_id,
        "createdAt": datetime.utcnow().isoformat() + "Z",
        "video": {
            "bucket": MODERATION_BUCKET,
            "objectKey": s3_key,
            "originalFilename": filename,
            "sizeBytes": file_size,
        },
        "codec": codec_metadata or None,
        "request": {
            "selectedCategories": sorted(selected_categories) if selected_categories else "all",
            "minConfidence": confidence_threshold,
        },
        "summary": summary,
        "moderationEvents": events,
        "metadata": {
            "analysisDurationSeconds": analysis_duration,
            "lowestConfidence": round(lowest_confidence, 2) if lowest_confidence is not None else None,
        },
    }

    try:
        _store_report(job_id, response_payload)
    except Exception as exc:  # pragma: no cover - persistence is best effort
        app.logger.warning("Failed to persist moderation report %s: %s", job_id, exc)

    return jsonify(response_payload)


@app.route("/result/<job_id>", methods=["GET"])
def get_report(job_id: str) -> Any:
    report_path = REPORT_DIR / f"{secure_filename(job_id)}.json"
    if not report_path.exists():
        return jsonify({"error": "Report not found."}), 404
    with report_path.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)
    return jsonify(payload)


if __name__ == "__main__":  # pragma: no cover - script entry point
    port = int(os.getenv("CONTENT_MODERATION_API_PORT", "5006"))
    debug = os.getenv("DEBUG", "false").lower() == "true"
    app.run(host="0.0.0.0", port=port, debug=debug)
