# Media Supply Chain Orchestration Service

This lightweight Flask service coordinates the Media Supply Chain use case outlined in the Excel tracker. It stitches together ingest, QC, enrichment, and packaging stages so the Live Demo can show deterministic runs without depending on heavyweight external tooling.

## Capabilities

- Loads workflow blueprints from `blueprints/*.json`.
- Persists run history to `config/media-supply-chain/runs.json`.
- Generates stage artifacts under `mediaSupplyChain/outputs/<run_id>/` for replay.
- Optionally pings existing services (scene summarization, content moderation, synthetic voiceover) and records their health in the QC stage.
- Captures user uploads via `/uploads`, storing assets locally (and in S3 when configured) while emitting manifest payloads ready for new workflow runs.

## Use Case Walkthrough (end-to-end)

The Live Demo uses this service to show an “agentic” supply-chain run over a single mezzanine asset:

1. **Upload mezzanine** (UI → `POST /uploads`)
   - The service saves the file to `mediaSupplyChain/uploads/` and returns `inputs.ingest_manifest`.
   - If `MEDIA_SUPPLY_CHAIN_UPLOAD_BUCKET` is set, the response includes `pending_s3`; the actual S3 upload happens during ingest.
2. **Start workflow** (UI → `POST /workflows/run` with `{ blueprint, inputs }`)
   - Returns `202` + a run object; the UI polls `GET /workflows?limit=25` while the run is active.
3. **Ingest stage**
   - Writes `01_ingest_manifest.json` and (optionally) uploads the mezzanine to S3.
4. **QC stage**
   - Produces `02_qc_report.json` and runs any blueprint-defined health checks (ex: Scene Summarization + Content Moderation).
5. **Personalize stage**
   - Produces `03_enrichment_plan.json` and can call Synthetic Voiceover to generate SSML.
6. **Package stage**
   - Produces `04_package_manifest.json` plus deliverables.
   - Preview URLs are derived automatically from each deliverable path (local artifact route or S3 URL/presign).

## Stage Overview (AWS-first)

1. **Ingest** – Accepts an ingest manifest (usually produced by the `/uploads` endpoint). Uploads are always saved to local disk first; when `MEDIA_SUPPLY_CHAIN_UPLOAD_BUCKET` is set, the upload response includes a `pending_s3` block and the ingest stage performs the actual S3 upload.
2. **QC** – Hydrates `samples/qc_report.json` and runs optional service health checks (Scene Summarization, Content Moderation) defined in the selected blueprint.
3. **Personalize** – Loads `samples/enrichment_plan.json` and can call the Synthetic Voiceover service (HTTP) to generate SSML.
4. **Package** – Generates deliverables via:
   - **AWS MediaConvert** only when the primary asset is in S3 *and* `MEDIA_CONVERT_ROLE` + `MEDIA_CONVERT_QUEUE` are configured.
   - **ffmpeg fallback** otherwise (outputs remain local unless `MEDIA_SUPPLY_CHAIN_DELIVERABLE_BUCKET` is set).

Future extensions such as a `Distribute` stage (MediaPackage, CloudFront, MediaTailor) or `Monitor` stage (CloudWatch metrics + EventBridge) can be layered on using the same AWS-first pattern.

### Demo assets pre-seeded

- `samples/ingest_manifest.json`: mezzanine delivery manifest used by the ingest stage.
- `samples/qc_report.json`: QC summary with warnings and synopsis for downstream stages.
- `samples/enrichment_plan.json`: localization/personalization plan plus CTA copy.
- `samples/package_manifest.json`: deliverable manifest for packaging.
- Reference workflow run ID (created on 8 Dec 2025): `3cfe5a92-39ae-412a-ac6d-0189a605db88`. Artifacts live under `mediaSupplyChain/outputs/3cfe5a92-39ae-412a-ac6d-0189a605db88/`.

## Key Endpoints

| Method | Endpoint | Description |
| --- | --- | --- |
| GET | `/health` | Service heartbeat with blueprint overview. |
| GET | `/blueprints` | Lists available workflow templates. |
| GET | `/workflows` | Returns recent orchestration runs (query `limit`). |
| GET | `/workflows/<run_id>` | Full detail for a specific run. |
| POST | `/workflows/run` | Starts a new run. Accepts `{ "blueprint": "media-supply-chain-phase-1", "inputs": {...} }`. |
| POST | `/uploads` | Accepts `multipart/form-data` with `file`, returning storage metadata plus the `inputs.ingest_manifest` block for a subsequent workflow run. |
| GET | `/uploads/<filename>` | Streams back an uploaded mezzanine asset (add `?download=1` to force attachment). |

## Local Development

1. Ensure the root virtual environment has the latest `requirements.txt` installed (`pip install -r requirements.txt`).
2. Run the service manually:
   ```bash
   cd mediaSupplyChain
   python app.py
   ```
3. Trigger a sample run:
   ```bash
   curl -X POST http://localhost:5011/workflows/run -H "Content-Type: application/json" -d '{}'
   ```
4. Inspect artifacts under `mediaSupplyChain/outputs/<run_id>/` (the reference run above is safe to demo).

## Local vs AWS configuration

| Goal | Recommended settings | Notes |
| --- | --- | --- |
| Local-only demo (no AWS spend) | Unset `MEDIA_SUPPLY_CHAIN_UPLOAD_BUCKET` and `MEDIA_SUPPLY_CHAIN_DELIVERABLE_BUCKET`; set `MEDIA_SUPPLY_CHAIN_FORCE_FFMPEG=true` | Runs fully from local disk; previews stream via `/media-supply-chain/artifacts/...` |
| Hybrid (store mezzanine in S3, package locally) | Set `MEDIA_SUPPLY_CHAIN_UPLOAD_BUCKET`; keep `MEDIA_CONVERT_*` unset | Ingest uploads to S3; packaging stays ffmpeg (deliverables local unless deliverable bucket set) |
| AWS packaging (MediaConvert) | Set `MEDIA_SUPPLY_CHAIN_UPLOAD_BUCKET`, `MEDIA_SUPPLY_CHAIN_DELIVERABLE_BUCKET`, `MEDIA_CONVERT_ROLE`, `MEDIA_CONVERT_QUEUE` | MediaConvert requires the source mezzanine be in S3 and boto3 available |

### Upload endpoint configuration

Set the following environment variables (optionally via `.env`) to control how uploads are handled:

- `MEDIA_SUPPLY_CHAIN_UPLOAD_BUCKET`: when set, the service records a `pending_s3` upload plan in the manifest; the ingest stage uploads to this bucket.
- `MEDIA_SUPPLY_CHAIN_UPLOAD_PREFIX`: logical folder prefix inside the bucket (defaults to `media-supply-chain/uploads`).
- `AWS_REGION` / `AWS_DEFAULT_REGION`: region used when initializing the S3 client.

Without `MEDIA_SUPPLY_CHAIN_UPLOAD_BUCKET`, workflows run entirely from `mediaSupplyChain/uploads/`.

The service is auto-started via `start-all.sh` and `start-backend.sh`. The Live Demo page at `/media-supply-chain` consumes the `/workflows` APIs directly, so keep this service running for the UI to render data.

### Packaging deliverables (MediaConvert + ffmpeg)

The packaging stage attempts to create UHD, HLS, and 9x16 TikTok deliverables.

- `MEDIA_SUPPLY_CHAIN_DELIVERABLE_BUCKET`: when set, ffmpeg outputs (and other local deliverables) are uploaded to this bucket.
- `MEDIA_SUPPLY_CHAIN_DELIVERABLE_PREFIX`: base key prefix for each run (defaults to `media-supply-chain/deliverables`).
- `MEDIA_CONVERT_ROLE`: IAM role ARN the service should assume when creating jobs.
- `MEDIA_CONVERT_QUEUE`: MediaConvert queue ARN to submit to.
- `MEDIA_CONVERT_JOB_TEMPLATE` (optional): Template name/ARN to reuse if you already modeled the job in AWS.
- `MEDIA_CONVERT_ENDPOINT` (optional): Override for the account-specific MediaConvert endpoint. When omitted, the service discovers one automatically.

If `MEDIA_SUPPLY_CHAIN_FORCE_FFMPEG=true`, or if MediaConvert is not usable (missing config, missing boto3, or source is local-only), the engine falls back to `ffmpeg` and saves deliverables under `mediaSupplyChain/outputs/<run_id>/deliverables/`. Configure the fallback with:

- `MEDIA_SUPPLY_CHAIN_FORCE_FFMPEG=true` to always skip MediaConvert.
- `FFMPEG_BINARY` when `ffmpeg` lives outside of `$PATH` (defaults to `ffmpeg`).

When `MEDIA_SUPPLY_CHAIN_DELIVERABLE_BUCKET` is configured and `boto3` is available, ffmpeg outputs are uploaded and their `path` becomes an `s3://...` URI.

### Preview URL signing

When a deliverable `path` is an `s3://...` URI, the engine derives a `preview_url` as either:
- a presigned S3 URL (default), or
- a public HTTPS URL (`https://<bucket>.s3.amazonaws.com/<key>`) when signing is disabled.

Environment variables:
- `MEDIA_SUPPLY_CHAIN_SIGN_PREVIEWS` (default `true`): enables presigned previews when `boto3` is available.
- `MEDIA_SUPPLY_CHAIN_PREVIEW_TTL` (default `900` seconds): TTL for presigned preview URLs (min 60, max 86400).

## Known gaps / risks (demo-relevant)

- **Deterministic-by-design:** QC/enrichment/package manifests are largely sample-driven; QC “service checks” are HTTP health probes, not full media analysis.
- **Voiceover reliability:** Run history shows repeated model invocation failures inside Synthetic Voiceover with a fallback SSML template; if you want fully-AI SSML, the voiceover service’s Bedrock request shape likely needs alignment with the configured model.
- **AWS spend controls:** Uploads do not auto-run (UI requires confirmation). MediaConvert only runs when explicitly configured; `MEDIA_SUPPLY_CHAIN_FORCE_FFMPEG=true` hard-disables it.
- **Preview exposure:** The artifacts endpoint serves files under the repo root (path traversal is checked, but it is still “serve local files”); treat this as demo-only and do not expose publicly.
