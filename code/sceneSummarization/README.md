# Scene Summarisation Service

This Flask microservice ingests images or short video clips, extracts rich scene metadata with the configured vision service, generates narrative recaps with the configured language model runtime, and produces a ready-to-use voiceover track via neural speech synthesis.

## Features

- **Object, activity, and scene detection** powered by computer-vision labels
- **Facial analysis** for emotions, age range, and accessories
- **Celebrity recognition** (when permitted by your cloud configuration)
- **Text detection** to capture signage, subtitles, or on-screen titles
- **Context inference** such as indoor/outdoor, action vs. dialogue, and lighting hints
- **GenAI summarisation** via a managed language model returning natural language plus SSML
- **Voiceover synthesis** delivered in MP3 using the configured neural speech engine
- RESTful endpoints for summary retrieval and audio streaming

## Requirements

- Python 3.10+
- Cloud credentials with access to the configured vision, text-generation, and speech services
- `ffmpeg` CLI available on the system `PATH`
- Virtual environment seeded with project-level `requirements.txt`

## Environment Variables

| Variable | Purpose | Default |
|----------|---------|---------|
| `BEDROCK_REGION` | Region for Bedrock runtime | `us-east-1` | 
| `REKOGNITION_REGION` | Region for Rekognition APIs | `BEDROCK_REGION` |
| `POLLY_REGION` | Region for Polly synthesis | `BEDROCK_REGION` |
| `SCENE_SUMMARY_MODEL_ID` | Bedrock model ID for summarisation | `meta.llama3-70b-instruct-v1:0` |
| `SCENE_SUMMARY_VOICE_ID` | Default Polly voice | `Joanna` |
| `SCENE_SUMMARY_MAX_TOKENS` | Max tokens for Bedrock generation | `600` |
| `SCENE_SUMMARY_TEMPERATURE` | Temperature for Bedrock generation | `0.4` |
| `SCENE_SUMMARY_TOP_P` | Top-p value for Bedrock generation | `0.9` |
| `CORS_ALLOWED_ORIGIN` / `CORS_ALLOWED_ORIGINS` | Additional allowed origins for CORS (comma-separated) | Localhost variants |
| `SCENE_SUMMARY_S3_BUCKET` | S3 bucket for storing uploaded videos prior to analysis | _unset_ |
| `SCENE_SUMMARY_S3_PREFIX` | Optional key prefix for uploaded media | `scene-summaries/` |
| `SCENE_SUMMARY_FRAME_STRIDE_SECONDS` | Seconds between sampled frames when analysing video | `1.7` |
| `SCENE_SUMMARY_MAX_FRAMES` | Upper bound on sampled frames per video | `120` |
| `REACT_APP_SCENE_TIMEOUT_MS` | Frontend fallback timeout (ms) if duration metadata is unavailable | `10800000` |

## Endpoints

- `GET /health` — Service status and configured regions
- `POST /summarize` — Upload a `media` file (image or video) plus optional `voice_id`; returns structured summary JSON and optional audio URL
- `GET /result/<file_id>` — Retrieve stored summary payload for a previous run
- `GET /audio/<file_id>` — Stream/download the synthesised MP3

## Running Locally

```bash
# From the project root (after provisioning the shared virtual environment)
source .venv/bin/activate
export FLASK_APP=sceneSummarization/app.py
export PORT=5004
python sceneSummarization/app.py
```

Alternatively, use the helper scripts:

```bash
./start-backend.sh   # launches all backend services including Scene Summarisation
./stop-backend.sh    # stops them
```

## Notes

- Videos are first persisted to S3 (when `SCENE_SUMMARY_S3_BUCKET` is configured) before frame sampling and analysis.
- Video processing samples frames across the full duration (using ffmpeg) with a configurable stride, yielding dozens of frames for multi-minute clips.
- The frontend automatically sets each scene-analysis request timeout to 1.5× the detected video runtime (falling back to `REACT_APP_SCENE_TIMEOUT_MS` when the duration cannot be read).
- Results are cached under `sceneSummarization/outputs` (JSON metadata) and `sceneSummarization/outputs/audio` (MP3).
- The frontend leverages `REACT_APP_SCENE_API_BASE` to connect to this service on port `5004`.
