# Content Moderation Service

This Flask service accepts short-form videos, uploads them to Amazon S3, and calls AWS video moderation APIs to detect sensitive content. The API returns the timestamps (in milliseconds, seconds, and formatted timecode) for every moderation label that crosses the configured confidence threshold.

## Requirements

Set the following environment variables before launching the service:

- `AWS_ACCESS_KEY_ID`
- `AWS_SECRET_ACCESS_KEY`
- `AWS_REGION` *(optional, defaults to `us-east-1`)*
- `CONTENT_MODERATION_BUCKET` *(S3 bucket that stores uploaded videos for downstream moderation processing)*
- `CONTENT_MODERATION_PREFIX` *(optional folder/prefix for uploaded keys)*

Optional tuning variables:

- `CONTENT_MODERATION_MIN_CONFIDENCE` (default `75`)
- `CONTENT_MODERATION_POLL_INTERVAL` (seconds, default `2`)
- `CONTENT_MODERATION_MAX_WAIT_SECONDS` (default `300`)
- `CONTENT_MODERATION_ALLOWED_ORIGINS` (comma separated CORS origins)
- `CONTENT_MODERATION_API_PORT` (default `5006`)
- `CONTENT_MODERATION_SNS_TOPIC_ARN` and `CONTENT_MODERATION_SNS_ROLE_ARN` (optional — provide both to stream moderation job status via SNS; leave unset or remove blank placeholders if you do not need notifications)

## Endpoints

- `POST /moderate` — Accepts multipart form data. Fields:
  - `video` *(file, required)* — MP4/MOV/MKV etc.
  - `categories` *(comma separated list, optional)* — Filters by moderation parent categories (e.g. `Alcohol,Tobacco,Drugs`).
  - `min_confidence` *(number, optional)* — Overrides the default confidence threshold.

  Response payload includes the detected moderation events, aggregated counts per category, and job metadata.

- `GET /result/<job_id>` — Retrieves the saved moderation report from disk if available.
- `GET /health` — Quick readiness check and downstream service availability (AWS moderation APIs/S3).

## Running locally

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt -r contentModeration/requirements.txt
cd contentModeration
python content_moderation_service.py
```

The service listens on port `5006` by default. Set `CONTENT_MODERATION_API_PORT` to change it.
