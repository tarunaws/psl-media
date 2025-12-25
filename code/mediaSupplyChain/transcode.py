from __future__ import annotations

import logging
import os
import shutil
import subprocess
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

try:  # Optional dependency for local dev
    import boto3
    from botocore.exceptions import BotoCoreError, ClientError
except Exception:  # pragma: no cover - boto3 not required for local demos
    boto3 = None  # type: ignore
    BotoCoreError = ClientError = Exception  # type: ignore


logger = logging.getLogger(__name__)
PROFILE_METADATA = {
    "uhd_prores": {
        "format": "MP4 · H.264",
        "resolution": "3840x2160",
        "bitrate": "~35 Mbps",
        "container": "MP4",
    },
    "hls_hdr": {
        "format": "HLS · H.264",
        "resolution": "1920x1080",
        "bitrate": "~6 Mbps",
        "container": "M3U8",
    },
    "tiktok_vertical": {
        "format": "MP4 · H.264",
        "resolution": "1080x1920",
        "bitrate": "~8.5 Mbps",
        "container": "MP4",
    },
}


def _env_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "on"}
    return False


class PackagingTranscoder:
    """Coordinates MediaConvert submissions with local ffmpeg fallbacks."""

    def __init__(self, base_dir: Path, config: Optional[Dict[str, Any]] = None):
        self.base_dir = Path(base_dir)
        self.config = config or {}
        self.enabled = _env_bool(self.config.get("enabled", True))
        self.bucket = self.config.get("bucket") or os.getenv("MEDIA_SUPPLY_CHAIN_DELIVERABLE_BUCKET")
        self.prefix = self.config.get("destination_prefix") or os.getenv(
            "MEDIA_SUPPLY_CHAIN_DELIVERABLE_PREFIX", "media-supply-chain/deliverables"
        )
        self.region = (
            self.config.get("region")
            or os.getenv("MEDIA_SUPPLY_CHAIN_AWS_REGION")
            or os.getenv("AWS_REGION")
            or os.getenv("AWS_DEFAULT_REGION")
        )
        self.force_ffmpeg = _env_bool(self.config.get("force_ffmpeg") or os.getenv("MEDIA_SUPPLY_CHAIN_FORCE_FFMPEG"))
        self.ffmpeg_binary = self.config.get("ffmpeg_binary") or os.getenv("FFMPEG_BINARY", "ffmpeg")
        self.mediaconvert_cfg = self.config.get("mediaconvert") or {}
        self._mediaconvert_endpoint = self.mediaconvert_cfg.get("endpoint_url")
        self._mediaconvert_client = None
        self._s3_client = None
        if self.bucket and boto3:
            try:
                if self.region:
                    self._s3_client = boto3.client("s3", region_name=self.region)
                else:
                    self._s3_client = boto3.client("s3")
            except Exception as exc:  # pragma: no cover - boto3 optional
                logger.warning("Unable to create S3 client: %s", exc)
                self._s3_client = None

    # ------------------------------------------------------------------
    def process(
        self,
        *,
        deliverables: List[Dict[str, Any]],
        primary_asset: Optional[Dict[str, Any]],
        run_id: str,
        run_dir: Path,
    ) -> Tuple[List[Dict[str, Any]], Dict[str, int]]:
        if not self.enabled or not deliverables:
            return deliverables, {"mediaconvert_jobs": 0, "ffmpeg_outputs": 0, "skipped": len(deliverables or [])}

        updated: List[Dict[str, Any]] = []
        summary = {"mediaconvert_jobs": 0, "ffmpeg_outputs": 0, "skipped": 0}
        source_s3, source_local = self._source_locations(primary_asset)

        for item in deliverables:
            deliverable = dict(item)
            profile = deliverable.get("profile") or self._infer_profile(deliverable)
            deliverable["profile"] = profile
            if not profile:
                deliverable["status"] = "skipped"
                deliverable["notes"] = "Unable to infer transcode profile."
                summary["skipped"] += 1
                updated.append(deliverable)
                continue

            try:
                if self._should_use_mediaconvert(deliverable, source_s3):
                    job = self._submit_mediaconvert_job(profile, deliverable, source_s3, run_id)
                    deliverable.update(
                        {
                            "status": "rendering",
                            "mode": "mediaconvert",
                            "job_id": job.get("job_id"),
                            "job_arn": job.get("job_arn"),
                            "path": job.get("destination"),
                        }
                    )
                    summary["mediaconvert_jobs"] += 1
                else:
                    output_path = self._run_ffmpeg(profile, deliverable, source_local, run_dir)
                    destination = self._upload_output(output_path, profile, run_id)
                    deliverable.update(
                        {
                            "status": "ready",
                            "mode": "ffmpeg",
                            "path": destination,
                        }
                    )
                    summary["ffmpeg_outputs"] += 1
                metadata = self._profile_metadata(profile)
                if metadata:
                    metadata = dict(metadata)
                    metadata.setdefault("profile", profile)
                    if deliverable.get("mode"):
                        metadata["mode"] = deliverable["mode"]
                    if source_local:
                        metadata["source"] = Path(source_local).name
                    deliverable["preview_metadata"] = metadata
            except Exception as exc:  # pragma: no cover - defensive logging
                logger.exception("Deliverable %s failed", profile)
                deliverable["status"] = "failed"
                deliverable["error"] = str(exc)
                summary["skipped"] += 1

            updated.append(deliverable)

        return updated, summary

    def _profile_metadata(self, profile: str) -> Optional[Dict[str, str]]:
        entry = PROFILE_METADATA.get(profile)
        if not entry:
            return None
        return entry

    # ------------------------------------------------------------------
    def _source_locations(self, asset: Optional[Dict[str, Any]]) -> Tuple[Optional[str], Optional[Path]]:
        if not asset:
            return None, None
        storage = asset.get("storage") or {}
        s3_uri = storage.get("s3_uri") or asset.get("mezzanine_uri")
        local_path = storage.get("local_path") or asset.get("local_path")
        resolved_path: Optional[Path] = None
        if local_path:
            candidate = Path(local_path)
            if candidate.exists():
                resolved_path = candidate
        return s3_uri, resolved_path

    def _infer_profile(self, deliverable: Dict[str, Any]) -> Optional[str]:
        label = (deliverable.get("label") or "").lower()
        kind = (deliverable.get("type") or "").lower()
        if "prores" in label or kind == "mezzanine":
            return "uhd_prores"
        if "hls" in label or kind in {"ott", "ott_packaged", "hls"}:
            return "hls_hdr"
        if "tiktok" in label or "vertical" in label or kind == "social_cut":
            return "tiktok_vertical"
        return None

    def _resolve_mediaconvert_value(self, key: str, deliverable: Dict[str, Any]) -> Optional[str]:
        deliverable_cfg = (deliverable.get("mediaconvert") or {}).get(key)
        if deliverable_cfg:
            return deliverable_cfg
        cfg_value = self.mediaconvert_cfg.get(key)
        if cfg_value:
            return cfg_value
        env_map = {
            "role": "MEDIA_CONVERT_ROLE",
            "queue": "MEDIA_CONVERT_QUEUE",
            "job_template": "MEDIA_CONVERT_JOB_TEMPLATE",
            "endpoint_url": "MEDIA_CONVERT_ENDPOINT",
        }
        env_var = env_map.get(key)
        if env_var:
            return os.getenv(env_var)
        return None

    def _should_use_mediaconvert(self, deliverable: Dict[str, Any], source_s3: Optional[str]) -> bool:
        if self.force_ffmpeg:
            return False
        if not boto3 or not source_s3 or not self.bucket:
            return False
        role = self._resolve_mediaconvert_value("role", deliverable)
        queue = self._resolve_mediaconvert_value("queue", deliverable)
        return bool(role and queue)

    def _get_mediaconvert_client(self):
        if self._mediaconvert_client:
            return self._mediaconvert_client
        if not boto3:
            return None
        try:
            region = self.region or os.getenv("AWS_REGION") or "us-east-1"
            if not self._mediaconvert_endpoint:
                discovery = boto3.client("mediaconvert", region_name=region)
                response = discovery.describe_endpoints(MaxResults=1)
                endpoints = response.get("Endpoints") or []
                if not endpoints:
                    raise RuntimeError("MediaConvert endpoint discovery failed.")
                self._mediaconvert_endpoint = endpoints[0]["Url"]
            self._mediaconvert_client = boto3.client(
                "mediaconvert", region_name=region, endpoint_url=self._mediaconvert_endpoint
            )
            return self._mediaconvert_client
        except Exception as exc:  # pragma: no cover - network heavy
            logger.warning("Unable to initialize MediaConvert client: %s", exc)
            return None

    def _submit_mediaconvert_job(
        self,
        profile: str,
        deliverable: Dict[str, Any],
        source_s3: str,
        run_id: str,
    ) -> Dict[str, Any]:
        client = self._get_mediaconvert_client()
        if not client:
            raise RuntimeError("MediaConvert client unavailable.")

        role = self._resolve_mediaconvert_value("role", deliverable)
        queue = self._resolve_mediaconvert_value("queue", deliverable)
        template = self._resolve_mediaconvert_value("job_template", deliverable)
        destination = self._destination_prefix(profile, run_id)
        base_name = self._input_basename(source_s3)
        settings = self._mediaconvert_settings(profile, source_s3, destination, base_name)

        job_args: Dict[str, Any] = {
            "Role": role,
            "Settings": settings,
            "Queue": queue,
            "UserMetadata": {"run_id": run_id, "profile": profile},
            "Tags": {"media-supply-chain": "packaging"},
        }
        if template:
            job_args["JobTemplate"] = template

        response = client.create_job(**job_args)
        job = response.get("Job", {})
        return {
            "job_id": job.get("Id"),
            "job_arn": job.get("Arn"),
            "destination": self._expected_destination(profile, destination, base_name),
        }

    def _destination_prefix(self, profile: str, run_id: str) -> str:
        prefix = self.prefix.strip("/") if self.prefix else "media-supply-chain/deliverables"
        return f"s3://{self.bucket}/{prefix}/{run_id}/{profile}/"

    def _input_basename(self, source_s3: str) -> str:
        parts = source_s3.split("/", 3)
        if len(parts) < 4:
            return "deliverable"
        key = parts[3]
        return Path(key).stem or "deliverable"

    def _expected_destination(self, profile: str, destination: str, base_name: str) -> str:
        if profile == "uhd_prores":
            return f"{destination}{base_name}_prores_master.mov"
        if profile == "tiktok_vertical":
            return f"{destination}{base_name}_tiktok_vertical.mp4"
        if profile == "hls_hdr":
            return f"{destination}{base_name}_hls.m3u8"
        return destination

    def _mediaconvert_settings(
        self,
        profile: str,
        source_s3: str,
        destination: str,
        base_name: str,
    ) -> Dict[str, Any]:
        common_input = {
            "FileInput": source_s3,
            "TimecodeSource": "ZEROBASED",
            "VideoSelector": {"ColorSpace": "FOLLOW"},
            "AudioSelectors": {
                "Audio Selector 1": {
                    "DefaultSelection": "DEFAULT",
                }
            },
        }

        if profile == "uhd_prores":
            return {
                "TimecodeConfig": {"Source": "ZEROBASED"},
                "Inputs": [common_input],
                "OutputGroups": [
                    {
                        "Name": "File Group",
                        "OutputGroupSettings": {
                            "Type": "FILE_GROUP_SETTINGS",
                            "FileGroupSettings": {"Destination": destination},
                        },
                        "Outputs": [
                            {
                                "ContainerSettings": {"Container": "MOV"},
                                "NameModifier": "_prores_master",
                                "VideoDescription": {
                                    "Width": 3840,
                                    "Height": 2160,
                                    "CodecSettings": {
                                        "Codec": "PRORES",
                                        "ProresSettings": {
                                            "CodecProfile": "APPLE_PRORES_422_HQ",
                                            "InterlaceMode": "PROGRESSIVE",
                                            "FramerateControl": "INITIALIZE_FROM_SOURCE",
                                        },
                                    },
                                },
                                "AudioDescriptions": [
                                    {
                                        "AudioSourceName": "Audio Selector 1",
                                        "CodecSettings": {
                                            "Codec": "PCM",
                                            "PcmSettings": {
                                                "BitDepth": 16,
                                                "SampleRate": 48000,
                                                "Channels": 2,
                                            },
                                        },
                                    }
                                ],
                            }
                        ],
                    }
                ],
            }

        if profile == "tiktok_vertical":
            return {
                "TimecodeConfig": {"Source": "ZEROBASED"},
                "Inputs": [common_input],
                "OutputGroups": [
                    {
                        "Name": "MP4",
                        "OutputGroupSettings": {
                            "Type": "FILE_GROUP_SETTINGS",
                            "FileGroupSettings": {"Destination": destination},
                        },
                        "Outputs": [
                            {
                                "ContainerSettings": {"Container": "MP4"},
                                "NameModifier": "_tiktok_vertical",
                                "VideoDescription": {
                                    "Width": 1080,
                                    "Height": 1920,
                                    "ScalingBehavior": "DEFAULT",
                                    "Sharpness": 50,
                                    "CodecSettings": {
                                        "Codec": "H_264",
                                        "H264Settings": {
                                            "RateControlMode": "QVBR",
                                            "Bitrate": 8500000,
                                            "GopSize": 2,
                                            "GopSizeUnits": "SECONDS",
                                            "SceneChangeDetect": "ENABLED",
                                            "QualityTuningLevel": "SINGLE_PASS_HQ",
                                        },
                                    },
                                },
                                "AudioDescriptions": [
                                    {
                                        "AudioSourceName": "Audio Selector 1",
                                        "CodecSettings": {
                                            "Codec": "AAC",
                                            "AacSettings": {
                                                "Bitrate": 192000,
                                                "CodingMode": "CODING_MODE_2_0",
                                                "SampleRate": 48000,
                                            },
                                        },
                                    }
                                ],
                            }
                        ],
                    }
                ],
            }

        if profile == "hls_hdr":
            return {
                "TimecodeConfig": {"Source": "ZEROBASED"},
                "Inputs": [common_input],
                "OutputGroups": [
                    {
                        "Name": "HLS",
                        "OutputGroupSettings": {
                            "Type": "HLS_GROUP_SETTINGS",
                            "HlsGroupSettings": {
                                "Destination": destination,
                                "SegmentLength": 4,
                                "MinSegmentLength": 1,
                                "DirectoryStructure": "SINGLE_DIRECTORY",
                                "ManifestCompression": "NONE",
                                "CodecSpecification": "RFC_4281",
                                "TimedMetadataId3Frame": "NONE",
                                "CaptionLanguageSetting": "OMIT",
                            },
                        },
                        "Outputs": [
                            {
                                "NameModifier": "_hls",
                                "ContainerSettings": {"Container": "M3U8"},
                                "VideoDescription": {
                                    "Width": 1920,
                                    "Height": 1080,
                                    "CodecSettings": {
                                        "Codec": "H_264",
                                        "H264Settings": {
                                            "RateControlMode": "QVBR",
                                            "Bitrate": 6000000,
                                            "GopSize": 2,
                                            "GopSizeUnits": "SECONDS",
                                            "SceneChangeDetect": "ENABLED",
                                            "QualityTuningLevel": "SINGLE_PASS_HQ",
                                        },
                                    },
                                },
                                "AudioDescriptions": [
                                    {
                                        "AudioSourceName": "Audio Selector 1",
                                        "CodecSettings": {
                                            "Codec": "AAC",
                                            "AacSettings": {
                                                "Bitrate": 160000,
                                                "CodingMode": "CODING_MODE_2_0",
                                                "SampleRate": 48000,
                                            },
                                        },
                                    }
                                ],
                                "HlsSettings": {
                                    "AudioGroupId": "program_audio",
                                    "IFrameOnlyManifest": "DISABLED",
                                },
                            }
                        ],
                    }
                ],
            }

        raise RuntimeError(f"Unknown transcode profile '{profile}'.")

    def _run_ffmpeg(
        self,
        profile: str,
        deliverable: Dict[str, Any],
        source_local: Optional[Path],
        run_dir: Path,
    ) -> Path:
        if not source_local or not source_local.exists():
            raise RuntimeError("Local mezzanine asset missing; cannot run ffmpeg fallback.")
        if not shutil.which(self.ffmpeg_binary):
            raise RuntimeError("ffmpeg binary not found on PATH.")

        output_base = Path(run_dir) / "deliverables" / profile
        output_base.mkdir(parents=True, exist_ok=True)
        args, artifact_path = self._ffmpeg_args(profile, output_base)
        if not args:
            raise RuntimeError(f"No ffmpeg preset available for profile '{profile}'.")

        command = [self.ffmpeg_binary, "-y", "-i", str(source_local)] + args
        result = subprocess.run(command, capture_output=True, text=True)
        if result.returncode != 0:
            raise RuntimeError(f"ffmpeg failed: {result.stderr.strip()}")
        return artifact_path

    def _ffmpeg_args(self, profile: str, output_base: Path) -> Tuple[List[str], Path]:
        if profile == "uhd_prores":
            output_file = output_base / "uhd_master.mp4"
            return (
                [
                    "-vf",
                    "scale=3840:2160:force_original_aspect_ratio=decrease,pad=3840:2160:(ow-iw)/2:(oh-ih)/2:black",
                    "-c:v",
                    "libx264",
                    "-preset",
                    "slow",
                    "-crf",
                    "17",
                    "-pix_fmt",
                    "yuv420p",
                    "-c:a",
                    "aac",
                    "-b:a",
                    "320k",
                    "-movflags",
                    "+faststart",
                    str(output_file),
                ],
                output_file,
            )

        if profile == "tiktok_vertical":
            output_file = output_base / "tiktok_vertical.mp4"
            return (
                [
                    "-vf",
                    "scale=1080:1920:force_original_aspect_ratio=decrease,pad=1080:1920:(ow-iw)/2:(oh-ih)/2:black",
                    "-c:v",
                    "libx264",
                    "-preset",
                    "fast",
                    "-crf",
                    "21",
                    "-c:a",
                    "aac",
                    "-b:a",
                    "160k",
                    "-pix_fmt",
                    "yuv420p",
                    str(output_file),
                ],
                output_file,
            )

        if profile == "hls_hdr":
            playlist = output_base / "master.m3u8"
            segment_template = output_base / "segment_%03d.ts"
            return (
                [
                    "-vf",
                    "scale=1920:1080:force_original_aspect_ratio=decrease,pad=1920:1080:(ow-iw)/2:(oh-ih)/2:black",
                    "-c:v",
                    "libx264",
                    "-preset",
                    "medium",
                    "-crf",
                    "19",
                    "-c:a",
                    "aac",
                    "-b:a",
                    "192k",
                    "-f",
                    "hls",
                    "-hls_time",
                    "4",
                    "-hls_playlist_type",
                    "vod",
                    "-hls_segment_filename",
                    str(segment_template),
                    str(playlist),
                ],
                playlist,
            )

        return [], output_base

    def _upload_output(self, path: Path, profile: str, run_id: str) -> str:
        if not self._s3_client or not self.bucket:
            return path.as_posix()

        prefix = self.prefix.strip("/") if self.prefix else "media-supply-chain/deliverables"
        base_prefix = f"{prefix}/{run_id}/{profile}"
        if path.is_dir() or (profile == "hls_hdr" and path.exists()):
            root = path if path.is_dir() else path.parent
            for file_path in root.rglob("*"):
                if file_path.is_file():
                    rel = file_path.relative_to(root).as_posix()
                    key = f"{base_prefix}/{rel}"
                    self._s3_client.upload_file(str(file_path), self.bucket, key)
            playlist = root / "master.m3u8"
            if playlist.exists():
                rel_playlist = playlist.relative_to(root).as_posix()
                return f"s3://{self.bucket}/{base_prefix}/{rel_playlist}"
            if path.is_dir():
                return f"s3://{self.bucket}/{base_prefix}/"

        key = f"{base_prefix}/{path.name}"
        self._s3_client.upload_file(str(path), self.bucket, key)
        return f"s3://{self.bucket}/{key}"
