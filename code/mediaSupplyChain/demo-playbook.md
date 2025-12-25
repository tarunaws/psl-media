# Media Supply Chain Demo Playbook

A lightweight runbook for showcasing the Media Supply Chain Orchestration use case end-to-end.

## Environment checklist

- All services running via `./start-all.sh` (ensure `media-supply-chain` on port 5011 is healthy).
- Frontend dev server active (`http://localhost:3000`).
- Reference workflow artifacts seeded (see `mediaSupplyChain/README.md`).
- Excel tracker `usecase.xlsx` (row `#5`) updated with PoCs, next steps, and demo-ready date.

## Demo flow

1. **Intro slide / context (optional)**
   - Remind audience of goals: reduce time-to-air, increase visibility, orchestrate ingest→delivery via agentic automation.
2. **Show Excel tracker entry**
   - Highlight `Media Supply Chain Orchestration` row with new PoCs (Virendra / Tarun), next steps, and `Demo-ready: 12 Dec 2025` timeline.
3. **Backend health check (optional CLI)**
   ```bash
   curl http://localhost:5011/health | jq
   ```
   - Call out blueprint count, active runs.
4. **Live Demo page** (`http://localhost:3000/media-supply-chain`)
   - Briefly describe the hero stats (time-to-air, automation coverage).
   - Click **"Run reference workflow"**.
   - Point out toast + stage cards shifting from pending → running → completed in seconds.
   - Scroll through **Service health checks** (shows `/scene-summarization` and `/content-moderation` statuses).
   - Review **Deliverables & insights** (distribution channels, manifest path, deliverable readiness).
   - In the sidebar, show run history and select an older run (if available) to compare timelines.
5. **Artifacts deep dive (optional)**
   - Open `mediaSupplyChain/outputs/<run_id>/01_ingest_manifest.json` etc. to show real data.

## Follow-up assets

- Capture screen recording (Loom) of the above flow.
- Export screenshot of the Live Demo timeline for slides.
- Use `mediaSupplyChain/README.md` as appendix material.

## Talking points

- Agentic pipeline reuses existing microservices (scene summarization, synthetic voiceover) via health checks and voiceover calls.
- Deterministic blueprint means consistent story while still reflecting real service statuses.
- Extendable: add more stages (transcode, ad insertion) by editing `blueprints/reference.json`.
- UI focuses on observability: metrics, deliverables, service health, and history all in one place.
