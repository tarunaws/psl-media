# BornInCloud Streaming — Copilot Instructions

## Big picture (source of truth)
- Stack lives in `code/`: multiple small Flask services + a Create React App frontend in `code/frontend/`.
- Prefer runtime truth over docs: `code/start-all.sh` and `code/start-backend.sh` define what runs, ports, and the required `PATH`/env defaults.
- Services share utilities via `code/shared/` (scripts export `PYTHONPATH="$PROJECT_ROOT:${PYTHONPATH:-}"`; do not add per-service `sys.path` hacks).

## Run / stop locally
From `code/`:
- `./start-all.sh` (backends + React) or `./start-backend.sh` (backends only)
- `./stop-all.sh` / `./stop-backend.sh` (uses `*.pid` then frees ports via `lsof`)
Scripts write `code/*.log` and `code/*.pid`.

## Toolchain assumptions
- Python runs from the single shared venv at `code/.venv/` with deps from `code/requirements.txt`.
- This repo uses the “one venv to rule them all” approach: do not add per-service virtualenvs or separate dependency sets; update `code/requirements.txt` to keep the whole stack compatible.
- Scripts enforce a PATH that includes Homebrew + Node (nvm) and expect `ffmpeg` available for media workflows (see `code/SERVICES_README.md`).
- Frontend is CRA (`npm start`/`npm test`/`npm run build`) in `code/frontend/`.

## Architecture & service boundaries
- `code/mediaSupplyChain/` (port 5011) is the local “gateway/orchestrator” consumed by the UI; new backend capabilities should prefer being exposed via 5011.
- Notable dev ports: `media-supply-chain` 5011, `usecase-visibility` 5012, `highlight-trailer` 5013, `engro-metadata` 5014 (Envid Metadata UI) (full list is in `code/start-all.sh`).

## Frontend → backend routing
React dev proxy in `code/frontend/src/setupProxy.js` (order matters):
- `/api/*` → 5011
- `/api/highlight-trailer/*` → 5013 (must be registered before `/api`)
- `/media-supply-chain/*` → 5011 with path rewrite; `/media-supply-chain/artifacts/*` preserves prefix for artifact streaming
- `/usecase-visibility/*` → 5012

## Config, secrets, logging, artifacts
- Layered env: `.env` then `.env.local` (override) via `shared.env_loader.load_environment()`; template at `code/.env.local.template`.
- Optional AWS Secrets Manager hydration: `shared.secret_loader.load_aws_secret_into_env(APP_SECRETS_ID, ...)`.
- Scripts set defaults used across services (e.g. `AWS_REGION`, `MEDIA_S3_BUCKET`, `VIDEO_GEN_S3_BUCKET`; and `PERSONALIZED_TRAILER_PIPELINE_MODE=mock` in `start-backend.sh`).
- Prefer JSON logging via `shared.logging_utils.configure_json_logging("<service>")` early in app startup.
- Artifacts are written under service folders (e.g. `mediaSupplyChain/outputs/<run_id>/`); cleanup helper: `code/scripts/prune_media_artifacts.py` (uses `ARTIFACT_RETENTION_HOURS`).
