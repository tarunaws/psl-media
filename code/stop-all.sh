#!/bin/bash

# Stop All Services Script
# This script stops backend services and the frontend

echo "🛑 Stopping MediaGenAI Complete Application..."

# Get the project root directory
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Stop frontend
echo "🎨 Stopping frontend application..."
if [ -f "$PROJECT_ROOT/frontend.pid" ]; then
    FRONTEND_PID=$(cat "$PROJECT_ROOT/frontend.pid")
    if ps -p $FRONTEND_PID > /dev/null; then
        echo "🔄 Stopping React development server (PID: $FRONTEND_PID)..."
        kill $FRONTEND_PID
        echo "✅ Frontend stopped"
    else
        echo "⚠️  Frontend process not running"
    fi
    rm -f "$PROJECT_ROOT/frontend.pid"
else
    echo "⚠️  No frontend PID file found"
fi

# Stop backend services
echo ""
echo "🔧 Stopping backend services..."

# Function to stop a service
stop_service() {
    local service_name=$1
    local pid_file="$PROJECT_ROOT/$service_name.pid"
    
    if [ -f "$pid_file" ]; then
        local pid=$(cat "$pid_file")
        if ps -p $pid > /dev/null; then
            echo "🔄 Stopping $service_name (PID: $pid)..."
            kill $pid
            echo "✅ $service_name stopped"
        else
            echo "⚠️  $service_name process not running"
        fi
        rm -f "$pid_file"
    else
        echo "⚠️  No $service_name PID file found"
    fi
}

stop_service "ai-subtitle"
stop_service "image-creation"
stop_service "synthetic-voiceover"
stop_service "scene-summarization"
stop_service "movie-script"
stop_service "content-moderation"
stop_service "personalized-trailer"
stop_service "semantic-search"
stop_service "video-generation"
stop_service "dynamic-ad-insertion"
stop_service "media-supply-chain"
stop_service "interactive-shoppable"
stop_service "highlight-trailer"
stop_service "usecase-visibility"

# Also kill any remaining processes on the ports (backup cleanup)
echo ""
echo "🧹 Cleaning up any remaining processes..."
lsof -ti:3000 2>/dev/null | xargs kill -9 2>/dev/null || true
lsof -ti:5001 2>/dev/null | xargs kill -9 2>/dev/null || true
lsof -ti:5002 2>/dev/null | xargs kill -9 2>/dev/null || true
lsof -ti:5003 2>/dev/null | xargs kill -9 2>/dev/null || true
lsof -ti:5004 2>/dev/null | xargs kill -9 2>/dev/null || true
lsof -ti:5005 2>/dev/null | xargs kill -9 2>/dev/null || true
lsof -ti:5006 2>/dev/null | xargs kill -9 2>/dev/null || true
lsof -ti:5007 2>/dev/null | xargs kill -9 2>/dev/null || true
lsof -ti:5008 2>/dev/null | xargs kill -9 2>/dev/null || true
lsof -ti:5009 2>/dev/null | xargs kill -9 2>/dev/null || true
lsof -ti:5010 2>/dev/null | xargs kill -9 2>/dev/null || true
lsof -ti:5011 2>/dev/null | xargs kill -9 2>/dev/null || true
lsof -ti:5012 2>/dev/null | xargs kill -9 2>/dev/null || true
lsof -ti:5013 2>/dev/null | xargs kill -9 2>/dev/null || true

echo ""
echo "✅ All services stopped!"