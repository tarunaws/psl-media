#!/bin/bash

# Semantic Search - Test Script
# This script helps you test the semantic search service

BACKEND_URL="http://localhost:5008"

echo "🧪 Testing Semantic Video Search Service"
echo "========================================"
echo ""

# Test 1: Health Check
echo "Test 1: Health Check"
echo "--------------------"
response=$(curl -s -w "\nHTTP_CODE:%{http_code}" "$BACKEND_URL/health")
http_code=$(echo "$response" | grep "HTTP_CODE" | cut -d: -f2)
body=$(echo "$response" | sed '/HTTP_CODE/d')

if [ "$http_code" = "200" ]; then
    echo "✅ Service is healthy"
    echo "$body" | jq .
else
    echo "❌ Health check failed (HTTP $http_code)"
    exit 1
fi
echo ""

# Test 2: List Videos (should be empty initially)
echo "Test 2: List Videos"
echo "-------------------"
response=$(curl -s "$BACKEND_URL/videos")
count=$(echo "$response" | jq -r '.total')
echo "📊 Total videos indexed: $count"
if [ "$count" -gt 0 ]; then
    echo "$response" | jq -r '.videos[] | "  - \(.title) (\(.id))"'
else
    echo "  (No videos uploaded yet)"
fi
echo ""

# Test 3: Search (should return error if no videos)
echo "Test 3: Search Test"
echo "-------------------"
search_query="happy moments"
response=$(curl -s -X POST "$BACKEND_URL/search" \
    -H "Content-Type: application/json" \
    -d "{\"query\": \"$search_query\", \"top_k\": 5}")

error=$(echo "$response" | jq -r '.error // empty')
if [ -n "$error" ]; then
    echo "⚠️  Expected: $error"
else
    result_count=$(echo "$response" | jq -r '.results | length')
    echo "✅ Search successful"
    echo "📊 Found $result_count results for '$search_query'"
fi
echo ""

# Test 4: Upload Video (interactive)
echo "Test 4: Upload Video"
echo "--------------------"
echo "To test video upload, run:"
echo ""
echo "  curl -X POST $BACKEND_URL/upload-video \\"
echo "    -F \"video=@/path/to/your/video.mp4\" \\"
echo "    -F \"title=Test Video\" \\"
echo "    -F \"description=Sample video for testing\""
echo ""
echo "Or use the UI at: http://localhost:3000/semantic-search"
echo ""

# Test 5: Service Ports
echo "Test 5: All MediaGenAI Services Status"
echo "--------------------------------------"
services=(
    "5001:AI Subtitle"
    "5002:Image Creation"
    "5003:Synthetic Voiceover"
    "5004:Scene Summarization"
    "5005:Movie Script"
    "5006:Content Moderation"
    "5007:Personalized Trailer"
    "5008:Semantic Search"
)

for service in "${services[@]}"; do
    port=$(echo "$service" | cut -d: -f1)
    name=$(echo "$service" | cut -d: -f2)
    
    if lsof -Pi :$port -sTCP:LISTEN -t >/dev/null 2>&1; then
        echo "✅ $name (port $port) - Running"
    else
        echo "❌ $name (port $port) - Not running"
    fi
done
echo ""

# Summary
echo "📝 Summary"
echo "========="
echo "Service URL: $BACKEND_URL"
echo "Frontend UI: http://localhost:3000/semantic-search"
echo "Logs: tail -f semantic-search.log"
echo ""
echo "Next steps:"
echo "1. Upload a video via UI or curl"
echo "2. Wait for processing (check logs)"
echo "3. Try searching with natural language"
echo ""
