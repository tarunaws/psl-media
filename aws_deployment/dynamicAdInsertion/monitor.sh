#!/bin/bash
# Simple monitor for demo ad generation

ID="571659d8-c391-4a2b-88f8-1292a89cd363"
echo "Monitoring video generation: $ID"
echo ""

for i in {1..20}; do
    STATUS=$(curl -s "http://localhost:5009/check-status/$ID" | grep -o '"status":"[^"]*"' | cut -d'"' -f4)
    echo "[$i/20] Status: $STATUS ($(date +%H:%M:%S))"
    
    if [ "$STATUS" = "completed" ]; then
        echo ""
        echo "✅ Video generation complete!"
        curl -s "http://localhost:5009/check-status/$ID" | python3 -m json.tool
        break
    elif [ "$STATUS" = "failed" ]; then
        echo "❌ Generation failed"
        break
    fi
    
    sleep 15
done
