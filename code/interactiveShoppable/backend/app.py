"""Lightweight API for the Interactive & Shoppable demo use case.

Endpoints
=========
GET /interactive/catalog
    Returns the curated dummy catalog derived from Rekognition labels.

GET /interactive/video
    Streams the local demo video (H.264) for the frontend player.

GET /interactive/summary
    Simple derived stats for display in the admin/ops console.

Run locally with:
    export FLASK_APP=app.py
    export FLASK_ENV=development
    flask run --port 5055
"""
from __future__ import annotations

import json
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import List

from flask import Flask, jsonify, send_file
from flask_cors import CORS

BASE_DIR = Path(__file__).resolve().parent
CATALOG_PATH = BASE_DIR / "metadata" / "catalog.json"
VIDEO_PATH = BASE_DIR.parent / "videos" / "productvideo.mp4"

if not CATALOG_PATH.exists():
    raise FileNotFoundError(f"Catalog data missing: {CATALOG_PATH}")
if not VIDEO_PATH.exists():
    raise FileNotFoundError(f"Demo video missing: {VIDEO_PATH}")

with CATALOG_PATH.open() as catalog_file:
    CATALOG: List[dict] = json.load(catalog_file)


@dataclass
class CatalogSummary:
    total_items: int
    unique_labels: int
    earliest_start_ms: int
    latest_end_ms: int


def build_summary() -> CatalogSummary:
    starts = [item.get("startMs", item.get("timestampMs", 0)) for item in CATALOG]
    ends = [item.get("endMs", item.get("timestampMs", 0)) for item in CATALOG]
    return CatalogSummary(
        total_items=len(CATALOG),
        unique_labels=len({item.get("label") for item in CATALOG}),
        earliest_start_ms=min(starts) if starts else 0,
        latest_end_ms=max(ends) if ends else 0,
    )


app = Flask(__name__)
CORS(app, resources={r"/interactive/*": {"origins": "*"}})
SUMMARY = build_summary()


@app.route("/interactive/catalog", methods=["GET"])
def catalog() -> tuple:
    return jsonify({
        "items": CATALOG,
        "generatedAt": SUMMARY.earliest_start_ms,
    })


@app.route("/interactive/video", methods=["GET"])
def video() -> send_file:
    # `conditional=True` allows range requests from the video element.
    return send_file(VIDEO_PATH, mimetype="video/mp4", conditional=True)


@app.route("/interactive/summary", methods=["GET"])
def summary() -> tuple:
    return jsonify(asdict(SUMMARY))


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5055, debug=True)
