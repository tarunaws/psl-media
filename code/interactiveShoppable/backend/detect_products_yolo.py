"""Detect shoppable objects in the demo video via an open-source model.

This script samples frames from ``videos/productvideo.mp4`` and runs a
pretrained Ultralytics YOLOv8 model (COCO weights) to identify objects. The
results are stored under ``metadata/yolo_candidates.json`` with timestamps that
can later be merged into ``catalog.json``.

Usage (run inside repo root venv):

    python code/interactiveShoppable/backend/detect_products_yolo.py

Ultralytics + PyTorch are already installed in the project virtual
environment via ``pip install ultralytics``.
"""

from __future__ import annotations

import importlib
import json
import pkgutil
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Dict, List

import cv2
import torch
import torch.nn as nn
from torch.serialization import add_safe_globals, safe_globals
from ultralytics import YOLO
from ultralytics.nn import modules as yolo_modules
from ultralytics.nn.tasks import DetectionModel


ROOT = Path(__file__).resolve().parents[1]
VIDEO_PATH = ROOT / "videos" / "productvideo.mp4"
OUTPUT_PATH = Path(__file__).resolve().parent / "metadata" / "yolo_candidates.json"

# Sample every N milliseconds to balance coverage with runtime.
FRAME_INTERVAL_MS = 400

# Map YOLO class names to higher-level product categories.
INTERESTING_CLASSES: Dict[str, Dict[str, str]] = {
    "cell phone": {"label": "Mobile Phone", "cta": "Add Phone"},
    "handbag": {"label": "Handbag", "cta": "Add Handbag"},
    "backpack": {"label": "Backpack", "cta": "Add Backpack"},
    "suitcase": {"label": "Suitcase", "cta": "Add Luggage"},
    "laptop": {"label": "Laptop", "cta": "Add Laptop"},
    "keyboard": {"label": "Computer Keyboard", "cta": "Add Keyboard"},
    "mouse": {"label": "Computer Mouse", "cta": "Add Mouse"},
    "umbrella": {"label": "Umbrella", "cta": "Add Umbrella"},
    "sports ball": {"label": "Sports Ball", "cta": "Add Sports Item"},
    "book": {"label": "Book", "cta": "Add Book"},
    "bottle": {"label": "Bottle", "cta": "Add Bottle"},
    "cup": {"label": "Cup", "cta": "Add Cup"},
    "wine glass": {"label": "Wine Glass", "cta": "Add Glass"},
    "clock": {"label": "Clock", "cta": "Add Clock"},
    "chair": {"label": "Chair", "cta": "Add Chair"},
    "sofa": {"label": "Sofa", "cta": "Add Sofa"},
    "tv": {"label": "Monitor", "cta": "Add Screen"},
    "refrigerator": {"label": "Appliance", "cta": "Add Appliance"},
    "microwave": {"label": "Appliance", "cta": "Add Appliance"},
    "oven": {"label": "Appliance", "cta": "Add Appliance"},
    "toaster": {"label": "Appliance", "cta": "Add Appliance"},
    "sink": {"label": "Kitchen Sink", "cta": "Add Sink"},
    "potted plant": {"label": "Plant", "cta": "Add Plant"},
    "bench": {"label": "Bench", "cta": "Add Bench"},
    "tie": {"label": "Tie", "cta": "Add Tie"},
    "bowl": {"label": "Bowl", "cta": "Add Bowl"},
    "fork": {"label": "Utensil", "cta": "Add Utensil"},
    "knife": {"label": "Utensil", "cta": "Add Utensil"},
    "spoon": {"label": "Utensil", "cta": "Add Utensil"},
    "dining table": {"label": "Table", "cta": "Add Table"},
}


@dataclass
class DetectionCandidate:
    label: str
    source_class: str
    timestamp_ms: int
    confidence: float
    bounding_box: Dict[str, float]
    frame_index: int
    frame_width: int
    frame_height: int
    cta_text: str


def sample_interval_frames(fps: float) -> int:
    interval = max(int((FRAME_INTERVAL_MS / 1000.0) * fps), 1)
    return interval


def normalize_box(x1: float, y1: float, x2: float, y2: float, width: int, height: int) -> Dict[str, float]:
    return {
        "Left": max(min(x1 / width, 1.0), 0.0),
        "Top": max(min(y1 / height, 1.0), 0.0),
        "Width": max(min((x2 - x1) / width, 1.0), 0.0),
        "Height": max(min((y2 - y1) / height, 1.0), 0.0),
    }


def detect() -> List[DetectionCandidate]:
    if not VIDEO_PATH.exists():
        raise FileNotFoundError(f"Demo video missing at {VIDEO_PATH}")

    safe_types = {DetectionModel, nn.Sequential}
    for value in yolo_modules.__dict__.values():
        if isinstance(value, type):
            safe_types.add(value)
    for _, module_name, _ in pkgutil.walk_packages(yolo_modules.__path__, yolo_modules.__name__ + "."):
        module = importlib.import_module(module_name)
        for value in module.__dict__.values():
            if isinstance(value, type):
                safe_types.add(value)
    add_safe_globals(safe_types)

    original_torch_load = torch.load

    def patched_torch_load(*args, **kwargs):
        kwargs.setdefault("weights_only", False)
        return original_torch_load(*args, **kwargs)

    torch.load = patched_torch_load
    try:
        with safe_globals(safe_types):
            model = YOLO("yolov8n.pt")  # lightweight COCO weights
    finally:
        torch.load = original_torch_load
    cap = cv2.VideoCapture(str(VIDEO_PATH))
    fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    frame_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH) or 1920)
    frame_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT) or 1080)
    frame_interval = sample_interval_frames(fps)

    frame_idx = 0
    detections: List[DetectionCandidate] = []

    while True:
        success, frame = cap.read()
        if not success:
            break
        if frame_idx % frame_interval != 0:
            frame_idx += 1
            continue

        timestamp_ms = int((frame_idx / fps) * 1000)
        results = model(frame, verbose=False)
        for result in results:
            if not hasattr(result, "boxes"):
                continue
            boxes = result.boxes
            if boxes is None:
                continue
            for xyxy, cls_idx, conf in zip(boxes.xyxy, boxes.cls, boxes.conf):
                source_label = model.names.get(int(cls_idx), "")
                mapping = INTERESTING_CLASSES.get(source_label)
                if not mapping:
                    continue
                bbox = normalize_box(*xyxy.tolist(), frame_width, frame_height)
                detections.append(
                    DetectionCandidate(
                        label=mapping["label"],
                        source_class=source_label,
                        timestamp_ms=timestamp_ms,
                        confidence=float(conf),
                        bounding_box=bbox,
                        frame_index=frame_idx,
                        frame_width=frame_width,
                        frame_height=frame_height,
                        cta_text=mapping["cta"],
                    )
                )
        frame_idx += 1

    cap.release()
    return detections


def main() -> None:
    detections = detect()
    payload = [asdict(d) for d in detections]
    OUTPUT_PATH.write_text(json.dumps(payload, indent=2))
    print(f"Saved {len(payload)} YOLO detections to {OUTPUT_PATH.relative_to(ROOT)}")


if __name__ == "__main__":
    main()