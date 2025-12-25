#!/usr/bin/env python3
"""
Generate all 10 advertisements for Dynamic Ad Insertion
"""
import os
import requests
import time
import json
import sys

VIDEO_GEN_URL = "http://localhost:5009"

# All 10 ad prompts optimized for Amazon Nova Reel
ADS = {
    "tech_gadget_ad": "A sleek futuristic smartphone with holographic display rotating in space with blue neon lighting and particle effects, cinematic product photography",
    "sports_drink_ad": "Dynamic sports drink advertisement with athletes in action, energy bursts, liquid splashes with vibrant colors, high-energy cinematography",
    "streaming_service_ad": "Cinematic streaming service advertisement with movie scenes, popcorn, cozy home theater, dramatic lighting and genre transitions",
    "family_vacation_ad": "Heartwarming family at a beach resort, children playing, sunset views, joyful moments, bright cheerful atmosphere",
    "fitness_equipment_ad": "Motivational gym equipment advertisement with people exercising intensely, sweat droplets, powerful movements, dramatic lighting",
    "gaming_console_ad": "Exciting gaming console with next-gen graphics, controller close-ups, explosive game scenes, neon cyberpunk lighting",
    "gourmet_food_ad": "Delicious gourmet food with chef preparing exquisite dishes, steam rising, elegant plating, warm restaurant ambiance",
    "travel_booking_ad": "Adventurous travel montage with exotic destinations, mountain peaks, tropical beaches, ancient temples, aerial views",
    "eco_products_ad": "Serene eco-friendly products with green nature, sustainable packaging, solar panels, wind turbines, natural lighting",
    "luxury_watch_ad": "Sophisticated luxury watch extreme close-up with intricate mechanics, gold diamond details, black velvet background, elegant rotation"
}

def generate_all():
    """Start all ad generations"""
    print("=" * 80)
    print("🎬 GENERATING 10 ADVERTISEMENTS WITH AMAZON NOVA REEL")
    print("=" * 80)
    print(f"\nStarting {len(ADS)} video generations...")
    print("Each video takes ~1-2 minutes. Total time: 10-20 minutes\n")
    
    jobs = []
    
    # Start all generations
    for ad_id, prompt in ADS.items():
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
        
        time.sleep(2)  # Small delay between requests
    
    print(f"\n✓ Started {len(jobs)}/{len(ADS)} generations")
    print("\n" + "=" * 80)
    print("MONITORING PROGRESS")
    print("=" * 80)
    print("Checking status every 30 seconds...\n")
    
    # Monitor progress
    completed = []
    failed = []
    max_wait = 1800  # 30 minutes
    start = time.time()
    
    while len(completed) + len(failed) < len(jobs) and (time.time() - start) < max_wait:
        for job in jobs:
            if job in completed or job in failed:
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
                        job["s3_path"] = job["video_url"].split(".com/")[-1] if ".com/" in job["video_url"] else ""
                        completed.append(job)
                        print(f"✅ {job['ad_id']}: COMPLETED")
                    elif status == "failed":
                        job["error"] = data.get("message", "Unknown error")
                        failed.append(job)
                        print(f"❌ {job['ad_id']}: FAILED - {job['error']}")
            except Exception as e:
                pass
        
        if len(completed) + len(failed) < len(jobs):
            remaining = len(jobs) - len(completed) - len(failed)
            elapsed = int(time.time() - start)
            print(f"⏳ {remaining} ads still processing... ({elapsed}s elapsed)")
            time.sleep(30)
    
    # Results
    print("\n" + "=" * 80)
    print("📊 GENERATION RESULTS")
    print("=" * 80)
    print(f"\n✅ Completed: {len(completed)}")
    print(f"❌ Failed: {len(failed)}")
    print(f"⏱ Total time: {int(time.time() - start)}s")
    
    if completed:
        print("\n" + "=" * 80)
        print("COMPLETED ADVERTISEMENTS")
        print("=" * 80)
        for job in completed:
            print(f"\n{job['ad_id']}:")
            print(f"  Video URL: {job['video_url']}")
            print(f"  S3 Path: {job['s3_path']}")
    
    if failed:
        print("\n" + "=" * 80)
        print("FAILED ADVERTISEMENTS")
        print("=" * 80)
        for job in failed:
            print(f"\n{job['ad_id']}: {job.get('error', 'Unknown')}")
    
    # Save results
    # Use relative path from script location
    script_dir = os.path.dirname(os.path.abspath(__file__))
    results_file = os.path.join(script_dir, "generated_ads_results.json")
    results = {
        "completed": completed,
        "failed": failed,
        "total": len(ADS),
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
    }
    
    with open(results_file, 'w') as f:
        json.dump(results, f, indent=2)
    
    print(f"\n💾 Results saved to: generated_ads_results.json")
    
    if completed:
        print("\n" + "=" * 80)
        print("NEXT STEPS")
        print("=" * 80)
        print("\n1. Update dynamicAdInsertion/app.py with these URLs:")
        print("\nReplace the video_url values in AD_INVENTORY:\n")
        for job in completed:
            print(f'    "{job["ad_id"]}": {{')
            print(f'        "video_url": "{job["video_url"]}",')
            print(f'        ...')
            print(f'    }},')
        print("\n2. Restart DAI service:")
        print("   lsof -ti:5010 | xargs kill -9")
        print("   source .venv/bin/activate && python dynamicAdInsertion/app.py &")
    
    print("\n" + "=" * 80)
    print("✓ ADVERTISEMENT GENERATION COMPLETE")
    print("=" * 80 + "\n")
    
    return len(completed), len(failed)

if __name__ == "__main__":
    try:
        completed, failed = generate_all()
        sys.exit(0 if failed == 0 else 1)
    except KeyboardInterrupt:
        print("\n\n⚠️  Generation interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ Error: {e}")
        sys.exit(1)
