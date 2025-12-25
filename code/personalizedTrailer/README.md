# Personalized Trailer Service

Generate audience-specific trailer treatments by combining viewer profiles with automated scene analysis and packaging.

## Overview

The service orchestrates a multi-stage workflow:

1. **Upload & Profiling** – Accept a hero video clip (MP4/MOV/etc.) together with a selected viewer profile.
2. **Scene Intelligence (Amazon Rekognition)** – Detect faces, emotions, and key objects to map candidate beats.
3. **Preference Ranking (Amazon Personalize / SageMaker)** – Score scenes against user taste (genre, emotion, engagement).
4. **Assembly (AWS Elemental MediaConvert)** – Stitch the highest scoring shots into a trailer timeline with multiple renditions.
5. **Delivery (Amazon S3 + AWS Lambda)** – Persist assets, emit events, and trigger downstream notifications.
6. **Accessibility (Amazon Transcribe + Amazon Translate)** – Produce localized captions for the viewer’s preferred language.

The default pipeline runs in **mock mode** so the frontend can demonstrate the flow without touching real AWS services. Supply the relevant environment variables to switch individual stages to managed AWS equivalents.

## Requirements

```bash
pip install -r requirements.txt -r ../requirements.txt
```

Optional tooling for the local rendering fallback:

```bash
brew install ffmpeg  # or use your package manager of choice
```

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `PERSONALIZED_TRAILER_PORT` | HTTP port for the Flask app | `5007` |
| `PERSONALIZED_TRAILER_PIPELINE_MODE` | `mock` (offline demo) or `aws` (invoke live services) | `mock` |
| `PERSONALIZED_TRAILER_REGION` | AWS region for live integrations | `AWS_REGION` or `us-east-1` |
| `PERSONALIZED_TRAILER_S3_BUCKET` | Bucket to store uploads and deliverables | _unset_ |
| `PERSONALIZED_TRAILER_PREFIX` | Optional key prefix for media | `personalized-trailers` |
| `PERSONALIZED_TRAILER_ALLOWED_ORIGINS` | Comma-separated CORS allow list | Localhost defaults |
| `PERSONALIZED_TRAILER_MAX_UPLOAD_BYTES` | Upload limit in bytes | `2 GiB` |

> When `PERSONALIZED_TRAILER_PIPELINE_MODE=aws`, ensure credentials are available for Rekognition, Personalize Runtime, MediaConvert, Transcribe, Translate, Lambda, and SageMaker. The mock pipeline always remains available as a fallback if any client cannot be created.

## REST API

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/health` | Service readiness, pipeline mode, and AWS connectivity. |
| `GET` | `/profiles` | Viewer profile presets plus default languages/durations. |
| `GET` | `/options` | Supported trailer durations, formats, and subtitle languages. |
| `POST` | `/generate` | Multipart submission with `video` + profile fields to build a trailer plan (returns job payload immediately). |
| `GET` | `/jobs/<job_id>` | Retrieve persisted job metadata and deliverable manifest. |
| `GET` | `/jobs/<job_id>/storyboard` | Download synthesized storyboard frames (mock mode). |
| `GET` | `/jobs/<job_id>/deliverables/<artifact>` | Stream or download generated assets (`artifact` values: `master`, `captions`, `storyboard`, ...). Append `?download=true` to force attachment. |

## Mock Pipeline Output (with FFmpeg fallback)

`jobs/<job_id>.json` captures the full response returned to the frontend, including:

- **analysis** – Detected scenes, emotions, labels, and characters.
- **personalization** – Ranked scene list and selections bounded by duration.
- **assembly** – Timeline with transitions, audio cues, and rendition targets.
- **deliverables** – Local MP4 rendered via FFmpeg (when installed) and optional captions/storyboard JSON. If FFmpeg is unavailable the manifest will note that the trailer is a placeholder.
- **providers** – Status of each AWS service touchpoint with timing metrics.

## Running Locally

```bash
cd personalizedTrailer
python app.py
```

Then open <http://localhost:5007/health> to verify the service.

### FFmpeg fallback rendering

When `ffmpeg` is available on the host, the mock pipeline stitches the selected timeline clips into a playable trailer located under `personalizedTrailer/outputs/<job_id>_trailer.<ext>`. The renderer trims each segment from the uploaded source, concatenates them, and records the output size inside the `deliverables.master` block. No additional configuration is required beyond having FFmpeg on the `$PATH`.

If FFmpeg is missing, the service will still return a full job payload and note that the trailer asset could not be rendered.
