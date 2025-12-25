# Personalized Trailer Multi-Variant Fix

## Issue Summary
After implementing the multi-variant trailer feature, users reported:
- "I can only see one variant that also still starting of the video"
- "No trailer has been generated"
- "Earlier it was working good with one trailer"

## Root Cause Analysis

### Problem 1: Incorrect Assembly Function
The variant assembly logic was using a new function `_mock_assemble_trailer_variant()` which didn't properly integrate with the existing timeline creation code. Each variant was being assembled incorrectly, resulting in:
- Only one variant being generated
- All variants pulling from the start of the video
- Timeline assembly failing silently

### Problem 2: Insufficient Scene Selection
The variant scene selection logic was too conservative with scene counts:
- Opening Act: Only 4+2+1 scenes (7 total)
- Middle Climax: Only 1+4+2 scenes (7 total)
- Grand Finale: Only 1+2+4 scenes (7 total)
- Balanced Mix: Only 2+2+2 scenes (6 total)

This caused issues when scenes had short durations or when the duration checks prevented scene addition.

### Problem 3: No Fallback Logic
If a variant ended up with no scenes (due to strict duration checks), there was no fallback to ensure at least some content was included.

## Solutions Implemented

### Fix 1: Use Original Assembly Function with Variant Scenes
**Location:** `personalizedTrailer/personalized_trailer_service.py` lines ~390-425

**Changed from:**
```python
assemblies = []
for variant in personalization.get("variants", []):
    variant_assembly = _mock_assemble_trailer_variant(...)
    assemblies.append(variant_assembly)
assembly = assemblies[0] if assemblies else _mock_assemble_trailer(...)
```

**Changed to:**
```python
# Generate main assembly (backward compatible)
assembly = _mock_assemble_trailer(personalization=personalization, ...)

# Generate variant assemblies using the SAME working function
assemblies = []
for variant in personalization.get("variants", []):
    # Create a temporary personalization object with this variant's scenes
    variant_personalization = dict(personalization)
    variant_personalization["selectedScenes"] = variant.get("scenes", [])
    
    # Use the proven assembly function with variant scenes
    variant_assembly = _mock_assemble_trailer(personalization=variant_personalization, ...)
    
    # Add variant metadata
    variant_assembly["variantName"] = variant.get("name")
    variant_assembly["variantDescription"] = variant.get("description")
    variant_assembly["distribution"] = variant.get("distribution")
    
    assemblies.append(variant_assembly)
```

**Why this works:**
- Reuses the battle-tested `_mock_assemble_trailer()` function
- Each variant gets its own personalization object with unique scene selection
- Preserves all variant metadata for deliverable generation
- Maintains backward compatibility with single-trailer mode

### Fix 2: Increased Scene Counts and Removed Strict Duration Checks
**Location:** `personalizedTrailer/personalized_trailer_service.py` lines ~950-1080

**Changes:**
1. **Opening Act** (60% early, 30% mid, 10% late):
   - Early scenes: 4 → 6
   - Middle scenes: 2 → 3
   - Late scenes: 1 (unchanged)
   - Relaxed duration checks (use >= instead of <)

2. **Middle Climax** (20% early, 60% mid, 20% late):
   - Early scenes: 1 → 2
   - Middle scenes: 4 → 6
   - Late scenes: 2 (unchanged)
   - Relaxed duration checks

3. **Grand Finale** (10% early, 30% mid, 60% late):
   - Early scenes: 1 (unchanged)
   - Middle scenes: 2 → 3
   - Late scenes: 4 → 6
   - Relaxed duration checks

4. **Balanced Mix** (33% each):
   - Early scenes: 2 → 3
   - Middle scenes: 2 → 3
   - Late scenes: 2 → 3
   - Relaxed duration checks

### Fix 3: Added Fallback Logic
**Location:** Added to each variant generation block

**Code added:**
```python
# Fallback: if no scenes, use from ranked list
if not variant_scenes and ranked:
    variant_scenes = ranked[:min(5, len(ranked))]
```

**Purpose:**
- Ensures every variant has at least some scenes
- Prevents empty variant deliverables
- Uses ranked scenes as fallback (already proven to work)

## Testing Instructions

### 1. Upload a Test Video
Use the frontend at http://localhost:3000 and navigate to the Personalized Trailer use case.

### 2. Generate Trailers
- Upload a video (recommend 3-5 minutes for testing)
- Submit for processing
- Wait for completion (mock mode should take ~30-60 seconds)

### 3. Verify Deliverables
The response should include multiple video files:
```json
{
  "deliverables": [
    {
      "url": "http://localhost:5007/download/job_xyz/job_xyz_trailer_opening_act.mp4",
      "label": "Opening Act",
      "description": "Emphasizes the beginning and setup",
      "distribution": {"early": "60%", "middle": "30%", "late": "10%"}
    },
    {
      "url": "http://localhost:5007/download/job_xyz/job_xyz_trailer_middle_climax.mp4",
      "label": "Middle Climax",
      "description": "Showcases the peak action and drama",
      "distribution": {"early": "20%", "middle": "60%", "late": "20%"}
    },
    {
      "url": "http://localhost:5007/download/job_xyz/job_xyz_trailer_grand_finale.mp4",
      "label": "Grand Finale",
      "description": "Highlights the climax and resolution",
      "distribution": {"early": "10%", "middle": "30%", "late": "60%"}
    },
    {
      "url": "http://localhost:5007/download/job_xyz/job_xyz_trailer_balanced_mix.mp4",
      "label": "Balanced Mix",
      "description": "Equal representation from beginning, middle, and end",
      "distribution": {"early": "33%", "middle": "33%", "late": "33%"}
    }
  ]
}
```

### 4. Verify Content Distribution
Download each variant and verify:
- **Opening Act**: Should emphasize content from the first 60% of the video
- **Middle Climax**: Should emphasize content from the middle section
- **Grand Finale**: Should emphasize content from the last 60% of the video
- **Balanced Mix**: Should have roughly equal content from all three sections

You can check the timestamps in the video filenames or by analyzing the scene selections in the response.

## Service Status
✅ All backend services restarted successfully
✅ Personalized Trailer service running on port 5007
✅ Service mode: MOCK (PERSONALIZED_TRAILER_PIPELINE_MODE=mock)
✅ Health check passing

## Process Information
- AI Subtitle: PID 4603
- Image Creation: PID 4604
- Synthetic Voiceover: PID 4605
- Scene Summarization: PID 4606
- Movie Script: PID 4607
- Content Moderation: PID 4608
- **Personalized Trailer: PID 4609** ← Fixed service

## Next Steps
1. Test with a sample video to verify all 4 variants are generated
2. Verify each variant pulls from the correct time ranges
3. Confirm video files are properly rendered and downloadable
4. If testing is successful, consider re-enabling AWS Rekognition mode (with timeout fixes)

## Related Documentation
- [Multi-Variant Implementation](./PERSONALIZED_TRAILER_MULTIVARIANT.md)
- [Services README](./SERVICES_README.md)
- [System Complete Guide](./SYSTEM_COMPLETE.md)
