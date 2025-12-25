# MediaGenAI - AI Coding Assistant Instructions

## Architecture Overview

MediaGenAI is a **microservices-based media AI platform** with 10+ Flask backend services and a React frontend. Each service runs independently on dedicated ports (5001-5007, 3000 for frontend) and handles a specific media processing capability: subtitle generation, voiceover synthesis, scene analysis, personalized trailers, etc.

**Key architectural principle:** Services are isolated Python apps with service-specific dependencies, but share common utilities via the `shared/` module using `PYTHONPATH` injection.

### Service Boundaries & Ports

```
aiSubtitle/             → Port 5001 (AWS Transcribe)
imageCreation/          → Port 5002 (AWS Bedrock image gen)
syntheticVoiceover/     → Port 5003 (AWS Polly + Bedrock SSML)
sceneSummarization/     → Port 5004 (Rekognition + Bedrock narrative)
movieScriptCreation/    → Port 5005 (Bedrock screenplay gen)
contentModeration/      → Port 5006 (Rekognition moderation)
personalizedTrailer/    → Port 5007 (multi-stage trailer pipeline)
semanticSearch/         → Port 5008 (Bedrock Titan embeddings + vector search)
videoGeneration/        → Port 5009 (Amazon Nova Reel video gen)
dynamicAdInsertion/     → Port 5010 (VAST/VMAP ad insertion)
mediaSupplyChain/       → Port 5011 (AWS Media Supply Chain workflows)
useCaseVisibility/      → Port 5012 (Use case documentation)
highlightTrailer/       → Port 5013 (Automated highlight reels)
interactiveShoppable/   → Port 5055 (Interactive video overlays)
frontend/               → Port 3000 (React SPA)
```

## Critical Developer Workflows

### Starting/Stopping Services

Always use the orchestration scripts from `code/`:

```bash
./start-all.sh      # Start all backend services + frontend
./stop-all.sh       # Stop all running services
./start-backend.sh  # Backend only (for frontend dev)
./stop-backend.sh   # Stop backend only
```

**PATH requirement:** Services require `ffmpeg` and Python toolchain. The startup scripts auto-export:
```bash
export PATH="/usr/local/bin/ffmpeg/:/opt/homebrew/bin/:$HOME/.nvm/versions/node/v22.20.0/bin:..."
```

For manual service runs, export this PATH first or services will fail silently.

### Dependency Management

**Single virtual environment pattern:** All services share one Python venv at `code/.venv/`:

```bash
# Initial setup (one-time):
cd code/
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

**Service execution:** Startup scripts use absolute path to venv Python:
```bash
VENV_PYTHON="$PROJECT_ROOT/.venv/bin/python"
nohup $VENV_PYTHON app.py > "../service-name.log" 2>&1 &
```

Individual service `requirements.txt` files are rare - most dependencies live in workspace root `code/requirements.txt`.

### Environment Configuration

**Two-layer .env pattern:**
- `code/.env` - Base config (versioned, no secrets)
- `code/.env.local` - Local secrets (gitignored, overrides base)

All services call `shared.env_loader.load_environment()` at startup to load both layers.

**Critical env vars pattern:**
- AWS credentials: `AWS_REGION`, `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`
- Service-specific buckets: `SCENE_SUMMARY_S3_BUCKET`, `PERSONALIZED_TRAILER_S3_BUCKET`, etc.
- Bedrock models: `MOVIE_SCRIPT_MODEL_ID` (default: `meta.llama3-70b-instruct-v1:0`)
- Frontend API bases: `REACT_APP_SUBTITLE_API_BASE`, `REACT_APP_SCENE_API_BASE`, etc.

### Mock vs. AWS Mode

Services default to **mock mode** for local dev without AWS costs. Switch to AWS mode via env vars:

```bash
PERSONALIZED_TRAILER_PIPELINE_MODE=aws  # Enables real AWS services
SUBTITLE_VIDEO_ENGINE=ffmpeg            # Local ffmpeg (default) vs AWS MediaConvert
```

Mock mode provides realistic data flows for UI development.

## Shared Utilities (`code/shared/`)

All services must import from `shared/` for cross-cutting concerns:

- **`env_loader.load_environment()`** - Load .env + .env.local (call at app startup)
- **`secret_loader.load_aws_secret_into_env()`** - Hydrate secrets from AWS Secrets Manager
- **`logging_utils.configure_json_logging()`** - Structured JSON logging for observability
- **`artifact_cleanup.purge_stale_artifacts()`** - Auto-cleanup of temp files/uploads

**Import pattern:** `from shared.env_loader import load_environment`

Services **must** set `PYTHONPATH` to include project root:
```python
# startup scripts handle this:
export PYTHONPATH="$PROJECT_ROOT:${PYTHONPATH:-}"
```

## Frontend-Backend Integration

### API Discovery Pattern

Frontend uses environment-aware API base resolution:

```javascript
// Pattern: Check REACT_APP_*_API_BASE, fallback to localhost:<port>
const envValue = process.env.REACT_APP_SUBTITLE_API_BASE;
const apiBase = envValue || 'http://localhost:5001';
```

For LAN testing, frontend auto-switches to current hostname:
```javascript
// Example from SyntheticVoiceover.js
const currentHost = window.location.hostname;
return `http://${currentHost}:5003`;  // Handles .local domains
```

### CORS Configuration

Backend services use Flask-CORS with explicit origins:

```python
# Pattern from most services:
allowed_origins = os.getenv('CORS_ALLOWED_ORIGINS', 'http://localhost:3000').split(',')
CORS(app, origins=allowed_origins, supports_credentials=True)
```

### Frontend Proxy Configuration

The React dev server uses `setupProxy.js` to route API calls to backend services:

```javascript
// Pattern: Route specific API paths to backend ports
app.use('/api/highlight-trailer', createProxyMiddleware({
  target: 'http://localhost:5013',
  changeOrigin: true,
  logLevel: 'debug',
}));
```

**Note:** Proxy routes must be ordered with most specific paths first to avoid route collisions.

## Project-Specific Conventions

### File Structure Patterns

Each service follows consistent structure:
```
<serviceName>/
├── app.py                    # Flask entrypoint (or <service>.py for older services like aiSubtitle.py)
├── <service>_service.py      # Business logic (if complex)
├── README.md                 # Service-specific docs
├── requirements.txt          # Service dependencies (rare, most in workspace root)
├── uploads/                  # Incoming media
├── outputs/                  # Generated artifacts
└── <service>.log             # Runtime logs (gitignored)
```

**Note:** Original services use non-standard naming (e.g., `aiSubtitle.py` instead of `app.py`). Newer services follow `app.py` convention.

### Video Processing Patterns

**Frame sampling** (Scene Summarization):
```python
# Extract frames using ffmpeg with configurable stride
SCENE_SUMMARY_FRAME_STRIDE_SECONDS=1.7  # Sample every 1.7s
SCENE_SUMMARY_MAX_FRAMES=120            # Cap at 120 frames
```

**Audio extraction** (AI Subtitle, Synthetic Voiceover):
```bash
# Standard ffmpeg command pattern:
ffmpeg -i video.mp4 -vn -ar 44100 -ac 2 -b:a 192k audio.mp3
```

### Bedrock LLM Integration

Services use consistent Bedrock invocation pattern:

```python
import boto3
bedrock = boto3.client('bedrock-runtime', region_name=bedrock_region)
response = bedrock.invoke_model(
    modelId=os.getenv('SCENE_SUMMARY_MODEL_ID', 'meta.llama3-70b-instruct-v1:0'),
    body=json.dumps({
        'prompt': prompt,
        'max_gen_len': 600,
        'temperature': 0.4,
        'top_p': 0.9
    })
)
```

Model IDs are env-driven: `MOVIE_SCRIPT_MODEL_ID`, `SCENE_SUMMARY_MODEL_ID`, `VOICEOVER_MODEL_ID`.

### Personalized Trailer Multi-Stage Pipeline

The trailer service orchestrates **6 AWS services** in sequence:

1. **S3 Upload** - Store hero video
2. **Rekognition** - Extract faces, emotions, objects
3. **Personalize/SageMaker** - Rank scenes by viewer profile
4. **MediaConvert** - Stitch top scenes into variants (15s, 30s, 60s)
5. **Transcribe + Translate** - Generate localized captions
6. **Lambda** - Emit completion events

Each stage has mock fallback. Check logs for `Using mock <stage> pipeline`.

### Semantic Search Architecture

The semantic search service (Port 5008) uses a multi-modal approach:

```python
# Video analysis pipeline:
1. Frame extraction (ffmpeg)
2. Rekognition: objects, scenes, faces, emotions, on-screen text
3. Transcribe: audio-to-text conversion
4. Bedrock Titan: generate vector embeddings from aggregated metadata
5. In-memory vector index for similarity search

# Query flow:
Query → Bedrock embedding → Cosine similarity → Ranked results
```

**Critical env vars:** `SEMANTIC_SEARCH_BUCKET`, `BEDROCK_REGION`

### Video Generation with Nova Reel

Video Generation service (Port 5009) uses Amazon Nova Reel model:

```python
# Default configuration pattern:
VIDEO_GEN_ENSURE_AUDIO=1              # Always include audio track
VIDEO_GEN_AUDIO_KIND=voiceover        # voiceover | music | ambient
VIDEO_GEN_AUDIO_TONE_VOLUME_DB=-12    # Background audio level
VIDEO_GEN_AD_VOICEOVER_ENABLED=1      # Generate ad-style narration
```

Voiceover generation uses **Bedrock → SSML → Polly** pipeline for natural speech.

## Testing & Debugging

### Process Management

Services run as background processes with PID tracking:

```bash
# PID files stored at code/<service-name>.pid
cat code/ai-subtitle.pid         # Get process ID
ps aux | grep aiSubtitle         # Check if running
kill $(cat code/ai-subtitle.pid) # Manual stop
```

**Service lifecycle:**
1. Start: `nohup $VENV_PYTHON app.py > "../service.log" 2>&1 &`
2. PID capture: `echo $! > "../service.pid"`
3. Stop: Read PID file and send kill signal

### Log Files

Services write to `code/<service>.log`:
```bash
tail -f code/ai-subtitle.log
tail -f code/personalized-trailer.log
```

Logs use structured JSON when `configure_json_logging()` is called.

### Health Endpoints

All services expose `/health`:
```bash
curl http://localhost:5001/health  # AI Subtitle
curl http://localhost:5007/health  # Personalized Trailer
```

Health checks include AWS connectivity status and pipeline mode.

### Common Issues

**"Cannot reach service"** - Check PID files:
```bash
cat code/ai-subtitle.pid    # Should contain running process ID
ps aux | grep aiSubtitle    # Verify process
```

**ffmpeg not found** - Ensure PATH includes `/usr/local/bin/ffmpeg/`:
```bash
which ffmpeg
export PATH="/usr/local/bin/ffmpeg/:$PATH"
```

**AWS credentials** - Services fail gracefully to mock mode. Check logs:
```
"aws_connectivity": {"rekognition": false, "s3": false}
```

## Key Files to Reference

- [code/SERVICES_README.md](code/SERVICES_README.md) - Service management guide
- [code/start-all.sh](code/start-all.sh) - Orchestration script with PATH setup
- [code/.env.local](code/.env.local) - Local environment template
- [code/shared/env_loader.py](code/shared/env_loader.py) - Environment loading logic
- [code/personalizedTrailer/README.md](code/personalizedTrailer/README.md) - Multi-stage pipeline docs
- [code/sceneSummarization/README.md](code/sceneSummarization/README.md) - Frame sampling patterns

## When Adding New Services

1. **Create service directory** under `code/` with standard structure
2. **Add app.py** with Flask app, call `shared.env_loader.load_environment()` early
3. **Update start-all.sh** to include new service in startup sequence
4. **Add port mapping** to SERVICES_README.md and this file
5. **Create README.md** documenting service-specific env vars and endpoints
6. **Add REACT_APP_*_API_BASE** to frontend .env and proxy config if needed
7. **Test mock mode** before implementing AWS integration
