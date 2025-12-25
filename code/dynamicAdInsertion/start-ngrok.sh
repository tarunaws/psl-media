#!/bin/bash

# Start ngrok tunnel for Dynamic Ad Insertion Service
# Exposes local ADS (port 5010) to the internet for MediaTailor

set -e

echo "🌐 Starting ngrok tunnel for Dynamic Ad Insertion"
echo "================================================="

# Check if ngrok is installed
if ! command -v ngrok &> /dev/null; then
    echo "❌ ngrok is not installed"
    echo ""
    echo "Install ngrok:"
    echo "  macOS:  brew install ngrok"
    echo "  Linux:  snap install ngrok"
    echo ""
    echo "Then configure your auth token:"
    echo "  ngrok config add-authtoken YOUR_TOKEN"
    echo "  Get token from: https://dashboard.ngrok.com/get-started/your-authtoken"
    exit 1
fi

# Check if local ADS is running
echo ""
echo "🔍 Checking if local Ad Decision Server is running..."
if curl -s -f http://localhost:5010/health > /dev/null 2>&1; then
    echo "✅ Local ADS is running on port 5010"
else
    echo "❌ Local ADS is NOT running on port 5010"
    echo ""
    echo "Start the service first:"
    echo "  cd \$(pwd)/../../  # Navigate to project root"
    echo "  .venv/bin/python dynamicAdInsertion/app.py"
    echo ""
    read -p "Continue anyway? (y/N): " CONTINUE
    if [[ ! "$CONTINUE" =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

echo ""
echo "📡 Starting ngrok tunnel..."
echo ""
echo "┌─────────────────────────────────────────────────────────┐"
echo "│  IMPORTANT: Keep this terminal window open!            │"
echo "│  ngrok must stay running for MediaTailor to work       │"
echo "└─────────────────────────────────────────────────────────┘"
echo ""
echo "Press Ctrl+C to stop the tunnel"
echo ""
echo "Web Interface: http://localhost:4040"
echo "  (View real-time requests from MediaTailor)"
echo ""
echo "─────────────────────────────────────────────────────────"
echo ""

# Start ngrok
ngrok http 5010 \
    --log=stdout \
    --log-level=info \
    --region=us
