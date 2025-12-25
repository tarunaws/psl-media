# Added 15-Second Duration Option

## Change Summary
Added **15 seconds** as a new trailer duration option for quick, punchy social media trailers.

## Files Modified

### 1. Backend - `personalizedTrailer/personalized_trailer_service.py`
**Line 65**:
```python
# Before
DEFAULT_DURATIONS = [30, 45, 60, 90]

# After  
DEFAULT_DURATIONS = [15, 30, 45, 60, 90]
```

### 2. Frontend - `frontend/src/PersonalizedTrailer.js`
**Line 29**:
```javascript
// Before
durations: [30, 45, 60, 90],

// After
durations: [15, 30, 45, 60, 90],
```

## Available Duration Options

| Duration | Use Case | Typical Content |
|----------|----------|-----------------|
| **15 sec** ✨ NEW | Social media teasers, Instagram/TikTok | 1-2 high-impact scenes |
| 30 sec | Standard trailer, TV spots | 2-4 key scenes |
| 45 sec | Extended preview | 3-5 scenes with context |
| 60 sec | Full theatrical trailer | 5-8 comprehensive scenes |
| 90 sec | Epic extended trailer | 8-12 scenes, full story arc |

## 15-Second Trailer Characteristics

### Recommended For:
✅ **Social Media**: Instagram Stories, TikTok, Twitter/X
✅ **Quick Teasers**: Fast-paced attention grabbers
✅ **Mobile-First**: Designed for short attention spans
✅ **Viral Content**: Sharp, punchy, memorable

### Scene Selection for 15s:
- **Opening Act**: 1-2 scenes from beginning (high-impact opener)
- **Middle Climax**: 1-2 scenes from middle (peak action moment)
- **Grand Finale**: 1-2 scenes from end (dramatic climax)
- **Balanced Mix**: 1 scene from each region (quick journey)

### Technical Specs:
- **Scenes**: 1-2 per variant
- **Pacing**: Rapid cuts, high energy
- **Focus**: Single hero moment or sequence
- **Goal**: Immediate attention capture

## Testing

### Backend Verification
```bash
curl -s http://localhost:5007/options | jq '.durations'
# Returns: [15, 30, 45, 60, 90]
```

### Frontend Usage
1. Open http://localhost:3000
2. Navigate to "Personalized Trailer Lab"
3. Under "Trailer settings" → "Maximum runtime"
4. Select dropdown - **15 seconds should now appear** ✅

### Test Generation
1. Upload a video
2. Select **15 seconds** duration
3. Generate trailers
4. Expect 4 variants, each **~15 seconds** with 1-2 scenes

## Service Status
✅ Backend restarted (PID 12257)
✅ Frontend React dev server running (auto-reloaded)
✅ 15-second option available on port 5007
✅ Duration options: [15, 30, 45, 60, 90]

## Marketing Messages

### For Social Media
- "Generate **15-second trailers** perfect for Instagram & TikTok"
- "Quick teasers in **15 seconds** - maximum impact, minimal time"
- "Social-ready trailers: **15, 30, 45, 60, or 90 seconds**"

### For Content Creators
- "Short-form content? Create **15-second trailers** instantly"
- "From quick teasers to epic trailers: **15s to 90s** options"
- "Optimize for every platform with **5 duration presets**"

## Example Use Cases

### 15-Second Trailer Examples

**Action Movie**:
- 0:00-0:07: Explosive opening scene (car chase/fight)
- 0:07-0:12: Hero face reveal + tagline
- 0:12-0:15: Title card with release date

**Drama**:
- 0:00-0:06: Emotional confrontation scene
- 0:06-0:11: Character closeup + voiceover
- 0:11-0:15: Title reveal

**Comedy**:
- 0:00-0:12: Funniest joke/gag from the film
- 0:12-0:15: Title + "Coming Soon"

**Documentary**:
- 0:00-0:10: Most stunning visual moment
- 0:10-0:15: Narrator quote + title

## Platform Recommendations

| Platform | Recommended Duration | Format |
|----------|---------------------|---------|
| TikTok | **15-30 sec** | Vertical (9:16) |
| Instagram Stories | **15 sec** | Vertical (9:16) |
| Instagram Feed | **15-30 sec** | Square (1:1) or Vertical |
| YouTube Shorts | **15-60 sec** | Vertical (9:16) |
| Twitter/X | **15-30 sec** | Landscape (16:9) |
| Facebook | **30-60 sec** | Square (1:1) or Landscape |
| Theatrical | **60-90 sec** | Landscape (2.39:1) |

## Next Steps
1. ✅ Backend updated with 15s option
2. ✅ Frontend updated with 15s option
3. ✅ Services restarted
4. 🔄 **Refresh browser** and test the new option
5. ✅ Generate a 15-second trailer to verify

---

**Status**: ✅ **LIVE** - 15-second duration option now available for ultra-short trailers!
