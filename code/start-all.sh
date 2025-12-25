#!/bin/bash

# Start All Services Script
# This script starts all backend services and the frontend

echo "🚀 Starting MediaGenAI Complete Application..."

# Get the project root directory
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_PYTHON="$PROJECT_ROOT/.venv/bin/python"

# Dynamically build PATH with commonly needed directories
# Prioritize local tools, then system paths
REQUIRED_PATH="/usr/local/bin:/opt/homebrew/bin:$HOME/.nvm/versions/node/v22.20.0/bin:$HOME/Library/Python/3.14/lib/python/site-packages/:$HOME/Library/Python/3.14/bin:/usr/bin:/bin:/usr/sbin:/sbin"

# Add ffmpeg if it exists in /usr/local/bin/ffmpeg
if [ -d "/usr/local/bin/ffmpeg" ]; then
    REQUIRED_PATH="/usr/local/bin/ffmpeg/:$REQUIRED_PATH"
fi

if [ "$PATH" != "$REQUIRED_PATH" ]; then
    echo "ℹ️  Exporting required PATH for MediaGenAI services"
fi
export PATH="$REQUIRED_PATH"

# Ensure all services can import the shared helpers without per-app sys.path hacks
export PYTHONPATH="$PROJECT_ROOT:${PYTHONPATH:-}"

# Ensure default engine selections prefer local ffmpeg processing
export SCENE_SUMMARY_VIDEO_ENGINE="${SCENE_SUMMARY_VIDEO_ENGINE:-ffmpeg}"
export SUBTITLE_VIDEO_ENGINE="${SUBTITLE_VIDEO_ENGINE:-ffmpeg}"

# Check if virtual environment exists
if [ ! -f "$VENV_PYTHON" ]; then
    echo "❌ Virtual environment not found at $PROJECT_ROOT/.venv"
    echo "Please run: python3 -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt"
    exit 1
fi

# Function to start a service in the background
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


# Start backend services
echo "🔧 Starting backend services..."

# Start AI Subtitle Service (Port 5001)
start_service "ai-subtitle" "aiSubtitle" "aiSubtitle.py" "5001"

# Start Image Creation Service (Port 5002)
start_service "image-creation" "imageCreation" "app.py" "5002"

# Start Synthetic Voiceover Service (Port 5003)
start_service "synthetic-voiceover" "syntheticVoiceover" "app.py" "5003"
# Start Scene Summarization Service (Port 5004)
start_service "scene-summarization" "sceneSummarization" "app.py" "5004"
# Start Movie Script Creation Service (Port 5005)
start_service "movie-script" "movieScriptCreation" "app.py" "5005"
# Start Content Moderation Service (Port 5006)
start_service "content-moderation" "contentModeration" "app.py" "5006"
start_service "personalized-trailer" "personalizedTrailer" "app.py" "5007"
start_service "semantic-search" "semanticSearch" "app.py" "5008"
start_service "video-generation" "videoGeneration" "app.py" "5009"
start_service "dynamic-ad-insertion" "dynamicAdInsertion" "app.py" "5010"
start_service "media-supply-chain" "mediaSupplyChain" "app.py" "5011"
start_service "interactive-shoppable" "interactiveShoppable/backend" "app.py" "5055"
start_service "usecase-visibility" "useCaseVisibility" "app.py" "5012"

# Start Highlight & Trailer Service (Port 5013)
start_service "highlight-trailer" "highlightTrailer" "app.py" "5013"
echo "   • Highlight & Trailer Service: http://localhost:5013"
echo "   • Highlight & Trailer logs: $PROJECT_ROOT/highlight-trailer.log"

# Wait a moment for backends to initialize
echo "⏳ Waiting for backend services to initialize..."
sleep 3

# Start frontend (if npm is available)
echo ""
if ! command -v npm >/dev/null 2>&1; then
    echo "⚠️  npm is not installed or not on PATH. Skipping frontend startup."
    echo "👉 Install Node.js (which bundles npm) and rerun ./start-all.sh to launch the React app."
else
    echo "🎨 Starting frontend application..."
    cd "$PROJECT_ROOT/frontend"

    # Check if node_modules exists
    if [ ! -d "node_modules" ]; then
        echo "📦 Installing frontend dependencies..."
        npm install
    fi

    # Start the React development server
    echo "🔄 Starting React development server on port 3000..."
    npm start &
    FRONTEND_PID=$!
    echo $FRONTEND_PID > "../frontend.pid"
fi

echo ""
echo "🎉 All services started successfully!"
echo ""
echo "🌐 Application URLs:"
if command -v npm >/dev/null 2>&1; then
    echo "   • Frontend (React App): http://localhost:3000"
else
    echo "   • Frontend (React App): Skipped (install Node/npm to enable)"
fi
echo "   • AI Subtitle Service: http://localhost:5001"
echo "   • Image Creation Service: http://localhost:5002"
echo "   • Synthetic Voiceover Service: http://localhost:5003"
echo "   • Scene Summarization Service: http://localhost:5004"
echo "   • Movie Script Creation Service: http://localhost:5005"
echo "   • Content Moderation Service: http://localhost:5006"
echo "   • Personalized Trailer Service: http://localhost:5007"
echo "   • Semantic Search Service: http://localhost:5008"
echo "   • Video Generation Service: http://localhost:5009"
echo "   • Dynamic Ad Insertion Service: http://localhost:5010"
echo "   • Media Supply Chain Service: http://localhost:5011"
echo "   • Interactive & Shoppable Service: http://localhost:5055"
echo "   • Use Case Visibility Service: http://localhost:5012"
echo ""
echo "📝 Log files:"
echo "   • AI Subtitle logs: $PROJECT_ROOT/ai-subtitle.log"
echo "   • Image Creation logs: $PROJECT_ROOT/image-creation.log"
echo "   • Synthetic Voiceover logs: $PROJECT_ROOT/synthetic-voiceover.log"
echo "   • Scene Summarization logs: $PROJECT_ROOT/scene-summarization.log"
echo "   • Movie Script Creation logs: $PROJECT_ROOT/movie-script.log"
echo "   • Content Moderation logs: $PROJECT_ROOT/content-moderation.log"
echo "   • Personalized Trailer logs: $PROJECT_ROOT/personalized-trailer.log"
echo "   • Semantic Search logs: $PROJECT_ROOT/semantic-search.log"
echo "   • Video Generation logs: $PROJECT_ROOT/video-generation.log"
echo "   • Dynamic Ad Insertion logs: $PROJECT_ROOT/dynamic-ad-insertion.log"
echo "   • Media Supply Chain logs: $PROJECT_ROOT/media-supply-chain.log"
echo "   • Interactive & Shoppable logs: $PROJECT_ROOT/interactive-shoppable.log"
echo "   • Use Case Visibility logs: $PROJECT_ROOT/usecase-visibility.log"
echo ""
echo "🛑 To stop all services, run: ./stop-all.sh"

echo "\n✅ Frontend is ok"
echo "✅ Backend is ok"