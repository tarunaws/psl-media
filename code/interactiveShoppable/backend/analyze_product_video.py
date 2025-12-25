"""Analyze interactive shoppable demo video with AWS Rekognition.

Steps:
1. Upload local demo asset to S3.
2. Run Rekognition label detection.
3. Persist raw response and condensed metadata for frontend use.

Requires AWS credentials with access to S3 + Rekognition.
"""
from __future__ import annotations

import json
import time
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Iterable, List, Dict, Any

import boto3

ROOT = Path(__file__).resolve().parents[1]
VIDEO_PATH = ROOT / "videos" / "productvideo.mp4"
OUTPUT_DIR = Path(__file__).resolve().parent / "metadata"
RAW_OUTPUT_PATH = OUTPUT_DIR / "rekognition_labels.json"
CATALOG_OUTPUT_PATH = OUTPUT_DIR / "catalog_candidates.json"

S3_BUCKET = "mediagenailab"
S3_KEY = "interactive-shoppable/productvideo.mp4"
MIN_CONFIDENCE = 70

RELEVANT_PARENTS = {
    "Apparel", "Clothing", "Footwear", "Shoe", "Dress", "Coat", "Handbag",
    "Bag", "Purse", "Watch", "Jewelry", "Electronics", "Appliance",
    "Phone", "Laptop", "Tablet", "Furniture", "Chair", "Table", "Sofa",
    "Home Decor", "Kitchen", "Food", "Drink", "Cosmetics", "Vehicle",
}


@dataclass
class CatalogCandidate:
    label: str
    confidence: float
    timestamp_ms: int
    parents: List[str]
    instances: List[Dict[str, Any]]


class RekognitionAnalyzer:
    def __init__(self) -> None:
        self.s3 = boto3.client("s3")
        self.rekognition = boto3.client("rekognition")

    def upload_video(self) -> None:
        if not VIDEO_PATH.exists():
            raise FileNotFoundError(f"Demo video missing: {VIDEO_PATH}")
        print(f"Uploading {VIDEO_PATH.name} to s3://{S3_BUCKET}/{S3_KEY} ...")
        self.s3.upload_file(str(VIDEO_PATH), S3_BUCKET, S3_KEY)
        print("Upload complete.")

    def start_label_detection(self) -> str:
        response = self.rekognition.start_label_detection(
            Video={"S3Object": {"Bucket": S3_BUCKET, "Name": S3_KEY}},
            MinConfidence=MIN_CONFIDENCE,
        )
        job_id = response["JobId"]
        print(f"Started label detection job: {job_id}")
        return job_id

    def wait_for_job(self, job_id: str) -> List[Dict[str, Any]]:
        print("Waiting for Rekognition job to finish ...")
        pagination_token = None
        finished = False
        all_labels: List[Dict[str, Any]] = []

        while True:
            kwargs = {"JobId": job_id, "SortBy": "TIMESTAMP", "MaxResults": 1000}
            if pagination_token:
                kwargs["NextToken"] = pagination_token
            response = self.rekognition.get_label_detection(**kwargs)
            status = response["JobStatus"]
            if status == "IN_PROGRESS":
                time.sleep(5)
                continue
            if status != "SUCCEEDED":
                raise RuntimeError(f"Rekognition job failed with status: {status}")

            labels = response.get("Labels", [])
            all_labels.extend(labels)
            pagination_token = response.get("NextToken")
            if not pagination_token:
                break
        print(f"Collected {len(all_labels)} label records.")
        return all_labels

    def save_raw_metadata(self, labels: List[Dict[str, Any]]) -> None:
        RAW_OUTPUT_PATH.write_text(json.dumps(labels, indent=2))
        print(f"Raw metadata saved to {RAW_OUTPUT_PATH.relative_to(Path.cwd())}")

    def build_catalog_candidates(self, labels: Iterable[Dict[str, Any]]) -> List[CatalogCandidate]:
        candidates: List[CatalogCandidate] = []
        for label_entry in labels:
            label = label_entry.get("Label", {})
            name = label.get("Name")
            parents = [p.get("Name") for p in label.get("Parents", [])]
            confidence = float(label.get("Confidence", 0))
            instances = label.get("Instances", [])
            timestamp = int(label_entry.get("Timestamp", 0))

            if not name:
                continue
            parent_hit = bool(RELEVANT_PARENTS.intersection(parents))
            direct_hit = name in RELEVANT_PARENTS
            if not parent_hit and not direct_hit:
                continue
            if not instances:
                continue

            candidates.append(
                CatalogCandidate(
                    label=name,
                    confidence=confidence,
                    timestamp_ms=timestamp,
                    parents=parents,
                    instances=[{
                        "confidence": float(inst.get("Confidence", 0)),
                        "boundingBox": inst.get("BoundingBox"),
                    } for inst in instances],
                )
            )
        print(f"Identified {len(candidates)} catalog-ready candidates.")
        return candidates

    def save_catalog_candidates(self, candidates: List[CatalogCandidate]) -> None:
        data = [asdict(c) for c in candidates]
        CATALOG_OUTPUT_PATH.write_text(json.dumps(data, indent=2))
        print(f"Catalog metadata saved to {CATALOG_OUTPUT_PATH.relative_to(Path.cwd())}")


def main() -> None:
    analyzer = RekognitionAnalyzer()
    analyzer.upload_video()
    job_id = analyzer.start_label_detection()
    labels = analyzer.wait_for_job(job_id)
    analyzer.save_raw_metadata(labels)
    candidates = analyzer.build_catalog_candidates(labels)
    analyzer.save_catalog_candidates(candidates)


if __name__ == "__main__":
    main()
