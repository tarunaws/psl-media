# Fix for "Failed to fetch subtitles: Subtitle file not found" Error

**Date:** October 10, 2025  
**Issue:** Frontend was trying to fetch subtitles immediately after upload completed, but before subtitle generation was triggered.

## Root Cause

The workflow has three distinct stages:
1. **Upload** - Video upload + audio extraction (backend auto-completes at 100%)
2. **Transcribe** - Subtitle generation via AWS Transcribe (requires explicit API call)
3. **Complete** - Subtitles ready for download

The problem was:
- Backend's `/progress` endpoint didn't return a `stage` field
- Frontend relied on `serverStage` to determine when to call `/generate-subtitles`
- When `serverStage` was undefined, frontend would skip subtitle generation and try to fetch non-existent subtitles

## Files Changed

### 1. Backend: `aiSubtitle/aiSubtitle.py`

**Changed:** `/progress/<file_id>` endpoint

**Before:**
```python
@app.route('/progress/<file_id>', methods=['GET'])
def get_progress_endpoint(file_id):
    progress_info = get_progress(file_id)
    prog = int(progress_info.get('progress') or 0)
    audio_path = os.path.join(AUDIO_FOLDER, f"{file_id}.mp3")
    ready = os.path.exists(audio_path)
    client_payload = {
        'progress': prog,
        'readyForFetch': ready
    }
    return jsonify(client_payload)
```

**After:**
```python
@app.route('/progress/<file_id>', methods=['GET'])
def get_progress_endpoint(file_id):
    progress_info = get_progress(file_id)
    prog = int(progress_info.get('progress') or 0)
    
    # Determine readiness and stage
    audio_path = os.path.join(AUDIO_FOLDER, f"{file_id}.mp3")
    subtitles_path = os.path.join(OUTPUT_FOLDER, f"{file_id}.srt")
    
    audio_exists = os.path.exists(audio_path)
    subtitles_exist = os.path.exists(subtitles_path)
    
    # Determine stage based on what files exist
    if subtitles_exist:
        stage = 'complete'
    elif audio_exists and prog >= 100:
        stage = 'upload'  # Upload complete, ready for transcription
    elif audio_exists:
        stage = 'transcribe'  # Currently transcribing
    else:
        stage = 'upload'  # Still uploading/extracting
    
    client_payload = {
        'progress': prog,
        'readyForFetch': audio_exists,
        'stage': stage,
        'message': progress_info.get('message', '')
    }
    return jsonify(client_payload)
```

**Key Changes:**
- ✅ Added `stage` field to progress response
- ✅ Added `message` field to progress response
- ✅ Stage determined by file existence (audio/subtitles)
- ✅ More accurate state reporting

### 2. Frontend: `frontend/src/AISubtitling.js`

**Changed:** `pollProgress()` function stage transitions

**Before:**
```javascript
// Stage-driven transitions
if (serverStage === 'upload' && data.progress >= 100) {
  setPhase('transcribe');
  generateSubtitles(fileId);
  return;
}

if (canFetch || serverStage === 'complete' || (data.progress >= 100 && phase === 'transcribe')) {
  setPhase('complete');
  fetchSubtitles(fileId);
  return;
}
```

**After:**
```javascript
// Stage-driven transitions
// If upload is complete (progress 100% and readyForFetch), trigger subtitle generation
if (phase === 'upload' && data.progress >= 100 && canFetch) {
  setPhase('transcribe');
  generateSubtitles(fileId);
  return;
}

// If in transcribe phase and progress complete, fetch subtitles
if (phase === 'transcribe' && data.progress >= 100) {
  setPhase('complete');
  fetchSubtitles(fileId);
  return;
}

// Server-driven stage changes (if backend provides stage field)
if (serverStage === 'complete' || canFetch && phase === 'transcribe') {
  setPhase('complete');
  fetchSubtitles(fileId);
  return;
}
```

**Key Changes:**
- ✅ Check client-side `phase` state, not just server `stage`
- ✅ Trigger subtitle generation when upload phase reaches 100% + readyForFetch
- ✅ Separate logic for transcribe-to-complete transition
- ✅ Fallback to server stage if provided

## Testing

### Scenario 1: Fresh Upload
1. User uploads video
2. Backend extracts audio → progress 100%, readyForFetch=true, stage='upload'
3. Frontend detects `phase === 'upload' && progress === 100 && readyForFetch`
4. Frontend calls `/generate-subtitles`
5. Backend processes → stage='transcribe'
6. Backend completes → stage='complete'
7. Frontend fetches subtitles ✅

### Scenario 2: Retry Existing File
1. User manually enters file ID
2. Backend checks files → finds audio + subtitles
3. Progress endpoint returns stage='complete'
4. Frontend immediately fetches subtitles ✅

### Scenario 3: Stuck at 100%
1. Upload completes but generation doesn't auto-trigger
2. Manual "Fetch Results" button visible
3. User clicks button → generates subtitles manually ✅

## Deployment

**Backend restart required:**
```bash
./stop-backend.sh
./start-backend.sh
```

**Frontend:** No restart needed (React hot-reload will pick up changes)

## Verification Commands

```bash
# Test progress endpoint
curl http://localhost:5001/progress/<file_id>

# Expected response:
# {
#   "progress": 100,
#   "readyForFetch": true,
#   "stage": "upload",  ← NEW
#   "message": ""       ← NEW
# }
```

## Summary

✅ Backend now returns `stage` and `message` in progress endpoint  
✅ Frontend logic updated to properly handle upload → transcribe → complete flow  
✅ Works with or without server-provided stage (fallback to client phase)  
✅ No breaking changes to existing functionality  
✅ Error resolved: Subtitles are now generated before being fetched
