# YouTube Downloader - Quality Fix Summary

## Issue
Downloaded videos were only 360p despite ffmpeg being installed and format selection logic in place.

## Root Causes Identified

### 1. **ffmpeg PATH Issue**
- ffmpeg was installed in `.venv/bin/` but wasn't in PATH when subprocess ran
- `shutil.which("ffmpeg")` returned None in `download_youtube()` function
- Solution: Created `_check_ffmpeg_available()` function that adds venv bin to PATH before checking

### 2. **Incorrect Format Priority**
- Original format candidates didn't constrain height, causing fallback to low-quality progressive streams
- Solution: Added explicit height constraints:
  ```python
  format_candidates = [
      "bestvideo[height<=1080][ext=mp4]+bestaudio[ext=m4a]/bestvideo[height<=1080]+bestaudio/best[height<=1080]",
      "bestvideo[height<=720][ext=mp4]+bestaudio[ext=m4a]/bestvideo[height<=720]+bestaudio/best[height<=720]",
      "bestvideo*+bestaudio/best",
      "bv*[ext=mp4]+ba[ext=m4a]/best[ext=mp4]/best",
      "22/18/best",
  ]
  ```

### 3. **YouTube Client Selection**
- Custom `player_client` extractor args (android,web / ios / tv_embedded) triggered YouTube's PO Token requirement
- All high-quality formats were skipped, forcing 360p fallback
- Solution: Removed custom extractor args, let yt-dlp use default client selection strategy

### 4. **ffmpeg Location Not Passed to yt-dlp**
- Even after PATH modification, subprocess didn't reliably find ffmpeg
- Solution: Added explicit `--ffmpeg-location` parameter to yt-dlp command

## Changes Made

### `/code/youtube_downloader.py`

1. **Added `_check_ffmpeg_available()` function** (lines ~140-154)
   - Checks if ffmpeg is in PATH
   - If not, adds `.venv/bin` to PATH
   - Returns True if ffmpeg is available

2. **Modified `download_youtube()` function** (lines ~156-185)
   - Calls `_check_ffmpeg_available()` early to set up PATH
   - If ffmpeg available, immediately uses yt-dlp path (bypasses pytube for quality)
   - Removed fallback to pytube when ffmpeg exists

3. **Updated `_download_with_ytdlp()` function** (lines ~44-88)
   - Added height-constrained format candidates (1080p, 720p priorities)
   - Removed custom `--extractor-args` that triggered PO Token requirements
   - Added `--ffmpeg-location` parameter with explicit path
   - Simplified ffmpeg detection (PATH already set by caller)

## Test Results

### Before Fix
```
Video: h264, 640x360, 309 kb/s
Duration: 00:32:40.55, bitrate: 314 kb/s
```

### After Fix
```
Video: av1, 1920x1080, 865 kb/s  
Duration: 00:32:40.60, bitrate: 998 kb/s
```

## How to Use

```bash
# Download highest quality (up to 1080p)
python code/youtube_downloader.py --url "https://youtube.com/watch?v=..."

# Specify output filename
python code/youtube_downloader.py --url "URL" --filename video.mp4

# Specify output directory
python code/youtube_downloader.py --url "URL" --output /path/to/dir
```

## Requirements
- Python 3.9+
- pytube 15.0.0
- yt-dlp 2025.10.22 (or later)
- ffmpeg 6.1.1+ (installed in `.venv/bin/`)

## Notes
- Downloads now default to 1080p when available
- Falls back to 720p, then lower qualities if 1080p not available
- Requires ffmpeg for merging separate video+audio streams
- Works without cookies for most public videos
- For age-restricted content, use `--cookies` parameter with exported browser cookies
