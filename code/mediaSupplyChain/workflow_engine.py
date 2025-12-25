from __future__ import annotations

import json
import logging
import os
import threading
import uuid
from copy import deepcopy
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional
from urllib.parse import quote

from transcode import PackagingTranscoder

try:  # Optional dependency during bootstrap
    import requests
except Exception:  # pragma: no cover - fallback when requests is missing
    requests = None  # type: ignore

try:  # Optional dependency for delayed S3 uploads
    import boto3
    from botocore.exceptions import BotoCoreError, ClientError
except Exception:  # pragma: no cover - boto3 not required for local demos
    boto3 = None  # type: ignore
    BotoCoreError = ClientError = Exception  # type: ignore


logger = logging.getLogger(__name__)
JSONDict = Dict[str, Any]
MAX_PERSISTED_RUNS = 30
VIDEO_EXTENSIONS = {".mp4", ".mov", ".m4v", ".mxf", ".m3u8", ".ts"}
ARTIFACT_ROUTE = "/media-supply-chain/artifacts"
DELIVERABLE_PREVIEW_FALLBACKS = {}


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


@dataclass
class StageResult:
    notes: Optional[str] = None
    artifacts: Optional[JSONDict] = None
    metrics: Optional[JSONDict] = None
    context: Optional[JSONDict] = None


class WorkflowEngineError(RuntimeError):
    """Raised when orchestration cannot continue."""


class WorkflowEngine:
    def __init__(self, base_dir: Path):
        self.base_dir = Path(base_dir)
        self.project_root = self.base_dir.parent
        self.samples_dir = self.base_dir / "samples"
        self.outputs_dir = self.base_dir / "outputs"
        self.blueprints_dir = self.base_dir / "blueprints"
        self.config_dir = self.project_root / "config" / "media-supply-chain"
        self.config_dir.mkdir(parents=True, exist_ok=True)
        self.outputs_dir.mkdir(parents=True, exist_ok=True)
        self.state_path = self.config_dir / "runs.json"

        self._blueprints: Dict[str, JSONDict] = {}
        self._stage_maps: Dict[str, Dict[str, JSONDict]] = {}
        self._load_blueprints()
        if not self._blueprints:
            raise WorkflowEngineError("No media supply chain blueprints found.")
        self.default_blueprint = next(iter(self._blueprints))

        self._runs: Dict[str, JSONDict] = {}
        self._lock = threading.Lock()
        self._executor = ThreadPoolExecutor(max_workers=4)
        self._load_state()
        self._s3_clients: Dict[str, Any] = {}
        self.preview_signing_enabled = os.getenv("MEDIA_SUPPLY_CHAIN_SIGN_PREVIEWS", "true").lower() in {"1", "true", "yes"}
        preview_ttl_env = os.getenv("MEDIA_SUPPLY_CHAIN_PREVIEW_TTL", "900")
        try:
            self.preview_signing_ttl = max(60, min(86400, int(preview_ttl_env)))
        except ValueError:
            self.preview_signing_ttl = 900

        self.stage_handlers = {
            "ingest": self._stage_ingest,
            "quality_control": self._stage_quality_control,
            "metadata_enrichment": self._stage_metadata_enrichment,
            "packaging": self._stage_packaging,
        }

    # ------------------------------------------------------------------
    # Blueprint helpers
    # ------------------------------------------------------------------
    def _load_blueprints(self) -> None:
        for blueprint_path in sorted(self.blueprints_dir.glob("*.json")):
            with open(blueprint_path, "r", encoding="utf-8") as handle:
                data: JSONDict = json.load(handle)
            blueprint_id = data.get("id")
            if not blueprint_id:
                logger.warning("Skipping blueprint without id: %s", blueprint_path)
                continue
            stages = data.get("stages", [])
            stage_map = {stage["id"]: stage for stage in stages if stage.get("id")}
            if not stage_map:
                logger.warning("Blueprint %s has no stages", blueprint_id)
                continue
            self._blueprints[blueprint_id] = data
            self._stage_maps[blueprint_id] = stage_map

    def list_blueprints(self) -> List[JSONDict]:
        blueprints: List[JSONDict] = []
        for blueprint in self._blueprints.values():
            entry = {
                "id": blueprint["id"],
                "name": blueprint.get("name"),
                "description": blueprint.get("description"),
                "stage_count": len(blueprint.get("stages", [])),
                "priority": blueprint.get("priority"),
                "status": blueprint.get("status", "draft"),
                "tags": blueprint.get("tags", []),
            }
            blueprints.append(entry)
        return blueprints

    def blueprint_overview(self) -> JSONDict:
        return {
            "count": len(self._blueprints),
            "default": self.default_blueprint,
            "items": self.list_blueprints(),
        }

    def _get_blueprint(self, blueprint_id: Optional[str]) -> JSONDict:
        target = blueprint_id or self.default_blueprint
        blueprint = self._blueprints.get(target)
        if not blueprint:
            raise WorkflowEngineError(f"Unknown blueprint '{target}'.")
        return blueprint

    # ------------------------------------------------------------------
    # Run persistence helpers
    # ------------------------------------------------------------------
    def _load_state(self) -> None:
        if not self.state_path.exists():
            return
        try:
            with open(self.state_path, "r", encoding="utf-8") as handle:
                payload = json.load(handle)
        except json.JSONDecodeError as exc:
            logger.warning("Unable to read existing run state: %s", exc)
            return
        runs = payload.get("runs", [])
        for run in runs:
            run_id = run.get("id")
            if not run_id:
                continue
            self._runs[run_id] = run

    def _persist_state(self) -> None:
        with self._lock:
            runs = list(self._runs.values())
        runs.sort(key=lambda run: run.get("started_at", ""), reverse=True)
        trimmed = runs[:MAX_PERSISTED_RUNS]
        payload = {"runs": trimmed}
        tmp_path = self.state_path.with_suffix(".tmp")
        with open(tmp_path, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, ensure_ascii=False, indent=2)
        tmp_path.replace(self.state_path)

    # ------------------------------------------------------------------
    # Public run APIs
    # ------------------------------------------------------------------
    def list_runs(self, limit: int = 25) -> List[JSONDict]:
        with self._lock:
            runs = list(self._runs.values())
        runs.sort(key=lambda run: run.get("started_at", ""), reverse=True)
        hydrated: List[JSONDict] = []
        for run in runs[:limit]:
            hydrated.append(self._prepare_run_response(run))
        return hydrated

    def active_run_count(self) -> int:
        with self._lock:
            return sum(1 for run in self._runs.values() if run.get("status") == "running")

    def get_run(self, run_id: str) -> JSONDict:
        with self._lock:
            run = self._runs.get(run_id)
            if not run:
                raise WorkflowEngineError(f"Run '{run_id}' not found.")
            return self._prepare_run_response(run)

    def start_run(self, blueprint_id: Optional[str], inputs: Optional[JSONDict] = None, labels: Optional[JSONDict] = None) -> JSONDict:
        blueprint = self._get_blueprint(blueprint_id)
        run_id = str(uuid.uuid4())
        run_dir = self.outputs_dir / run_id
        run_dir.mkdir(parents=True, exist_ok=True)

        stages = []
        for stage in blueprint.get("stages", []):
            stages.append({
                "id": stage["id"],
                "name": stage.get("name"),
                "type": stage.get("type"),
                "status": "pending",
                "started_at": None,
                "finished_at": None,
                "metrics": {},
                "artifacts": {},
                "notes": None,
            })

        run_payload: JSONDict = {
            "id": run_id,
            "blueprint": blueprint["id"],
            "name": blueprint.get("name"),
            "status": "pending",
            "started_at": _utc_now(),
            "finished_at": None,
            "progress": 0.0,
            "stage_count": len(stages),
            "stages": stages,
            "inputs": inputs or {},
            "labels": labels or {},
            "output_dir": self._relative_path(run_dir),
        }

        with self._lock:
            self._runs[run_id] = run_payload
        self._persist_state()

        self._executor.submit(self._execute_run, run_id)
        return self._prepare_run_response(run_payload)

    # ------------------------------------------------------------------
    # Stage execution
    # ------------------------------------------------------------------
    def _execute_run(self, run_id: str) -> None:
        with self._lock:
            run = self._runs[run_id]
            run["status"] = "running"
            blueprint_id = run["blueprint"]
            output_dir = run["output_dir"]
        blueprint = self._get_blueprint(blueprint_id)
        stage_map = self._stage_maps[blueprint["id"]]
        context: JSONDict = {
            "run_id": run_id,
            "run_dir": Path(self.project_root / output_dir),
            "inputs": run.get("inputs") or {},
        }
        self._persist_state()

        for index, stage_state in enumerate(run["stages"]):
            stage_id = stage_state["id"]
            definition = stage_map.get(stage_id)
            if not definition:
                raise WorkflowEngineError(f"Blueprint {blueprint['id']} missing stage '{stage_id}'.")

            handler = self.stage_handlers.get(definition.get("type"))
            if not handler:
                raise WorkflowEngineError(f"No handler for stage type '{definition.get('type')}'.")

            stage_state["status"] = "running"
            stage_state["started_at"] = _utc_now()
            self._persist_state()

            context["_update_stage"] = lambda **kwargs: self._update_stage_runtime(stage_state, **kwargs)

            try:
                result = handler(definition, context)
            except Exception as exc:  # pragma: no cover - defensive logging
                logger.exception("Stage %s failed", stage_id)
                stage_state["status"] = "failed"
                stage_state["finished_at"] = _utc_now()
                stage_state["error"] = str(exc)
                run["status"] = "failed"
                run["finished_at"] = _utc_now()
                run.setdefault("errors", []).append({"stage": stage_id, "message": str(exc)})
                self._persist_state()
                return

            stage_state["status"] = "completed"
            stage_state["finished_at"] = _utc_now()
            if result.artifacts:
                stage_state["artifacts"] = result.artifacts
            if result.metrics:
                stage_state["metrics"] = result.metrics
            if result.notes:
                stage_state["notes"] = result.notes
            if result.context:
                context.update(result.context)

            run["progress"] = round((index + 1) / len(run["stages"]), 2)
            self._persist_state()

            context.pop("_update_stage", None)

        run["status"] = "completed"
        run["finished_at"] = _utc_now()
        run["outputs"] = {
            "package_manifest": context.get("package_manifest"),
            "insights": context.get("insights"),
        }
        self._persist_state()

    # ------------------------------------------------------------------
    # Stage handlers
    # ------------------------------------------------------------------
    def _stage_ingest(self, definition: JSONDict, context: JSONDict) -> StageResult:
        config = definition.get("config", {})
        inputs = context.get("inputs") or {}
        manifest_override = inputs.get("ingest_manifest")
        if manifest_override:
            manifest = deepcopy(manifest_override)
        else:
            manifest_file = config.get("manifest", "ingest_manifest.json")
            manifest = self._load_sample_json(manifest_file)
        media_metadata = inputs.get("media_convert_metadata")
        if media_metadata:
            self._merge_media_convert_metadata(manifest, media_metadata)
        manifest["ingested_at"] = _utc_now()
        manifest["run_id"] = context["run_id"]

        update_stage = context.get("_update_stage")
        upload_summary = self._upload_pending_assets(manifest.get("assets", []), update_stage)

        run_dir = Path(context["run_dir"])
        output_path = run_dir / "01_ingest_manifest.json"
        self._write_json(output_path, manifest)

        asset_count = len(manifest.get("assets", []))
        s3_uploads = (upload_summary or {}).get("uploaded", 0)
        s3_note = f" | Uploaded {s3_uploads} asset(s) to S3" if s3_uploads else ""
        context["manifest"] = manifest
        return StageResult(
            notes=f"Captured {asset_count} mezzanine asset(s) from {manifest.get('source_system')}{s3_note}",
            artifacts={
                "manifest_path": self._relative_path(output_path),
                "asset_count": asset_count,
                "transfer_session": manifest.get("transfer_session"),
                "s3_uploads": upload_summary,
            },
            metrics={
                "asset_count": asset_count,
                "estimated_runtime_minutes": config.get("eta_minutes", 12),
                "s3_uploads": s3_uploads,
                "s3_bytes_transferred": (upload_summary or {}).get("bytes", 0),
            },
            context={
                "assets": manifest.get("assets", []),
                "primary_asset": (manifest.get("assets") or [{}])[0],
                "media_convert_metadata": media_metadata,
            },
        )

    def _stage_quality_control(self, definition: JSONDict, context: JSONDict) -> StageResult:
        config = definition.get("config", {})
        report_file = config.get("report", "qc_report.json")
        report = self._load_sample_json(report_file)
        update_stage = context.get("_update_stage")

        def emit_qc_status(state: str, percent: int, message: str, extra: Optional[JSONDict] = None) -> None:
            if not update_stage:
                return
            payload: JSONDict = {
                "qc_status": {
                    "state": state,
                    "percent": max(0, min(100, int(percent))),
                    "message": message,
                }
            }
            if extra:
                payload["qc_status"].update(deepcopy(extra))
            update_stage(artifacts=payload, notes=message)

        emit_qc_status("initializing", 5, "Booting QC policy templates")

        assets = context.get("assets", [])
        if assets:
            report["asset"] = {
                "asset_id": assets[0].get("asset_id"),
                "title": assets[0].get("title"),
                "duration_seconds": assets[0].get("duration_seconds"),
            }
            asset_label = report["asset"].get("title") or report["asset"].get("asset_id") or "primary asset"
            emit_qc_status(
                "analyzing",
                15,
                f"Locking {asset_label} for QC review",
                {
                    "asset": report["asset"],
                },
            )
        else:
            emit_qc_status("analyzing", 10, "Gathering manifest for QC")

        findings = report.get("findings", {})
        warning_templates: List[JSONDict] = findings.get("warnings") or []
        blocking_templates: List[JSONDict] = findings.get("blocking") or []
        emit_qc_status(
            "analyzing",
            25,
            "Running QC heuristics and policy sweeps",
            {
                "warnings_total": len(warning_templates),
                "blocking_total": len(blocking_templates),
            },
        )
        resolved_warnings: List[JSONDict] = []
        total_warning_count = len(warning_templates) or 1
        for index, warning in enumerate(warning_templates):
            resolved_warnings.append(warning)
            progress = 30 + int(((index + 1) / total_warning_count) * 25)
            headline = warning.get("description") or warning.get("type") or "QC warning"
            emit_qc_status(
                "findings",
                progress,
                f"Flagged warning: {headline}",
                {
                    "warnings": deepcopy(resolved_warnings),
                    "latest_warning": warning,
                    "warnings_found": len(resolved_warnings),
                },
            )

        service_checks = []
        check_configs = config.get("service_checks", [])
        total_checks = len(check_configs) or 1
        if check_configs:
            emit_qc_status("checks", 60, "Running downstream service checks")
        for index, target in enumerate(check_configs):
            name = target.get("name") or target.get("url") or "service"
            emit_qc_status(
                "checks",
                60 + int((index / total_checks) * 15),
                f"Pinging {name}",
                {
                    "service_checks": deepcopy(service_checks),
                    "active_check": name,
                },
            )
            result = self._ping_service(target)
            service_checks.append(result)
            emit_qc_status(
                "checks",
                70 + int(((index + 1) / total_checks) * 15),
                f"{name} responded {result.get('status', 'unknown')}",
                {
                    "service_checks": deepcopy(service_checks),
                    "latest_check": result,
                },
            )
        report["service_checks"] = service_checks

        run_dir = Path(context["run_dir"])
        output_path = run_dir / "02_qc_report.json"
        self._write_json(output_path, report)

        warnings = len(warning_templates)
        blocking = len(blocking_templates)
        synopsis = report.get("metadata", {}).get("synopsis")
        emit_qc_status(
            "completed",
            100,
            "QC report ready",
            {
                "warnings": deepcopy(warning_templates),
                "warnings_total": len(warning_templates),
                "warnings_found": len(warning_templates),
                "blocking": deepcopy(blocking_templates),
                "blocking_total": len(blocking_templates),
                "service_checks": deepcopy(service_checks),
            },
        )
        context["qc_report"] = report
        context["summary_prompt"] = synopsis

        return StageResult(
            notes=report.get("summary", {}).get("headline"),
            artifacts={
                "qc_report": self._relative_path(output_path),
                "service_checks": service_checks,
                "qc_status": {
                    "state": "completed",
                    "percent": 100,
                    "message": report.get("summary", {}).get("headline"),
                    "warnings": warning_templates,
                    "warnings_total": len(warning_templates),
                    "warnings_found": len(warning_templates),
                    "blocking": blocking_templates,
                    "blocking_total": len(blocking_templates),
                    "service_checks": service_checks,
                },
            },
            metrics={
                "automation_coverage": report.get("summary", {}).get("automation_coverage", 0),
                "warnings": warnings,
                "blocking_issues": blocking,
            },
            context={"synopsis": synopsis},
        )

    def _stage_metadata_enrichment(self, definition: JSONDict, context: JSONDict) -> StageResult:
        config = definition.get("config", {})
        plan_file = config.get("plan", "enrichment_plan.json")
        plan = self._load_sample_json(plan_file)
        synopsis = context.get("synopsis") or plan.get("narrative")
        voiceover_result: Optional[JSONDict] = None

        voiceover_cfg = config.get("voiceover_service")
        if voiceover_cfg and synopsis:
            voiceover_result = self._invoke_voiceover(synopsis, voiceover_cfg)
            if voiceover_result and voiceover_result.get("ssml"):
                plan.setdefault("voiceover", {})["ssml"] = voiceover_result["ssml"]
                plan["voiceover"]["engine"] = voiceover_cfg.get("label", "synthetic-voiceover")

        run_dir = Path(context["run_dir"])
        output_path = run_dir / "03_enrichment_plan.json"
        self._write_json(output_path, plan)

        localization_tracks = plan.get("localization_tracks", [])
        recipes = plan.get("personalization_recipes", [])
        context["enrichment_plan"] = plan

        return StageResult(
            notes=f"Prepared {len(localization_tracks)} localization tracks and {len(recipes)} personalization recipes",
            artifacts={
                "plan": self._relative_path(output_path),
                "voiceover": voiceover_result or {"status": "skipped"},
            },
            metrics={
                "localization_tracks": len(localization_tracks),
                "personalization_recipes": len(recipes),
            },
            context={"voiceover": voiceover_result},
        )

    def _stage_packaging(self, definition: JSONDict, context: JSONDict) -> StageResult:
        config = definition.get("config", {})
        manifest_file = config.get("package_manifest", "package_manifest.json")
        package_manifest = self._load_sample_json(manifest_file)
        package_manifest["run_id"] = context["run_id"]
        package_manifest["source_asset"] = context.get("primary_asset")
        package_manifest["localization_tracks"] = context.get("enrichment_plan", {}).get("localization_tracks")

        qc_report = context.get("qc_report", {})
        package_manifest.setdefault("compliance_notes", []).extend(qc_report.get("findings", {}).get("warnings", []))

        transcode_summary = None
        deliverables = package_manifest.get("deliverables", [])
        if deliverables:
            transcoder = PackagingTranscoder(self.base_dir, config.get("transcode"))
            transcoded, transcode_summary = transcoder.process(
                deliverables=deepcopy(deliverables),
                primary_asset=context.get("primary_asset"),
                run_id=context["run_id"],
                run_dir=Path(context["run_dir"]),
            )
            normalized: List[JSONDict] = []
            for entry in transcoded:
                updated = deepcopy(entry)
                updated.pop("preview_url", None)
                updated.pop("fallback_preview_url", None)
                path_value = updated.get("path")
                if isinstance(path_value, str) and path_value.startswith(str(self.project_root)):
                    updated["path"] = self._relative_path(Path(path_value))
                normalized.append(updated)
            package_manifest["deliverables"] = normalized
            deliverables = normalized

        used_transcode_outputs = bool(
            transcode_summary and (transcode_summary.get("ffmpeg_outputs") or transcode_summary.get("mediaconvert_jobs"))
        )
        if not used_transcode_outputs:
            self._fallback_to_primary_asset_preview(deliverables, context.get("primary_asset"))

        if isinstance(deliverables, list) and deliverables:
            self._populate_deliverable_previews(deliverables)

        insights = {
            "time_to_air_minutes": package_manifest.get("time_to_air_minutes"),
            "automation_coverage": qc_report.get("summary", {}).get("automation_coverage"),
            "asset_title": (context.get("primary_asset") or {}).get("title"),
        }

        run_dir = Path(context["run_dir"])
        output_path = run_dir / "04_package_manifest.json"
        self._write_json(output_path, package_manifest)

        context["package_manifest"] = package_manifest
        context["insights"] = insights
        context["deliverables"] = deliverables
        if transcode_summary:
            context["transcode_summary"] = transcode_summary

        deliverables = package_manifest.get("deliverables", [])
        ready = sum(1 for item in deliverables if item.get("status") == "ready")
        metrics = {
            "deliverables_ready": ready,
            "deliverables_total": len(deliverables),
        }
        if transcode_summary:
            metrics["mediaconvert_jobs"] = transcode_summary.get("mediaconvert_jobs", 0)
            metrics["ffmpeg_outputs"] = transcode_summary.get("ffmpeg_outputs", 0)

        return StageResult(
            notes=f"{ready}/{len(deliverables)} deliverables packaged",
            artifacts={
                "package_manifest": self._relative_path(output_path),
                "deliverables": deliverables,
                "transcode_summary": transcode_summary,
            },
            metrics=metrics,
            context={"insights": insights},
        )

    # ------------------------------------------------------------------
    # Media metadata helpers
    # ------------------------------------------------------------------
    def _merge_media_convert_metadata(self, manifest: JSONDict, metadata: Any) -> None:
        assets = manifest.get("assets")
        if not isinstance(assets, list) or not assets:
            return
        metadata_map = self._index_media_metadata(metadata)
        if not metadata_map:
            return
        for asset in assets:
            asset_id = asset.get("asset_id")
            if not asset_id:
                continue
            info = metadata_map.get(asset_id)
            if not info:
                continue
            technical = asset.setdefault("technical_metadata", {})
            for key in ("codec", "video_codec", "audio_codec", "duration_seconds", "frame_rate", "width", "height", "bitrate"):
                if info.get(key) is not None:
                    technical[key] = info[key]
            if info.get("duration_seconds") and not asset.get("duration_seconds"):
                asset["duration_seconds"] = info["duration_seconds"]
            if info.get("renditions"):
                technical["renditions"] = info["renditions"]

    def _index_media_metadata(self, metadata: Any) -> Dict[str, JSONDict]:
        if not metadata:
            return {}
        candidates: List[JSONDict] = []
        if isinstance(metadata, list):
            candidates = [item for item in metadata if isinstance(item, dict)]
        elif isinstance(metadata, dict):
            if metadata.get("asset_id"):
                candidates = [metadata]
            else:
                for key in ("outputs", "assets", "items", "renditions"):
                    value = metadata.get(key)
                    if isinstance(value, list):
                        candidates = [item for item in value if isinstance(item, dict)]
                        if candidates:
                            break
        index: Dict[str, JSONDict] = {}
        for item in candidates:
            asset_id = item.get("asset_id")
            if not asset_id:
                continue
            index[asset_id] = item
        return index

    # ------------------------------------------------------------------
    # Utilities
    # ------------------------------------------------------------------
    def _relative_path(self, target: Path) -> str:
        try:
            return str(target.relative_to(self.project_root))
        except ValueError:
            return str(target)

    def _populate_deliverable_previews(self, deliverables: List[JSONDict]) -> None:
        for entry in deliverables:
            preview = self._derive_deliverable_preview(entry)
            if preview:
                entry["preview_url"] = preview
            else:
                entry.pop("preview_url", None)
            fallback = DELIVERABLE_PREVIEW_FALLBACKS.get(entry.get("type"))
            if fallback and not entry.get("fallback_preview_url"):
                entry["fallback_preview_url"] = fallback

    def _refresh_deliverable_previews(self, run: JSONDict) -> None:
        deliverable_groups: List[List[JSONDict]] = []
        outputs = run.get("outputs") or {}
        package_manifest = outputs.get("package_manifest") or {}
        manifest_deliverables = package_manifest.get("deliverables")
        if isinstance(manifest_deliverables, list):
            deliverable_groups.append(manifest_deliverables)

        for stage in run.get("stages") or []:
            artifacts = stage.get("artifacts") or {}
            stage_deliverables = artifacts.get("deliverables")
            if isinstance(stage_deliverables, list):
                deliverable_groups.append(stage_deliverables)

        for group in deliverable_groups:
            self._populate_deliverable_previews(group)

    def _derive_deliverable_preview(self, deliverable: JSONDict) -> Optional[str]:
        preview = deliverable.get("preview_url")
        if isinstance(preview, str) and preview.strip():
            return preview.strip()
        path_value = deliverable.get("path")
        preview_from_path = self._preview_from_path(path_value, deliverable.get("type"))
        if preview_from_path:
            return preview_from_path
        deliverable_type = deliverable.get("type")
        return DELIVERABLE_PREVIEW_FALLBACKS.get(deliverable_type)

    def _preview_from_path(self, value: Any, deliverable_type: Optional[str] = None) -> Optional[str]:
        if not isinstance(value, str):
            return None
        candidate = value.strip()
        if not candidate:
            return None
        if deliverable_type == "ott_packaged" and candidate.endswith("/"):
            candidate = candidate.rstrip("/") + "/master.m3u8"
        path_only = candidate.split("?", 1)[0]
        suffix = Path(path_only).suffix.lower()
        if suffix not in VIDEO_EXTENSIONS:
            return None
        if candidate.startswith(("http://", "https://")):
            return candidate
        parsed = self._parse_s3_uri(candidate)
        if parsed:
            bucket, key = parsed
            return self._build_s3_preview_url(bucket, key)
        filesystem_url = self._filesystem_preview_url(candidate)
        if filesystem_url:
            return filesystem_url
        return None

    def _filesystem_preview_url(self, candidate: str) -> Optional[str]:
        try:
            path = Path(candidate)
        except Exception:
            return None
        if not path.is_absolute():
            path = (self.project_root / path).resolve()
        else:
            path = path.resolve()
        try:
            relative = path.relative_to(self.project_root)
        except ValueError:
            return None
        if not path.exists():
            return None
        return f"{ARTIFACT_ROUTE}/{relative.as_posix()}"

    def _fallback_to_primary_asset_preview(self, deliverables: Optional[List[JSONDict]], primary_asset: Optional[JSONDict]) -> None:
        if not deliverables or not primary_asset:
            return
        storage = primary_asset.get("storage") or {}
        download_url = primary_asset.get("download_url")
        mezzanine_uri = primary_asset.get("mezzanine_uri")
        local_path = storage.get("local_path") or storage.get("web_path")
        candidate = download_url or local_path or mezzanine_uri
        if not candidate:
            return
        for entry in deliverables:
            if entry.get("path"):
                continue
            entry["path"] = candidate
            entry["mode"] = "upload"
            entry.pop("preview_url", None)
            entry.pop("fallback_preview_url", None)
            entry.setdefault("notes", "Preview linked to uploaded mezzanine")

    def _parse_s3_uri(self, value: str) -> Optional[tuple[str, str]]:
        if not value.lower().startswith("s3://"):
            return None
        remainder = value[5:]
        parts = remainder.split("/", 1)
        if len(parts) != 2:
            return None
        bucket, key = parts
        if not bucket or not key:
            return None
        return bucket, key

    def _build_s3_preview_url(self, bucket: str, key: str) -> Optional[str]:
        if not bucket or not key:
            return None
        if self.preview_signing_enabled and boto3:
            client = self._get_s3_client(os.getenv("MEDIA_SUPPLY_CHAIN_AWS_REGION") or os.getenv("AWS_REGION") or os.getenv("AWS_DEFAULT_REGION"))
            if client:
                try:
                    return client.generate_presigned_url(
                        "get_object",
                        Params={"Bucket": bucket, "Key": key},
                        ExpiresIn=self.preview_signing_ttl,
                    )
                except Exception as exc:  # pragma: no cover - network heavy
                    logger.warning("Unable to sign preview for %s/%s: %s", bucket, key, exc)
        encoded_key = quote(key, safe="/=")
        return f"https://{bucket}.s3.amazonaws.com/{encoded_key}"

    def _update_stage_runtime(self, stage_state: JSONDict, *, artifacts: Optional[JSONDict] = None, metrics: Optional[JSONDict] = None, notes: Optional[str] = None) -> None:
        if artifacts:
            current = stage_state.setdefault("artifacts", {})
            current.update(artifacts)
        if metrics:
            stage_metrics = stage_state.setdefault("metrics", {})
            stage_metrics.update(metrics)
        if notes is not None:
            stage_state["notes"] = notes
        self._persist_state()

    def _get_s3_client(self, region: Optional[str]) -> Optional[Any]:
        cache_key = region or "default"
        if cache_key in self._s3_clients:
            return self._s3_clients[cache_key]
        if not boto3:
            return None
        try:
            client = boto3.client("s3", region_name=region) if region else boto3.client("s3")
            self._s3_clients[cache_key] = client
            return client
        except Exception as exc:  # pragma: no cover - boto3 optional
            logger.warning("Unable to initialize S3 client: %s", exc)
            return None

    def _upload_pending_assets(self, assets: Optional[List[JSONDict]], update_stage: Optional[Any]) -> Optional[JSONDict]:
        if not assets:
            return None
        pending_items: List[JSONDict] = []
        for asset in assets:
            storage = asset.get("storage") or {}
            pending = storage.get("pending_s3")
            if not pending:
                continue
            bucket = pending.get("bucket")
            key = pending.get("key")
            local_path = pending.get("local_path") or storage.get("local_path")
            region = pending.get("region") or os.getenv("MEDIA_SUPPLY_CHAIN_AWS_REGION") or os.getenv("AWS_REGION") or os.getenv("AWS_DEFAULT_REGION")
            if not bucket or not key or not local_path:
                continue
            pending_items.append({
                "asset": asset,
                "storage": storage,
                "bucket": bucket,
                "key": key,
                "local_path": local_path,
                "region": region,
            })

        if not pending_items:
            return None

        client_cache: Dict[str, Any] = {}
        uploaded = 0
        bytes_moved = 0
        failures: List[JSONDict] = []

        total_bytes = 0
        for item in pending_items:
            local_path = Path(item["local_path"])
            if local_path.exists():
                total_bytes += local_path.stat().st_size

        current_bytes = 0

        def emit_progress(state: str = "uploading", message: Optional[str] = None):
            if not update_stage:
                return
            percent = 0
            if total_bytes:
                percent = min(100, max(0, int((current_bytes / total_bytes) * 100)))
            status = {
                "state": state,
                "bytes_total": total_bytes,
                "bytes_uploaded": min(current_bytes, total_bytes),
                "percent": percent,
                "asset_count": len(pending_items),
            }
            note = message or ("Uploading mezzanine to S3" if state == "uploading" else "Upload completed")
            update_stage(artifacts={"upload_status": status}, notes=note)

        emit_progress()

        for item in pending_items:
            bucket = item["bucket"]
            key = item["key"]
            local_path = Path(item["local_path"])
            if not local_path.exists():
                failures.append({"bucket": bucket, "key": key, "error": "local file missing"})
                continue
            region = item["region"]
            cache_key = region or "default"
            if cache_key in client_cache:
                client = client_cache[cache_key]
            else:
                client = self._get_s3_client(region)
                client_cache[cache_key] = client
            if not client:
                failures.append({"bucket": bucket, "key": key, "error": "s3 client unavailable"})
                continue
            try:
                if update_stage and total_bytes:
                    def _progress_callback(bytes_amount: int) -> None:
                        nonlocal current_bytes
                        current_bytes = min(total_bytes, current_bytes + bytes_amount)
                        emit_progress()

                    client.upload_file(str(local_path), bucket, key, Callback=_progress_callback)
                else:
                    client.upload_file(str(local_path), bucket, key)
            except (BotoCoreError, ClientError, Exception) as exc:  # pragma: no cover - network heavy
                failures.append({"bucket": bucket, "key": key, "error": str(exc)})
                continue

            s3_uri = f"s3://{bucket}/{key}"
            storage = item["storage"]
            storage["bucket"] = bucket
            storage["key"] = key
            storage["s3_uri"] = s3_uri
            storage.pop("pending_s3", None)
            item["asset"]["mezzanine_uri"] = s3_uri
            uploaded += 1
            bytes_moved += local_path.stat().st_size
            if not update_stage and total_bytes:
                current_bytes = min(total_bytes, current_bytes + local_path.stat().st_size)

        if failures and update_stage:
            emit_progress(state="failed", message="S3 upload failed")
        elif total_bytes and update_stage:
            current_bytes = total_bytes
            emit_progress(state="completed")

        summary = {
            "uploaded": uploaded,
            "bytes": bytes_moved,
            "failed": failures,
            "pending": len(pending_items) - uploaded - len(failures),
        }
        if failures:
            logger.warning("S3 ingest uploads encountered %d failure(s)", len(failures))
        return summary

    def _safe_copy(self, payload: JSONDict) -> JSONDict:
        return json.loads(json.dumps(payload, ensure_ascii=False))

    def _prepare_run_response(self, payload: JSONDict) -> JSONDict:
        run_copy = self._safe_copy(payload)
        self._refresh_deliverable_previews(run_copy)
        return run_copy

    def _load_sample_json(self, relative_path: str) -> JSONDict:
        resolved = (self.samples_dir / relative_path).resolve()
        if not resolved.exists():
            raise WorkflowEngineError(f"Sample file '{relative_path}' not found.")
        with open(resolved, "r", encoding="utf-8") as handle:
            return json.load(handle)

    def _write_json(self, path: Path, payload: JSONDict) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, ensure_ascii=False, indent=2)

    def _ping_service(self, target: JSONDict) -> JSONDict:
        endpoint = target.get("url")
        name = target.get("name") or endpoint
        timeout = target.get("timeout", 3)
        if not endpoint or not requests:
            return {"name": name, "status": "skipped", "reason": "requests not available"}
        try:
            response = requests.get(endpoint, timeout=timeout)
            status = "ok" if response.ok else "degraded"
            body: Any
            try:
                body = response.json()
            except ValueError:
                body = {
                    "text": response.text[:280],
                }
            return {
                "name": name,
                "status": status,
                "code": response.status_code,
                "url": endpoint,
                "details": body,
            }
        except Exception as exc:  # pragma: no cover - defensive
            return {
                "name": name,
                "status": "offline",
                "url": endpoint,
                "error": str(exc),
            }

    def _invoke_voiceover(self, prompt: str, config: JSONDict) -> Optional[JSONDict]:
        if not requests:
            return {"status": "skipped", "reason": "requests not available"}
        url = config.get("url")
        if not url:
            return None
        payload = {
            "prompt": prompt,
            "persona": config.get("persona"),
            "language": config.get("language", "en"),
        }
        timeout = config.get("timeout", 20)
        try:
            response = requests.post(url, json=payload, timeout=timeout)
            response.raise_for_status()
            data = response.json()
            data.setdefault("status", "completed")
            data["source"] = url
            return data
        except Exception as exc:  # pragma: no cover - network heavy
            return {
                "status": "failed",
                "error": str(exc),
                "source": url,
            }
