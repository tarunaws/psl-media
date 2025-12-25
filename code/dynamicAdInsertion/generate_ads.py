#!/usr/bin/env python3
"""
Script to generate 10-second advertisements using Amazon Nova Reel.
This script creates ads for all categories in the Dynamic Ad Insertion feature.
"""

import os
import requests
import time
import json
import shutil
import subprocess
import tempfile
import math
import struct
import wave
from pathlib import Path
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse

import boto3
from botocore.exceptions import ClientError, BotoCoreError

from shared.env_loader import load_environment

# Video Generation Service URL
VIDEO_GEN_URL = "http://localhost:5009"

# Ad prompts for each category
AD_PROMPTS = {
    "tech_gadget_ad": {
        "duration": 10,
        "segments": [
            {
                "label": "Launch",
                "duration": 5,
                "prompt": "Opening hero shot of a futuristic smartphone emerging from a vortex of data streams, chrome reflections, particle trails, studio-grade product cinematography, volumetric lighting"
            },
            {
                "label": "Features",
                "duration": 5,
                "prompt": "Macro close-ups of holographic display, AI interface icons, camera array spinning with neon accents, seamless transition to device hovering over a minimalist desk"
            }
        ]
    },
    "sports_drink_ad": {
        "duration": 10,
        "segments": [
            {
                "label": "Action",
                "duration": 5,
                "prompt": "High-energy montage of athletes sprinting and leaping through mist, colorful vapor trails, splashes of citrus liquid suspended mid-air, cinematic slow motion"
            },
            {
                "label": "Refresh",
                "duration": 5,
                "prompt": "Bottle hero shot on ice with droplets, liquid pouring in macro, electrified water arcs wrapping around product, bold typography hovering in air"
            }
        ]
    },
    "streaming_service_ad": {
        "duration": 10,
        "segments": [
            {
                "label": "Genres",
                "duration": 5,
                "prompt": "Collage of movie scenes across sci-fi, romance, thriller dissolving across a floating smart TV in a cozy living room, cinematic lighting, shallow depth of field"
            },
            {
                "label": "Cinema Night",
                "duration": 5,
                "prompt": "Slow push-in on popcorn bowl, remote control, ambient LED glow, title cards appearing in the air celebrating new releases, luxurious streaming vibe"
            }
        ]
    },
    "family_vacation_ad": {
        "duration": 10,
        "segments": [
            {
                "label": "Beach Day",
                "duration": 5,
                "prompt": "Happy family running toward turquoise ocean, drone sweep over resort cabanas, kids splashing, golden-hour sunbeams"
            },
            {
                "label": "Sunset Magic",
                "duration": 5,
                "prompt": "Parents and kids toasting mocktails at sunset bonfire, aerial fireworks, resort skyline glowing, cinematic lens flares"
            }
        ]
    },
    "fitness_equipment_ad": {
        "duration": 10,
        "segments": [
            {
                "label": "Intensity",
                "duration": 5,
                "prompt": "Athlete powering through battle ropes and connected smart weights, sweat particles, dramatic rim lighting, digital HUD overlays"
            },
            {
                "label": "Smart Studio",
                "duration": 5,
                "prompt": "Wide shot of premium home gym with mirrored screens coaching form, close-up on adaptive resistance dial, glowing metrics hovering"
            }
        ]
    },
    "gaming_console_ad": {
        "duration": 10,
        "segments": [
            {
                "label": "Gameplay Surge",
                "duration": 5,
                "prompt": "Explosive cyberpunk city chase with neon trails, character dodging laser fire, controller haptics visualized as light pulses"
            },
            {
                "label": "Hero Console",
                "duration": 5,
                "prompt": "Console levitating in dark studio, holographic UI showcasing ray tracing, close-up of controller triggers, energy arcs wrapping hardware"
            }
        ]
    },
    "gourmet_food_ad": {
        "duration": 10,
        "segments": [
            {
                "label": "Chef Craft",
                "duration": 5,
                "prompt": "Chef searing ingredients in copper pan, steam swirling in golden light, slow-motion seasoning dust, cinematic kitchen"
            },
            {
                "label": "Plating",
                "duration": 5,
                "prompt": "Elegant plating sequence on marble table, drizzle of sauce, macro of desserts, candlelit restaurant ambiance"
            }
        ]
    },
    "travel_booking_ad": {
        "duration": 10,
        "segments": [
            {
                "label": "Adventure",
                "duration": 5,
                "prompt": "Drone flyover of mountains, waterfall hikers, hot air balloons rising above savanna, cinematic travel montage"
            },
            {
                "label": "Ease",
                "duration": 5,
                "prompt": "Traveler tapping itinerary on holographic tablet in boutique hotel, transitions to aerial view of tropical beach arrival"
            }
        ]
    },
    "eco_products_ad": {
        "duration": 10,
        "segments": [
            {
                "label": "Nature",
                "duration": 5,
                "prompt": "Sunlit forest, dew drops on leaves, wind turbines turning slowly, close-up of recycled materials"
            },
            {
                "label": "Lifestyle",
                "duration": 5,
                "prompt": "Modern kitchen using refillable eco products, solar-powered gadgets charging, family opening sustainable packaging"
            }
        ]
    },
    "luxury_watch_ad": {
        "duration": 10,
        "segments": [
            {
                "label": "Mechanics",
                "duration": 5,
                "prompt": "Ultra close-up of tourbillon gears rotating under sapphire crystal, moody chiaroscuro lighting, floating specs"
            },
            {
                "label": "Lifestyle",
                "duration": 5,
                "prompt": "Watch resting on black velvet beside champagne flute, evening skyline reflections across polished metal, elegant hand putting it on"
            }
        ]
    }
}

VOICEOVER_SCRIPTS = {
    "tech_gadget_ad": "Experience the new Nova X smartphone. Stunning holographic glass, adaptive intelligence, and all day speed. Elevate every moment with the future of mobile in the palm of your hand.",
    "sports_drink_ad": "Push harder, hydrate smarter. Quantum Fuel surges through every muscle, cooling heat with citrus energy. Sip, charge, and rule the final seconds of the game.",
    "streaming_service_ad": "Tonight the theatre moves to your couch. Infinite genres, brand new originals, and zero commercials with Aurora Stream. Press play and let every mood find its movie.",
    "family_vacation_ad": "Pack wonder into every day. Ocean Crest Resorts surrounds your family with sunrise breakfasts, splash zones, and sunset campfires. Make ten seconds of memories that last all year.",
    "fitness_equipment_ad": "Turn the spare room into a pro studio. Atlas Flex adapts to each rep, tracking form, pacing breath, and coaching every push. Stronger stories start right here.",
    "gaming_console_ad": "Power up the pulse with Nebula One. Ray-traced worlds, zero-lag cloud play, and a controller that vibes with every combo. This is more than a game—it's your hero moment.",
    "gourmet_food_ad": "Chef's Table delivery brings five star artistry home. Sear, drizzle, and share courses plated by Michelin creators, finished in your kitchen in under ten minutes.",
    "travel_booking_ad": "Unlock the itinerary of your dreams with Horizon Loop. One tap bundles flights, boutique stays, and local guides so you chase more sunsets and fewer tabs.",
    "eco_products_ad": "Choose Verdant Living and watch daily habits heal the planet. Refillable cleaners, solar smart plugs, and circular packaging keep your routine fresh and guilt-free.",
    "luxury_watch_ad": "Time glows differently with the Celesté chronograph. Hand-cut sapphire, midnight enamel, and a heartbeat of Swiss precision. Write the next decade in brilliance."
}

MAX_NOVA_DURATION = 6


def _get_active_prompts() -> Dict[str, Dict[str, str]]:
    filter_env = os.getenv("DAI_AD_IDS", "").strip()
    if not filter_env:
        return AD_PROMPTS
    requested = [item.strip() for item in filter_env.split(",") if item.strip()]
    subset = {ad_id: AD_PROMPTS[ad_id] for ad_id in requested if ad_id in AD_PROMPTS}
    if not subset:
        print("⚠️  DAI_AD_IDS did not match any known ads; defaulting to full inventory")
        return AD_PROMPTS
    print(f"ℹ️  Filtering ad generation to: {', '.join(subset.keys())}")
    return subset


def _expand_segments(config: Dict[str, Dict[str, str]]) -> List[Dict[str, str]]:
    segments = config.get("segments") or []
    if not segments:
        base_duration = min(config.get("duration", 10), MAX_NOVA_DURATION)
        return [{"prompt": config.get("prompt", ""), "duration": base_duration, "label": "Primary"}]

    normalized = []
    for idx, segment in enumerate(segments):
        prompt = segment.get("prompt") or config.get("prompt", "")
        duration = min(max(segment.get("duration", config.get("duration", 10)), 1), MAX_NOVA_DURATION)
        label = segment.get("label") or f"Segment {idx + 1}"
        normalized.append({
            "prompt": prompt,
            "duration": duration,
            "label": label
        })
    return normalized


load_environment()

AWS_REGION = os.getenv("AWS_REGION")
if not AWS_REGION:
    raise RuntimeError("Set AWS_REGION before running ad generation script")

SOURCE_VIDEO_BUCKET = os.getenv("VIDEO_GEN_S3_BUCKET") or os.getenv("MEDIA_S3_BUCKET")
if not SOURCE_VIDEO_BUCKET:
    raise RuntimeError("Set VIDEO_GEN_S3_BUCKET or MEDIA_S3_BUCKET before running ad generation script")

DAI_BUCKET = os.getenv("DAI_S3_BUCKET") or SOURCE_VIDEO_BUCKET
DAI_ADS_PREFIX = os.getenv("DAI_S3_PREFIX", "ads")

try:
    DAI_THUMBNAIL_OFFSET = float(os.getenv("DAI_THUMBNAIL_SECOND", "1.0"))
except ValueError:
    DAI_THUMBNAIL_OFFSET = 1.0

s3_client = boto3.client("s3", region_name=AWS_REGION)
polly_client = boto3.client("polly", region_name=AWS_REGION)
FFMPEG_BIN = shutil.which("ffmpeg")
FFPROBE_BIN = shutil.which("ffprobe")
if FFMPEG_BIN and not FFPROBE_BIN and "ffmpeg" in FFMPEG_BIN:
    probe_candidate = FFMPEG_BIN.replace("ffmpeg", "ffprobe")
    if Path(probe_candidate).exists():
        FFPROBE_BIN = probe_candidate
VOICEOVER_VOICE_ID = os.getenv("DAI_VOICEOVER_VOICE", "Joanna")
ENABLE_VOICEOVER = os.getenv("DAI_ENABLE_VOICEOVER", "true").lower() == "true"
try:
    VOICEOVER_GAIN_DB = float(os.getenv("DAI_VOICEOVER_GAIN_DB", "0"))
except ValueError:
    VOICEOVER_GAIN_DB = 0.0

try:
    TARGET_AUDIO_SAMPLE_RATE = int(os.getenv("DAI_AUDIO_SAMPLE_RATE", "44100"))
except ValueError:
    TARGET_AUDIO_SAMPLE_RATE = 44100

LOOP_VIDEO_FOR_PADDING = os.getenv("DAI_LOOP_VIDEO_FOR_PADDING", "true").lower() == "true"

ENABLE_BACKGROUND_MUSIC = os.getenv("DAI_ENABLE_BG_MUSIC", "true").lower() == "true"
BG_MUSIC_BUCKET = os.getenv("DAI_BG_MUSIC_BUCKET") or DAI_BUCKET
BG_MUSIC_KEY = (os.getenv("DAI_BG_MUSIC_KEY") or "").strip()
BG_MUSIC_FILE = os.getenv("DAI_BG_MUSIC_FILE")
try:
    BG_MUSIC_GAIN_DB = float(os.getenv("DAI_BG_MUSIC_GAIN_DB", "-12"))
except ValueError:
    BG_MUSIC_GAIN_DB = -12.0

BG_MUSIC_OVERRIDES = {}
raw_bg_override = os.getenv("DAI_BG_MUSIC_OVERRIDES", "").strip()
if raw_bg_override:
    try:
        parsed_override = json.loads(raw_bg_override)
        if isinstance(parsed_override, dict):
            BG_MUSIC_OVERRIDES = parsed_override
        else:
            print("⚠️  DAI_BG_MUSIC_OVERRIDES must be a JSON object mapping ad IDs to S3 keys; ignoring.")
    except json.JSONDecodeError as exc:
        print(f"⚠️  Unable to parse DAI_BG_MUSIC_OVERRIDES: {exc}")


def derive_s3_key_from_url(url: str) -> str:
    """Return the S3 object key embedded within a presigned URL."""
    if not url:
        return ""
    parsed = urlparse(url)
    return parsed.path.lstrip("/")


def sync_generated_asset(ad_id: str, source_key: str, local_path: Optional[Path] = None) -> Dict[str, str]:
    """Copy or upload the generated video into the DAI bucket and create a thumbnail."""
    dest_video_key = f"{DAI_ADS_PREFIX}/{ad_id}/creative.mp4"

    if local_path:
        if not local_path.exists():
            raise FileNotFoundError(f"Local asset for {ad_id} missing at {local_path}")
        print(f"   ↳ Uploading assembled video into s3://{DAI_BUCKET}/{dest_video_key}")
        try:
            s3_client.upload_file(
                str(local_path),
                DAI_BUCKET,
                dest_video_key,
                ExtraArgs={"ContentType": "video/mp4"}
            )
        except ClientError as exc:
            raise RuntimeError(f"Failed to upload assembled video for {ad_id}: {exc}") from exc
    else:
        if not source_key:
            raise ValueError(f"Missing source key for {ad_id}")
        copy_source = {"Bucket": SOURCE_VIDEO_BUCKET, "Key": source_key}
        print(f"   ↳ Copying video into s3://{DAI_BUCKET}/{dest_video_key}")
        try:
            s3_client.copy(
                copy_source,
                DAI_BUCKET,
                dest_video_key,
                ExtraArgs={"ContentType": "video/mp4"}
            )
        except ClientError as exc:
            raise RuntimeError(f"Failed to copy video for {ad_id}: {exc}") from exc

    dest_thumb_key = None
    if FFMPEG_BIN:
        dest_thumb_key = f"{DAI_ADS_PREFIX}/{ad_id}/thumbnail.jpg"
        try:
            with tempfile.TemporaryDirectory() as tmpdir:
                local_video = Path(tmpdir) / "ad.mp4"
                local_thumb = Path(tmpdir) / "thumb.jpg"
                s3_client.download_file(DAI_BUCKET, dest_video_key, str(local_video))

                ts = max(DAI_THUMBNAIL_OFFSET, 0.0)
                ffmpeg_cmd = [
                    FFMPEG_BIN,
                    "-y",
                    "-ss",
                    f"{ts:.2f}",
                    "-i",
                    str(local_video),
                    "-frames:v",
                    "1",
                    "-q:v",
                    "2",
                    str(local_thumb)
                ]

                subprocess.run(ffmpeg_cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

                if local_thumb.exists():
                    s3_client.upload_file(
                        str(local_thumb),
                        DAI_BUCKET,
                        dest_thumb_key,
                        ExtraArgs={"ContentType": "image/jpeg"}
                    )
                    print(f"   ↳ Uploaded thumbnail s3://{DAI_BUCKET}/{dest_thumb_key}")
                else:
                    print(f"   ⚠️  Thumbnail not created for {ad_id}")
        except (ClientError, subprocess.CalledProcessError, FileNotFoundError) as exc:
            print(f"   ⚠️  Thumbnail generation failed for {ad_id}: {exc}")
            dest_thumb_key = None
    else:
        print("   ⚠️  ffmpeg not available; skipping thumbnail generation")

    return {
        "dai_video_key": dest_video_key,
        "dai_thumbnail_key": dest_thumb_key
    }


def _probe_video_duration(path: Path) -> float:
    if not FFPROBE_BIN or not path.exists():
        return 0.0
    try:
        result = subprocess.run(
            [FFPROBE_BIN, "-v", "error", "-show_entries", "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", str(path)],
            check=True,
            capture_output=True,
            text=True
        )
        return float(result.stdout.strip())
    except (subprocess.CalledProcessError, ValueError):
        return 0.0


def _db_to_linear(db_value: float) -> float:
    try:
        return pow(10.0, db_value / 20.0)
    except (ValueError, OverflowError):
        return 1.0


def _synthesize_default_background_track(output_path: Path, duration: float) -> Path:
    duration = max(duration, 6.0)
    sample_rate = 44100
    total_samples = int(sample_rate * duration)
    freqs = (196.0, 246.94, 311.13, 392.0)
    tremolo_freq = 0.35
    attack = 1.2
    release = 1.2

    with wave.open(str(output_path), "w") as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(sample_rate)

        for i in range(total_samples):
            t = i / sample_rate
            base = sum(math.sin(2 * math.pi * freq * t) for freq in freqs) / len(freqs)
            lfo = 0.65 + 0.35 * math.sin(2 * math.pi * tremolo_freq * t)
            fade_in = min(1.0, t / max(attack, 0.01))
            fade_out = min(1.0, max(duration - t, 0.0) / max(release, 0.01))
            envelope = max(0.0, min(1.0, fade_in)) * max(0.0, min(1.0, fade_out)) * lfo
            sample = max(-1.0, min(1.0, base * envelope))
            wav_file.writeframes(struct.pack("<h", int(sample * 16000)))

    return output_path


def _prepare_background_track(ad_id: str, tmpdir: Path, duration: float) -> Optional[Path]:
    if not ENABLE_BACKGROUND_MUSIC:
        return None

    duration = max(duration, 1.0)

    if BG_MUSIC_FILE:
        local_track = Path(BG_MUSIC_FILE).expanduser()
        if local_track.exists():
            dest = tmpdir / f"{ad_id}_bg{local_track.suffix or '.mp3'}"
            shutil.copy(local_track, dest)
            return dest
        print(f"   ⚠️  Background music file {local_track} not found; falling back to defaults")

    key = BG_MUSIC_OVERRIDES.get(ad_id) or BG_MUSIC_KEY
    if key:
        dest = tmpdir / f"{ad_id}_bg{Path(key).suffix or '.mp3'}"
        try:
            s3_client.download_file(BG_MUSIC_BUCKET, key, str(dest))
            return dest
        except ClientError as exc:
            print(f"   ⚠️  Could not download bg music {key} from s3://{BG_MUSIC_BUCKET}: {exc}")

    synth_path = tmpdir / f"{ad_id}_bg_default.wav"
    return _synthesize_default_background_track(synth_path, duration)


def _mix_audio_tracks(voice_path: Path, music_path: Path, output_path: Path, duration: float) -> bool:
    if not FFMPEG_BIN:
        return False

    duration = max(duration, 1.0)
    voice_volume = _db_to_linear(VOICEOVER_GAIN_DB)
    music_volume = _db_to_linear(BG_MUSIC_GAIN_DB)

    voice_chain = f"[0:a]apad,atrim=0:{duration:.2f}"
    if not math.isclose(voice_volume, 1.0, rel_tol=1e-2):
        voice_chain += f",volume={voice_volume:.3f}"
    voice_chain += "[voice]"

    music_chain = f"[1:a]aloop=loop=-1:size=0,apad,atrim=0:{duration:.2f}"
    if not math.isclose(music_volume, 1.0, rel_tol=1e-2):
        music_chain += f",volume={music_volume:.3f}"
    music_chain += "[music]"

    filter_complex = (
        f"{voice_chain};{music_chain};"
        "[voice][music]amix=inputs=2:duration=first:dropout_transition=2,"
        "loudnorm=I=-16:LRA=11:TP=-1.5[mix]"
    )
    cmd = [
        FFMPEG_BIN,
        "-y",
        "-i",
        str(voice_path),
        "-i",
        str(music_path),
        "-filter_complex",
        filter_complex,
        "-map",
        "[mix]",
        "-c:a",
        "aac",
        "-ar",
        str(TARGET_AUDIO_SAMPLE_RATE),
        "-t",
        f"{duration:.2f}",
        str(output_path)
    ]

    try:
        subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        return True
    except subprocess.CalledProcessError as exc:
        print(f"   ⚠️  Background music mix failed: {exc}")
        return False


def _finalize_ad_segments(ad_id: str, ad_plan: Dict[str, Any]) -> Dict[str, Any]:
    segments_meta = sorted(ad_plan["segments"], key=lambda seg: seg["segment_index"])
    if not segments_meta:
        raise RuntimeError("No completed segments available for assembly")
    if not FFMPEG_BIN:
        raise RuntimeError("ffmpeg is required to assemble video segments")

    print(f"   ↳ Assembling {len(segments_meta)} Nova segments for {ad_id}")
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir_path = Path(tmpdir)
        local_segments = []
        for idx, segment in enumerate(segments_meta, start=1):
            local_path = tmpdir_path / f"segment_{idx}.mp4"
            s3_key = segment.get("s3_key")
            if not s3_key:
                raise RuntimeError(f"Segment {idx} for {ad_id} missing S3 key")
            s3_client.download_file(SOURCE_VIDEO_BUCKET, s3_key, str(local_path))
            local_segments.append(local_path)

        if not local_segments:
            raise RuntimeError("Failed to download any segments")

        assembled_path = local_segments[0]
        if len(local_segments) > 1:
            concat_list = tmpdir_path / "segments.txt"
            with open(concat_list, "w", encoding="utf-8") as handle:
                for path in local_segments:
                    handle.write(f"file '{path}'\n")
            assembled_path = tmpdir_path / "assembled.mp4"
            concat_cmd = [
                FFMPEG_BIN,
                "-y",
                "-f",
                "concat",
                "-safe",
                "0",
                "-i",
                str(concat_list),
                "-c",
                "copy",
                str(assembled_path)
            ]
            subprocess.run(concat_cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

        sync_info = sync_generated_asset(ad_id, segments_meta[0]["s3_key"], local_path=assembled_path)
        target_duration = ad_plan["config"].get("duration", 10)
        if not apply_voiceover_track(ad_id, sync_info["dai_video_key"], target_duration):
            raise RuntimeError("Voiceover creation failed")

        ad_plan["finalized"] = True
        ad_plan["voiceover_applied"] = True
        ad_plan["sync_info"] = sync_info

        return {
            "ad_id": ad_id,
            "generation_ids": [seg["generation_id"] for seg in segments_meta],
            "segment_details": segments_meta,
            "dai_video_key": sync_info["dai_video_key"],
            "dai_thumbnail_key": sync_info["dai_thumbnail_key"],
            "voiceover_applied": True
        }


def apply_voiceover_track(ad_id: str, video_key: str, target_duration: float) -> bool:
    """Overlay a narrated voiceover onto the provided video asset."""
    if not ENABLE_VOICEOVER:
        print("   ℹ️  Voiceover generation disabled via env flag; skipping")
        return True
    if not FFMPEG_BIN:
        print(f"   ⚠️  Skipping voiceover for {ad_id}: ffmpeg not available")
        return False
    script = VOICEOVER_SCRIPTS.get(ad_id)
    if not script:
        print(f"   ⚠️  Skipping voiceover for {ad_id}: no script configured")
        return False
    if target_duration <= 0:
        target_duration = 10.0
    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)
            local_video = tmpdir_path / "video.mp4"
            voice_file = tmpdir_path / "voiceover.mp3"
            final_video = tmpdir_path / "final.mp4"

            s3_client.download_file(DAI_BUCKET, video_key, str(local_video))

            polly_kwargs = {
                "Text": script,
                "VoiceId": VOICEOVER_VOICE_ID,
                "OutputFormat": "mp3",
                "Engine": "neural"
            }
            response = polly_client.synthesize_speech(**polly_kwargs)
            audio_stream = response.get("AudioStream")
            if not audio_stream:
                raise RuntimeError("Polly returned empty audio stream")
            with open(voice_file, "wb") as voice_handle:
                voice_handle.write(audio_stream.read())

            audio_input = voice_file
            if ENABLE_BACKGROUND_MUSIC:
                bg_track = _prepare_background_track(ad_id, tmpdir_path, target_duration)
                if bg_track:
                    mixed_audio = tmpdir_path / "voice_with_music.m4a"
                    if _mix_audio_tracks(voice_file, bg_track, mixed_audio, target_duration):
                        audio_input = mixed_audio
                        print(f"   ↳ Added background music bed for {ad_id}")
                    else:
                        print("   ⚠️  Continuing without music due to mix error")

            current_duration = _probe_video_duration(local_video)
            if current_duration <= 0:
                current_duration = target_duration

            pad_seconds = max(0.0, target_duration - current_duration)
            needs_padding = pad_seconds > 0.05
            use_looping = bool(LOOP_VIDEO_FOR_PADDING and needs_padding and current_duration > 0.2)
            loop_count = 0
            if use_looping:
                loop_count = max(0, math.ceil(target_duration / current_duration) - 1)
                if loop_count == 0:
                    use_looping = False

            video_filter = None
            if needs_padding and not use_looping:
                video_filter = f"tpad=stop_mode=clone:stop_duration={pad_seconds:.2f}"

            ffmpeg_cmd = [FFMPEG_BIN, "-y"]
            if use_looping and loop_count > 0:
                ffmpeg_cmd += ["-stream_loop", str(loop_count)]
            ffmpeg_cmd += ["-i", str(local_video), "-i", str(audio_input)]
            if video_filter:
                ffmpeg_cmd += ["-vf", video_filter]

            video_codec = "libx264" if (use_looping or video_filter) else "copy"
            ffmpeg_cmd += [
                "-map", "0:v:0",
                "-map", "1:a:0",
                "-c:v", video_codec
            ]
            if video_codec != "copy":
                ffmpeg_cmd += ["-preset", "veryfast", "-crf", "18"]

            ffmpeg_cmd += [
                "-c:a", "aac",
                "-ar", str(TARGET_AUDIO_SAMPLE_RATE),
                "-t", f"{target_duration:.2f}",
                str(final_video)
            ]
            subprocess.run(ffmpeg_cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

            s3_client.upload_file(
                str(final_video),
                DAI_BUCKET,
                video_key,
                ExtraArgs={"ContentType": "video/mp4"}
            )
            return True
    except (ClientError, BotoCoreError, subprocess.CalledProcessError, FileNotFoundError) as exc:
        print(f"   ⚠️  Voiceover generation failed for {ad_id}: {exc}")
    return False


def generate_video(ad_id: str, prompt: str, duration: int, segment_label: Optional[str] = None) -> Dict:
    """Generate a video using the video generation service."""
    display_name = f"{ad_id} [{segment_label}]" if segment_label else ad_id
    print(f"🎬 Generating {display_name}...")
    
    try:
        response = requests.post(
            f"{VIDEO_GEN_URL}/generate-video",
            json={
                "prompt": prompt,
                "duration": duration
            },
            timeout=10
        )
        
        if response.status_code == 202:
            data = response.json()
            generation_id = data.get('id') or data.get('generation_id')
            print(f"✓ {display_name}: Generation started (ID: {generation_id})")
            return {
                "ad_id": ad_id,
                "generation_id": generation_id,
                "status": "processing"
            }
        else:
            print(f"✗ {display_name}: Failed to start generation - {response.status_code}")
            return {
                "ad_id": ad_id,
                "error": f"HTTP {response.status_code}",
                "status": "failed"
            }
    except Exception as e:
        print(f"✗ {display_name}: Error - {str(e)}")
        return {
            "ad_id": ad_id,
            "error": str(e),
            "status": "failed"
        }


def check_status(generation_id: str) -> Dict:
    """Check the status of a video generation."""
    try:
        response = requests.get(
            f"{VIDEO_GEN_URL}/check-status/{generation_id}",
            timeout=5
        )
        
        if response.status_code == 200:
            return response.json()
        else:
            return {"status": "error", "message": f"HTTP {response.status_code}"}
    except Exception as e:
        return {"status": "error", "message": str(e)}


def main():
    """Main function to generate all advertisements."""
    active_prompts = _get_active_prompts()
    total_ads = len(active_prompts)
    if total_ads == 0:
        print("No advertisements selected. Set DAI_AD_IDS or update prompts.")
        return

    print("=" * 80)
    print("🎥 Dynamic Ad Insertion - Advertisement Generator")
    print("=" * 80)
    print(f"\nGenerating {total_ads} advertisements using chained Nova Reel segments...")
    print()

    ad_plans: Dict[str, Dict[str, Any]] = {}
    generation_requests: List[Dict[str, Any]] = []
    total_segments_requested = 0

    # Step 1: Start all video generations (two Nova segments per ad)
    print("STEP 1: Starting Nova Reel generations...")
    print("-" * 80)

    for ad_id, config in active_prompts.items():
        segments = _expand_segments(config)
        ad_plans[ad_id] = {
            "config": config,
            "segments": [],
            "expected": len(segments),
            "finalized": False,
            "error": None
        }
        for idx, segment in enumerate(segments):
            label = segment.get("label") or f"Segment {idx + 1}"
            duration = int(max(1, min(segment.get("duration", config.get("duration", 10)), MAX_NOVA_DURATION)))
            result = generate_video(ad_id, segment["prompt"], duration, label)
            result.update({
                "segment_index": idx,
                "segment_label": label
            })
            generation_requests.append(result)
            if result["status"] == "processing":
                total_segments_requested += 1
            else:
                err = result.get("error", "Failed to start generation")
                if not ad_plans[ad_id].get("error"):
                    ad_plans[ad_id]["error"] = err
            time.sleep(1)  # Gentle pacing between Bedrock calls

    ads_failed: Dict[str, Dict[str, str]] = {}
    ads_completed: List[Dict[str, Any]] = []

    # Flag ads that never launched all required segments
    for ad_id, plan in ad_plans.items():
        launched = sum(1 for req in generation_requests if req["ad_id"] == ad_id and req["status"] == "processing")
        if launched != plan["expected"]:
            if not plan.get("error"):
                plan["error"] = "Failed to start all Nova segments"
            plan["finalized"] = True
            ads_failed[ad_id] = {"ad_id": ad_id, "error": plan["error"]}

    processing_segments = [
        req for req in generation_requests
        if req["status"] == "processing" and req["ad_id"] not in ads_failed
    ]

    if not processing_segments:
        if ads_failed:
            print("✗ Unable to start any Nova segments. Exiting.")
        else:
            print("✗ No successful generations. Exiting.")
        return

    print()
    print("STEP 2: Monitoring Nova Reel progress...")
    print("-" * 80)
    print("Chained segments refresh roughly every 30 seconds.")
    print()

    max_wait = 1800  # 30 minutes
    start_time = time.time()

    def mark_failed(ad_id: str, message: str) -> None:
        plan = ad_plans[ad_id]
        plan["error"] = message
        plan["finalized"] = True
        ads_failed[ad_id] = {"ad_id": ad_id, "error": message}

    def finalize_if_ready(ad_id: str) -> None:
        plan = ad_plans[ad_id]
        if plan.get("finalized") or plan.get("error"):
            return
        if len(plan["segments"]) != plan["expected"]:
            return
        try:
            record = _finalize_ad_segments(ad_id, plan)
        except Exception as exc:  # noqa: BLE001
            mark_failed(ad_id, str(exc))
            print(f"✗ {ad_id}: Post-processing failed - {exc}")
        else:
            ads_completed.append(record)
            print(f"✓ {ad_id}: COMPLETED with stitched Nova segments, music bed, and voiceover")

    while True:
        remaining = 0
        for gen in processing_segments:
            if gen.get("final_state"):
                continue
            if ad_plans[gen["ad_id"]].get("finalized"):
                gen["final_state"] = "skipped"
                continue

            remaining += 1
            status_data = check_status(gen["generation_id"])

            if status_data.get("status") == "completed":
                video_url = status_data.get("video_url", "")
                s3_key = status_data.get("s3_key") or derive_s3_key_from_url(video_url)
                gen["video_url"] = video_url
                gen["s3_key"] = s3_key
                gen["final_state"] = "completed"

                plan = ad_plans[gen["ad_id"]]
                plan["segments"].append({
                    "segment_index": gen["segment_index"],
                    "segment_label": gen.get("segment_label"),
                    "generation_id": gen["generation_id"],
                    "video_url": video_url,
                    "s3_key": s3_key
                })
                print(f"   • {gen['ad_id']} [{gen.get('segment_label')}] ready")
                finalize_if_ready(gen["ad_id"])
            elif status_data.get("status") == "failed":
                message = status_data.get("message", "Unknown error")
                gen["final_state"] = "failed"
                print(f"✗ {gen['ad_id']} [{gen.get('segment_label')}]: {message}")
                mark_failed(gen["ad_id"], message)
            # else status still processing

        if remaining == 0:
            break

        if time.time() - start_time > max_wait:
            print("⚠ Maximum wait time exceeded. Stopping monitoring.")
            break

        print(f"⏳ {remaining} Nova segments still processing... (waiting 30s)")
        time.sleep(30)

    # Mark any unfinished ads as failed (timeout)
    for gen in processing_segments:
        if gen.get("final_state"):
            continue
        if gen["ad_id"] in ads_failed:
            continue
        mark_failed(gen["ad_id"], "Timed out waiting for Nova Reel segment")

    failed_list = list(ads_failed.values())

    print("\n" + "=" * 80)
    print("📊 GENERATION RESULTS")
    print("=" * 80)
    print(f"\n✓ Completed Ads: {len(ads_completed)}")
    print(f"✗ Failed Ads: {len(failed_list)}")
    print()

    if ads_completed:
        print("COMPLETED ADS:")
        print("-" * 80)
        for record in ads_completed:
            print(f"\n{record['ad_id']}:")
            segment_details = sorted(record.get("segment_details", []), key=lambda seg: seg["segment_index"])
            for seg in segment_details:
                print(f"  • Segment {seg['segment_index'] + 1} ({seg.get('segment_label')}): {seg['generation_id']}")
            print(f"  DAI Video: s3://{DAI_BUCKET}/{record.get('dai_video_key', 'unknown')}")
            if record.get("dai_thumbnail_key"):
                print(f"  DAI Thumbnail: s3://{DAI_BUCKET}/{record['dai_thumbnail_key']}")
            print("  Voiceover: Yes")

    if failed_list:
        print("\nFAILED ADS:")
        print("-" * 80)
        for entry in failed_list:
            print(f"\n{entry['ad_id']}:")
            print(f"  Error: {entry.get('error', 'Unknown')}")

    # Step 4: Save results to disk
    script_dir = os.path.dirname(os.path.abspath(__file__))
    results_file = os.path.join(script_dir, "generated_ads.json")
    results = {
        "completed": ads_completed,
        "failed": failed_list,
        "summary": {
            "total_ads": total_ads,
            "total_segments": total_segments_requested,
            "completed": len(ads_completed),
            "failed": len(failed_list),
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "source_bucket": SOURCE_VIDEO_BUCKET,
            "dai_bucket": DAI_BUCKET
        }
    }

    with open(results_file, "w", encoding="utf-8") as handle:
        json.dump(results, handle, indent=2)

    print(f"\n💾 Results saved to: {results_file}")

    if ads_completed:
        print("\n" + "=" * 80)
        print("📝 NEXT STEPS")
        print("=" * 80)
        print("\n1. Assets have been copied to the Dynamic Ad Insertion bucket:")
        for record in ads_completed:
            print(f"   • {record['ad_id']}: s3://{DAI_BUCKET}/{record.get('dai_video_key', 'unknown')}")
        print("\n2. Restart the Dynamic Ad Insertion service so it presigns the new creatives:")
        print("   ./stop-all.sh && ./start-all.sh")
        print("\n3. Hard-refresh the frontend (Shift+Cmd+R) before testing the new pre-rolls.")

    print("\n" + "=" * 80)
    print("✓ Advertisement generation complete!")
    print("=" * 80)


if __name__ == "__main__":
    main()
