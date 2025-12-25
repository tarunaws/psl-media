from __future__ import annotations

import os
import re
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional


@dataclass
class UploadedAsset:
    asset_id: str
    filename: str
    size_bytes: int
    local_path: Path
    bucket: Optional[str] = None
    key: Optional[str] = None
    s3_uri: Optional[str] = None
    web_path: Optional[str] = None
    pending_s3: Optional[Dict[str, Any]] = None

    def to_manifest_asset(self, title: Optional[str] = None, description: Optional[str] = None) -> Dict[str, Any]:
        """Build ingest-manifest friendly payload for the workflow engine."""
        storage_ref = self.s3_uri or self.local_path.as_posix()
        payload = {
            "asset_id": self.asset_id,
            "title": title or self.filename,
            "description": description,
            "mezzanine_uri": storage_ref,
            "storage": {
                "bucket": self.bucket,
                "key": self.key,
                "local_path": self.local_path.as_posix(),
                "s3_uri": self.s3_uri,
            },
            "status": "uploaded",
            "size_bytes": self.size_bytes,
            "labels": [],
            "download_url": self.public_url(),
        }
        if self.pending_s3:
            payload["storage"].setdefault("pending_s3", self.pending_s3)
        return payload

    def public_url(self) -> Optional[str]:
        if not self.web_path:
            return None
        return f"/media-supply-chain/uploads/{self.web_path}"


class AssetStorageError(RuntimeError):
    pass


class AssetStorage:
    def __init__(self, base_dir: Path):
        self.base_dir = Path(base_dir)
        self.upload_dir = self.base_dir / "uploads"
        self.upload_dir.mkdir(parents=True, exist_ok=True)

        self.bucket = os.getenv("MEDIA_SUPPLY_CHAIN_UPLOAD_BUCKET")
        self.prefix = os.getenv("MEDIA_SUPPLY_CHAIN_UPLOAD_PREFIX", "media-supply-chain/uploads")
        self.region = os.getenv("AWS_REGION") or os.getenv("AWS_DEFAULT_REGION")

    # ------------------------------------------------------------------
    def save(self, file_storage, *, title: Optional[str] = None, description: Optional[str] = None) -> Dict[str, Any]:
        """Persist the uploaded file locally and optionally to S3."""
        if not file_storage:
            raise AssetStorageError("Missing file upload payload.")

        original_name = getattr(file_storage, "filename", None) or "upload.bin"
        safe_name = self._sanitize_filename(original_name)
        asset_id = uuid.uuid4().hex
        local_name = f"{asset_id}_{safe_name}"
        local_path = self.upload_dir / local_name

        try:
            file_storage.save(local_path)
        except Exception as exc:  # pragma: no cover - Werkzeug handles most errors
            raise AssetStorageError(f"Unable to save upload: {exc}") from exc

        size_bytes = local_path.stat().st_size
        bucket = key = s3_uri = None
        pending_s3: Optional[Dict[str, Any]] = None
        if self.bucket:
            key = self._build_s3_key(asset_id, safe_name)
            pending_s3 = {
                "bucket": self.bucket,
                "key": key,
            }
            if self.region:
                pending_s3["region"] = self.region
            pending_s3["local_path"] = local_path.as_posix()

        asset = UploadedAsset(
            asset_id=asset_id,
            filename=safe_name,
            size_bytes=size_bytes,
            local_path=local_path,
            bucket=bucket,
            key=key,
            s3_uri=s3_uri,
            web_path=local_name,
            pending_s3=pending_s3,
        )

        manifest_assets = [asset.to_manifest_asset(title=title, description=description)]
        manifest = {
            "source_system": "user-upload",
            "transfer_session": asset.asset_id,
            "assets": manifest_assets,
        }

        return {
            "asset": asset,
            "manifest": manifest,
        }

    # ------------------------------------------------------------------
    def _sanitize_filename(self, filename: str) -> str:
        name = filename.rsplit("/", 1)[-1].rsplit("\\", 1)[-1]
        name = re.sub(r"[^A-Za-z0-9_.-]", "_", name)
        return name or "upload.bin"

    def _build_s3_key(self, asset_id: str, filename: str) -> str:
        prefix = self.prefix.strip("/")
        if prefix:
            return f"{prefix}/{asset_id}/{filename}"
        return f"{asset_id}/{filename}"

    def resolve_upload_path(self, relative_name: str) -> Path:
        if not relative_name:
            raise AssetStorageError("Missing filename.")
        if os.path.isabs(relative_name) or ".." in Path(relative_name).parts:
            raise AssetStorageError("Invalid filename.")
        candidate = self.upload_dir / relative_name
        if not candidate.exists() or not candidate.is_file():
            raise AssetStorageError("File not found.")
        return candidate
