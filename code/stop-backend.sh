#!/bin/bash

# Stop Backend Services Only
# - AI Subtitle Service (5001)
# - Image Creation Service (5002)
# - Synthetic Voiceover Service (5003)
# - Scene Summarization Service (5004)
# - Movie Script Creation Service (5005)
# - Content Moderation Service (5006)
# - Personalized Trailer Service (5007)
# - Semantic Search Service (5008)

echo "🛑 Stopping backend services..."

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

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

stop_service "video-generation"
stop_service "semantic-search"
stop_service "media-supply-chain"
stop_service "highlight-trailer"
stop_service "usecase-visibility"

echo "🧹 Cleaning up any remaining processes on ports..."
lsof -ti:5001 2>/dev/null | xargs kill -9 2>/dev/null || true
lsof -ti:5002 2>/dev/null | xargs kill -9 2>/dev/null || true
lsof -ti:5003 2>/dev/null | xargs kill -9 2>/dev/null || true
lsof -ti:5004 2>/dev/null | xargs kill -9 2>/dev/null || true
lsof -ti:5005 2>/dev/null | xargs kill -9 2>/dev/null || true
lsof -ti:5006 2>/dev/null | xargs kill -9 2>/dev/null || true
lsof -ti:5007 2>/dev/null | xargs kill -9 2>/dev/null || true
lsof -ti:5008 2>/dev/null | xargs kill -9 2>/dev/null || true
lsof -ti:5009 2>/dev/null | xargs kill -9 2>/dev/null || true
lsof -ti:5011 2>/dev/null | xargs kill -9 2>/dev/null || true
lsof -ti:5012 2>/dev/null | xargs kill -9 2>/dev/null || true
lsof -ti:5013 2>/dev/null | xargs kill -9 2>/dev/null || true

echo "✅ Backend services stopped!"
