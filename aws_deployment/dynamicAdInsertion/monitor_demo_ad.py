#!/usr/bin/env python3
"""
Quick fix: Generate one demo ad and update the DAI service.
This demonstrates the feature with a real GenAI video.
"""

import requests
import time
import sys

VIDEO_GEN_URL = "http://localhost:5009"
GENERATION_ID = "571659d8-c391-4a2b-88f8-1292a89cd363"

print("🎬 Monitoring demo ad generation...")
print(f"Generation ID: {GENERATION_ID}")
print()

max_wait = 300  # 5 minutes
start = time.time()
last_status = None

while (time.time() - start) < max_wait:
    try:
        response = requests.get(f"{VIDEO_GEN_URL}/check-status/{GENERATION_ID}", timeout=5)
        
        if response.status_code == 200:
            data = response.json()
            status = data.get("status")
            
            if status != last_status:
                print(f"Status: {status}")
                last_status = status
            
            if status == "completed":
                video_url = data.get("video_url", "")
                print(f"\n✅ Video generated successfully!")
                print(f"URL: {video_url}")
                print()
                print("To use this video in DAI:")
                print(f"1. Update dynamicAdInsertion/app.py line ~135")
                print(f'2. Change tech_gadget_ad video_url to:')
                print(f'   "{video_url}"')
                print(f"3. Restart DAI service: lsof -ti:5010 | xargs kill -9 && python dynamicAdInsertion/app.py &")
                sys.exit(0)
            elif status == "failed":
                print(f"\n❌ Generation failed: {data.get('message', 'Unknown error')}")
                sys.exit(1)
        else:
            print(f"HTTP {response.status_code}")
    except Exception as e:
        print(f"Error checking status: {e}")
    
    elapsed = int(time.time() - start)
    sys.stdout.write(f"\r⏳ Waiting... {elapsed}s elapsed")
    sys.stdout.flush()
    time.sleep(10)

print(f"\n⚠️ Timeout after {max_wait}s")
