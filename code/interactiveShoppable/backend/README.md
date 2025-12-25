# Interactive & Shoppable Backend

Lightweight Flask service that powers the local "Interactive & Shoppable Video" demo.

## Features

- Serves the curated dummy catalog (`metadata/catalog.json`) created from AWS Rekognition analysis.
- Streams the local `productvideo.mp4` asset so the React frontend can play it without copying files into `public/`.
- Provides a small `/interactive/summary` endpoint for diagnostics and admin dashboards.

## Prerequisites

- Python 3.10+
- Local AWS credentials (only needed if you plan to re-run `analyze_product_video.py`).

Install deps once:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Run the API

```bash
export FLASK_APP=app.py
export FLASK_ENV=development
flask run --port 5055
```

Endpoints:

- `GET /interactive/catalog`
- `GET /interactive/video`
- `GET /interactive/summary`

## Rekognition Workflow (optional)

`analyze_product_video.py` uploads the demo video to S3, invokes AWS Rekognition label detection, and writes:

- `metadata/rekognition_labels.json` – full response
- `metadata/catalog_candidates.json` – filtered candidates used to craft the curated catalog

Edit `metadata/catalog.json` as needed to change the dummy SKUs that appear in the Live Demo experience.
