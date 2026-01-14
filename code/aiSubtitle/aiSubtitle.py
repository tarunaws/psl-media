#!/usr/bin/env python3
"""
AI Subtitle Generation Service
A Flask-based backend service for generating subtitles from video files using AWS Transcribe.
"""
import logging

from flask import Flask, request, jsonify, send_file, render_template, send_from_directory
from flask_cors import CORS
from werkzeug.middleware.proxy_fix import ProxyFix
try:
    from flask_limiter import Limiter
    from flask_limiter.util import get_remote_address
except ImportError:  # pragma: no cover - optional dependency
    class Limiter:  # type: ignore[override]
        def __init__(self, *_, **__):
            logging.getLogger(__name__).warning(
                "flask-limiter not installed; disabling rate limiting"
            )

        def limit(self, *_, **__):
            def decorator(func):
                return func

            return decorator

    def get_remote_address(*_args, **_kwargs):  # type: ignore[override]
        return None
import os
import subprocess
from datetime import datetime
import uuid
import json
import time
import threading
import shutil
from shared.artifact_cleanup import purge_stale_artifacts
from shared.env_loader import load_environment
from shared.logging_utils import configure_json_logging
from shared.secret_loader import load_aws_secret_into_env

try:
    import sentry_sdk
    from sentry_sdk.integrations.flask import FlaskIntegration
except ImportError:  # pragma: no cover - sentry not installed
    sentry_sdk = None
    FlaskIntegration = None

# Load environment variables
load_environment()

LOGGER = configure_json_logging('aiSubtitle')

_secret_identifier = os.getenv('AI_SUBTITLE_SECRET_ID') or os.getenv('APP_SECRETS_ID')
if _secret_identifier:
    load_aws_secret_into_env(
        _secret_identifier,
        region=os.getenv('AWS_REGION'),
        logger=LOGGER,
    )

_sentry_dsn = os.getenv('AI_SUBTITLE_SENTRY_DSN') or os.getenv('SENTRY_DSN')
if sentry_sdk and FlaskIntegration and _sentry_dsn:
    sentry_sdk.init(
        dsn=_sentry_dsn,
        integrations=[FlaskIntegration()],
        traces_sample_rate=float(os.getenv('SENTRY_TRACES_SAMPLE_RATE', '0.05')),
        environment=os.getenv('SENTRY_ENVIRONMENT', 'development'),
        send_default_pii=False,
    )

def _normalise_bucket_region(region: str | None) -> str:
    if not region:
        return "us-east-1"
    if region == "EU":
        return "eu-west-1"
    return region


def _detect_bucket_region(bucket_name: str, fallback_region: str | None) -> str | None:
    try:
        probe_client = boto3.client('s3', region_name=fallback_region or "us-east-1")
        response = probe_client.get_bucket_location(Bucket=bucket_name)
        return _normalise_bucket_region(response.get('LocationConstraint'))
    except Exception as exc:  # pragma: no cover - best-effort detection
        LOGGER.warning("Unable to determine region for bucket %s: %s", bucket_name, exc)
        return None


def _resolve_transcribe_region(bucket_region: str | None, default_region: str | None) -> str:
    override = os.getenv('TRANSCRIBE_REGION')
    if override:
        if bucket_region and bucket_region != override:
            LOGGER.warning(
                "TRANSCRIBE_REGION override (%s) differs from bucket region %s",
                override,
                bucket_region,
            )
        return override
    if bucket_region:
        return bucket_region
    if default_region:
        return default_region
    raise RuntimeError("Set TRANSCRIBE_REGION or AWS_REGION before initializing AWS Transcribe")

# AWS imports (will be imported only if AWS credentials are available)
try:
    import boto3
    from botocore.config import Config
    
    # Initialize AWS clients if credentials are available
    aws_access_key = os.getenv('AWS_ACCESS_KEY_ID')
    aws_secret_key = os.getenv('AWS_SECRET_ACCESS_KEY')
    aws_region = os.getenv('AWS_REGION')
    aws_s3_bucket = os.getenv('AWS_S3_BUCKET')

    aws_client_config = Config(
        connect_timeout=int(os.getenv('AWS_CONNECT_TIMEOUT_SECONDS', '10')),
        read_timeout=int(os.getenv('AWS_READ_TIMEOUT_SECONDS', '60')),
        retries={
            'max_attempts': int(os.getenv('AWS_MAX_ATTEMPTS', '3')),
            'mode': os.getenv('AWS_RETRY_MODE', 'standard'),
        },
    )

    if aws_access_key and aws_secret_key and aws_s3_bucket:
        if not aws_region:
            raise RuntimeError("Set AWS_REGION before starting aiSubtitle service with AWS credentials")
        bucket_region = _detect_bucket_region(aws_s3_bucket, aws_region)
        if aws_s3_bucket and not bucket_region:
            LOGGER.warning(
                "Falling back to AWS_REGION %s for bucket %s", aws_region, aws_s3_bucket
            )
        s3_region = bucket_region or aws_region
        transcribe_region = _resolve_transcribe_region(bucket_region, aws_region)
        LOGGER.info(
            "aiSubtitle using S3 region %s and Transcribe region %s",
            s3_region,
            transcribe_region,
        )

        transcribe_client = boto3.client(
            'transcribe',
            aws_access_key_id=aws_access_key,
            aws_secret_access_key=aws_secret_key,
            region_name=transcribe_region,
            config=aws_client_config,
        )
        s3_client = boto3.client(
            's3',
            aws_access_key_id=aws_access_key,
            aws_secret_access_key=aws_secret_key,
            region_name=s3_region,
            config=aws_client_config,
        )
        translate_client = boto3.client(
            'translate',
            aws_access_key_id=aws_access_key,
            aws_secret_access_key=aws_secret_key,
            region_name=aws_region,
            config=aws_client_config,
        )
    else:
        transcribe_client = None
        s3_client = None
        translate_client = None
except ImportError:
    transcribe_client = None
    s3_client = None
    translate_client = None

app = Flask(__name__)
app.logger.handlers = logging.getLogger().handlers
app.logger.setLevel(logging.getLogger().level)
LOGGER = app.logger

# Trust upstream proxies (CloudFront -> ALB -> nginx) for client IP/scheme.
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=2, x_proto=2, x_host=1)

# Configure Flask for larger file uploads and longer timeouts
app.config['MAX_CONTENT_LENGTH'] = 5 * 1024 * 1024 * 1024  # 5GB
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 300  # 5 minutes for file serving
# Increase timeout for large file processing
app.config['PERMANENT_SESSION_LIFETIME'] = 30 * 60  # 30 minutes

CORS(app, 
     origins=['http://localhost:3000'],  # Allow frontend origin
     methods=['GET', 'POST', 'OPTIONS'],  # Allow necessary HTTP methods
     allow_headers=['Content-Type', 'Range'],  # Allow Range header for audio streaming
     expose_headers=['Accept-Ranges', 'Content-Range', 'Content-Length'],  # Expose headers for streaming
     max_age=600  # CORS preflight cache for 10 minutes
)

RATE_LIMIT_STORAGE_URI = os.getenv('RATE_LIMIT_STORAGE_URI', 'memory://')
DEFAULT_RATE_LIMIT = os.getenv('DEFAULT_RATE_LIMIT', '120 per minute')
UPLOAD_RATE_LIMIT = os.getenv('UPLOAD_RATE_LIMIT', '4 per minute')
GENERATE_RATE_LIMIT = os.getenv('GENERATE_RATE_LIMIT', '6 per minute')


def _limiter_key_func() -> str:
    """Rate limit by the real client IP when behind proxies."""
    forwarded_for = request.headers.get('X-Forwarded-For', '')
    if forwarded_for:
        first = forwarded_for.split(',')[0].strip()
        if first:
            return first
    return get_remote_address()

limiter = Limiter(
    _limiter_key_func,
    app=app,
    storage_uri=RATE_LIMIT_STORAGE_URI,
    default_limits=[DEFAULT_RATE_LIMIT],
)

# Configuration
UPLOAD_FOLDER = 'uploads'
OUTPUT_FOLDER = 'outputs'
AUDIO_FOLDER = 'audio'
STREAMS_FOLDER = os.path.join(OUTPUT_FOLDER, 'streams')
SUBTITLE_FOLDER = os.path.join(OUTPUT_FOLDER, 'subtitles')

ARTIFACT_RETENTION_HOURS = int(os.getenv('ARTIFACT_RETENTION_HOURS', '72'))
ARTIFACT_CLEANUP_INTERVAL_MINUTES = int(os.getenv('ARTIFACT_CLEANUP_INTERVAL_MINUTES', '30'))
ENABLE_ARTIFACT_CLEANUP = os.getenv('ENABLE_ARTIFACT_CLEANUP', '1') not in {'0', 'false', 'False'}

DEFAULT_SUBTITLE_LANGUAGES = [
    'en', 'es', 'fr', 'de', 'it', 'pt', 'hi', 'ja', 'ko', 'zh', 'ar', 'ru'
]

LANGUAGE_LABELS = {
    'en': 'English',
    'es': 'Spanish',
    'fr': 'French',
    'de': 'German',
    'it': 'Italian',
    'pt': 'Portuguese',
    'hi': 'Hindi',
    'ja': 'Japanese',
    'ko': 'Korean',
    'zh': 'Chinese',
    'ar': 'Arabic',
    'ru': 'Russian'
}
MAX_FILE_SIZE = 5 * 1024 * 1024 * 1024  # 5GB
ALLOWED_EXTENSIONS = {'mp4', 'avi', 'mov', 'mkv', 'webm', 'flv'}


def run_artifact_cleanup() -> None:
    summary = purge_stale_artifacts(
        [UPLOAD_FOLDER, AUDIO_FOLDER, OUTPUT_FOLDER],
        retention_hours=ARTIFACT_RETENTION_HOURS,
        logger=LOGGER,
    )
    LOGGER.info(
        'artifact_cleanup_complete',
        extra={'deleted': summary['deleted'], 'freed_bytes': summary['freed_bytes']},
    )


def _start_artifact_cleanup_thread() -> None:
    if not ENABLE_ARTIFACT_CLEANUP or ARTIFACT_CLEANUP_INTERVAL_MINUTES <= 0:
        LOGGER.info('artifact_cleanup_disabled')
        return

    interval = ARTIFACT_CLEANUP_INTERVAL_MINUTES * 60

    def _loop() -> None:
        while True:
            try:
                run_artifact_cleanup()
            except Exception:  # pragma: no cover - defensive logging
                LOGGER.exception('artifact_cleanup_failed')
            time.sleep(interval)

    thread = threading.Thread(target=_loop, name='artifact-cleanup', daemon=True)
    thread.start()


def _resolve_binary(default_name: str, env_keys: tuple[str, ...], extra_paths: tuple[str, ...] = ()) -> str | None:
    """Resolve an executable path with env overrides and common fallbacks."""
    for key in env_keys:
        candidate = os.getenv(key)
        if not candidate:
            continue
        if os.path.isfile(candidate) and os.access(candidate, os.X_OK):
            return candidate
        resolved = shutil.which(candidate)
        if resolved:
            return resolved

    resolved = shutil.which(default_name)
    if resolved:
        return resolved

    for candidate in extra_paths:
        if os.path.isfile(candidate) and os.access(candidate, os.X_OK):
            return candidate

    return None


FFMPEG_BINARY = _resolve_binary(
    'ffmpeg',
    ('FFMPEG_BINARY', 'FFMPEG_PATH'),
    (
        '/opt/homebrew/bin/ffmpeg',
        '/usr/local/bin/ffmpeg',
        '/usr/bin/ffmpeg',
    ),
)


def _derive_probe_binary() -> str | None:
    explicit = _resolve_binary(
        'ffprobe',
        ('FFPROBE_BINARY', 'FFPROBE_PATH'),
        (
            '/opt/homebrew/bin/ffprobe',
            '/usr/local/bin/ffprobe',
            '/usr/bin/ffprobe',
        ),
    )
    if explicit:
        return explicit
    if FFMPEG_BINARY:
        candidate = os.path.join(os.path.dirname(FFMPEG_BINARY), 'ffprobe')
        if os.path.isfile(candidate) and os.access(candidate, os.X_OK):
            return candidate
    return None


FFPROBE_BINARY = _derive_probe_binary()

# Create necessary directories
for folder in [UPLOAD_FOLDER, OUTPUT_FOLDER, AUDIO_FOLDER, STREAMS_FOLDER, SUBTITLE_FOLDER]:
    os.makedirs(folder, exist_ok=True)

_start_artifact_cleanup_thread()

# Progress tracking system
progress_data = {}
progress_lock = threading.Lock()

def update_progress(file_id, progress, message=None, **extra):
    """Update progress for a specific file_id."""
    with progress_lock:
        entry = progress_data.get(file_id, {})
        entry['progress'] = progress
        if message is not None:
            entry['message'] = message
        for key, value in extra.items():
            entry[key] = value
        progress_data[file_id] = entry

def get_progress(file_id):
    """Get progress for a specific file_id."""
    with progress_lock:
        return progress_data.get(file_id, {'progress': 0})

def allowed_file(filename):
    """Check if the uploaded file has an allowed extension."""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def extract_audio_from_video(video_path, audio_path):
    """Extract audio from video file using ffmpeg and convert to MP3."""
    if not FFMPEG_BINARY:
        print("FFmpeg binary not configured or found on PATH.")
        return False

    try:
        cmd = [
            FFMPEG_BINARY,
            '-y',
            '-i', video_path,
            '-acodec', 'mp3',
            '-ab', '128k',
            '-ac', '2',
            '-ar', '44100',
            '-vn',
            audio_path
        ]
        subprocess.run(cmd, check=True, capture_output=True, text=True)

        if not os.path.exists(audio_path):
            print("FFmpeg completed but no audio file was produced.")
            return False

        try:
            audio_size = os.path.getsize(audio_path)
        except OSError as size_error:
            print(f"Unable to inspect extracted audio file: {size_error}")
            return False

        if audio_size == 0:
            print("Extracted audio file is empty; removing the zero-byte file to avoid downstream errors.")
            try:
                os.remove(audio_path)
            except OSError:
                pass
            return False

        return True
    except subprocess.CalledProcessError as e:
        print(f"Error extracting audio: {e.stderr if hasattr(e, 'stderr') else e}")
        return False
    except FileNotFoundError:
        print("FFmpeg binary missing when attempting extraction.")
        return False

def upload_to_s3_with_progress(
    file_path,
    bucket_name,
    object_name,
    file_id=None,
    progress_start: int | None = None,
    progress_end: int | None = None,
):
    """Upload a file to an S3 bucket with progress tracking.

    If progress_start/progress_end are provided and file_id is set, the internal 0-100%
    upload progress is mapped into the provided inclusive range.
    """
    try:
        file_size = os.path.getsize(file_path)

        mapped_start = int(progress_start) if progress_start is not None else None
        mapped_end = int(progress_end) if progress_end is not None else None

        if file_id and mapped_start is not None and mapped_end is not None:
            if mapped_end < mapped_start:
                mapped_start, mapped_end = mapped_end, mapped_start
        
        # Use multipart upload for files larger than 100MB
        if file_size > 100 * 1024 * 1024:  # 100MB threshold
            return _multipart_upload_to_s3(
                file_path,
                bucket_name,
                object_name,
                file_id,
                file_size,
                progress_start=mapped_start,
                progress_end=mapped_end,
            )
        else:
            return _single_upload_to_s3(
                file_path,
                bucket_name,
                object_name,
                file_id,
                file_size,
                progress_start=mapped_start,
                progress_end=mapped_end,
            )
            
    except Exception as e:
        error_message = f"Failed to upload {object_name} to {bucket_name}: {e}"
        if file_id:
            update_progress(file_id, -1, error_message)
        print(f"Error uploading to S3: {error_message}")
        raise RuntimeError(error_message) from e

def _single_upload_to_s3(
    file_path,
    bucket_name,
    object_name,
    file_id,
    file_size,
    progress_start: int | None = None,
    progress_end: int | None = None,
):
    """Single-part upload for smaller files."""
    bytes_seen = 0

    def _map_progress(raw_percent: int) -> int:
        if progress_start is None or progress_end is None:
            return raw_percent
        span = progress_end - progress_start
        return progress_start + int((raw_percent / 100) * span)

    def progress_callback(bytes_transferred):
        nonlocal bytes_seen
        if not file_id:
            return

        # boto3's upload_file Callback receives incremental bytes, not total.
        bytes_seen += bytes_transferred
        if file_size <= 0:
            return

        raw_progress = min(int((bytes_seen / file_size) * 100), 100)
        update_progress(file_id, _map_progress(raw_progress))
    
    s3_client.upload_file(
        file_path, 
        bucket_name, 
        object_name,
        Callback=progress_callback
    )
    
    if file_id:
        update_progress(file_id, _map_progress(100))
    
    return f"s3://{bucket_name}/{object_name}"

def _multipart_upload_to_s3(
    file_path,
    bucket_name,
    object_name,
    file_id,
    file_size,
    progress_start: int | None = None,
    progress_end: int | None = None,
):
    """Multipart upload for large files with progress tracking."""
    def _map_progress(raw_percent: int) -> int:
        if progress_start is None or progress_end is None:
            return raw_percent
        span = progress_end - progress_start
        return progress_start + int((raw_percent / 100) * span)

    # Initialize multipart upload
    response = s3_client.create_multipart_upload(
        Bucket=bucket_name,
        Key=object_name
    )
    upload_id = response['UploadId']
    
    try:
        parts = []
        part_size = 100 * 1024 * 1024  # 100MB parts
        part_number = 1
        bytes_uploaded = 0
        
        if file_id:
            update_progress(file_id, _map_progress(0))
        
        with open(file_path, 'rb') as file:
            while True:
                # Read part
                part_data = file.read(part_size)
                if not part_data:
                    break
                
                if file_id and file_size > 0:
                    progress = min(int((bytes_uploaded / file_size) * 100), 100)
                    update_progress(file_id, _map_progress(progress))
                
                # Upload part
                part_response = s3_client.upload_part(
                    Bucket=bucket_name,
                    Key=object_name,
                    PartNumber=part_number,
                    UploadId=upload_id,
                    Body=part_data
                )
                
                parts.append({
                    'ETag': part_response['ETag'],
                    'PartNumber': part_number
                })
                
                bytes_uploaded += len(part_data)
                part_number += 1

                if file_id and file_size > 0:
                    progress = min(int((bytes_uploaded / file_size) * 100), 100)
                    update_progress(file_id, _map_progress(progress))
        
        # Complete multipart upload
        s3_client.complete_multipart_upload(
            Bucket=bucket_name,
            Key=object_name,
            UploadId=upload_id,
            MultipartUpload={'Parts': parts}
        )
        
        if file_id:
            update_progress(file_id, _map_progress(100))
        
        return f"s3://{bucket_name}/{object_name}"
        
    except Exception as e:
        # Abort multipart upload on error
        s3_client.abort_multipart_upload(
            Bucket=bucket_name,
            Key=object_name,
            UploadId=upload_id
        )
        raise e

def upload_to_s3(file_path, bucket_name, object_name):
    """Upload a file to an S3 bucket for AWS Transcribe processing (legacy function)."""
    return upload_to_s3_with_progress(file_path, bucket_name, object_name)


def ensure_directory(path):
    os.makedirs(path, exist_ok=True)
    return path


def generate_hls_variant(video_path, file_id):
    """Generate HLS streaming assets from the source video."""
    if not FFMPEG_BINARY:
        print("Cannot generate HLS variant without FFmpeg binary.")
        return None
    try:
        hls_dir = ensure_directory(os.path.join(STREAMS_FOLDER, file_id, 'hls'))
        segment_pattern = os.path.join(hls_dir, 'segment_%03d.ts')
        manifest_path = os.path.join(hls_dir, 'master.m3u8')

        cmd = [
            FFMPEG_BINARY, '-y',
            '-i', video_path,
            '-c:v', 'libx264', '-preset', 'veryfast', '-profile:v', 'main', '-level', '3.1',
            '-c:a', 'aac', '-b:a', '128k',
            '-start_number', '0',
            '-hls_time', '6',
            '-hls_list_size', '0',
            '-hls_segment_filename', segment_pattern,
            manifest_path
        ]
        subprocess.run(cmd, check=True, capture_output=True)
        return manifest_path
    except subprocess.CalledProcessError as exc:
        print(f"Failed to generate HLS stream: {exc.stderr}")
        return None


def generate_dash_variant(video_path, file_id):
    """Generate MPEG-DASH streaming assets from the source video."""
    if not FFMPEG_BINARY:
        print("Cannot generate DASH variant without FFmpeg binary.")
        return None
    try:
        dash_dir = ensure_directory(os.path.join(STREAMS_FOLDER, file_id, 'dash'))
        manifest_path = os.path.join(dash_dir, 'manifest.mpd')

        cmd = [
            FFMPEG_BINARY, '-y',
            '-i', video_path,
            '-map', '0',
            '-c:v', 'libx264', '-preset', 'veryfast', '-profile:v', 'main', '-level', '3.1',
            '-c:a', 'aac', '-b:a', '128k',
            '-f', 'dash',
            '-use_template', '1',
            '-use_timeline', '1',
            '-seg_duration', '6',
            manifest_path
        ]
        subprocess.run(cmd, check=True, capture_output=True)
        return manifest_path
    except subprocess.CalledProcessError as exc:
        print(f"Failed to generate DASH stream: {exc.stderr}")
        return None


def convert_srt_to_vtt(srt_content: str) -> str:
    """Convert SRT subtitle text to WebVTT format."""
    if not srt_content:
        return ''
    vtt_lines = ['WEBVTT', '']
    for line in srt_content.splitlines():
        if '-->' in line:
            vtt_lines.append(line.replace(',', '.'))
        else:
            vtt_lines.append(line)
    return '\n'.join(vtt_lines).strip() + '\n'


def get_media_duration(filepath: str) -> float:
    """Return media duration in seconds using ffprobe."""
    if not FFPROBE_BINARY:
        print("FFprobe binary not configured; skipping duration analysis.")
        return 0.0
    try:
        cmd = [
            FFPROBE_BINARY, '-v', 'error',
            '-show_entries', 'format=duration',
            '-of', 'default=noprint_wrappers=1:nokey=1',
            filepath
        ]
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        return float(result.stdout.strip())
    except Exception as exc:
        print(f"Unable to determine duration for {filepath}: {exc}")
        return 0.0


def analyze_subtitle_accuracy(segments, audio_duration):
    """Compute simple alignment metrics between subtitles and audio duration."""
    if not segments:
        return {
            'audioDuration': audio_duration,
            'subtitleDuration': 0,
            'driftSeconds': audio_duration,
            'withinThreshold': False
        }

    subtitle_duration = segments[-1]['end_time']
    drift = abs(audio_duration - subtitle_duration)
    threshold = max(5.0, audio_duration * 0.05)
    return {
        'audioDuration': audio_duration,
        'subtitleDuration': subtitle_duration,
        'driftSeconds': drift,
        'withinThreshold': drift <= threshold
    }

TRANSLATE_LANGUAGE_MAP = {
    'zh-CN': 'zh',
    'zh-TW': 'zh-TW',
    'pt-BR': 'pt',
    'pt-PT': 'pt',
    'en-US': 'en',
    'en-GB': 'en',
    'es-US': 'es',
    'es-ES': 'es',
    'fr-CA': 'fr',
    'fr-FR': 'fr',
    'de-DE': 'de'
}


def map_transcribe_to_translate_code(language_code: str) -> str:
    if not language_code:
        return None
    cleaned = language_code.strip()
    if cleaned.lower() == 'auto':
        return None
    return TRANSLATE_LANGUAGE_MAP.get(cleaned, cleaned.split('-')[0])


def normalize_translate_language_code(language_code: str) -> str:
    """Normalize incoming target language codes to AWS Translate expectations."""
    if not language_code:
        return None
    cleaned = language_code.strip()
    if not cleaned or cleaned.lower() in {'same', 'auto'}:
        return None
    return map_transcribe_to_translate_code(cleaned)


def build_transcript_segments(
    transcription_json,
    words_per_segment=12,
    *,
    audio_duration: float | None = None,
    placeholder_text: str = 'No speech detected.',
):
    """Convert AWS Transcribe JSON output into structured segments.

    AWS Transcribe may return a valid payload with no word-level `items` (for example,
    silent clips or music-only audio). In that case, we fall back to the top-level
    transcript string (if present) or a placeholder segment so the UI can still
    deliver a subtitle file.
    """
    try:
        if isinstance(transcription_json, str):
            transcription_data = json.loads(transcription_json)
        else:
            transcription_data = transcription_json

        results = transcription_data.get('results') or {}
        items = results.get('items') or []
        words = []

        for item in items:
            if item['type'] == 'pronunciation' and 'start_time' in item:
                words.append({
                    'word': item['alternatives'][0]['content'],
                    'start_time': float(item['start_time']),
                    'end_time': float(item['end_time'])
                })

        if not words:
            transcript_text = ''
            transcripts = results.get('transcripts') or []
            if transcripts and isinstance(transcripts, list) and isinstance(transcripts[0], dict):
                transcript_text = (transcripts[0].get('transcript') or '').strip()

            resolved_text = transcript_text or placeholder_text
            resolved_duration = float(audio_duration) if audio_duration and audio_duration > 0 else 2.0
            resolved_duration = max(0.5, resolved_duration)
            return [{
                'index': 1,
                'start_time': 0.0,
                'end_time': resolved_duration,
                'text': resolved_text,
            }]

        segments = []
        segment_num = 1

        for i in range(0, len(words), words_per_segment):
            segment_words = words[i:i + words_per_segment]
            if not segment_words:
                continue

            segments.append({
                'index': segment_num,
                'start_time': segment_words[0]['start_time'],
                'end_time': segment_words[-1]['end_time'],
                'text': ' '.join(word['word'] for word in segment_words)
            })
            segment_num += 1

        return segments
    except Exception as e:
        print(f"Error building transcript segments: {e}")
        return []


def segments_to_srt(segments):
    """Convert structured segments into SRT formatted text."""
    def format_srt_time(seconds):
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        millisecs = int((seconds % 1) * 1000)
        return f"{hours:02d}:{minutes:02d}:{secs:02d},{millisecs:03d}"

    srt_lines = []
    for segment in segments:
        srt_lines.append(str(segment['index']))
        srt_lines.append(
            f"{format_srt_time(segment['start_time'])} --> {format_srt_time(segment['end_time'])}"
        )
        srt_lines.append(segment['text'])
        srt_lines.append('')

    return '\n'.join(srt_lines).strip()


def translate_segments(segments, source_language, target_language):
    if not translate_client:
        raise ValueError('AWS Translate is not configured. Please provide AWS credentials with translate access.')

    translated_segments = []
    for segment in segments:
        response = translate_client.translate_text(
            Text=segment['text'],
            SourceLanguageCode=source_language,
            TargetLanguageCode=target_language
        )
        translated_segments.append({
            **segment,
            'text': response['TranslatedText']
        })
    return translated_segments

def generate_subtitles_with_aws_transcribe(
    audio_path,
    file_id=None,
    source_language=None,
    target_languages=None,
    language_options=None
):
    """
    Generate subtitles using AWS Transcribe service.
    Returns multi-language subtitle payloads and metadata.
    Requires valid AWS credentials and configuration.
    """
    # Validate AWS configuration
    aws_access_key = os.getenv('AWS_ACCESS_KEY_ID')
    aws_secret_key = os.getenv('AWS_SECRET_ACCESS_KEY')
    aws_s3_bucket = os.getenv('AWS_S3_BUCKET')

    # Ensure AWS is properly configured
    if not transcribe_client or not s3_client or not aws_s3_bucket:
        error_msg = "AWS Transcribe is not configured. Please set AWS credentials and S3 bucket."
        if file_id:
            update_progress(file_id, -1)
        raise ValueError(error_msg)
    
    try:
        if file_id:
            update_progress(file_id, 20, 'Preparing transcription job...')

        requested_targets = []
        if isinstance(target_languages, (list, tuple)):
            requested_targets = [lang for lang in target_languages if lang is not None]
        elif isinstance(target_languages, str) and target_languages.strip():
            requested_targets = [target_languages.strip()]
        else:
            requested_targets = DEFAULT_SUBTITLE_LANGUAGES.copy()

        requested_targets = [lang.lower() for lang in requested_targets]

        # Generate unique job name
        job_name = f"transcription-{uuid.uuid4().hex[:8]}-{int(time.time())}"

        if not os.path.isfile(audio_path):
            raise FileNotFoundError("Extracted audio file is missing. Please re-run the upload to regenerate it.")

        try:
            audio_size = os.path.getsize(audio_path)
        except OSError as size_error:
            raise ValueError(f"Unable to read extracted audio file: {size_error}")

        if audio_size == 0:
            raise ValueError("Extracted audio file is empty. Ensure the source media contains an audio track and try again.")
        
        # Upload audio file to S3
        audio_filename = os.path.basename(audio_path)
        s3_object_name = f"audio/{job_name}/{audio_filename}"
        
        if file_id:
            update_progress(file_id, 30, 'Uploading audio for transcription...')
        
        try:
            # Map internal 0-100% upload progress into the overall pipeline range.
            # This prevents the UI from appearing "stuck" at 30% during large/slow uploads.
            s3_uri = upload_to_s3_with_progress(
                audio_path,
                os.getenv('AWS_S3_BUCKET'),
                s3_object_name,
                file_id=file_id,
                progress_start=30,
                progress_end=49,
            )
        except Exception as upload_error:
            raise RuntimeError(f"Failed to upload audio to S3: {upload_error}") from upload_error
        
        if not s3_uri:
            raise RuntimeError("Failed to upload audio to S3: No S3 URI returned")
        
        # Start transcription job
        transcription_params = {
            'TranscriptionJobName': job_name,
            'Media': {'MediaFileUri': s3_uri},
            'MediaFormat': 'mp3',
            'OutputBucketName': os.getenv('AWS_S3_BUCKET'),
            'OutputKey': f"transcriptions/{job_name}.json"
        }

        if source_language == 'auto' or source_language is None:
            transcription_params['IdentifyLanguage'] = True
            if language_options:
                transcription_params['LanguageOptions'] = language_options
        else:
            transcription_params['LanguageCode'] = source_language

        transcribe_client.start_transcription_job(**transcription_params)
        
        # Wait for transcription to complete
        if file_id:
            update_progress(file_id, 50, 'Transcription started...')

        # Transcribe duration can scale with input length and service load.
        # Default to 30 minutes, but allow override via env.
        # If we can estimate media duration, allow longer waits for longer inputs.
        configured_max_wait = int(os.getenv('TRANSCRIBE_MAX_WAIT_SECONDS', '1800'))
        estimated_duration = get_media_duration(audio_path) or 0.0
        duration_based_wait = int(min(6 * 3600, max(300, (estimated_duration * 2) + 180))) if estimated_duration else 0
        max_wait_time = max(configured_max_wait, duration_based_wait)
        wait_time = 0
        
        while wait_time < max_wait_time:
            response = transcribe_client.get_transcription_job(TranscriptionJobName=job_name)
            job_details = response['TranscriptionJob']
            status = job_details['TranscriptionJobStatus']
            detected_language = job_details.get('LanguageCode', source_language)
            detected_languages = job_details.get('IdentifiedLanguageCodes', [])
            detection_error = job_details.get('FailureReason') if status == 'FAILED' else None
            
            # Update progress based on wait time
            if file_id:
                progress = min(50 + (wait_time / max_wait_time) * 30, 80)
                message = 'Detecting spoken language automatically…' if (source_language == 'auto' or source_language is None) else 'Transcription in progress…'
                update_progress(
                    file_id,
                    int(progress),
                    message,
                    transcribe_job_name=job_name,
                    transcribe_status=status,
                    detected_language=detected_language,
                    available_source_languages=detected_languages,
                    language_detection_error=detection_error
                )
            
            if status == 'COMPLETED':
                if file_id:
                    update_progress(
                        file_id,
                        85,
                        detected_language=detected_language,
                        available_source_languages=detected_languages
                    )

                transcript_uri = job_details['Transcript']['TranscriptFileUri']
                import urllib.parse
                parsed_uri = urllib.parse.urlparse(transcript_uri)
                path_parts = parsed_uri.path.strip('/').split('/', 1)
                transcript_key = path_parts[1] if len(path_parts) > 1 else parsed_uri.path.lstrip('/')
                
                transcript_file = f"/tmp/{job_name}_transcript.json"
                
                s3_client.download_file(os.getenv('AWS_S3_BUCKET'), transcript_key, transcript_file)
                
                if file_id:
                    update_progress(file_id, 90, 'Building subtitle tracks...')
                
                # Read and convert to SRT
                with open(transcript_file, 'r') as f:
                    transcript_data = json.load(f)

                audio_duration = get_media_duration(audio_path)
                segments = build_transcript_segments(transcript_data, audio_duration=audio_duration)
                if not segments:
                    raise Exception('No transcribed text available for subtitle generation')

                base_language = map_transcribe_to_translate_code(detected_language) or map_transcribe_to_translate_code(source_language) or None
                subtitle_payloads = []

                original_srt = segments_to_srt(segments)
                if not original_srt:
                    raise Exception('Failed to convert transcription to SRT format')

                subtitle_payloads.append({
                    'code': base_language or detected_language or 'original',
                    'label': LANGUAGE_LABELS.get(base_language, 'Original Audio'),
                    'isOriginal': True,
                    'srt': original_srt,
                    'vtt': convert_srt_to_vtt(original_srt)
                })

                unique_targets = []
                for lang in requested_targets:
                    normalized = normalize_translate_language_code(lang) or lang
                    if not normalized:
                        continue
                    if normalized in (base_language, detected_language, 'original'):
                        continue
                    if normalized not in unique_targets:
                        unique_targets.append(normalized)

                if translate_client and unique_targets:
                    source_for_translate = base_language or map_transcribe_to_translate_code(source_language) or 'auto'
                    total_targets = len(unique_targets)
                    for index, lang_code in enumerate(unique_targets):
                        try:
                            if file_id:
                                # Keep this under 100; finalization happens later.
                                translate_progress = 92 + int(((index) / max(1, total_targets)) * 6)
                                update_progress(
                                    file_id,
                                    translate_progress,
                                    f"Translating subtitles to {lang_code}…",
                                    target_language_requested=requested_targets,
                                )
                            translated = translate_segments(segments, source_for_translate, lang_code)
                            translated_srt = segments_to_srt(translated)
                            subtitle_payloads.append({
                                'code': lang_code,
                                'label': LANGUAGE_LABELS.get(lang_code, lang_code),
                                'isOriginal': False,
                                'srt': translated_srt,
                                'vtt': convert_srt_to_vtt(translated_srt)
                            })
                        except Exception as exc:
                            print(f"Translation failed for {lang_code}: {exc}")

                    if file_id:
                        update_progress(file_id, 98, 'Translation complete. Finalizing...')

                # Cleanup temporary files
                try:
                    os.remove(transcript_file)
                    s3_client.delete_object(Bucket=os.getenv('AWS_S3_BUCKET'), Key=s3_object_name)
                    s3_client.delete_object(Bucket=os.getenv('AWS_S3_BUCKET'), Key=transcript_key)
                except Exception as cleanup_error:
                    print(f"Cleanup warning: {cleanup_error}")

                return subtitle_payloads, detected_language, segments
            elif status == 'FAILED':
                failure_reason = response['TranscriptionJob'].get('FailureReason', 'Unknown error')
                raise Exception(f"Transcription failed: {failure_reason}")
            
            time.sleep(10)  # Wait 10 seconds before checking again
            wait_time += 10
        
        raise Exception("Transcription timed out")
    except Exception as e:
        print(f"Error in AWS Transcribe: {e}")
        if file_id:
            update_progress(file_id, -1, str(e))
        raise e

def format_timestamp(seconds):
    """Convert seconds to SRT timestamp format (HH:MM:SS,mmm)."""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    millisecs = int((seconds % 1) * 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{millisecs:03d}"

@app.route('/', methods=['GET'])
def index():
    """Serve the main HTML page."""
    return render_template('index.html')

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint."""
    return jsonify({
        'status': 'healthy',
        'service': 'AI Subtitle Generation',
        'port': 5001,
        'timestamp': datetime.now().isoformat()
    })

@app.route('/progress/<file_id>', methods=['GET'])
def get_progress_endpoint(file_id):
    """Get progress for a specific file upload/processing."""
    progress_info = get_progress(file_id)
    prog = int(progress_info.get('progress') or 0)
    subtitles_in_progress = bool(progress_info.get('subtitles_in_progress'))
    available_tracks = progress_info.get('available_subtitles') or []
    streams_ready = progress_info.get('streams_ready') or {}
    accuracy_report = progress_info.get('subtitle_accuracy')
    
    # Determine readiness and stage
    # NOTE: os.path.exists(audio_path) can become true before FFmpeg finishes writing.
    # Treat audio as "ready" only once we have a non-empty file and the background
    # pipeline has advanced past extraction (progress >= 50).
    audio_path = os.path.join(AUDIO_FOLDER, f"{file_id}.mp3")
    audio_exists = os.path.exists(audio_path)
    audio_size = 0
    if audio_exists:
        try:
            audio_size = os.path.getsize(audio_path)
        except OSError:
            audio_size = 0
    audio_ready = bool(audio_exists and audio_size > 0 and prog >= 50)
    subtitle_dir = os.path.join(SUBTITLE_FOLDER, file_id)
    subtitles_exist = os.path.isdir(subtitle_dir)

    # Determine stage based on what files exist
    if subtitles_exist and available_tracks:
        stage = 'complete'
    elif audio_ready:
        stage = 'transcribe'  # Audio extracted, ready or in transcription
    else:
        stage = 'upload'  # Still uploading/extracting

    # Some clients interpret translationApplied as "requested languages are ready".
    # Historically we only set translation_applied when an actual translated (non-original)
    # track was generated, which can leave states like "en pending" even though the English
    # (original) track is already available.
    requested_targets = progress_info.get('target_language_requested')
    requested_codes = []
    if isinstance(requested_targets, (list, tuple)):
        requested_codes = [normalize_translate_language_code(str(lang)) for lang in requested_targets]
    elif isinstance(requested_targets, str) and requested_targets.strip():
        requested_codes = [normalize_translate_language_code(requested_targets.strip())]

    available_codes = {
        str(track.get('code')).lower()
        for track in (available_tracks or [])
        if isinstance(track, dict) and track.get('code')
    }

    translation_applied = progress_info.get('translation_applied')
    if requested_codes and all(code in available_codes for code in requested_codes if code):
        translation_applied = True

    client_payload = {
        'progress': prog,
        'readyForFetch': bool(available_tracks) and not subtitles_in_progress,
        'readyForTranscription': audio_ready,
        'stage': stage,
        'message': progress_info.get('message', ''),
        'transcribeJobName': progress_info.get('transcribe_job_name'),
        'transcribeStatus': progress_info.get('transcribe_status'),
        'detectedLanguage': progress_info.get('detected_language'),
        'targetLanguageRequested': progress_info.get('target_language_requested'),
        'translationApplied': translation_applied,
        'availableSourceLanguages': progress_info.get('available_source_languages'),
        'languageDetectionError': progress_info.get('language_detection_error'),
        'subtitlesInProgress': subtitles_in_progress,
        'availableSubtitles': available_tracks,
        'streamsReady': streams_ready,
        'subtitleAccuracy': accuracy_report
    }
    response = jsonify(client_payload)
    # This endpoint is polled frequently; caching can cause the UI to show stale
    # states like "Translation requested: en (pending)" even after completion.
    response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    return response

@app.route('/api-status', methods=['GET'])
def api_status():
    """Minimal status: no body so frontend debug cannot render."""
    return ('', 204)

def _save_large_file_streaming(file_stream, output_path, file_id, total_size):
    """Save large file using streaming to avoid memory issues."""
    chunk_size = 8 * 1024 * 1024
    bytes_written = 0
    with open(output_path, 'wb') as output_file:
        while True:
            chunk = file_stream.read(chunk_size)
            if not chunk:
                break
            output_file.write(chunk)
            bytes_written += len(chunk)
            progress = int((bytes_written / total_size) * 20)
            update_progress(file_id, progress)
    update_progress(file_id, 20)


def _resolve_raw_video_prefix() -> str:
    prefix = os.getenv('RAW_VIDEO_PREFIX', 'rawVideo/')
    prefix = (prefix or 'rawVideo/').lstrip('/')
    if prefix and not prefix.endswith('/'):
        prefix += '/'
    return prefix


def _get_s3_client():
    """Return an initialized S3 client.

    Prefers the module-level client, but can fall back to boto3's default
    credential chain (useful for IAM roles / IRSA / instance profiles).
    """
    global s3_client
    if s3_client is not None:
        return s3_client

    try:
        import boto3 as _boto3
    except Exception:
        return None

    bucket = os.getenv('AWS_S3_BUCKET')
    region = os.getenv('AWS_REGION') or 'us-east-1'
    if bucket:
        bucket_region = _detect_bucket_region(bucket, region)
        region = bucket_region or region

    try:
        from botocore.config import Config

        client_config = Config(
            connect_timeout=int(os.getenv('AWS_CONNECT_TIMEOUT_SECONDS', '10')),
            read_timeout=int(os.getenv('AWS_READ_TIMEOUT_SECONDS', '60')),
            retries={
                'max_attempts': int(os.getenv('AWS_MAX_ATTEMPTS', '3')),
                'mode': os.getenv('AWS_RETRY_MODE', 'standard'),
            },
        )
        s3_client = _boto3.client('s3', region_name=region, config=client_config)
        return s3_client
    except Exception as exc:
        LOGGER.warning('Unable to initialize s3 client: %s', exc)
        return None


def _start_background_video_processing(file_id: str, video_path: str, video_filename: str):
    def process_in_background():
        try:
            audio_filename = f"{file_id}.mp3"
            audio_path = os.path.join(AUDIO_FOLDER, audio_filename)

            update_progress(file_id, 30)

            if not FFMPEG_BINARY:
                update_progress(
                    file_id,
                    -1,
                    'Audio extraction requires FFmpeg. Install ffmpeg and expose it via PATH or set FFMPEG_BINARY in the environment before restarting the backend.'
                )
                return

            if not extract_audio_from_video(video_path, audio_path):
                update_progress(
                    file_id,
                    -1,
                    'Failed to extract audio with FFmpeg. Verify the binary is installed and the uploaded file has an audio track.'
                )
                return

            update_progress(file_id, 50)

            # Generate streaming variants (HLS & DASH)
            streams_ready = {}
            try:
                update_progress(file_id, 55, 'Generating streaming variants...')
                hls_manifest = generate_hls_variant(video_path, file_id)
                if hls_manifest:
                    streams_ready['hls'] = f"/stream/{file_id}/hls/master.m3u8"
                dash_manifest = generate_dash_variant(video_path, file_id)
                if dash_manifest:
                    streams_ready['dash'] = f"/stream/{file_id}/dash/manifest.mpd"
            except Exception as stream_error:
                print(f"Stream generation failed for {file_id}: {stream_error}")
            finally:
                if streams_ready:
                    update_progress(
                        file_id,
                        58,
                        'Streaming variants ready',
                        streams_ready=streams_ready
                    )

            # Upload to S3
            try:
                client = _get_s3_client()
                bucket = os.getenv('AWS_S3_BUCKET')
                if client and bucket:
                    update_progress(file_id, 60)

                    s3_video_key = f"videos/{file_id}/{video_filename}"
                    s3_audio_key = f"audio/{file_id}/{audio_filename}"

                    upload_to_s3_with_progress(video_path, bucket, s3_video_key, file_id)
                    upload_to_s3_with_progress(audio_path, bucket, s3_audio_key, file_id)
            except Exception as exc:
                error_message = f"S3 upload failed: {exc}"
                update_progress(file_id, -1, error_message)
                app.logger.exception(error_message)
                return

            update_progress(file_id, 100)

        except Exception as exc:
            update_progress(file_id, -1, str(exc))

    thread = threading.Thread(target=process_in_background)
    thread.daemon = True
    thread.start()


@app.route('/s3/raw-videos', methods=['GET'])
def list_raw_videos():
    bucket = os.getenv('AWS_S3_BUCKET')
    if not bucket:
        return jsonify({'error': 'AWS_S3_BUCKET is not set'}), 503

    client = _get_s3_client()
    if not client:
        return jsonify({'error': 'S3 client is not configured'}), 503

    prefix = _resolve_raw_video_prefix()
    try:
        max_keys = int(request.args.get('max_keys', '200'))
    except ValueError:
        max_keys = 200

    try:
        response = client.list_objects_v2(Bucket=bucket, Prefix=prefix, MaxKeys=max_keys)
        contents = response.get('Contents') or []
        items = []
        for obj in contents:
            key = obj.get('Key')
            if not key or key.endswith('/'):
                continue
            items.append({
                'key': key,
                'size': obj.get('Size'),
                'last_modified': obj.get('LastModified').isoformat() if obj.get('LastModified') else None,
            })
        return jsonify({'bucket': bucket, 'prefix': prefix, 'items': items})
    except Exception as exc:
        LOGGER.exception('list_raw_videos failed')
        return jsonify({'error': str(exc)}), 500


@app.route('/s3/browse', methods=['GET'])
def browse_s3():
    """Browse S3 under the configured rawVideo root prefix.

    Returns subfolders (CommonPrefixes) and video files for the requested prefix.
    """
    bucket = os.getenv('AWS_S3_BUCKET')
    if not bucket:
        return jsonify({'error': 'AWS_S3_BUCKET is not set'}), 503

    client = _get_s3_client()
    if not client:
        return jsonify({'error': 'S3 client is not configured'}), 503

    root_prefix = _resolve_raw_video_prefix()

    requested_prefix = (request.args.get('prefix') or '').strip()
    if requested_prefix:
        requested_prefix = requested_prefix.lstrip('/')
        if not requested_prefix.endswith('/'):
            requested_prefix += '/'
        if not requested_prefix.startswith(root_prefix):
            return jsonify({'error': f'prefix must start with {root_prefix}'}), 400
        prefix = requested_prefix
    else:
        prefix = root_prefix

    try:
        max_keys = int(request.args.get('max_keys', '500'))
    except ValueError:
        max_keys = 500

    try:
        response = client.list_objects_v2(
            Bucket=bucket,
            Prefix=prefix,
            Delimiter='/',
            MaxKeys=max_keys,
        )
    except Exception as exc:
        LOGGER.exception('browse_s3 failed')
        return jsonify({'error': str(exc)}), 500

    folders = []
    for entry in response.get('CommonPrefixes', []) or []:
        folder_prefix = entry.get('Prefix')
        if not folder_prefix:
            continue
        name = folder_prefix
        if folder_prefix.startswith(prefix):
            name = folder_prefix[len(prefix):]
        name = name.rstrip('/')
        if not name:
            continue
        folders.append({'prefix': folder_prefix, 'name': name})

    allowed_extensions = set((ALLOWED_EXTENSIONS or []))
    files = []
    for obj in response.get('Contents', []) or []:
        key = obj.get('Key')
        if not key or key.endswith('/'):
            continue
        if key == prefix:
            continue
        basename = key
        if key.startswith(prefix):
            basename = key[len(prefix):]
        if '/' in basename:
            continue
        extension = (basename.rsplit('.', 1)[-1] or '').lower()
        if allowed_extensions and extension and extension not in allowed_extensions:
            continue
        files.append({
            'key': key,
            'name': basename,
            'size': obj.get('Size'),
            'last_modified': obj.get('LastModified').isoformat() if obj.get('LastModified') else None,
        })

    return jsonify({
        'bucket': bucket,
        'root_prefix': root_prefix,
        'prefix': prefix,
        'folders': folders,
        'files': files,
    })


@app.route('/upload-s3', methods=['POST'])
@limiter.limit(UPLOAD_RATE_LIMIT)
def upload_video_s3():
    try:
        bucket = os.getenv('AWS_S3_BUCKET')
        if not bucket:
            return jsonify({'error': 'AWS_S3_BUCKET is not set'}), 503

        client = _get_s3_client()
        if not client:
            return jsonify({'error': 'S3 client is not configured'}), 503

        payload = request.get_json(silent=True) or {}
        s3_key = payload.get('s3_key') or payload.get('key')
        if not s3_key or not isinstance(s3_key, str):
            return jsonify({'error': 'Missing s3_key in request body'}), 400

        file_id = str(uuid.uuid4())
        ext = os.path.splitext(s3_key)[1].lstrip('.').lower() or 'mp4'
        video_filename = f"{file_id}.{ext}"
        video_path = os.path.join(UPLOAD_FOLDER, video_filename)

        update_progress(file_id, 0)
        update_progress(file_id, 10, 'Downloading from S3...')
        client.download_file(bucket, s3_key, video_path)
        update_progress(file_id, 20)

        _start_background_video_processing(file_id, video_path, video_filename)

        return jsonify({
            'file_id': file_id,
            's3_key': s3_key,
            'message': 'S3 import started successfully'
        }), 200
    except Exception as exc:
        LOGGER.exception('upload_video_s3 failed')
        return jsonify({'error': f'Upload failed: {exc}'}), 500

@app.route('/upload', methods=['POST'])
@limiter.limit(UPLOAD_RATE_LIMIT)
def upload_video():
    """Upload video file and automatically extract audio. Requires AWS configuration."""
    try:
        # Check AWS configuration first
        if not transcribe_client or not s3_client or not os.getenv('AWS_S3_BUCKET'):
            return jsonify({
                'error': 'AWS Transcribe is not configured. Please set AWS credentials and S3 bucket.',
                'aws_configured': False
            }), 503
        
        # Check if file is present
        if 'video' not in request.files:
            return jsonify({'error': 'No video file provided'}), 400
        
        file = request.files['video']
        
        # Check if file is selected
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400
        
        # Check file extension
        if not allowed_file(file.filename):
            return jsonify({'error': 'Invalid file type. Allowed: ' + ', '.join(ALLOWED_EXTENSIONS)}), 400
        
        # Check file size
        file.seek(0, os.SEEK_END)
        file_size = file.tell()
        file.seek(0)
        
        if file_size > MAX_FILE_SIZE:
            # Convert to GB for display
            max_size_gb = MAX_FILE_SIZE / (1024 * 1024 * 1024)
            return jsonify({'error': f'File too large. Maximum size: {max_size_gb:.0f}GB'}), 400
        
        # Generate unique filename
        file_id = str(uuid.uuid4())
        file_extension = file.filename.rsplit('.', 1)[1].lower()
        video_filename = f"{file_id}.{file_extension}"
        video_path = os.path.join(UPLOAD_FOLDER, video_filename)
        
        # Initialize progress
        update_progress(file_id, 0)
        
        # Save uploaded file with streaming for large files
        if file_size > 100 * 1024 * 1024:  # Stream files larger than 100MB
            _save_large_file_streaming(file, video_path, file_id, file_size)
        else:
            file.save(video_path)
            update_progress(file_id, 20)
        
        _start_background_video_processing(file_id, video_path, video_filename)
        
        # Return response with file info
        return jsonify({
            'file_id': file_id,
            'filename': file.filename,
            'size': file_size,
            'message': 'Upload started successfully'
        }), 200
        
    except Exception as e:
        return jsonify({'error': f'Upload failed: {str(e)}'}), 500

@app.route('/download-audio/<file_id>', methods=['GET'])
def download_audio(file_id):
    """Serve extracted audio file for playback or download."""
    try:
        audio_path = os.path.join(AUDIO_FOLDER, f"{file_id}.mp3")
        
        if not os.path.exists(audio_path):
            return jsonify({'error': 'Audio file not found'}), 404
        
        # Check if client wants to download or stream
        # If 'download' parameter is present, serve as attachment
        download_requested = request.args.get('download') is not None
        
        return send_file(
            audio_path,
            as_attachment=download_requested,
            download_name=f"audio_{file_id}.mp3" if download_requested else None,
            mimetype='audio/mpeg',
            conditional=True  # Enable range requests for audio streaming
        )
        
    except Exception as e:
        return jsonify({'error': f'Download failed: {str(e)}'}), 500

@app.route('/stream-audio/<file_id>', methods=['GET'])
def stream_audio(file_id):
    """Stream audio file for web playback with proper headers."""
    try:
        audio_path = os.path.join(AUDIO_FOLDER, f"{file_id}.mp3")
        
        if not os.path.exists(audio_path):
            return jsonify({'error': 'Audio file not found'}), 404
        
        # Serve audio file with streaming-friendly headers
        response = send_file(
            audio_path,
            mimetype='audio/mpeg',
            as_attachment=False,
            conditional=True  # Enable range requests for streaming
        )
        
        # Add headers for better browser compatibility
        response.headers['Accept-Ranges'] = 'bytes'
        response.headers['Cache-Control'] = 'public, max-age=3600'
        response.headers['Content-Disposition'] = 'inline'
        
        return response
        
    except Exception as e:
        return jsonify({'error': f'Streaming failed: {str(e)}'}), 500

@app.route('/generate-subtitles', methods=['POST'])
@limiter.limit(GENERATE_RATE_LIMIT)
def generate_subtitles():
    """Generate subtitles from uploaded video using AWS Transcribe."""
    try:
        # Check AWS configuration first
        if not transcribe_client or not s3_client or not os.getenv('AWS_S3_BUCKET'):
            return jsonify({
                'error': 'AWS Transcribe is not configured. Please set AWS credentials and S3 bucket.',
                'aws_configured': False
            }), 503
        
        data = request.get_json() or {}
        file_id = data.get('file_id')
        source_language = data.get('source_language') or 'auto'
        language_options = data.get('language_options') or []

        requested_targets = []
        if isinstance(data.get('target_languages'), list):
            requested_targets.extend([lang for lang in data['target_languages'] if lang])
        elif isinstance(data.get('target_languages'), str):
            requested_targets.append(data['target_languages'])

        # Backward compatibility with single target_language parameter
        legacy_target = data.get('target_language')
        if legacy_target:
            requested_targets.append(legacy_target)

        # Remove empty entries and normalise to lowercase strings
        requested_targets = [str(lang).strip() for lang in requested_targets if str(lang).strip()]

        # Default to configured languages if nothing provided
        if not requested_targets:
            requested_targets = DEFAULT_SUBTITLE_LANGUAGES.copy()

        requires_translation = any(normalize_translate_language_code(lang) for lang in requested_targets)

        if not file_id:
            return jsonify({'error': 'File ID is required'}), 400

        if requires_translation and not translate_client:
            return jsonify({'error': 'AWS Translate is not configured. Please set AWS credentials for translation.'}), 503
        
        # Initialize progress for subtitle generation
        update_progress(
            file_id,
            0,
            'Preparing subtitle generation...',
            target_language_requested=requested_targets,
            translation_applied=False,
            subtitles_in_progress=True
        )
        
        # Find audio file (should already exist from upload)
        audio_path = os.path.join(AUDIO_FOLDER, f"{file_id}.mp3")
        
        if not os.path.exists(audio_path):
            return jsonify({'error': 'Audio file not found. Please upload video first.'}), 404
        
        # Start background subtitle generation
        def generate_in_background():
            try:
                update_progress(file_id, 10, 'Starting transcription...')
                
                # Generate subtitles using AWS Transcribe
                subtitle_payloads, detected_language, segments = generate_subtitles_with_aws_transcribe(
                    audio_path,
                    file_id,
                    source_language=source_language,
                    target_languages=requested_targets,
                    language_options=language_options
                )
                if subtitle_payloads:
                    subtitle_dir = ensure_directory(os.path.join(SUBTITLE_FOLDER, file_id))
                    available_tracks = []

                    for entry in subtitle_payloads:
                        code = (entry.get('code') or 'original').lower()
                        label = entry.get('label') or code
                        srt_content = entry.get('srt') or ''
                        vtt_content = entry.get('vtt') or convert_srt_to_vtt(srt_content)

                        srt_path = os.path.join(subtitle_dir, f"{code}.srt")
                        with open(srt_path, 'w', encoding='utf-8') as srt_file:
                            srt_file.write(srt_content)

                        vtt_path = os.path.join(subtitle_dir, f"{code}.vtt")
                        with open(vtt_path, 'w', encoding='utf-8') as vtt_file:
                            vtt_file.write(vtt_content)

                        available_tracks.append({
                            'code': code,
                            'label': label,
                            'isOriginal': entry.get('isOriginal', False)
                        })

                    # Maintain backwards compatibility file for legacy clients
                    fallback_srt = subtitle_payloads[0]['srt'] if subtitle_payloads else ''
                    fallback_path = os.path.join(OUTPUT_FOLDER, f"{file_id}.srt")
                    with open(fallback_path, 'w', encoding='utf-8') as fallback_file:
                        fallback_file.write(fallback_srt)

                    audio_duration = get_media_duration(audio_path)
                    accuracy_report = analyze_subtitle_accuracy(segments, audio_duration)
                    translation_generated = any(not entry.get('isOriginal', False) for entry in subtitle_payloads)

                    update_progress(
                        file_id,
                        90,
                        'Saving subtitles...',
                        detected_language=detected_language,
                        target_language_requested=requested_targets,
                        translation_applied=translation_generated,
                        subtitles_in_progress=True,
                        available_subtitles=available_tracks,
                        subtitle_accuracy=accuracy_report,
                        language_detection_error=None
                    )

                    update_progress(
                        file_id,
                        100,
                        'Subtitles ready',
                        detected_language=detected_language,
                        target_language_requested=requested_targets,
                        translation_applied=translation_generated,
                        subtitles_in_progress=False,
                        available_subtitles=available_tracks,
                        subtitle_accuracy=accuracy_report,
                        language_detection_error=None
                    )
                else:
                    update_progress(
                        file_id,
                        -1,
                        'Failed to build subtitles',
                        subtitles_in_progress=False,
                        translation_applied=False
                    )
            except Exception as e:
                update_progress(
                    file_id,
                    -1,
                    str(e),
                    subtitles_in_progress=False,
                    translation_applied=False
                )
        
        # Start background thread
        thread = threading.Thread(target=generate_in_background)
        thread.start()
        
        return jsonify({
            'message': 'Subtitle generation started',
            'file_id': file_id,
            'progress_url': f'/progress/{file_id}',
            'source_language': source_language,
            'target_languages': requested_targets,
            'language_options': language_options
        }), 200
        
    except Exception as e:
        return jsonify({'error': f'Subtitle generation failed: {str(e)}'}), 500

@app.route('/subtitles/<file_id>', methods=['GET'])
def get_subtitles(file_id):
    """Get generated subtitles for a file."""
    try:
        subtitle_dir = os.path.join(SUBTITLE_FOLDER, file_id)

        if not os.path.isdir(subtitle_dir):
            return jsonify({'error': 'Subtitle files not found'}), 404

        available_info = progress_data.get(file_id, {}).get('available_subtitles') or []
        info_map = {entry['code']: entry for entry in available_info if isinstance(entry, dict)}

        tracks = []
        for filename in sorted(os.listdir(subtitle_dir)):
            if not filename.endswith('.vtt') and not filename.endswith('.srt'):
                continue
            code = filename.rsplit('.', 1)[0]
            if any(track.get('code') == code and track.get('url') for track in tracks):
                continue

            track_info = info_map.get(code, {})
            tracks.append({
                'code': code,
                'label': track_info.get('label') or LANGUAGE_LABELS.get(code, code),
                'isOriginal': track_info.get('isOriginal', False),
                'srt': f"/subtitle-track/{file_id}/{code}.srt",
                'vtt': f"/subtitle-track/{file_id}/{code}.vtt"
            })

        if not tracks:
            return jsonify({'error': 'Subtitle files not found'}), 404

        response = jsonify({
            'file_id': file_id,
            'tracks': tracks,
            'detected_language': progress_data.get(file_id, {}).get('detected_language'),
            'subtitle_accuracy': progress_data.get(file_id, {}).get('subtitle_accuracy')
        })
        response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
        response.headers['Pragma'] = 'no-cache'
        response.headers['Expires'] = '0'
        return response, 200
        
    except Exception as e:
        return jsonify({'error': f'Failed to get subtitles: {str(e)}'}), 500

@app.route('/download/<file_id>', methods=['GET'])
def download_subtitles(file_id):
    """Download generated subtitle file."""
    try:
        subtitles_path = os.path.join(OUTPUT_FOLDER, f"{file_id}.srt");
        
        if not os.path.exists(subtitles_path):
            return jsonify({'error': 'Subtitle file not found'}), 404
        
        return send_file(
            subtitles_path,
            as_attachment=True,
            download_name=f"subtitles_{file_id}.srt",
            mimetype='text/plain'
        )
        
    except Exception as e:
        return jsonify({'error': f'Download failed: {str(e)}'}), 500


@app.route('/streams/<file_id>', methods=['GET'])
def get_streams(file_id):
    """Return available streaming manifests for a video."""
    protocols = {}
    hls_manifest = os.path.join(STREAMS_FOLDER, file_id, 'hls', 'master.m3u8')
    dash_manifest = os.path.join(STREAMS_FOLDER, file_id, 'dash', 'manifest.mpd')

    if os.path.exists(hls_manifest):
        protocols['hls'] = {
            'manifest': f"/stream/{file_id}/hls/master.m3u8"
        }

    if os.path.exists(dash_manifest):
        protocols['dash'] = {
            'manifest': f"/stream/{file_id}/dash/manifest.mpd"
        }

    if not protocols:
        return jsonify({'error': 'Streaming manifests not found'}), 404

    response = jsonify({
        'file_id': file_id,
        'protocols': protocols
    })
    response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    return response, 200


@app.route('/stream/<file_id>/<protocol>/<path:filename>', methods=['GET'])
def serve_stream_asset(file_id, protocol, filename):
    """Serve HLS or DASH streaming asset."""
    protocol = protocol.lower()
    if protocol not in {'hls', 'dash'}:
        return jsonify({'error': 'Unsupported protocol'}), 400

    base_dir = os.path.join(STREAMS_FOLDER, file_id, protocol)
    if not os.path.isdir(base_dir):
        return jsonify({'error': 'Stream not found'}), 404

    return send_from_directory(base_dir, filename, conditional=True)


@app.route('/subtitle-track/<file_id>/<path:filename>', methods=['GET'])
def serve_subtitle_track(file_id, filename):
    """Serve individual subtitle track files (SRT/VTT)."""
    subtitle_dir = os.path.join(SUBTITLE_FOLDER, file_id)
    if not os.path.isdir(subtitle_dir):
        return jsonify({'error': 'Subtitle track not found'}), 404

    extension = filename.rsplit('.', 1)[-1].lower()
    mimetype = 'text/plain'
    if extension == 'vtt':
        mimetype = 'text/vtt'
    elif extension == 'srt':
        mimetype = 'application/x-subrip'
    as_attachment = request.args.get('download') == '1'

    response = send_from_directory(
        subtitle_dir,
        filename,
        mimetype=mimetype,
        conditional=not as_attachment,
        as_attachment=as_attachment,
        download_name=filename
    )

    if as_attachment:
        response.headers['Cache-Control'] = 'no-cache'

    return response

@app.route('/status/<file_id>', methods=['GET'])
def get_processing_status(file_id):
    """Get processing status for a file."""
    try:
        video_files = [f for f in os.listdir(UPLOAD_FOLDER) if f.startswith(file_id)]
        subtitles_path = os.path.join(OUTPUT_FOLDER, f"{file_id}.srt")
        
        if not video_files:
            return jsonify({'status': 'not_found'}), 404
        
        if os.path.exists(subtitles_path):
            return jsonify({'status': 'completed'}), 200
        else:
            return jsonify({'status': 'processing'}), 200
            
    except Exception as e:
        return jsonify({'error': f'Status check failed: {str(e)}'}), 500

@app.route('/cleanup/<file_id>', methods=['DELETE'])
def cleanup_files(file_id):
    """Clean up uploaded and generated files."""
    try:
        # Remove video file
        video_files = [f for f in os.listdir(UPLOAD_FOLDER) if f.startswith(file_id)]
        for video_file in video_files:
            video_path = os.path.join(UPLOAD_FOLDER, video_file)
            if os.path.exists(video_path):
                os.remove(video_path)
        
        # Remove subtitle file
        subtitles_path = os.path.join(OUTPUT_FOLDER, f"{file_id}.srt")
        if os.path.exists(subtitles_path):
            os.remove(subtitles_path)

        # Remove subtitle directory
        subtitle_dir = os.path.join(SUBTITLE_FOLDER, file_id)
        if os.path.isdir(subtitle_dir):
            shutil.rmtree(subtitle_dir, ignore_errors=True)

        # Remove streaming directories
        stream_dir = os.path.join(STREAMS_FOLDER, file_id)
        if os.path.isdir(stream_dir):
            shutil.rmtree(stream_dir, ignore_errors=True)
        
        return jsonify({'message': 'Files cleaned up successfully'}), 200
        
    except Exception as e:
        return jsonify({'error': f'Cleanup failed: {str(e)}'}), 500

@app.errorhandler(413)
def too_large(e):
    """Handle file too large error."""
    return jsonify({'error': 'File too large'}), 413

@app.errorhandler(404)
def not_found(e):
    """Handle not found errors."""
    return jsonify({'error': 'Resource not found'}), 404

@app.errorhandler(500)
def internal_error(e):
    """Handle internal server errors."""
    return jsonify({'error': 'Internal server error'}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5001))
    debug_flag = os.environ.get('DEBUG', 'false').lower() == 'true'
    use_reloader = os.environ.get('RELOADER', 'false').lower() == 'true'
    
    from werkzeug.serving import WSGIRequestHandler
    
    # Increase request timeout for large file uploads
    WSGIRequestHandler.timeout = 30 * 60  # 30 minutes
    
    app.run(
        host='0.0.0.0',
        port=port,
        debug=debug_flag,
        threaded=True,
        use_reloader=use_reloader,
        request_handler=WSGIRequestHandler
    )