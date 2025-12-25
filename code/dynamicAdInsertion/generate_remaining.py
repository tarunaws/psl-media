#!/usr/bin/env python3
"""
Generate the remaining 3 advertisements
"""
import os
import requests
import time
import json

VIDEO_GEN_URL = "http://localhost:5009"

# Remaining 3 ads
REMAINING_ADS = {
    "travel_booking_ad": "Adventurous travel montage with exotic destinations, mountain peaks, tropical beaches, ancient temples, aerial views",
    "eco_products_ad": "Serene eco-friendly products with green nature, sustainable packaging, solar panels, wind turbines, natural lighting",
    "luxury_watch_ad": "Sophisticated luxury watch extreme close-up with intricate mechanics, gold diamond details, black velvet background, elegant rotation"
}

print("=" * 70)
print("🎬 GENERATING REMAINING 3 ADVERTISEMENTS")
print("=" * 70)
print()

# Start generations
jobs = []
for ad_id, prompt in REMAINING_ADS.items():
    print(f"🎥 Starting {ad_id}...")
    try:
        response = requests.post(
            f"{VIDEO_GEN_URL}/generate-video",
            json={"prompt": prompt, "duration": 6},
            timeout=10
        )
        
        if response.status_code == 202:
            data = response.json()
            gen_id = data.get('id')
            jobs.append({
                "ad_id": ad_id,
                "generation_id": gen_id,
                "prompt": prompt
            })
            print(f"   ✓ Started (ID: {gen_id})")
        else:
            print(f"   ✗ Failed: HTTP {response.status_code}")
    except Exception as e:
        print(f"   ✗ Error: {e}")
    
    time.sleep(2)

print(f"\n✓ Started {len(jobs)}/3 generations")
print("\n" + "=" * 70)
print("MONITORING PROGRESS")
print("=" * 70)
print()

# Monitor
completed = []
max_wait = 600  # 10 minutes
start = time.time()

while len(completed) < len(jobs) and (time.time() - start) < max_wait:
    for job in jobs:
        if job in completed:
            continue
        
        try:
            response = requests.get(
                f"{VIDEO_GEN_URL}/check-status/{job['generation_id']}",
                timeout=5
            )
            
            if response.status_code == 200:
                data = response.json()
                status = data.get("status")
                
                if status == "completed":
                    job["video_url"] = data.get("video_url", "")
                    completed.append(job)
                    print(f"✅ {job['ad_id']}: COMPLETED")
                elif status == "failed":
                    job["error"] = data.get("message", "Unknown")
                    completed.append(job)
                    print(f"❌ {job['ad_id']}: FAILED")
        except:
            pass
    
    if len(completed) < len(jobs):
        remaining = len(jobs) - len(completed)
        elapsed = int(time.time() - start)
        print(f"⏳ {remaining} ads still processing... ({elapsed}s)")
        time.sleep(15)

# Results
print("\n" + "=" * 70)
print("RESULTS")
print("=" * 70)

successful = [j for j in completed if "video_url" in j]
print(f"\n✅ Completed: {len(successful)}/3")

if successful:
    print("\nGeneration IDs to update in app.py:\n")
    for job in successful:
        print(f'{job["ad_id"]}:')
        print(f'  generation_id: "{job["generation_id"]}"')
        print(f'  video_url: "http://localhost:5009/video/{job["generation_id"]}"')
        print()

# Save
# Use relative path from script location
script_dir = os.path.dirname(os.path.abspath(__file__))
results_file = os.path.join(script_dir, "remaining_ads.json")
with open(results_file, 'w') as f:
    json.dump({
        "completed": successful,
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
    }, f, indent=2)

print(f"💾 Results saved to: remaining_ads.json")
print("=" * 70)
