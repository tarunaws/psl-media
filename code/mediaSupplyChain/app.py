from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from flask import Flask, abort, jsonify, request, send_from_directory
from flask_cors import CORS

from workflow_engine import WorkflowEngine, WorkflowEngineError
from storage import AssetStorage, AssetStorageError, UploadedAsset

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}})

BASE_DIR = Path(__file__).parent
engine = WorkflowEngine(BASE_DIR)
storage = AssetStorage(BASE_DIR)


@app.errorhandler(WorkflowEngineError)
def handle_engine_error(exc: WorkflowEngineError):
    message = str(exc)
    status_code = 404 if "not found" in message.lower() else 400
    return jsonify({"error": message}), status_code


@app.route("/health", methods=["GET"])
def health() -> Any:
    return jsonify(
        {
            "status": "ok",
            "service": "media-supply-chain",
            "blueprints": engine.blueprint_overview(),
            "active_runs": engine.active_run_count(),
        }
    )


@app.route("/blueprints", methods=["GET"])
def blueprints() -> Any:
    return jsonify({"blueprints": engine.list_blueprints()})


@app.route("/workflows", methods=["GET"])
def list_workflows() -> Any:
    limit_param = request.args.get("limit", "25")
    try:
        limit = max(1, min(100, int(limit_param)))
    except ValueError:
        limit = 25
    return jsonify({"runs": engine.list_runs(limit=limit)})


@app.route("/workflows/<run_id>", methods=["GET"])
def get_workflow(run_id: str) -> Any:
    run = engine.get_run(run_id)
    return jsonify(run)


@app.route("/workflows/run", methods=["POST"])
def trigger_workflow() -> Any:
    payload = request.get_json(silent=True) or {}
    blueprint = payload.get("blueprint")
    inputs = payload.get("inputs") or {}
    labels = payload.get("labels") or {}
    run = engine.start_run(blueprint, inputs=inputs, labels=labels)
    return jsonify(run), 202


def _serialize_asset(asset: UploadedAsset) -> dict:
    return {
        "asset_id": asset.asset_id,
        "filename": asset.filename,
        "size_bytes": asset.size_bytes,
        "bucket": asset.bucket,
        "key": asset.key,
        "s3_uri": asset.s3_uri,
        "local_path": asset.local_path.as_posix(),
        "download_url": asset.public_url(),
        "pending_s3": asset.pending_s3,
    }


@app.route("/uploads", methods=["POST"])
def upload_asset() -> Any:
    if "file" not in request.files:
        return jsonify({"error": "Missing 'file' field."}), 400

    upload = request.files["file"]
    if not upload or not upload.filename:
        return jsonify({"error": "Empty upload payload."}), 400

    title = request.form.get("title")
    description = request.form.get("description")
    blueprint = request.form.get("blueprint") or engine.default_blueprint

    try:
        saved = storage.save(upload, title=title, description=description)
    except AssetStorageError as exc:
        return jsonify({"error": str(exc)}), 400

    response = {
        "message": "Upload captured successfully.",
        "blueprint": blueprint,
        "asset": _serialize_asset(saved["asset"]),
        "inputs": {
            "ingest_manifest": saved["manifest"],
        },
    }
    return jsonify(response), 201


@app.route("/uploads/<path:filename>", methods=["GET"])
def download_uploaded_asset(filename: str):
    download = (request.args.get("download", "false").lower() in {"1", "true", "yes"})
    try:
        storage.resolve_upload_path(filename)
    except AssetStorageError as exc:
        return jsonify({"error": str(exc)}), 404
    return send_from_directory(storage.upload_dir, filename, as_attachment=download)


@app.route("/media-supply-chain/artifacts/<path:filename>", methods=["GET"])
def serve_artifact(filename: str):
    try:
        resolved = (engine.project_root / filename).resolve()
    except (OSError, ValueError):
        abort(404)
    project_root = engine.project_root.resolve()
    if not resolved.exists():
        abort(404)
    try:
        relative = resolved.relative_to(project_root)
    except ValueError:
        abort(404)
    return send_from_directory(project_root, relative.as_posix())


if __name__ == "__main__":  # pragma: no cover - manual invocation
    port = int(os.getenv("PORT", "5011"))
    app.run(host="0.0.0.0", port=port, debug=os.getenv("DEBUG", "false").lower() == "true")
