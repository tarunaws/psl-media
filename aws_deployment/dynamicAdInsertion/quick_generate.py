#!/usr/bin/env python3
"""
Quick ad generator - generates 4 sample ads to demonstrate the feature.
"""

import os
import requests
import time
import json

VIDEO_GEN_URL = "http://localhost:5009"

# Priority ads to generate first
PRIORITY_ADS = {
    "tech_gadget_ad": "A sleek 10-second advertisement showing a futuristic smartphone with holographic display, rotating in space with blue neon lighting and particle effects",
    "fitness_equipment_ad": "A motivational 10-second fitness ad showing modern gym equipment, people exercising with determination, dynamic camera movements",
    "gaming_console_ad": "An exciting 10-second gaming console ad with next-gen graphics, controller close-ups, neon cyberpunk lighting",
    "luxury_watch_ad": "A sophisticated 10-second luxury watch ad with extreme close-up of premium timepiece, gold details, elegant rotation"
}

def generate_ad(ad_id, prompt):
    """Generate a single ad."""
    print(f"🎬 Generating {ad_id}...")
    try:
        response = requests.post(
            f"{VIDEO_GEN_URL}/generate-video",
            json={"prompt": prompt, "duration": 6},
            timeout=10
        )
        
        if response.status_code == 202:
            data = response.json()
            gen_id = data.get('id')
            print(f"✓ Started: {gen_id}")
            return {"ad_id": ad_id, "generation_id": gen_id}
        else:
            print(f"✗ Failed: {response.status_code}")
            return None
    except Exception as e:
        print(f"✗ Error: {e}")
        return None

def check_status(gen_id):
    """Check generation status."""
    try:
        response = requests.get(f"{VIDEO_GEN_URL}/check-status/{gen_id}", timeout=5)
        if response.status_code == 200:
            return response.json()
        return {"status": "error"}
    except:
        return {"status": "error"}

print("=" * 60)
print("🎥 Generating 4 Priority Advertisements")
print("=" * 60)

# Start all generations
jobs = []
for ad_id, prompt in PRIORITY_ADS.items():
    job = generate_ad(ad_id, prompt)
    if job:
        jobs.append(job)
    time.sleep(2)

print(f"\n✓ Started {len(jobs)} generations\n")

# Monitor progress
print("Monitoring (checking every 30s, max 25 minutes)...")
completed = []
max_wait = 1500  # 25 minutes
start = time.time()

while len(completed) < len(jobs) and (time.time() - start) < max_wait:
    for job in jobs:
        if job in completed:
            continue
        
        status = check_status(job["generation_id"])
        if status.get("status") == "completed":
            job["video_url"] = status.get("video_url", "")
            completed.append(job)
            print(f"✓ {job['ad_id']}: DONE - {job['video_url']}")
        elif status.get("status") == "failed":
            job["error"] = status.get("message", "Failed")
            completed.append(job)
            print(f"✗ {job['ad_id']}: FAILED")
    
    if len(completed) < len(jobs):
        remaining = len(jobs) - len(completed)
        elapsed = int(time.time() - start)
        print(f"⏳ {remaining} pending... ({elapsed}s elapsed)")
        time.sleep(30)

# Save results
results = {
    "ads": [j for j in completed if "video_url" in j],
    "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
}

# Use relative path from script location
script_dir = os.path.dirname(os.path.abspath(__file__))
results_file = os.path.join(script_dir, "quick_ads.json")

with open(results_file, "w") as f:
    json.dump(results, f, indent=2)

print("\n" + "=" * 60)
print(f"✓ Completed: {len([j for j in completed if 'video_url' in j])}/{len(jobs)}")
print("=" * 60)

for job in completed:
    if "video_url" in job:
        print(f"\n{job['ad_id']}:")
        print(f"  {job['video_url']}")
