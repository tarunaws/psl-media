# psl-media — Copilot Instructions

## Where the “real” code lives
- Canonical dev stack is under `code/` (multiple Flask services + a Create React App frontend in `code/frontend/`).
- Prefer runtime truth over docs: `code/start-all.sh` and `code/start-backend.sh` define what runs, ports, and PATH/env defaults.
- Root-level service folders mirror older layouts; prefer editing `code/<service>/`.
- Services share utilities via `code/shared/` (startup scripts export `PYTHONPATH="$PROJECT_ROOT:${PYTHONPATH:-}"`; do not add per-service `sys.path` hacks).

## Run / stop locally (macOS)
From `code/`:
- Local startup is **disabled by default** (cloud-only mode). To run locally: `ENABLE_LOCAL_START=1 ./start-all.sh` or `ENABLE_LOCAL_START=1 ./start-backend.sh`.
- Stop via `./stop-all.sh` / `./stop-backend.sh` (uses `*.pid` then frees ports via `lsof`). Logs + PIDs land in `code/*.log` and `code/*.pid`.

## Toolchain assumptions
- One shared venv at `code/.venv/` with deps from `code/requirements.txt` (includes `python-dotenv`, Flask, `boto3`). Avoid per-service virtualenvs.
- Scripts enforce a PATH that includes Homebrew + Node (nvm) and expect `ffmpeg` available for media workflows.
- Frontend is CRA: `npm start` / `npm test` / `npm run build` in `code/frontend/`.

## Architecture & service boundaries
- `code/mediaSupplyChain/` (port 5011) is the local orchestrator and primary UI backend (uploads + workflow runs + artifact streaming). Prefer exposing new “demo workflow” backend capabilities through 5011.
- Other UI-facing services: `useCaseVisibility` (5012), `highlightTrailer` (5013), `metadata` (5014), `interactiveShoppable/backend` (5055). Most other services run standalone but may be called by 5011 workflows.

## Frontend → backend routing (dev)
React dev proxy is `code/frontend/src/setupProxy.js` (order matters):
- `/api/highlight-trailer/*` → 5013 (must be registered before `/api`)
- `/usecase-visibility/*` → 5012
- `/media-supply-chain/artifacts/*` → 5011 with prefix preserved (artifact streaming)
- `/media-supply-chain/*` → 5011 with path rewrite
- `/api/*` → 5011 (generic gateway)

## Config, AWS, logging, artifacts
- Layered env: `.env` then `.env.local` (override) via `shared.env_loader.load_environment()`; template at `code/.env.local.template`. Startup scripts also `source` these files.
- Optional AWS Secrets Manager hydration: `shared.secret_loader.load_aws_secret_into_env(APP_SECRETS_ID, ...)`.
- Startup scripts set defaults used across services (e.g. `AWS_REGION`, `MEDIA_S3_BUCKET`, `VIDEO_GEN_S3_BUCKET`; `PERSONALIZED_TRAILER_PIPELINE_MODE=mock`; DAI defaults like `DAI_MEDIA_SOURCE=local`).
- Prefer JSON logging via `shared.logging_utils.configure_json_logging("<service>")` early in app startup.
- Artifacts are written under service folders (e.g. `mediaSupplyChain/outputs/<run_id>/`); cleanup helper: `code/scripts/prune_media_artifacts.py` (uses `ARTIFACT_RETENTION_HOURS`, default 72).
