#!/usr/bin/env python3
"""AI Based Highlight & Trailer backend service.

Accepts video uploads for two flows:
- Match Video: Uses AWS Rekognition/media services to generate highlights.
- Generic Content: Generates a trailer using AWS media services.

Accepts output duration as a parameter.
"""


import os
import time
import logging
import shutil
import tempfile
import subprocess
from uuid import uuid4
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from pathlib import Path
import boto3
from botocore.exceptions import NoCredentialsError, ClientError
from werkzeug.utils import secure_filename


BASE_DIR = Path(__file__).resolve().parent
UPLOAD_DIR = BASE_DIR / "uploads"
OUTPUT_DIR = BASE_DIR / "outputs"

os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(OUTPUT_DIR, exist_ok=True)

# Attempt to load environment variables from project .env files before reading values
def load_env_file(env_path):
    try:
        with open(env_path, 'r', encoding='utf-8') as env_file:
            for raw_line in env_file:
                line = raw_line.strip()
                if not line or line.startswith('#'):
                    continue
                if '=' not in line:
                    continue
                key, value = line.split('=', 1)
                key = key.strip()
                value = value.strip().strip('"').strip("'")
                os.environ.setdefault(key, value)
    except FileNotFoundError:
        pass


PROJECT_ROOT = BASE_DIR.parent
for candidate in [PROJECT_ROOT / '.env', PROJECT_ROOT / 'aiSubtitle/.env']:
    load_env_file(candidate)

# Setup logging
logging.basicConfig(
    filename=str(BASE_DIR / "highlight_trailer.log"),
    level=logging.INFO,
    format='%(asctime)s %(levelname)s %(message)s'
)
logger = logging.getLogger(__name__)

# AWS config from env
AWS_ACCESS_KEY_ID = os.getenv('AWS_ACCESS_KEY_ID')
AWS_SECRET_ACCESS_KEY = os.getenv('AWS_SECRET_ACCESS_KEY')
AWS_REGION = os.getenv('AWS_REGION', 'us-east-1')
AWS_S3_BUCKET = os.getenv('AWS_S3_BUCKET')

def aws_enabled():
    return all([AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, AWS_S3_BUCKET])


def ffmpeg_available():
    return shutil.which('ffmpeg') is not None


def run_subprocess(command, context):
    """Run subprocess command and raise with detailed error if it fails."""
    result = subprocess.run(command, capture_output=True, text=True)
    if result.returncode != 0:
        logger.error("%s failed: %s", context, result.stderr.strip())
        raise RuntimeError(f"{context} failed: {result.stderr.strip()}")
    return result.stdout.strip()


def trim_video_with_ffmpeg(source_path, duration_seconds, destination_path, context_suffix='trim'):
    if not ffmpeg_available():
        shutil.copy2(source_path, destination_path)
        return False
    temp_destination = destination_path.with_suffix('.tmp.mp4')
    command = [
        'ffmpeg', '-y',
        '-ss', '0',
        '-i', str(source_path),
        '-t', f"{duration_seconds:.3f}",
        '-c', 'copy',
        str(temp_destination)
    ]
    run_subprocess(command, f"ffmpeg {context_suffix}")
    shutil.move(temp_destination, destination_path)
    return True


def enforce_max_duration(output_path, duration_seconds):
    if not ffmpeg_available():
        return False
    temp_destination = output_path.with_suffix('.trim.mp4')
    command = [
        'ffmpeg', '-y',
        '-i', str(output_path),
        '-t', f"{duration_seconds:.3f}",
        '-c', 'copy',
        str(temp_destination)
    ]
    run_subprocess(command, 'ffmpeg enforce duration')
    shutil.move(temp_destination, output_path)
    return True


def get_rekognition_client():
    return boto3.client(
        'rekognition',
        aws_access_key_id=AWS_ACCESS_KEY_ID,
        aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
        region_name=AWS_REGION
    )


def start_segment_detection_job(rekognition_client, s3_key, video_type):
    params = {
        'Video': {'S3Object': {'Bucket': AWS_S3_BUCKET, 'Name': s3_key}},
        'SegmentTypes': ['SHOT']
    }
    # Generic trailers benefit from additional technical cues for faster cuts
    if video_type == 'generic':
        params['SegmentTypes'].append('TECHNICAL_CUE')

    filters = {}
    if video_type == 'match':
        filters['ShotFilter'] = {'MinSegmentConfidence': 85.0}
    else:
        filters['ShotFilter'] = {'MinSegmentConfidence': 60.0}
        filters['TechnicalCueFilter'] = {'MinSegmentConfidence': 70.0}

    if filters:
        params['Filters'] = filters

    response = rekognition_client.start_segment_detection(**params)
    return response['JobId']


def wait_for_segment_detection(job_id, rekognition_client, poll_seconds=4, timeout_seconds=600):
    start_time = time.time()
    next_token = None
    collected_segments = []
    video_metadata = []

    while True:
        if (time.time() - start_time) > timeout_seconds:
            raise TimeoutError('Rekognition segment detection timed out.')

        kwargs = {'JobId': job_id, 'MaxResults': 1000}
        if next_token:
            kwargs['NextToken'] = next_token

        response = rekognition_client.get_segment_detection(**kwargs)
        status = response.get('JobStatus')

        if status == 'SUCCEEDED':
            collected_segments.extend(response.get('Segments', []))
            video_metadata = response.get('VideoMetadata', [])
            next_token = response.get('NextToken')
            if not next_token:
                return collected_segments, video_metadata
        elif status == 'FAILED':
            raise RuntimeError(f"Rekognition segment detection failed: {response.get('StatusMessage')}")
        else:
            time.sleep(poll_seconds)


def normalize_segments(raw_segments):
    normalized = []
    for item in raw_segments:
        segment = item.get('Segment', {})
        seg_type = segment.get('Type')
        start_ms = item.get('StartTimestampMillis') or 0
        end_ms = item.get('EndTimestampMillis') or start_ms
        duration_ms = max(end_ms - start_ms, 0)
        confidence = 0.0
        if seg_type == 'SHOT':
            confidence = segment.get('ShotSegment', {}).get('Confidence', 0.0)
        elif seg_type == 'TECHNICAL_CUE':
            confidence = segment.get('TechnicalCueSegment', {}).get('Confidence', 0.0)

        normalized.append({
            'type': seg_type,
            'start': start_ms / 1000.0,
            'end': end_ms / 1000.0,
            'duration': duration_ms / 1000.0,
            'confidence': confidence
        })
    return normalized


def choose_segments_for_duration(segments, target_seconds, video_type):
    if not segments:
        return []

    shots = [seg for seg in segments if seg['type'] == 'SHOT']
    if not shots:
        return []

    if video_type == 'match':
        ranked = sorted(shots, key=lambda seg: (seg['confidence'], seg['duration']), reverse=True)
        max_clip = 12
    else:
        ranked = sorted(shots, key=lambda seg: seg['duration'])
        max_clip = 5

    highlight_windows = []
    remaining = float(target_seconds)

    for seg in ranked:
        seg_start = seg['start']
        seg_remaining = seg['duration']
        while seg_remaining > 0 and remaining > 0:
            clip_len = min(max_clip, seg_remaining, remaining)
            highlight_windows.append((seg_start, seg_start + clip_len))
            seg_start += clip_len
            seg_remaining -= clip_len
            remaining -= clip_len
        if remaining <= 0:
            break

    return sorted(highlight_windows, key=lambda window: window[0])


def generate_highlight_with_ffmpeg(source_path, windows, output_path):
    if not ffmpeg_available() or not windows:
        return False

    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir_path = Path(tmpdir)
        concat_list_path = tmpdir_path / 'segments.txt'
        clip_paths = []

        for idx, (start, end) in enumerate(windows):
            duration = max(end - start, 0)
            if duration <= 0:
                continue
            clip_path = tmpdir_path / f"clip_{idx:03d}.mp4"
            command = [
                'ffmpeg', '-y',
                '-ss', f"{start:.3f}",
                '-i', str(source_path),
                '-t', f"{duration:.3f}",
                '-c', 'copy',
                str(clip_path)
            ]
            run_subprocess(command, f"ffmpeg segment {idx}")
            clip_paths.append(clip_path)

        if not clip_paths:
            return False

        with open(concat_list_path, 'w', encoding='utf-8') as concat_file:
            for clip_path in clip_paths:
                concat_file.write(f"file '{clip_path}'\n")

        concat_command = [
            'ffmpeg', '-y',
            '-f', 'concat',
            '-safe', '0',
            '-i', str(concat_list_path),
            '-c', 'copy',
            str(output_path)
        ]
        run_subprocess(concat_command, 'ffmpeg concat highlight')
        return True


def process_with_rekognition(source_path, filename, video_type, duration_seconds, output_path):
    s3_key = f"highlight-trailer/uploads/{uuid4().hex}_{filename}"
    if not upload_to_s3(source_path, s3_key):
        raise RuntimeError('S3 upload failed')

    rekognition_client = get_rekognition_client()
    job_id = start_segment_detection_job(rekognition_client, s3_key, video_type)
    raw_segments, metadata = wait_for_segment_detection(job_id, rekognition_client)
    normalized_segments = normalize_segments(raw_segments)
    highlight_windows = choose_segments_for_duration(normalized_segments, duration_seconds, video_type)

    generated = generate_highlight_with_ffmpeg(source_path, highlight_windows, output_path)
    highlight_mode = 'aws_segments'

    if generated:
        enforce_max_duration(output_path, duration_seconds)
    else:
        trim_success = trim_video_with_ffmpeg(source_path, duration_seconds, output_path, 'fallback_trim')
        highlight_mode = 'fallback_trim' if trim_success else 'fallback_copy'
        if not trim_success:
            shutil.copy2(source_path, output_path)

    return {
        's3Key': s3_key,
        'jobId': job_id,
        'segmentsEvaluated': len(normalized_segments),
        'segmentsUsed': len(highlight_windows),
        'highlightMode': highlight_mode,
        'videoMetadata': metadata,
        'requestedDuration': duration_seconds
    }


def upload_to_s3(local_path, s3_key):
    s3 = boto3.client('s3',
        aws_access_key_id=AWS_ACCESS_KEY_ID,
        aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
        region_name=AWS_REGION)
    try:
        s3.upload_file(str(local_path), AWS_S3_BUCKET, s3_key)
        return True
    except (NoCredentialsError, ClientError) as e:
        print(f"S3 upload failed: {e}")
        return False

app = Flask(__name__)
CORS(app)


@app.route('/health', methods=['GET'])
def health():
    return jsonify({
        'status': 'ok',
        'service': 'highlight-trailer',
        'aws_enabled': aws_enabled(),
        'ffmpeg_available': ffmpeg_available(),
    }), 200



@app.route('/api/highlight-trailer/upload', methods=['POST'])
def upload():
    try:
        # Check upload dir permissions
        if not os.access(UPLOAD_DIR, os.W_OK):
            logger.error(f"Upload directory {UPLOAD_DIR} is not writable.")
            return jsonify({'error': f'Upload directory {UPLOAD_DIR} is not writable.'}), 500

        video = request.files.get('video')
        video_type = request.form.get('videoType')  # 'match' or 'generic'
        duration = request.form.get('duration')
        if not video or not video_type or not duration:
            logger.warning('Missing required fields in upload request.')
            return jsonify({'error': 'Missing required fields'}), 400
        filename = secure_filename(video.filename)
        save_path = UPLOAD_DIR / filename
        try:
            video.save(save_path)
        except Exception as e:
            logger.error(f"Failed to save uploaded file: {e}")
            return jsonify({'error': f'Failed to save uploaded file: {e}'}), 500

        try:
            duration_seconds = max(5, min(600, int(duration)))
        except (TypeError, ValueError):
            logger.warning('Invalid duration supplied: %s', duration)
            return jsonify({'error': 'Invalid duration provided'}), 400

        result_name = f"{video_type}_{duration_seconds}s_{filename}"
        result_path = OUTPUT_DIR / result_name
        processing_payload = {}

        if aws_enabled():
            try:
                processing_payload = process_with_rekognition(
                    save_path,
                    filename,
                    video_type,
                    duration_seconds,
                    result_path
                )
            except Exception as err:
                logger.exception('AWS highlight processing failed: %s', err)
                trimmed = False
                try:
                    trimmed = trim_video_with_ffmpeg(save_path, duration_seconds, result_path, 'aws_error_trim')
                    if not trimmed:
                        shutil.copy2(save_path, result_path)
                except Exception as copy_error:
                    logger.error('Failed to stage fallback copy: %s', copy_error)
                    return jsonify({'error': f'Failed to create fallback highlight: {copy_error}'}), 500
                processing_payload = {
                    'highlightMode': 'aws_error_trim' if trimmed else 'aws_error_copy',
                    'error': str(err),
                    'requestedDuration': duration_seconds
                }
        else:
            trimmed = False
            try:
                trimmed = trim_video_with_ffmpeg(save_path, duration_seconds, result_path, 'mock_trim')
                if not trimmed:
                    shutil.move(str(save_path), str(result_path))
            except Exception as move_error:
                logger.error(f"Failed to move file to outputs: {move_error}")
                return jsonify({'error': f'Failed to move file to outputs: {move_error}'}), 500
            processing_payload = {
                'highlightMode': 'mock_trim' if trimmed else 'mock_local',
                'requestedDuration': duration_seconds
            }

        if save_path.exists():
            try:
                save_path.unlink()
            except OSError:
                pass

        logger.info('Upload and processing complete: %s', result_name)
        response_body = {
            'downloadUrl': f'/api/highlight-trailer/download/{result_name}',
            'durationSeconds': duration_seconds,
            'processing': processing_payload
        }
        return jsonify(response_body)
    except Exception as exc:
        logger.exception(f"Unexpected error in upload: {exc}")
        return jsonify({'error': f'Unexpected error: {exc}'}), 500

@app.route('/api/highlight-trailer/download/<filename>')
def download(filename):
    return send_from_directory(OUTPUT_DIR, filename, as_attachment=True)

if __name__ == "__main__":
    port_value = os.getenv("PORT") or os.getenv("HIGHLIGHT_TRAILER_BIND_PORT") or os.getenv("HIGHLIGHT_TRAILER_PORT", "5013")
    try:
        port = int(port_value)
    except (TypeError, ValueError):
        # Kubernetes may inject HIGHLIGHT_TRAILER_PORT as: tcp://<ip>:<port>
        try:
            port = int(str(port_value).rsplit(':', 1)[-1])
        except (TypeError, ValueError):
            port = 5013
    app.run(host="0.0.0.0", port=port, debug=True)
