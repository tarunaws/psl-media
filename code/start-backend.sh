#!/bin/bash

# Start Backend Services Only
# - AI Subtitle Service (5001)
# - Image Creation Service (5002)
# - Synthetic Voiceover Service (5003)
# - Scene Summarization Service (5004)
# - Movie Script Creation Service (5005)
# - Content Moderation Service (5006)
# - Personalized Trailer Service (5007)
# - Semantic Search Service (5008)
# - Dynamic Ad Insertion Service (5010)

echo "🔧 Starting backend services..."

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_PYTHON="$PROJECT_ROOT/.venv/bin/python"
ENV_FILE="$PROJECT_ROOT/.env"
ENV_LOCAL_FILE="$PROJECT_ROOT/.env.local"

# Ensure services can import shared/ utilities.
export PYTHONPATH="$PROJECT_ROOT:${PYTHONPATH:-}"

# Dynamically build PATH with commonly needed directories
# Prioritize local tools, then system paths
REQUIRED_PATH="/usr/local/bin:/opt/homebrew/bin:$HOME/.nvm/versions/node/v22.20.0/bin:$HOME/Library/Python/3.14/lib/python/site-packages/:$HOME/Library/Python/3.14/bin:/usr/bin:/bin:/usr/sbin:/sbin"

if [ "$PATH" != "$REQUIRED_PATH" ]; then
  echo "ℹ️  Exporting required PATH for BornInCloud Streaming services"
fi
export PATH="$REQUIRED_PATH"

if [ -f "$ENV_FILE" ]; then
  echo "ℹ️  Loading environment from $ENV_FILE"
  set -a
  # shellcheck disable=SC1090
  source "$ENV_FILE"
  set +a
fi

if [ -f "$ENV_LOCAL_FILE" ]; then
  echo "ℹ️  Loading environment from $ENV_LOCAL_FILE"
  set -a
  # shellcheck disable=SC1090
  source "$ENV_LOCAL_FILE"
  set +a
fi

export AWS_REGION="${AWS_REGION:-us-east-1}"

if [ -z "$MEDIA_S3_BUCKET" ] && [ -n "$AWS_S3_BUCKET" ]; then
  MEDIA_S3_BUCKET="$AWS_S3_BUCKET"
fi
export MEDIA_S3_BUCKET="${MEDIA_S3_BUCKET:-mediagenailab}"
export VIDEO_GEN_S3_BUCKET="${VIDEO_GEN_S3_BUCKET:-mediagenai-video-generation}"

# Dynamic Ad Insertion (DAI) defaults
# - Use the same bucket as video-generation unless explicitly overridden.
# - Default to local media serving unless DAI_MEDIA_SOURCE is set to 's3'.
export DAI_S3_BUCKET="${DAI_S3_BUCKET:-$VIDEO_GEN_S3_BUCKET}"
export DAI_MEDIA_SOURCE="${DAI_MEDIA_SOURCE:-local}"

if [ ! -f "$VENV_PYTHON" ]; then
  echo "❌ Virtual environment not found at $PROJECT_ROOT/.venv"
  echo "Please run: python3 -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt"
  exit 1
fi

start_service() {
  local service_name=$1
  local service_dir=$2
  local service_file=$3
  local port=$4

  echo "🔄 Starting $service_name on port $port..."
  cd "$PROJECT_ROOT/$service_dir"
  nohup $VENV_PYTHON $service_file > "../$service_name.log" 2>&1 &
  local pid=$!
  echo $pid > "../$service_name.pid"
  echo "✅ $service_name started with PID $pid"
}

# Start AI Subtitle (5001)
start_service "ai-subtitle" "aiSubtitle" "aiSubtitle.py" "5001"

# Start Image Creation (5002)
start_service "image-creation" "imageCreation" "app.py" "5002"

# Start Synthetic Voiceover (5003)
start_service "synthetic-voiceover" "syntheticVoiceover" "app.py" "5003"

# Start Scene Summarization (5004)
start_service "scene-summarization" "sceneSummarization" "app.py" "5004"

# Start Movie Script Creation (5005)
start_service "movie-script" "movieScriptCreation" "app.py" "5005"

# Start Content Moderation (5006)
start_service "content-moderation" "contentModeration" "app.py" "5006"

# Start Personalized Trailer (5007)
# Temporarily using mock mode for stability (AWS Rekognition causes timeouts)
export PERSONALIZED_TRAILER_PIPELINE_MODE=mock
start_service "personalized-trailer" "personalizedTrailer" "app.py" "5007"


# Start Semantic Search (5008)
start_service "semantic-search" "semanticSearch" "app.py" "5008"

# Start Envid Metadata (5014)
start_service "engro-metadata" "engroMetadata" "app.py" "5014"

# Start AI-Powered Video Generation (5009)
start_service "video-generation" "videoGeneration" "app.py" "5009"

# Start Dynamic Ad Insertion (5010)
start_service "dynamic-ad-insertion" "dynamicAdInsertion" "app.py" "5010"

# Start Media Supply Chain Orchestrator (5011)
start_service "media-supply-chain" "mediaSupplyChain" "app.py" "5011"

# Start Use Case Visibility (5012)
start_service "usecase-visibility" "useCaseVisibility" "app.py" "5012"

# Start Highlight & Trailer (5013)
start_service "highlight-trailer" "highlightTrailer" "app.py" "5013"

echo "🎉 Backend services started!"
echo "\n✅ Backend is ok"
