# Synthetic Voiceover - Video Audio Replacement Feature Overview

**Feature:** Replace Video Audio with Synthetic Voiceover  
**Date:** October 23, 2025  
**Status:** ✅ LIVE

---

## Quick Start

### Upload video, get video with synthetic voiceover:

```bash
curl -X POST http://localhost:5003/replace-video-audio \
  -F "video=@my_video.mp4" \
  -F "voice_id=Matthew" \
  -F "engine=neural"
```

**Returns:** Base64-encoded video with synthetic voiceover

---

## What It Does

1. **Extracts** audio from your video (FFmpeg)
2. **Transcribes** audio to text (AWS Transcribe)
3. **Generates** expressive SSML (AWS Bedrock)
4. **Synthesizes** synthetic speech (AWS Polly)
5. **Replaces** audio in video (FFmpeg)
6. **Returns** new video

---

## Example Output

```json
{
  "success": true,
  "jobId": "a3b5c7d9",
  "video": "base64_encoded_video_data...",
  "contentType": "video/mp4",
  "originalTranscript": "Hello everyone, welcome to this tutorial...",
  "ssml": "<speak>Hello everyone, <emphasis>welcome</emphasis>...</speak>",
  "voiceId": "Matthew",
  "videoDuration": 45.2
}
```

---

## Use Cases

✅ **Language Dubbing** - English video → Spanish voiceover  
✅ **Voice Standardization** - Multiple speakers → One voice  
✅ **Audio Quality** - Noisy audio → Crystal clear  
✅ **Content Localization** - Same video, different languages  

---

## Available Voices

- **Joanna** (Female, US)
- **Matthew** (Male, US)
- **Amy** (Female, UK)
- **Brian** (Male, UK)
- **Lupe** (Female, Spanish)
- **+50 more voices!**

---

## Processing Time

- **30-second video:** ~20 seconds
- **2-minute video:** ~45 seconds

---

## Documentation

📖 **Full Docs:** `SYNTHETIC_VOICEOVER_VIDEO_AUDIO_REPLACEMENT.md`  
📄 **Summary:** `SYNTHETIC_VOICEOVER_VIDEO_AUDIO_REPLACEMENT_SUMMARY.md`

---

**Endpoint:** `POST /replace-video-audio`  
**Port:** 5003  
**Status:** 🟢 LIVE
