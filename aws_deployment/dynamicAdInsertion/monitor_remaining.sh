#!/bin/bash
# Monitor remaining 3 ads

IDS=(
  "44801165-cca2-4360-89ff-2b81e9bd8e12"  # travel
  "c5490916-79cc-4ae2-92ed-dad79e06112f"  # eco
  "88fca849-e73e-46f0-9ffb-8509aac9a84a"  # luxury
)

NAMES=("travel_booking_ad" "eco_products_ad" "luxury_watch_ad")

echo "Monitoring 3 remaining ads (checking every 20 seconds)..."
echo ""

completed=0
max_checks=20

for ((i=1; i<=max_checks; i++)); do
    echo "[$i/$max_checks] Checking status..."
    
    for idx in 0 1 2; do
        id="${IDS[$idx]}"
        name="${NAMES[$idx]}"
        
        result=$(curl -s "http://localhost:5009/check-status/$id" 2>/dev/null)
        stat=$(echo "$result" | python3 -c "import sys,json; print(json.load(sys.stdin).get('status','error'))" 2>/dev/null)
        
        if [ "$stat" = "completed" ]; then
            echo "  ✅ $name: COMPLETED"
        elif [ "$stat" = "failed" ]; then
            echo "  ❌ $name: FAILED"
        else
            echo "  ⏳ $name: $stat"
        fi
    done
    
    # Check if all complete
    all_done=$(curl -s "http://localhost:5009/check-status/${IDS[0]}" 2>/dev/null | grep -c "completed")
    all_done=$((all_done + $(curl -s "http://localhost:5009/check-status/${IDS[1]}" 2>/dev/null | grep -c "completed")))
    all_done=$((all_done + $(curl -s "http://localhost:5009/check-status/${IDS[2]}" 2>/dev/null | grep -c "completed")))
    
    if [ "$all_done" -eq 3 ]; then
        echo ""
        echo "🎉 All 3 ads completed!"
        break
    fi
    
    echo ""
    sleep 20
done

echo ""
echo "Final Results:"
echo "=============="
for idx in 0 1 2; do
    id="${IDS[$idx]}"
    name="${NAMES[$idx]}"
    echo ""
    echo "$name ($id):"
    curl -s "http://localhost:5009/check-status/$id" | python3 -m json.tool | grep -E "(status|video_url)" | head -2
done
