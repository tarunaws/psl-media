"""
Video Generation Service using Amazon Nova Reel
Generates videos from text prompts and stores them in S3
"""

import os
import uuid
import logging
import traceback
import tempfile
import subprocess
import shutil
from pathlib import Path
from datetime import datetime
from typing import Any, Dict, List, Optional
import json
from flask import Flask, request, jsonify, Response
from flask_cors import CORS
import boto3
from botocore.exceptions import ClientError
from botocore.config import Config
from shared.env_loader import load_environment

# Configure logging
logging.basicConfig(level=logging.INFO)

app = Flask(__name__)
CORS(app)

load_environment()

# AWS Configuration
AWS_REGION = os.getenv('AWS_REGION')
if not AWS_REGION:
    raise RuntimeError("Set AWS_REGION before starting video generation service")

DEFAULT_MEDIA_BUCKET = os.getenv('MEDIA_S3_BUCKET')
S3_BUCKET = os.getenv('VIDEO_GEN_S3_BUCKET', DEFAULT_MEDIA_BUCKET)

if not S3_BUCKET:
    raise RuntimeError("Set VIDEO_GEN_S3_BUCKET or MEDIA_S3_BUCKET before starting video generation service")

# Initialize AWS clients with conservative timeouts so startup doesn't hang
AWS_CLIENT_CONFIG = Config(
    connect_timeout=int(os.getenv('AWS_CONNECT_TIMEOUT_SECONDS', '5')),
    read_timeout=int(os.getenv('AWS_READ_TIMEOUT_SECONDS', '30')),
    retries={'max_attempts': int(os.getenv('AWS_MAX_ATTEMPTS', '3'))},
)

bedrock_runtime = boto3.client('bedrock-runtime', region_name=AWS_REGION, config=AWS_CLIENT_CONFIG)
s3_client = boto3.client('s3', region_name=AWS_REGION, config=AWS_CLIENT_CONFIG)
POLLY_REGION = (os.getenv('POLLY_REGION') or AWS_REGION).strip()
polly_client = boto3.client('polly', region_name=POLLY_REGION, config=AWS_CLIENT_CONFIG)

# In-memory storage for generation history
GENERATION_HISTORY = []
MAX_REFERENCE_IMAGES = int(os.getenv('VIDEO_GEN_MAX_REFERENCE_IMAGES', '4'))
REFERENCE_URL_TTL = int(os.getenv('VIDEO_GEN_REFERENCE_TTL_SECONDS', str(3600 * 24 * 7)))
DEFAULT_VIDEO_DURATION = int(os.getenv('VIDEO_GEN_DEFAULT_DURATION', '6'))
MIN_VIDEO_DURATION = int(os.getenv('VIDEO_GEN_MIN_DURATION', '3'))
MAX_VIDEO_DURATION = int(os.getenv('VIDEO_GEN_MAX_DURATION', '6'))

# Audio handling
VIDEO_GEN_ENSURE_AUDIO = os.getenv('VIDEO_GEN_ENSURE_AUDIO', '1') not in {'0', 'false', 'False'}
# "tone" ensures an audible track exists (simple sine wave). "silence" keeps the previous behavior.
# "voiceover" generates spoken audio using Amazon Polly.
VIDEO_GEN_AUDIO_KIND = os.getenv('VIDEO_GEN_AUDIO_KIND', 'tone').strip().lower()
VIDEO_GEN_AUDIO_TONE_FREQUENCY_HZ = float(os.getenv('VIDEO_GEN_AUDIO_TONE_FREQUENCY_HZ', '440'))
VIDEO_GEN_AUDIO_TONE_VOLUME_DB = float(os.getenv('VIDEO_GEN_AUDIO_TONE_VOLUME_DB', '-22'))
VIDEO_GEN_AUDIO_SAMPLE_RATE = int(os.getenv('VIDEO_GEN_AUDIO_SAMPLE_RATE', '44100'))
VIDEO_GEN_AUDIO_CHANNEL_LAYOUT = os.getenv('VIDEO_GEN_AUDIO_CHANNEL_LAYOUT', 'stereo')

# Voiceover (Polly)
VIDEO_GEN_VOICEOVER_VOICE_ID = os.getenv('VIDEO_GEN_VOICEOVER_VOICE_ID', 'Joanna').strip() or 'Joanna'
VIDEO_GEN_DEFAULT_VOICEOVER_TEXT = os.getenv('VIDEO_GEN_DEFAULT_VOICEOVER_TEXT', 'This is a generated video.').strip()
VIDEO_GEN_VOICEOVER_VOLUME_DB = float(os.getenv('VIDEO_GEN_VOICEOVER_VOLUME_DB', '0'))

# Advertisement voiceover generation (Bedrock LLM)
VIDEO_GEN_AD_VOICEOVER_ENABLED = os.getenv('VIDEO_GEN_AD_VOICEOVER_ENABLED', '1') not in {'0', 'false', 'False'}
VIDEO_GEN_AD_VOICEOVER_MODEL_ID = os.getenv('VIDEO_GEN_AD_VOICEOVER_MODEL_ID') or os.getenv('MOVIE_SCRIPT_MODEL_ID') or 'meta.llama3-70b-instruct-v1:0'
VIDEO_GEN_AD_VOICEOVER_MAX_CHARS = int(os.getenv('VIDEO_GEN_AD_VOICEOVER_MAX_CHARS', '280'))
VIDEO_GEN_AD_VOICEOVER_MAX_GEN_LEN = int(os.getenv('VIDEO_GEN_AD_VOICEOVER_MAX_GEN_LEN', '180'))
VIDEO_GEN_AD_VOICEOVER_TEMPERATURE = float(os.getenv('VIDEO_GEN_AD_VOICEOVER_TEMPERATURE', '0.4'))


def _which(binary_name: str) -> str | None:
    try:
        return shutil.which(binary_name)
    except Exception:
        return None


FFMPEG_BIN = os.getenv('VIDEO_GEN_FFMPEG') or _which('ffmpeg')
FFPROBE_BIN = os.getenv('VIDEO_GEN_FFPROBE') or _which('ffprobe')


def _probe_has_audio(video_path: Path) -> bool:
    """Return True if the media file has at least one audio stream."""
    if not FFPROBE_BIN:
        # If we can't probe, assume no audio and fall back to adding it.
        return False
    cmd = [
        FFPROBE_BIN,
        '-v', 'error',
        '-select_streams', 'a',
        '-show_entries', 'stream=codec_name',
        '-of', 'csv=p=0',
        str(video_path)
    ]
    try:
        out = subprocess.check_output(cmd, stderr=subprocess.STDOUT, text=True).strip()
        return bool(out)
    except subprocess.CalledProcessError as exc:
        app.logger.warning('ffprobe failed when checking audio streams: %s', exc.output)
        return False


def _probe_duration_seconds(video_path: Path) -> Optional[float]:
    """Return the duration in seconds if available."""
    if not FFPROBE_BIN:
        return None
    cmd = [
        FFPROBE_BIN,
        '-v', 'error',
        '-show_entries', 'format=duration',
        '-of', 'default=nw=1:nk=1',
        str(video_path)
    ]
    try:
        out = subprocess.check_output(cmd, stderr=subprocess.STDOUT, text=True).strip()
        if not out:
            return None
        return float(out)
    except Exception as exc:
        app.logger.warning('ffprobe failed when checking duration: %s', exc)
        return None


def _synthesize_voiceover_mp3(text: str, output_path: Path, *, voice_id: str) -> None:
    """Generate an MP3 voiceover using Amazon Polly."""
    if not text.strip():
        raise ValueError('voiceover text is empty')

    try:
        resp = polly_client.synthesize_speech(
            Text=text,
            OutputFormat='mp3',
            VoiceId=voice_id,
        )
    except Exception as exc:
        raise RuntimeError(f'Polly synthesize_speech failed: {exc}') from exc

    stream = resp.get('AudioStream')
    if not stream:
        raise RuntimeError('Polly did not return an AudioStream')

    with open(output_path, 'wb') as f:
        f.write(stream.read())


def _default_voiceover_text_from_prompt(prompt: str) -> str:
    """Derive a Polly-safe narration string from the user prompt."""
    cleaned = (prompt or '').strip().replace('\n', ' ')
    if not cleaned:
        return VIDEO_GEN_DEFAULT_VOICEOVER_TEXT

    # Polly plain text has limits; keep it comfortably under the max.
    max_chars = int(os.getenv('VIDEO_GEN_VOICEOVER_MAX_CHARS', '800'))
    if max_chars > 0 and len(cleaned) > max_chars:
        cleaned = cleaned[: max_chars - 1].rstrip() + '…'
    return cleaned


def _extract_bedrock_text(payload: Any) -> Optional[str]:
    """Best-effort extraction of text from various Bedrock model response shapes."""
    if isinstance(payload, str):
        return payload.strip() or None
    if isinstance(payload, dict):
        for key in ('generation', 'output', 'text', 'completion'):
            val = payload.get(key)
            if isinstance(val, str) and val.strip():
                return val.strip()
        outputs = payload.get('outputs')
        if isinstance(outputs, list) and outputs:
            first = outputs[0]
            if isinstance(first, dict):
                for key in ('text', 'generation', 'output'):
                    val = first.get(key)
                    if isinstance(val, str) and val.strip():
                        return val.strip()
    return None


def _clean_ad_voiceover_text(text: str) -> str:
    cleaned = (text or '').strip()
    if not cleaned:
        return ''

    # Remove common markdown/code-fence artifacts.
    cleaned = cleaned.replace('```', ' ')
    cleaned = cleaned.replace('`', '')

    # Strip surrounding quotes.
    if (cleaned.startswith('"') and cleaned.endswith('"')) or (cleaned.startswith("'") and cleaned.endswith("'")):
        cleaned = cleaned[1:-1].strip()

    # Collapse whitespace.
    cleaned = ' '.join(cleaned.replace('\n', ' ').split())

    # Enforce a max word count (approx. 35 words) for ad-style VO.
    max_words = int(os.getenv('VIDEO_GEN_AD_VOICEOVER_MAX_WORDS', '35'))
    if max_words > 0:
        words = cleaned.split()
        if len(words) > max_words:
            cleaned = ' '.join(words[:max_words]).rstrip(' ,;:.') + '…'

    return cleaned


def _generate_ad_voiceover_from_prompt(prompt: str) -> str:
    """Generate short advertisement-style voiceover copy from the user's prompt."""
    fallback = _default_voiceover_text_from_prompt(prompt)
    if not VIDEO_GEN_AD_VOICEOVER_ENABLED:
        return fallback

    cleaned_prompt = (prompt or '').strip()
    if not cleaned_prompt:
        return VIDEO_GEN_DEFAULT_VOICEOVER_TEXT

    instruction = (
        "You are a creative advertising copywriter.\n"
        "Write a short voiceover script for an advertisement based on the video concept below.\n"
        "Constraints:\n"
        "- 1 to 2 sentences\n"
        "- Max 35 words\n"
        "- Clear call-to-action\n"
        "- Do not mention that you are an AI.\n"
        "- Output only the voiceover text, no quotes, no headings.\n\n"
        f"Video concept: {cleaned_prompt}\n"
    )

    try:
        resp = bedrock_runtime.invoke_model(
            modelId=VIDEO_GEN_AD_VOICEOVER_MODEL_ID,
            body=json.dumps({
                'prompt': instruction,
                'max_gen_len': VIDEO_GEN_AD_VOICEOVER_MAX_GEN_LEN,
                'temperature': VIDEO_GEN_AD_VOICEOVER_TEMPERATURE,
                'top_p': 0.9,
            })
        )
        raw = resp.get('body').read() if isinstance(resp, dict) and resp.get('body') else None
        if not raw:
            return fallback
        parsed = json.loads(raw)
        text = _extract_bedrock_text(parsed) or ''
        text = _clean_ad_voiceover_text(text)
        if not text:
            return fallback

        # Enforce a hard char cap for Polly and UX.
        if VIDEO_GEN_AD_VOICEOVER_MAX_CHARS > 0 and len(text) > VIDEO_GEN_AD_VOICEOVER_MAX_CHARS:
            text = text[: VIDEO_GEN_AD_VOICEOVER_MAX_CHARS - 1].rstrip() + '…'
        return text
    except Exception as exc:
        app.logger.warning('Ad voiceover generation failed; falling back to prompt text: %s', exc)
        return fallback


def _mux_generated_audio(
    input_path: Path,
    output_path: Path,
    *,
    kind: str,
    voiceover_text: Optional[str] = None,
    voice_id: Optional[str] = None,
) -> str:
    """Mux a generated audio track (tone, silence, or Polly voiceover) into an existing video file.

    Returns the effective kind used (may fall back to tone on failures).
    """
    if not FFMPEG_BIN:
        raise RuntimeError('ffmpeg is required to add audio to generated videos. Ensure ffmpeg is on PATH.')

    requested_voiceover = bool((voiceover_text or '').strip())
    effective_kind = kind
    duration_seconds = _probe_duration_seconds(input_path)

    # Voiceover path: generate an MP3 via Polly and pad it so the output keeps the full video duration.
    if requested_voiceover or kind == 'voiceover':
        effective_kind = 'voiceover'
        final_voice_id = (voice_id or VIDEO_GEN_VOICEOVER_VOICE_ID).strip() or VIDEO_GEN_VOICEOVER_VOICE_ID
        final_text = (voiceover_text or VIDEO_GEN_DEFAULT_VOICEOVER_TEXT).strip() or VIDEO_GEN_DEFAULT_VOICEOVER_TEXT

        if duration_seconds is None:
            app.logger.warning('Unable to determine video duration; falling back to tone audio')
            effective_kind = 'tone'
        else:
            with tempfile.TemporaryDirectory(prefix='video_gen_voiceover_') as tmpdir:
                mp3_path = Path(tmpdir) / 'voiceover.mp3'
                _synthesize_voiceover_mp3(final_text, mp3_path, voice_id=final_voice_id)

                # Pad audio so we don't truncate the video if voiceover is shorter than the video.
                volume_db = VIDEO_GEN_VOICEOVER_VOLUME_DB
                if volume_db == 0:
                    audio_filter_complex = '[1:a]apad[a]'
                else:
                    audio_filter_complex = f'[1:a]volume={volume_db}dB,apad[a]'

                cmd = [
                    FFMPEG_BIN,
                    '-y',
                    '-i', str(input_path),
                    '-i', str(mp3_path),
                    '-filter_complex', audio_filter_complex,
                    '-map', '0:v:0',
                    '-map', '[a]',
                    '-t', f'{duration_seconds:.3f}',
                    '-c:v', 'copy',
                    '-c:a', 'aac',
                    '-movflags', '+faststart',
                    str(output_path)
                ]
                subprocess.run(cmd, check=True, capture_output=True)
                return effective_kind

    # Tone/silence path (lavfi). Using -t keeps output aligned to the video.
    if effective_kind == 'silence':
        audio_filter = f"anullsrc=channel_layout={VIDEO_GEN_AUDIO_CHANNEL_LAYOUT}:sample_rate={VIDEO_GEN_AUDIO_SAMPLE_RATE}"
    else:
        audio_filter = (
            f"sine=frequency={VIDEO_GEN_AUDIO_TONE_FREQUENCY_HZ}:sample_rate={VIDEO_GEN_AUDIO_SAMPLE_RATE}"
            f",volume={VIDEO_GEN_AUDIO_TONE_VOLUME_DB}dB"
        )

    cmd = [
        FFMPEG_BIN,
        '-y',
        '-i', str(input_path),
        '-f', 'lavfi',
        '-i', audio_filter,
        '-map', '0:v:0',
        '-map', '1:a:0',
        '-c:v', 'copy',
        '-c:a', 'aac',
        '-movflags', '+faststart',
    ]

    if duration_seconds is not None:
        cmd.extend(['-t', f'{duration_seconds:.3f}'])
    else:
        cmd.append('-shortest')

    cmd.append(str(output_path))
    subprocess.run(cmd, check=True, capture_output=True)
    return effective_kind


def _ensure_s3_video_has_audio(
    bucket: str,
    key: str,
    *,
    force: bool = False,
    voiceover_text: Optional[str] = None,
    voice_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Ensure the S3 video object has an audio stream.

    If missing (or if force=True), mux a generated audio track based on VIDEO_GEN_AUDIO_KIND.

    Returns a dict with {changed: bool, kind: str}.
    """
    if not VIDEO_GEN_ENSURE_AUDIO:
        return {"changed": False, "kind": VIDEO_GEN_AUDIO_KIND}

    with tempfile.TemporaryDirectory(prefix='video_gen_audio_') as tmpdir:
        tmpdir_path = Path(tmpdir)
        input_path = tmpdir_path / 'input.mp4'
        output_path = tmpdir_path / 'output_with_audio.mp4'

        s3_client.download_file(bucket, key, str(input_path))

        if (not force) and _probe_has_audio(input_path):
            return {"changed": False, "kind": VIDEO_GEN_AUDIO_KIND}

        if force:
            app.logger.info('Force remux audio for %s/%s (kind=%s)', bucket, key, VIDEO_GEN_AUDIO_KIND)
        else:
            app.logger.info('No audio stream detected for %s/%s; muxing audio (kind=%s)', bucket, key, VIDEO_GEN_AUDIO_KIND)

        effective_kind = _mux_generated_audio(
            input_path,
            output_path,
            kind=VIDEO_GEN_AUDIO_KIND,
            voiceover_text=voiceover_text,
            voice_id=voice_id,
        )

        s3_client.upload_file(
            str(output_path),
            bucket,
            key,
            ExtraArgs={'ContentType': 'video/mp4'}
        )
        return {"changed": True, "kind": effective_kind}


def _sanitize_duration(raw_value) -> int:
    try:
        value = int(raw_value)
    except (TypeError, ValueError):
        value = DEFAULT_VIDEO_DURATION
    return max(MIN_VIDEO_DURATION, min(MAX_VIDEO_DURATION, value))


def upload_reference_images(uploaded_files, generation_id: str) -> List[Dict[str, str]]:
    """Upload reference images to S3 and return metadata."""
    references = []
    for file_obj in uploaded_files:
        if not file_obj or file_obj.filename == '':
            continue

        original_name = file_obj.filename
        _, ext = os.path.splitext(original_name)
        extension = ext if ext else '.png'
        safe_key = f"generated-videos/{generation_id}/references/{uuid.uuid4().hex}{extension}"
        content_type = file_obj.mimetype or 'application/octet-stream'

        # Reset stream position before uploading
        file_obj.stream.seek(0)
        s3_client.upload_fileobj(
            file_obj,
            S3_BUCKET,
            safe_key,
            ExtraArgs={'ContentType': content_type}
        )

        references.append({
            "s3_key": safe_key,
            "filename": original_name,
            "content_type": content_type
        })

    return references


def build_prompt_with_references(user_prompt: str, references: List[Dict[str, str]]) -> str:
    """Augment the user prompt with reference image context."""
    prompt = user_prompt.strip()

    if not prompt:
        prompt = "Create a cinematic video inspired by the uploaded reference images."

    if not references:
        return prompt

    reference_lines = []
    for ref in references:
        name = ref.get('filename') or 'reference image'
        reference_lines.append(f"- {name}")

    reference_block = "\n".join(reference_lines)
    prompt_with_refs = (
        f"{prompt}\n\nReference visuals to honor:\n{reference_block}\n"
    )

    return prompt_with_refs


def format_history_entry(entry: Dict[str, Any]) -> Dict[str, Any]:
    """Return a serializable copy of the history entry with presigned URLs."""
    formatted = dict(entry)
    references_with_urls = []

    for ref in entry.get('reference_images', []):
        s3_key = ref.get('s3_key')
        if not s3_key:
            continue

        try:
            url = s3_client.generate_presigned_url(
                'get_object',
                Params={
                    'Bucket': S3_BUCKET,
                    'Key': s3_key,
                    'ResponseContentType': ref.get('content_type', 'image/jpeg')
                },
                ExpiresIn=REFERENCE_URL_TTL
            )
        except ClientError:
            url = None

        references_with_urls.append({
            **ref,
            "url": url
        })

    formatted['reference_images'] = references_with_urls
    return formatted


def ensure_s3_bucket():
    """Ensure S3 bucket exists, create if not."""
    try:
        s3_client.head_bucket(Bucket=S3_BUCKET)
        app.logger.info(f"S3 bucket {S3_BUCKET} exists")
    except ClientError as e:
        error_code = e.response['Error']['Code']
        if error_code == '404':
            app.logger.info(f"Creating S3 bucket: {S3_BUCKET}")
            try:
                if AWS_REGION == 'us-east-1':
                    s3_client.create_bucket(Bucket=S3_BUCKET)
                else:
                    s3_client.create_bucket(
                        Bucket=S3_BUCKET,
                        CreateBucketConfiguration={'LocationConstraint': AWS_REGION}
                    )
                app.logger.info(f"S3 bucket created: {S3_BUCKET}")
            except Exception as create_error:
                app.logger.error(f"Failed to create bucket: {create_error}")
        else:
            app.logger.error(f"Error checking bucket: {e}")


def _generation_request_s3_key(generation_id: str) -> str:
    return f"generated-videos/{generation_id}/request.json"


def _save_generation_request_to_s3(generation_id: str, payload: Dict[str, Any]) -> None:
    """Persist prompt/voiceover settings so retrofits can be prompt-based even after restarts."""
    try:
        s3_client.put_object(
            Bucket=S3_BUCKET,
            Key=_generation_request_s3_key(generation_id),
            Body=json.dumps(payload, ensure_ascii=False).encode('utf-8'),
            ContentType='application/json',
        )
    except Exception as exc:
        # Non-fatal: generation can proceed without this.
        app.logger.warning('Failed to save generation request to S3 for %s: %s', generation_id, exc)


def _load_generation_request_from_s3(generation_id: str) -> Optional[Dict[str, Any]]:
    try:
        obj = s3_client.get_object(Bucket=S3_BUCKET, Key=_generation_request_s3_key(generation_id))
        body = obj['Body'].read().decode('utf-8')
        return json.loads(body)
    except Exception:
        return None


@app.route("/health", methods=["GET"])
def health_check() -> Any:
    """Health check endpoint."""
    return jsonify({
        "status": "ok",
        "service": "video-generation",
        "region": AWS_REGION,
        "s3_bucket": S3_BUCKET
    }), 200


@app.route("/generate-video", methods=["POST"])
def generate_video() -> Any:
    """Start async video generation from text prompt using Amazon Nova Reel."""
    try:
        content_type = (request.content_type or '').lower()
        is_multipart = content_type.startswith('multipart/form-data')

        if is_multipart:
            prompt = (request.form.get('prompt') or '').strip()
            uploaded_images = request.files.getlist('images')
            duration_value = request.form.get('duration')
            voiceover_text = (request.form.get('voiceover_text') or '').strip()
            voice_id = (request.form.get('voice_id') or '').strip()
        else:
            data = request.get_json(silent=True) or {}
            prompt = (data.get('prompt') or '').strip()
            uploaded_images = []
            duration_value = data.get('duration')
            voiceover_text = (data.get('voiceover_text') or '').strip()
            voice_id = (data.get('voice_id') or '').strip()

        duration_seconds = _sanitize_duration(duration_value)

        if not prompt and not uploaded_images:
            return jsonify({"error": "Please enter a prompt or upload at least one reference image."}), 400

        if uploaded_images and len(uploaded_images) > MAX_REFERENCE_IMAGES:
            return jsonify({
                "error": f"You can upload up to {MAX_REFERENCE_IMAGES} reference images."
            }), 400
        
        # Generate unique ID for this generation
        generation_id = str(uuid.uuid4())
        timestamp = datetime.utcnow().isoformat()
        
        reference_images = []
        if uploaded_images:
            reference_images = upload_reference_images(uploaded_images, generation_id)
            app.logger.info(
                "Uploaded %s reference image(s) for generation %s",
                len(reference_images),
                generation_id
            )

        model_prompt = build_prompt_with_references(prompt, reference_images)
        user_prompt = prompt

        app.logger.info(f"Starting async video generation for prompt: {prompt}")
        
        # Generate random seed for unique results
        import random
        seed = random.randint(0, 2147483646)
        
        # Prepare request body for Nova Reel (async API)
        model_input = {
            "taskType": "TEXT_VIDEO",
            "textToVideoParams": {"text": model_prompt},
            "videoGenerationConfig": {
                "fps": 24,
                "durationSeconds": duration_seconds,
                "dimension": "1280x720",
                "seed": seed
            }
        }
        
        # S3 output location
        s3_output_uri = f"s3://{S3_BUCKET}/generated-videos/{generation_id}/"
        output_config = {
            "s3OutputDataConfig": {
                "s3Uri": s3_output_uri
            }
        }
        
        app.logger.info(f"Invoking Amazon Nova Reel model asynchronously...")
        
        # Start async invocation
        response = bedrock_runtime.start_async_invoke(
            modelId='amazon.nova-reel-v1:0',
            modelInput=model_input,
            outputDataConfig=output_config
        )
        
        invocation_arn = response['invocationArn']
        
        app.logger.info(f"Async job started with ARN: {invocation_arn}")
        
        # Store the pending job in history with "pending" status
        # If voiceover is enabled and caller didn't provide custom narration,
        # generate advertisement-style voiceover from the prompt.
        if VIDEO_GEN_AUDIO_KIND == 'voiceover' and not voiceover_text:
            voiceover_text = _generate_ad_voiceover_from_prompt(user_prompt)

        _save_generation_request_to_s3(
            generation_id,
            {
                'generation_id': generation_id,
                'timestamp': timestamp,
                'prompt': user_prompt,
                'duration': duration_seconds,
                'voiceover_text': voiceover_text or None,
                'voice_id': voice_id or None,
                'audio_kind': VIDEO_GEN_AUDIO_KIND,
                'voiceover_mode': 'advertisement' if VIDEO_GEN_AD_VOICEOVER_ENABLED else 'prompt',
            }
        )

        pending_entry = {
            "id": generation_id,
            "prompt": user_prompt,
            "status": "pending",
            "invocation_arn": invocation_arn,
            "timestamp": timestamp,
            "duration": duration_seconds,
            "resolution": "1280x720",
            "reference_images": reference_images,
            # Optional: used later when muxing audio on completion.
            "voiceover_text": voiceover_text or None,
            "voice_id": voice_id or None,
        }
        GENERATION_HISTORY.insert(0, pending_entry)
        
        # Return immediately with job ID for frontend polling
        return jsonify({
            "success": True,
            "id": generation_id,
            "status": "pending",
            "message": "Video generation started. Please wait 1-2 minutes.",
            "invocation_arn": invocation_arn,
            "reference_images": format_history_entry(pending_entry).get('reference_images', [])
        }), 202  # 202 Accepted
        
    except ClientError as e:
        error_code = e.response['Error']['Code']
        error_message = e.response['Error']['Message']
        app.logger.error(f"AWS Error: {error_code} - {error_message}")
        app.logger.error(traceback.format_exc())
        return jsonify({
            "error": f"AWS Error: {error_message}",
            "code": error_code
        }), 500
        
    except Exception as e:
        app.logger.error(f"Video generation failed: {str(e)}")
        app.logger.error(traceback.format_exc())
        return jsonify({"error": f"Video generation failed: {str(e)}"}), 500


@app.route("/check-status/<generation_id>", methods=["GET"])
def check_status(generation_id):
    """Check the status of a video generation job."""
    try:
        # Find the entry in history
        entry = None
        entry_idx = None
        for idx, item in enumerate(GENERATION_HISTORY):
            if item['id'] == generation_id:
                entry = item
                entry_idx = idx
                break
        
        if not entry:
            return jsonify({"error": "Generation not found"}), 404
        
        # If already completed/failed, return the entry (but ensure audio for completed videos)
        if entry.get('status') != 'pending':
            if entry.get('status') == 'completed' and entry.get('s3_key') and not entry.get('audio_ensured'):
                try:
                    audio_result = _ensure_s3_video_has_audio(
                        S3_BUCKET,
                        entry['s3_key'],
                        voiceover_text=entry.get('voiceover_text'),
                        voice_id=entry.get('voice_id'),
                    )
                    entry['audio_ensured'] = True
                    entry['audio_added'] = bool(audio_result.get('changed'))
                    entry['audio_kind_used'] = audio_result.get('kind')
                    if entry_idx is not None:
                        GENERATION_HISTORY[entry_idx] = entry
                except Exception as audio_exc:
                    app.logger.error('Failed to ensure audio track for %s: %s', entry.get('s3_key'), audio_exc)
            return jsonify(format_history_entry(entry)), 200
        
        # Check job status with AWS
        invocation_arn = entry['invocation_arn']
        job_status = bedrock_runtime.get_async_invoke(invocationArn=invocation_arn)
        status = job_status['status']
        
        app.logger.info(f"Job {generation_id} status: {status}")
        
        if status == "Completed":
            # Get the actual S3 key from the response
            output_data = job_status.get('outputDataConfig', {})
            s3_uri = output_data.get('s3OutputDataConfig', {}).get('s3Uri', '')
            
            app.logger.info(f"Job completed. Output URI: {s3_uri}")
            
            # List files in the S3 prefix to find the actual video file
            prefix = f"generated-videos/{generation_id}/"
            try:
                response_list = s3_client.list_objects_v2(Bucket=S3_BUCKET, Prefix=prefix)
                if 'Contents' in response_list:
                    # Find the MP4 file (not the manifest.json)
                    video_s3_key = None
                    for obj in response_list['Contents']:
                        if obj['Key'].endswith('.mp4'):
                            video_s3_key = obj['Key']
                            break
                    
                    if not video_s3_key:
                        app.logger.error(f"No MP4 file found in S3 prefix: {prefix}")
                        app.logger.error(f"Files found: {[obj['Key'] for obj in response_list['Contents']]}")
                        return jsonify({"error": "Video MP4 file not found in S3", "status": "failed"}), 500
                    
                    app.logger.info(f"Found video at: {video_s3_key}")
                else:
                    app.logger.error(f"No files found in S3 prefix: {prefix}")
                    return jsonify({"error": "Video file not found in S3", "status": "failed"}), 500
            except Exception as e:
                app.logger.error(f"Error listing S3 files: {e}")
                return jsonify({"error": f"Failed to locate video: {str(e)}", "status": "failed"}), 500

            # Ensure the MP4 has an audio stream (mux silent AAC if missing)
            try:
                audio_result = _ensure_s3_video_has_audio(
                    S3_BUCKET,
                    video_s3_key,
                    voiceover_text=entry.get('voiceover_text'),
                    voice_id=entry.get('voice_id'),
                )
                entry['audio_ensured'] = True
                entry['audio_added'] = bool(audio_result.get('changed'))
                entry['audio_kind_used'] = audio_result.get('kind')
                if entry['audio_added']:
                    app.logger.info('Added audio track (%s) to %s', entry.get('audio_kind_used'), video_s3_key)
            except Exception as audio_exc:
                # Non-fatal: return video anyway, but log so we can fix env/ffmpeg.
                app.logger.error('Failed to ensure audio track for %s: %s', video_s3_key, audio_exc)
            
            # Generate presigned URL
            video_url = s3_client.generate_presigned_url(
                'get_object',
                Params={
                    'Bucket': S3_BUCKET, 
                    'Key': video_s3_key,
                    'ResponseContentType': 'video/mp4'
                },
                ExpiresIn=3600 * 24 * 7  # 7 days
            )
            
            # Update history entry
            entry['status'] = 'completed'
            entry['video_url'] = video_url
            entry['s3_key'] = video_s3_key
            GENERATION_HISTORY[entry_idx] = entry
            
            return jsonify(format_history_entry(entry)), 200
            
        elif status == "Failed":
            failure_message = job_status.get('failureMessage', 'Unknown error')
            app.logger.error(f"Video generation failed: {failure_message}")
            
            # Update history
            entry['status'] = 'failed'
            entry['error'] = failure_message
            GENERATION_HISTORY[entry_idx] = entry
            
            return jsonify(format_history_entry(entry)), 200
        
        # Still in progress
        entry['status'] = 'pending'
        return jsonify(format_history_entry(entry)), 200
        
    except Exception as e:
        app.logger.error(f"Error checking status: {e}")
        app.logger.error(traceback.format_exc())
        return jsonify({"error": str(e), "status": "error"}), 500


@app.route("/history", methods=["GET"])
def get_history() -> Any:
    """Get generation history."""
    # Filter out failed entries, only show pending and completed
    filtered_history = [h for h in GENERATION_HISTORY if h.get('status') != 'failed']
    return jsonify({
        "history": [format_history_entry(h) for h in filtered_history],
        "total": len(filtered_history)
    }), 200


@app.route("/history/<generation_id>", methods=["DELETE"])
def delete_from_history(generation_id: str) -> Any:
    """Delete a generation from history."""
    entry_idx = None
    for idx, entry in enumerate(GENERATION_HISTORY):
        if entry['id'] == generation_id:
            entry_idx = idx
            break
    
    if entry_idx is None:
        return jsonify({"error": "Generation not found"}), 404
    
    entry = GENERATION_HISTORY.pop(entry_idx)
    
    # Optionally delete from S3
    delete_from_s3 = request.args.get('delete_s3', 'false').lower() == 'true'
    if delete_from_s3:
        try:
            keys_to_delete = []
            primary_key = entry.get('s3_key', '')
            if primary_key:
                keys_to_delete.append(primary_key)

            for ref in entry.get('reference_images', []):
                ref_key = ref.get('s3_key')
                if ref_key:
                    keys_to_delete.append(ref_key)

            for key in keys_to_delete:
                s3_client.delete_object(Bucket=S3_BUCKET, Key=key)
                app.logger.info(f"Deleted from S3: {key}")
        except Exception as e:
            app.logger.error(f"Failed to delete from S3: {e}")
    
    return jsonify({
        "message": "Generation deleted from history",
        "deleted_from_s3": delete_from_s3
    }), 200


@app.route('/ensure-audio/<generation_id>', methods=['POST'])
def ensure_audio_for_generation(generation_id: str) -> Any:
    """Retrofit audio for an existing generation by scanning its S3 prefix for an MP4 and muxing silent audio if needed."""
    try:
        payload = request.get_json(silent=True) or {}
        force = bool(payload.get('force'))
        voiceover_text = (payload.get('voiceover_text') or '').strip()
        voice_id = (payload.get('voice_id') or '').strip()

        # If caller didn't supply narration text, try to derive it from:
        # 1) stored in-memory history (current process)
        # 2) persisted S3 request.json
        # 3) request payload prompt
        if VIDEO_GEN_AUDIO_KIND == 'voiceover' and not voiceover_text:
            for item in GENERATION_HISTORY:
                if item.get('id') == generation_id:
                    voiceover_text = _generate_ad_voiceover_from_prompt(item.get('prompt', ''))
                    if not voice_id:
                        voice_id = (item.get('voice_id') or '').strip()
                    break

        if VIDEO_GEN_AUDIO_KIND == 'voiceover' and not voiceover_text:
            saved = _load_generation_request_from_s3(generation_id)
            if saved:
                saved_prompt = str(saved.get('prompt', '') or '')
                voiceover_text = _generate_ad_voiceover_from_prompt(saved_prompt)
                if not voice_id:
                    voice_id = str(saved.get('voice_id', '') or '').strip()

        if VIDEO_GEN_AUDIO_KIND == 'voiceover' and not voiceover_text:
            voiceover_text = _generate_ad_voiceover_from_prompt(str(payload.get('prompt', '') or ''))

        # If caller didn't supply narration text, try to derive it from the stored prompt.
        if VIDEO_GEN_AUDIO_KIND == 'voiceover' and not voiceover_text:
            for item in GENERATION_HISTORY:
                if item.get('id') == generation_id:
                    voiceover_text = _default_voiceover_text_from_prompt(item.get('prompt', ''))
                    if not voice_id:
                        voice_id = (item.get('voice_id') or '').strip()
                    break
        prefix = f"generated-videos/{generation_id}/"
        response_list = s3_client.list_objects_v2(Bucket=S3_BUCKET, Prefix=prefix)
        if 'Contents' not in response_list:
            return jsonify({"error": "No files found for generation", "generation_id": generation_id}), 404

        video_s3_key = None
        for obj in response_list['Contents']:
            if obj.get('Key', '').endswith('.mp4'):
                video_s3_key = obj['Key']
                break

        if not video_s3_key:
            return jsonify({"error": "Video MP4 file not found in S3", "generation_id": generation_id}), 404

        audio_result = _ensure_s3_video_has_audio(
            S3_BUCKET,
            video_s3_key,
            force=force,
            voiceover_text=voiceover_text or None,
            voice_id=voice_id or None,
        )
        video_url = s3_client.generate_presigned_url(
            'get_object',
            Params={
                'Bucket': S3_BUCKET,
                'Key': video_s3_key,
                'ResponseContentType': 'video/mp4'
            },
            ExpiresIn=3600 * 24 * 7
        )

        return jsonify({
            "generation_id": generation_id,
            "s3_key": video_s3_key,
            "audio_added": bool(audio_result.get('changed')),
            "audio_ensured": True,
            "audio_kind": VIDEO_GEN_AUDIO_KIND,
            "audio_kind_used": audio_result.get('kind'),
            "force": force,
            "voiceover_text": voiceover_text or None,
            "voice_id": voice_id or None,
            "video_url": video_url,
        }), 200
    except Exception as exc:
        app.logger.error('Failed to ensure audio for generation %s: %s', generation_id, exc)
        app.logger.error(traceback.format_exc())
        return jsonify({"error": f"Failed to ensure audio: {str(exc)}"}), 500


@app.route('/video/<generation_id>', methods=['GET'])
def stream_video(generation_id):
    """Proxy endpoint to stream video from S3 with proper headers"""
    try:
        # Find the video in history
        entry = None
        for item in GENERATION_HISTORY:
            if item['id'] == generation_id:
                entry = item
                break
        
        if not entry:
            return jsonify({"error": "Video not found"}), 404
        
        if entry.get('status') != 'completed':
            return jsonify({"error": "Video not ready", "status": entry.get('status')}), 404
        
        # Get video from S3
        s3_key = entry.get('s3_key')
        if not s3_key:
            return jsonify({"error": "Video file not found"}), 404
            
        response = s3_client.get_object(Bucket=S3_BUCKET, Key=s3_key)
        
        # Return video with proper headers
        return Response(
            response['Body'].read(),
            mimetype='video/mp4',
            headers={
                'Accept-Ranges': 'bytes',
                'Content-Type': 'video/mp4',
                'Access-Control-Allow-Origin': '*'
            }
        )
    except Exception as e:
        app.logger.error(f"Error streaming video: {e}")
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    app.logger.info("Starting Video Generation Service...")
    app.logger.info(f"AWS Region: {AWS_REGION}")
    app.logger.info(f"S3 Bucket: {S3_BUCKET}")
    
    # Ensure S3 bucket exists
    ensure_s3_bucket()
    
    # Start Flask app
    app.run(host="0.0.0.0", port=5009, debug=False)
