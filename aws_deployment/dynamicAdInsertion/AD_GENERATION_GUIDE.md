# Generate Advertisements with Amazon Nova Reel

This guide explains how to generate 10-second GenAI advertisements for the Dynamic Ad Insertion feature using Amazon Nova Reel.

## Overview

The Dynamic Ad Insertion feature now supports **10 user profiles**:
1. **Tech Enthusiast** - Technology, Gaming, Innovation
2. **Sports Fan** - Sports, Fitness, Athletics
3. **Movie Lover** - Movies, Entertainment, Streaming
4. **Family Viewer** - Family, Education, Kids Content
5. **Fitness Enthusiast** - Fitness, Health, Wellness
6. **Gamer** - Gaming, Esports, Virtual Reality
7. **Foodie** - Cooking, Food, Culinary Arts
8. **Traveler** - Travel, Adventure, Culture
9. **Eco-Conscious** - Sustainability, Environment, Green Living
10. **Luxury Shopper** - Luxury, Fashion, Premium Brands

Each profile needs matching advertisements generated using Amazon Nova Reel.

## Prerequisites

- Video Generation service running on port 5009
- AWS credentials configured with Bedrock + S3 access
- Environment variables in `.env.local`:
    - `AWS_REGION`
    - `VIDEO_GEN_S3_BUCKET`
    - `DAI_S3_BUCKET`
- Optional: `ffmpeg` installed locally (required for thumbnail extraction and audio muxing)
- Amazon Polly access for voiceover synthesis

## Quick Start - Generate All Ads

### Option 1: Automated Script (Recommended)

```bash
cd /Users/tarun_bhardwaj/mydrive/Projects/mediaGenAI/code/dynamicAdInsertion
python3 generate_ads.py
```

Want to refresh only a few campaigns? Set `DAI_AD_IDS` before running the script:

```bash
DAI_AD_IDS="tech_gadget_ad,sports_drink_ad" python3 generate_ads.py
```

This script will:
- Generate 10 advertisements (one per category)
- Launch two Nova Reel segments per campaign (opening + closing prompts) and stitch them into a single master clip so you get a true 10-second ad even though Bedrock caps each render at ~6 seconds
- Monitor progress every 30 seconds
- Copy each finished MP4 into `DAI_S3_BUCKET/ads/<ad_id>/creative.mp4`
- Try to capture a thumbnail (requires `ffmpeg`) and upload it as `thumbnail.jpg`
- Layer an Amazon Polly voiceover on each ad and mux it with FFmpeg
- Blend a subtle background music bed under the narration (uses your track if provided, otherwise synthesizes a calm pad automatically)
- Save run metadata to `generated_ads.json`

> ℹ️ Amazon Nova Reel currently supports video clips up to roughly 6 seconds. The automation automatically pads each render (freezing the final frame) so the exported MP4s with narration last the full 10 seconds requested by the frontend.

### Customize Voiceover + Music

Current defaults already enable both narration and a gentle instrumental backing track, but you can tweak them via environment variables:

- `DAI_ENABLE_VOICEOVER=true|false` – master switch for Polly synthesis.
- `DAI_VOICEOVER_VOICE=Joanna` – set any Polly neural voice; optional `DAI_VOICEOVER_GAIN_DB` lets you nudge narration loudness (0 dB by default).
- `DAI_ENABLE_BG_MUSIC=true|false` – toggle the music bed.
- Supply a custom tune one of two ways:
  - Local file: `DAI_BG_MUSIC_FILE=/absolute/path/to/pad.mp3`
  - S3 object: set `DAI_BG_MUSIC_BUCKET` (defaults to `DAI_S3_BUCKET`) plus `DAI_BG_MUSIC_KEY=assets/audio/energy_bed.mp3`
- Need different vibes per campaign? Use JSON overrides: `DAI_BG_MUSIC_OVERRIDES='{"sports_drink_ad":"audio/high_energy.mp3","luxury_watch_ad":"audio/lounge.mp3"}'`
- Balance the mix with `DAI_BG_MUSIC_GAIN_DB` (default `-12`) so music sits underneath the narration.
- Normalize / sample rate knobs:
  - `DAI_AUDIO_SAMPLE_RATE` (default `44100`) keeps Safari + Chrome happy.
  - `DAI_VOICEOVER_GAIN_DB` nudges narration up/down before loudness normalization (target `-16 LUFS`).
- Motion padding options:
  - `DAI_LOOP_VIDEO_FOR_PADDING=true` (default) loops the rendered clip so 10-second exports keep moving instead of freezing on the last frame.
  - Set it to `false` if you prefer the old freeze-frame padding, or tweak `DAI_THUMBNAIL_SECOND` separately for stills.

  ### Customize Nova Segments

  Every entry in `AD_PROMPTS` now ships with two `segments` prompts (intro + outro). Each segment is kept at ≤6 seconds so Nova Reel accepts it, then the script concatenates them before audio. To change the storytelling beats:

  1. Open `dynamicAdInsertion/generate_ads.py` and edit the `segments` list under the desired `ad_id`. Each segment supports `label`, `duration`, and `prompt`.
  2. Keep `duration` ≤6 (the script enforces this), but you can mix 4s + 6s, duplicate segments, or even drop to a single segment by removing the `segments` array.
  3. Re-run `python3 generate_ads.py`. The tool automatically requests both segments, waits for Bedrock, stitches them with `ffmpeg concat`, and then runs the audio pipeline.

  If a segment fails to start or complete, that campaign is marked failed so you can tweak just that prompt and rerun via `DAI_AD_IDS`.

If you skip all of the above, the script synthesizes a warm ambient loop on the fly, keeping the ads from sounding empty while still avoiding licensing hassles.

**Time:** Approximately 20-30 minutes total

### Option 2: Manual Generation via API

Generate ads one at a time using the Video Generation API:

```bash
# Example: Generate tech gadget ad
curl -X POST http://localhost:5009/generate-video \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "A sleek 10-second advertisement showing a futuristic smartphone with holographic display, rotating in space with blue neon lighting and particle effects",
    "duration": 10
  }'

# Response:
# {
#   "id": "abc-123-def",
#   "status": "pending",
#   "message": "Video generation started"
# }

# Check status (poll every 30 seconds)
curl http://localhost:5009/check-status/abc-123-def

# When status is "completed", you'll get:
# {
#   "status": "completed",
#   "video_url": "https://mediagenai-video-generation.s3.us-east-1.amazonaws.com/..."
# }
```

### Option 3: Quick Test (4 Ads Only)

For a faster demo, generate just 4 priority ads:

```bash
cd /Users/tarun_bhardwaj/mydrive/Projects/mediaGenAI/code/dynamicAdInsertion
python3 quick_generate.py
```

This generates ads for:
- Tech Gadget
- Fitness Equipment
- Gaming Console
- Luxury Watch

**Time:** Approximately 8-10 minutes

## Advertisement Prompts

Use these optimized prompts for each category:

### 1. Tech Gadget Ad (`tech_gadget_ad`)
```
A sleek 10-second advertisement showing a futuristic smartphone with holographic display, rotating in space with blue neon lighting and particle effects, professional product photography style
```

### 2. Sports Drink Ad (`sports_drink_ad`)
```
A dynamic 10-second sports drink advertisement showing athletes in action, energy bursts, refreshing liquid splashes with vibrant colors, high-energy fast-paced cinematography
```

### 3. Streaming Service Ad (`streaming_service_ad`)
```
A cinematic 10-second streaming service advertisement with movie scenes, popcorn, cozy home theater setup, dramatic lighting and transitions between different genres
```

### 4. Family Vacation Ad (`family_vacation_ad`)
```
A heartwarming 10-second family vacation advertisement showing a happy family at a beach resort, children playing, sunset views, joyful moments, bright and cheerful atmosphere
```

### 5. Fitness Equipment Ad (`fitness_equipment_ad`)
```
A motivational 10-second fitness equipment advertisement showing modern gym equipment, people exercising with determination, sweat droplets, powerful movements, high-contrast dramatic lighting
```

### 6. Gaming Console Ad (`gaming_console_ad`)
```
An exciting 10-second gaming console advertisement with next-gen graphics, controller close-ups, explosive game scenes, neon lighting, cyberpunk aesthetic, fast cuts
```

### 7. Gourmet Food Ad (`gourmet_food_ad`)
```
A delicious 10-second gourmet food advertisement showing chef preparing exquisite dishes, steam rising, elegant plating, warm restaurant ambiance, mouth-watering close-ups
```

### 8. Travel Booking Ad (`travel_booking_ad`)
```
An adventurous 10-second travel advertisement showing exotic destinations, mountain peaks, tropical beaches, ancient temples, adventure activities, breathtaking aerial views
```

### 9. Eco Products Ad (`eco_products_ad`)
```
A serene 10-second eco-friendly products advertisement with green nature, sustainable packaging, solar panels, wind turbines, clean water, earth-friendly imagery, natural lighting
```

### 10. Luxury Watch Ad (`luxury_watch_ad`)
```
A sophisticated 10-second luxury watch advertisement with extreme close-up of premium timepiece, intricate mechanics, gold and diamond details, black velvet background, elegant rotation
```

## Deploying Creatives to Dynamic Ad Insertion

`generate_ads.py` now copies every completed MP4 into the Dynamic Ad Insertion bucket using the canonical layout the service expects:

```
s3://<DAI_S3_BUCKET>/ads/<ad_id>/creative.mp4
s3://<DAI_S3_BUCKET>/ads/<ad_id>/thumbnail.jpg
```

Because `dynamicAdInsertion/app.py` presigns assets based on `ad_id`, **no manual changes to `AD_INVENTORY` are required** once the files exist in S3.

After the script finishes:

1. Restart the stack (or at least the DAI service) so it notices the new files:
   ```bash
   cd /Users/tarun_bhardwaj/mydrive/Projects/mediaGenAI/code
   ./stop-all.sh && ./start-all.sh
   ```
2. Hard-refresh the frontend (`Shift+Cmd+R`) to drop cached HLS URLs.
3. Hit the `/ads` endpoint to confirm the new presigned locations:
   ```bash
   curl -s "http://localhost:5010/ads?profile_id=sports_fan" | python3 -m json.tool
   ```

## Manual Copy / Re-Sync (Optional)

The generator script already copies each MP4/thumbnail into `DAI_S3_BUCKET/ads/<ad_id>/`. Use the commands below only if you need to re-sync a single asset or copy it into another bucket (for MediaTailor, archival, etc.):

```bash
# List generated videos
aws s3 ls s3://mediagenai-video-generation/generated-videos/ --recursive | grep .mp4

# Copy to ad insertion bucket
aws s3 cp s3://mediagenai-video-generation/generated-videos/abc-123/video.mp4 \
  s3://mediagenai-ad-insertion/ads/tech_gadget_ad.mp4

# Repeat for all 10 ads
```

## Monitoring Progress

### Check Video Generation Service

```bash
# Service health
curl http://localhost:5009/health

# List all generations
curl http://localhost:5009/history | python3 -m json.tool

# Check specific generation
curl http://localhost:5009/check-status/GENERATION_ID
```

### View Logs

```bash
# Video generation logs
tail -f /Users/tarun_bhardwaj/mydrive/Projects/mediaGenAI/videoGeneration/video-generation.log

# Ad generation script logs
tail -f /Users/tarun_bhardwaj/mydrive/Projects/mediaGenAI/dynamicAdInsertion/ad_generation.log
```

## Troubleshooting

### Generation Takes Too Long

Amazon Nova Reel typically takes 1-2 minutes per video. For 10 ads:
- **Expected:** 10-20 minutes total
- **Maximum:** Up to 30 minutes if AWS is busy

If a generation exceeds 5 minutes, check the logs.

### Generation Fails

Check the error message:
```bash
curl http://localhost:5009/check-status/GENERATION_ID
```

Common issues:
- **Quota exceeded**: Wait and retry
- **Invalid prompt**: Simplify the prompt
- **S3 permissions**: Verify bucket access

### Video Not Found in S3

Videos are stored at:
```
s3://mediagenai-video-generation/generated-videos/GENERATION_ID/video.mp4
```

List the bucket to verify:
```bash
aws s3 ls s3://mediagenai-video-generation/generated-videos/GENERATION_ID/
```

### DAI Service Not Reflecting Updates

1. Verify the service restarted:
   ```bash
   curl http://localhost:5010/health
   ```

2. Check the logs:
   ```bash
   tail -50 dynamic-ad-insertion.log
   ```

3. Clear cache and restart:
   ```bash
   lsof -ti:5010 | xargs kill -9
   rm -f dynamicAdInsertion/__pycache__/*
   python dynamicAdInsertion/app.py
   ```

## Testing the Feature

After generating and updating ads:

1. **Open the frontend**: http://localhost:3000/dynamic-ad-insertion

2. **Select different user profiles** and click "Request Ad"

3. **Verify targeting**:
   - Tech Enthusiast → Tech Gadget Ad
   - Fitness Enthusiast → Fitness Equipment Ad
   - Gamer → Gaming Console Ad
   - Luxury Shopper → Luxury Watch Ad
   - etc.

4. **Check ad statistics** in the dashboard

5. **View request logs** to see targeting decisions

## Next Steps

1. **Generate all 10 ads** using the automated script
2. **Restart the Dynamic Ad Insertion service** to presign the fresh assets
3. **Test each user profile** in the frontend
4. **Optional**: Integrate with AWS MediaTailor for server-side ad insertion
5. **Optional**: Add more user profiles or ad variations

## Advanced: Batch Generation Script

For automated batch generation with error handling:

```python
#!/usr/bin/env python3
import requests
import time

ADS = {
    "tech_gadget_ad": "Your prompt here...",
    # ... all 10 ads
}

for ad_id, prompt in ADS.items():
    response = requests.post(
        "http://localhost:5009/generate-video",
        json={"prompt": prompt, "duration": 10}
    )
    
    if response.status_code == 202:
        gen_id = response.json()['id']
        print(f"Started {ad_id}: {gen_id}")
    else:
        print(f"Failed {ad_id}")
    
    time.sleep(2)  # Rate limiting
```

## Support

For issues or questions:
- Check `videoGeneration/README.md` for video generation details
- Check `dynamicAdInsertion/README.md` for DAI feature details
- View logs in `*.log` files
- AWS Bedrock documentation: https://docs.aws.amazon.com/bedrock/

---

**Pro Tip**: Run the automated script in a `screen` or `tmux` session so it continues even if you disconnect:

```bash
screen -S ad-gen
python3 dynamicAdInsertion/generate_ads.py
# Press Ctrl+A, then D to detach
# Reattach with: screen -r ad-gen
```
