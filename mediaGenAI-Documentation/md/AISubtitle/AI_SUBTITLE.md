# AI Subtitle Service - Complete Reference Guide

**Version:** 1.0  
**Last Updated:** October 21, 2025  
**Service Port:** 5001  
**Technology Stack:** Python 3.11+, Flask, AWS Transcribe, AWS Translate, FFmpeg

---

## Table of Contents

1. [Architecture Overview](#architecture-overview)
2. [System Components](#system-components)
3. [Backend Architecture](#backend-architecture)
4. [Frontend Architecture](#frontend-architecture)
5. [Data Flow & Processing Pipeline](#data-flow--processing-pipeline)
6. [AWS Integration](#aws-integration)
7. [Key Logic & Algorithms](#key-logic--algorithms)
8. [API Reference](#api-reference)
9. [Configuration](#configuration)
10. [Deployment](#deployment)
11. [Troubleshooting](#troubleshooting)
12. [Performance Optimization](#performance-optimization)

---

## Architecture Overview

### High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         User Browser                             │
│                    (React Frontend - Port 3000)                  │
└────────────┬────────────────────────────────────────────────────┘
             │ HTTP/AJAX (axios)
             │ • Video Upload (multipart/form-data)
             │ • Progress Polling (GET /progress)
             │ • Subtitle Download (GET /download)
             │ • Audio Streaming (Range Requests)
             ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Flask Backend Service                         │
│                         (Port 5001)                              │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │              Flask Routes & Handlers                      │  │
│  │  • /upload           • /extract-audio                     │  │
│  │  • /generate-subtitles  • /download/<file_id>            │  │
│  │  • /progress/<file_id>  • /stream-audio/<file_id>        │  │
│  └────────────┬─────────────────────────────────────────────┘  │
│               │                                                  │
│  ┌────────────▼─────────────────────────────────────────────┐  │
│  │         Core Processing Modules                          │  │
│  │  • Video Handling    • Audio Extraction (FFmpeg)         │  │
│  │  • AWS S3 Upload     • Transcription Management          │  │
│  │  • Translation       • Format Conversion (SRT/VTT)       │  │
│  │  • Stream Generation (HLS/DASH)                          │  │
│  └────────────┬─────────────────────────────────────────────┘  │
│               │                                                  │
│  ┌────────────▼─────────────────────────────────────────────┐  │
│  │           File System Storage                            │  │
│  │  • uploads/          - Original video files              │  │
│  │  • audio/            - Extracted MP3 files               │  │
│  │  • outputs/subtitles/- Generated SRT/VTT files          │  │
│  │  • outputs/streams/  - HLS/DASH manifests & segments    │  │
│  └──────────────────────────────────────────────────────────┘  │
└────────────┬────────────────────────────────────────────────────┘
             │ AWS SDK (boto3)
             │ • S3 Upload (multipart for large files)
             │ • Transcribe Job Management
             │ • Translate API Calls
             ▼
┌─────────────────────────────────────────────────────────────────┐
│                        AWS Services                              │
│  ┌─────────────┐  ┌─────────────────┐  ┌──────────────────┐   │
│  │   Amazon    │  │    Amazon       │  │     Amazon       │   │
│  │     S3      │  │   Transcribe    │  │    Translate     │   │
│  │  (Storage)  │  │ (Speech-to-Text)│  │  (Translation)   │   │
│  └─────────────┘  └─────────────────┘  └──────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
```

### Design Principles

1. **Asynchronous Processing**: Long-running AWS Transcribe jobs don't block the UI
2. **Progress Tracking**: In-memory progress state with thread-safe updates
3. **Multi-language Support**: Auto-detection + translation to 70+ languages
4. **Scalable Uploads**: Multipart S3 uploads for files >100MB
5. **Adaptive Streaming**: HLS and DASH generation for browser compatibility
6. **Fault Tolerance**: Graceful degradation when AWS services unavailable

---

## System Components

### Backend Components

| Component | Technology | Purpose |
|-----------|-----------|---------|
| **Web Framework** | Flask 2.3.3 | HTTP request handling, routing |
| **CORS Handler** | Flask-CORS 4.0.0 | Cross-origin resource sharing |
| **AWS SDK** | boto3 ≥1.28.0 | AWS service integration |
| **Media Processing** | FFmpeg/FFprobe | Audio extraction, streaming |
| **File Handling** | Werkzeug 2.3.7 | Secure filename handling |
| **Text Processing** | Unidecode 1.3.8 | Unicode normalization |
| **Config Management** | python-dotenv 1.0.1 | Environment variables |

### Frontend Components

| Component | Technology | Purpose |
|-----------|-----------|---------|
| **UI Framework** | React 18.3.0 | Component-based UI |
| **HTTP Client** | axios 1.12.2 | API communication |
| **HLS Player** | hls.js 1.5.7 | HTTP Live Streaming playback |
| **DASH Player** | dashjs 4.6.1 | MPEG-DASH playback |
| **Styling** | styled-components 6.1.19 | CSS-in-JS styling |
| **Routing** | react-router-dom 6.21.2 | Client-side navigation |

---

## Backend Architecture

### File Structure

```
aiSubtitle/
├── aiSubtitle.py              # Main Flask application (1424 lines)
├── requirements.txt           # Python dependencies
├── README.md                 # Service documentation
├── AWS_TRANSCRIBE_SETUP.md   # AWS setup guide
├── .env.example              # Environment template
├── uploads/                  # Uploaded video files
├── audio/                    # Extracted MP3 audio
├── outputs/
│   ├── subtitles/           # Generated SRT/VTT files
│   └── streams/             # HLS/DASH streaming assets
└── templates/
    └── index.html           # Basic web interface
```

### Core Modules

#### 1. Binary Resolution (`_resolve_binary`)

**Purpose**: Locate FFmpeg/FFprobe executables across different platforms

**Algorithm**:
```python
def _resolve_binary(default_name, env_keys, extra_paths):
    # 1. Check environment variables (FFMPEG_BINARY, FFMPEG_PATH)
    for key in env_keys:
        candidate = os.getenv(key)
        if candidate exists and is executable:
            return candidate
    
    # 2. Search system PATH
    resolved = shutil.which(default_name)
    if resolved:
        return resolved
    
    # 3. Check common install locations
    for candidate in ['/opt/homebrew/bin', '/usr/local/bin', '/usr/bin']:
        if candidate exists and is executable:
            return candidate
    
    return None
```

**Supported Paths**:
- macOS Homebrew: `/opt/homebrew/bin/ffmpeg`
- Linux standard: `/usr/local/bin/ffmpeg`, `/usr/bin/ffmpeg`
- Custom: Environment variable override

#### 2. Audio Extraction (`extract_audio_from_video`)

**Purpose**: Convert video to MP3 audio for AWS Transcribe processing

**FFmpeg Command**:
```bash
ffmpeg -y -i <video_path> \
  -acodec mp3 \
  -ab 128k \      # Bitrate: 128 kbps
  -ac 2 \         # Channels: stereo
  -ar 44100 \     # Sample rate: 44.1 kHz
  -vn \           # No video output
  <audio_path>
```

**Validation**:
- Check file exists after extraction
- Verify file size > 0 bytes (prevents empty files)
- Remove zero-byte files to avoid downstream errors

**Error Handling**:
```python
try:
    subprocess.run(cmd, check=True, capture_output=True, text=True)
    if audio_size == 0:
        os.remove(audio_path)
        return False
    return True
except subprocess.CalledProcessError as e:
    print(f"Error extracting audio: {e.stderr}")
    return False
```

#### 3. S3 Upload with Progress (`upload_to_s3_with_progress`)

**Purpose**: Upload large files to S3 with multipart upload and progress tracking

**Decision Logic**:
```
File Size > 100MB?
├─ YES → Multipart Upload (100MB chunks)
└─ NO  → Single-part Upload
```

**Multipart Upload Flow**:
```python
def _multipart_upload_to_s3(file_path, bucket_name, object_name, file_id, file_size):
    # 1. Initialize multipart upload
    response = s3_client.create_multipart_upload(Bucket=bucket_name, Key=object_name)
    upload_id = response['UploadId']
    
    parts = []
    part_size = 100 * 1024 * 1024  # 100MB
    part_number = 1
    bytes_uploaded = 0
    
    # 2. Upload parts sequentially
    with open(file_path, 'rb') as file:
        while True:
            part_data = file.read(part_size)
            if not part_data:
                break
            
            # Update progress
            progress = int((bytes_uploaded / file_size) * 100)
            update_progress(file_id, progress)
            
            # Upload part
            part_response = s3_client.upload_part(
                Bucket=bucket_name,
                Key=object_name,
                PartNumber=part_number,
                UploadId=upload_id,
                Body=part_data
            )
            
            parts.append({'ETag': part_response['ETag'], 'PartNumber': part_number})
            bytes_uploaded += len(part_data)
            part_number += 1
    
    # 3. Complete multipart upload
    s3_client.complete_multipart_upload(
        Bucket=bucket_name,
        Key=object_name,
        UploadId=upload_id,
        MultipartUpload={'Parts': parts}
    )
    
    return f"s3://{bucket_name}/{object_name}"
```

**Benefits**:
- Progress tracking per 100MB chunk
- Resumable uploads (if abort/retry implemented)
- Better memory efficiency for large files
- Improved reliability for slow connections

#### 4. AWS Transcribe Integration (`generate_subtitles_with_aws_transcribe`)

**Purpose**: Generate subtitles using AWS Transcribe with auto-detection and translation

**Processing Flow**:

```
1. Validation
   ├─ Check AWS credentials
   ├─ Validate audio file exists
   └─ Verify file size > 0

2. S3 Upload (30% progress)
   ├─ Generate unique job name
   ├─ Upload audio to s3://bucket/audio/{job_name}/
   └─ Get S3 URI

3. Start Transcription Job (50% progress)
   ├─ Language Detection?
   │  ├─ YES → IdentifyLanguage = True
   │  └─ NO  → LanguageCode = {source_language}
   ├─ Submit job to AWS Transcribe
   └─ Poll for completion (max 5 minutes)

4. Process Results (85% progress)
   ├─ Download transcript JSON from S3
   ├─ Build segments (12 words per subtitle)
   ├─ Convert to SRT format
   └─ Generate VTT format

5. Translation (90-100% progress)
   ├─ For each target language:
   │  ├─ Translate segment text via AWS Translate
   │  ├─ Preserve timestamps
   │  └─ Save SRT/VTT files
   └─ Return all language variants
```

**Segment Building Algorithm**:
```python
def build_transcript_segments(transcription_json, words_per_segment=12):
    # Extract pronunciation items with timestamps
    items = transcription_json['results']['items']
    words = []
    for item in items:
        if item['type'] == 'pronunciation' and 'start_time' in item:
            words.append({
                'word': item['alternatives'][0]['content'],
                'start_time': float(item['start_time']),
                'end_time': float(item['end_time'])
            })
    
    # Group into segments (12 words each)
    segments = []
    for i in range(0, len(words), words_per_segment):
        segment_words = words[i:i + words_per_segment]
        segments.append({
            'index': segment_num,
            'start_time': segment_words[0]['start_time'],
            'end_time': segment_words[-1]['end_time'],
            'text': ' '.join(word['word'] for word in segment_words)
        })
        segment_num += 1
    
    return segments
```

**Why 12 words per segment?**
- Optimal reading speed: ~2-3 words/second
- Typical segment duration: 4-6 seconds
- Balances readability vs. screen clutter

#### 5. Format Conversion

**SRT Format**:
```
1
00:00:00,000 --> 00:00:05,240
This is the first subtitle segment with approximately twelve words.

2
00:00:05,240 --> 00:00:10,580
This is the second subtitle segment continuing the transcription.
```

**VTT Format**:
```
WEBVTT

00:00:00.000 --> 00:00:05.240
This is the first subtitle segment with approximately twelve words.

00:00:05.240 --> 00:00:10.580
This is the second subtitle segment continuing the transcription.
```

**Conversion Logic**:
```python
def convert_srt_to_vtt(srt_content: str) -> str:
    vtt_lines = ['WEBVTT', '']
    for line in srt_content.splitlines():
        if '-->' in line:
            # Replace comma with period for milliseconds
            vtt_lines.append(line.replace(',', '.'))
        else:
            vtt_lines.append(line)
    return '\n'.join(vtt_lines).strip() + '\n'
```

#### 6. Streaming Generation

**HLS (HTTP Live Streaming)**:
```bash
ffmpeg -y -i <video_path> \
  -c:v libx264 -preset veryfast -profile:v main -level 3.1 \
  -c:a aac -b:a 128k \
  -start_number 0 \
  -hls_time 6 \           # 6-second segments
  -hls_list_size 0 \      # Include all segments in playlist
  -hls_segment_filename 'segment_%03d.ts' \
  master.m3u8
```

**DASH (MPEG-DASH)**:
```bash
ffmpeg -y -i <video_path> \
  -map 0 \
  -c:v libx264 -preset veryfast -profile:v main -level 3.1 \
  -c:a aac -b:a 128k \
  -f dash \
  -use_template 1 \
  -use_timeline 1 \
  -seg_duration 6 \
  manifest.mpd
```

**Output Structure**:
```
outputs/streams/{file_id}/
├── hls/
│   ├── master.m3u8
│   ├── segment_000.ts
│   ├── segment_001.ts
│   └── ...
└── dash/
    ├── manifest.mpd
    ├── init-stream0.m4s
    ├── chunk-stream0-00001.m4s
    └── ...
```

#### 7. Progress Tracking System

**Thread-Safe Progress Management**:
```python
# Global state
progress_data = {}
progress_lock = threading.Lock()

def update_progress(file_id, progress, message=None, **extra):
    with progress_lock:
        entry = progress_data.get(file_id, {})
        entry['progress'] = progress
        if message is not None:
            entry['message'] = message
        for key, value in extra.items():
            entry[key] = value
        progress_data[file_id] = entry

def get_progress(file_id):
    with progress_lock:
        return progress_data.get(file_id, {'progress': 0})
```

**Progress Milestones**:
- 0-20%: Video upload and validation
- 20-30%: Audio extraction
- 30-50%: S3 upload
- 50-85%: AWS Transcribe processing
- 85-90%: Subtitle generation
- 90-100%: Translation to target languages

---

## Frontend Architecture

### Component Structure

```
AISubtitling.js (1431 lines)
├── Configuration
│   ├── API Base URL Resolution
│   ├── Language Options (Transcribe + Translate)
│   └── Stage Baseline Calculation
├── Styled Components
│   ├── Layout (Page, Container, Card)
│   ├── Form Controls (Button, Select, Input)
│   ├── Progress Indicators
│   ├── Video Player (with subtitle overlay)
│   └── Language Tabs
├── State Management (useState)
│   ├── Upload State
│   ├── Progress State
│   ├── Subtitle Data
│   ├── Video Player State
│   └── Language Selection
├── Effects (useEffect)
│   ├── Progress Polling
│   ├── Video Player Initialization
│   ├── Subtitle Track Management
│   └── Cleanup
└── Event Handlers
    ├── File Upload
    ├── Subtitle Generation
    ├── Language Selection
    ├── Download Actions
    └── Video Playback Controls
```

### Key Logic

#### 1. API Base URL Resolution

**Purpose**: Dynamically resolve backend URL for local/LAN/production environments

```javascript
const resolveSubtitleApiBase = () => {
  const envValue = process.env.REACT_APP_SUBTITLE_API_BASE;
  if (envValue) {
    return envValue.replace(/\/$/, '');
  }
  
  if (typeof window !== 'undefined') {
    const { protocol, hostname } = window.location;
    const localHosts = new Set(['localhost', '127.0.0.1', '0.0.0.0']);
    const isLanHost = /^(192\.168\.|10\.|172\.(1[6-9]|2[0-9]|3[0-1]))/.test(hostname) 
                      || hostname.endsWith('.local');
    
    if (localHosts.has(hostname) || isLanHost) {
      return `${protocol}//${hostname}:5001`;
    }
    return `${protocol}//${hostname}`;
  }
  return '';
};
```

**Scenarios**:
- **Local dev**: `http://localhost:5001`
- **LAN access**: `http://192.168.1.100:5001`
- **Production**: Same domain as frontend

#### 2. Progress Baseline Calculation

**Purpose**: Map backend progress to UI stages with smooth transitions

```javascript
const computeStageBaseline = ({
  stage,
  readyForTranscription,
  subtitlesInProgress,
  subtitlesAvailable
}) => {
  if (!stage) return 0;
  
  if (stage === 'upload') {
    return readyForTranscription ? 55 : 12;
  }
  
  if (stage === 'transcribe') {
    if (subtitlesAvailable) return 90;
    return subtitlesInProgress ? 78 : 64;
  }
  
  if (stage === 'complete') return 100;
  
  return 0;
};
```

#### 3. Video Player with Subtitle Overlay

**HLS Player Initialization**:
```javascript
useEffect(() => {
  if (!videoRef.current || !videoFileUrl) return;
  
  if (Hls.isSupported()) {
    const hls = new Hls();
    hls.loadSource(videoFileUrl);
    hls.attachMedia(videoRef.current);
    
    hls.on(Hls.Events.MANIFEST_PARSED, () => {
      // Auto-play when ready
    });
    
    return () => {
      hls.destroy();
    };
  } else if (videoRef.current.canPlayType('application/vnd.apple.mpegurl')) {
    // Native HLS support (Safari)
    videoRef.current.src = videoFileUrl;
  }
}, [videoFileUrl]);
```

**Subtitle Track Management**:
```javascript
useEffect(() => {
  if (!videoRef.current || !selectedLanguageForPreview || !subtitlesByLanguage) return;
  
  const subtitle = subtitlesByLanguage.find(
    (s) => s.languageCode.toLowerCase() === selectedLanguageForPreview.toLowerCase()
  );
  
  if (!subtitle) return;
  
  // Remove existing tracks
  Array.from(videoRef.current.textTracks).forEach((track) => {
    track.mode = 'hidden';
  });
  
  // Add new track
  const track = document.createElement('track');
  track.kind = 'subtitles';
  track.label = subtitle.languageLabel;
  track.srclang = subtitle.languageCode;
  track.src = subtitle.vttUrl;
  track.default = true;
  
  videoRef.current.appendChild(track);
  track.track.mode = 'showing';
  
  return () => {
    track.remove();
  };
}, [selectedLanguageForPreview, subtitlesByLanguage]);
```

#### 4. Progress Polling

**Purpose**: Check backend progress every 2 seconds during processing

```javascript
useEffect(() => {
  if (!fileId || stage === 'complete') return;
  
  const pollProgress = async () => {
    try {
      const response = await axios.get(`${API_BASE}/progress/${fileId}`);
      const data = response.data;
      
      setProgress(data.progress || 0);
      setMessage(data.message || '');
      
      // Update state based on progress
      if (data.progress >= 100) {
        setStage('complete');
      } else if (data.progress >= 50) {
        setStage('transcribe');
      }
      
      // Store detected language
      if (data.detected_language) {
        setDetectedLanguage(data.detected_language);
      }
    } catch (error) {
      console.error('Progress poll failed:', error);
    }
  };
  
  const interval = setInterval(pollProgress, 2000);
  
  return () => clearInterval(interval);
}, [fileId, stage]);
```

---

## Data Flow & Processing Pipeline

### Complete Workflow

```
┌─────────────────────────────────────────────────────────────────┐
│ 1. USER UPLOAD (Frontend)                                       │
│    • Select video file                                           │
│    • Choose source language (or auto-detect)                     │
│    • Select target languages for translation                     │
└────────────┬────────────────────────────────────────────────────┘
             │ POST /upload (multipart/form-data)
             ▼
┌─────────────────────────────────────────────────────────────────┐
│ 2. VIDEO UPLOAD (Backend)                                       │
│    • Validate file extension (mp4, mov, mkv, etc.)              │
│    • Generate unique file_id (UUID)                              │
│    • Save to uploads/{file_id}_{filename}                       │
│    • Return: { file_id, filename, size }                        │
└────────────┬────────────────────────────────────────────────────┘
             │ Frontend stores file_id
             │ POST /extract-audio
             ▼
┌─────────────────────────────────────────────────────────────────┐
│ 3. AUDIO EXTRACTION (Backend)                                   │
│    • FFmpeg: video → MP3 (128kbps, 44.1kHz)                     │
│    • Validate output file size > 0                               │
│    • Save to audio/{file_id}.mp3                                │
│    • Update progress: 20%                                        │
│    • Return: { audio_path, duration }                           │
└────────────┬────────────────────────────────────────────────────┘
             │ Frontend shows "Ready for transcription"
             │ User clicks "Generate Subtitles"
             │ POST /generate-subtitles
             ▼
┌─────────────────────────────────────────────────────────────────┐
│ 4. S3 UPLOAD (Backend)                                          │
│    • Decision: file_size > 100MB?                               │
│      ├─ YES → Multipart upload (100MB chunks)                   │
│      └─ NO  → Single-part upload                                │
│    • Upload to s3://bucket/audio/{job_name}/                    │
│    • Update progress: 30-50%                                     │
│    • Return S3 URI: s3://bucket/audio/{job_name}/{file}.mp3    │
└────────────┬────────────────────────────────────────────────────┘
             │
             ▼
┌─────────────────────────────────────────────────────────────────┐
│ 5. AWS TRANSCRIBE JOB (Backend)                                │
│    • Create transcription job:                                  │
│      - Job name: transcription-{uuid}-{timestamp}               │
│      - Media URI: S3 URI from step 4                            │
│      - Language: auto-detect OR specified code                  │
│    • Poll job status every 2 seconds                            │
│    • Update progress: 50-85%                                     │
│    • When COMPLETED:                                             │
│      - Download transcript JSON from S3                         │
│      - Parse results                                             │
└────────────┬────────────────────────────────────────────────────┘
             │
             ▼
┌─────────────────────────────────────────────────────────────────┐
│ 6. SUBTITLE GENERATION (Backend)                                │
│    • Extract word-level timestamps from transcript              │
│    • Build segments (12 words per subtitle)                     │
│    • Convert to SRT format                                      │
│    • Convert to VTT format                                      │
│    • Save original language files:                              │
│      - outputs/subtitles/{file_id}_{lang}.srt                   │
│      - outputs/subtitles/{file_id}_{lang}.vtt                   │
│    • Update progress: 85-90%                                     │
└────────────┬────────────────────────────────────────────────────┘
             │
             ▼
┌─────────────────────────────────────────────────────────────────┐
│ 7. TRANSLATION (Backend)                                        │
│    • For each target language:                                  │
│      - Call AWS Translate API for each segment                  │
│      - Preserve original timestamps                             │
│      - Generate SRT/VTT files                                   │
│    • Update progress: 90-100%                                    │
│    • Return all language variants                               │
└────────────┬────────────────────────────────────────────────────┘
             │
             ▼
┌─────────────────────────────────────────────────────────────────┐
│ 8. FRONTEND DISPLAY                                             │
│    • Display video with subtitle preview                        │
│    • Show language tabs for all available subtitles             │
│    • Enable download buttons (SRT/VTT)                          │
│    • Stream video with HLS/DASH player                          │
│    • Overlay selected subtitle track                            │
└─────────────────────────────────────────────────────────────────┘
```

---

## AWS Integration

### Required AWS Services

1. **Amazon S3**
   - Purpose: Store uploaded audio files and transcription results
   - Configuration: `AWS_S3_BUCKET` environment variable
   - Permissions needed:
     - `s3:PutObject` - Upload audio files
     - `s3:GetObject` - Download transcription results
     - `s3:CreateMultipartUpload` - Large file uploads
     - `s3:CompleteMultipartUpload` - Finalize multipart uploads

2. **Amazon Transcribe**
   - Purpose: Speech-to-text conversion with auto language detection
   - Permissions needed:
     - `transcribe:StartTranscriptionJob`
     - `transcribe:GetTranscriptionJob`
     - `transcribe:ListTranscriptionJobs`
   - Supported languages: 70+ (see TRANSCRIBE_LANGUAGE_OPTIONS)

3. **Amazon Translate**
   - Purpose: Translate subtitles to 70+ languages
   - Permissions needed:
     - `translate:TranslateText`
   - Supported languages: 75+ (see TRANSLATE_LANGUAGE_OPTIONS)

### Language Code Mapping

**Transcribe → Translate Conversion**:
```python
TRANSLATE_LANGUAGE_MAP = {
    'zh-CN': 'zh',       # Chinese Simplified
    'zh-TW': 'zh-TW',    # Chinese Traditional
    'pt-BR': 'pt',       # Portuguese Brazil → Generic
    'pt-PT': 'pt',       # Portuguese Portugal → Generic
    'en-US': 'en',       # English US → Generic
    'en-GB': 'en',       # English UK → Generic
    'es-US': 'es',       # Spanish US → Generic
    'es-ES': 'es',       # Spanish Spain → Generic
    'fr-CA': 'fr',       # French Canada → Generic
    'fr-FR': 'fr',       # French France → Generic
    'de-DE': 'de'        # German → Generic
}
```

---

## API Reference

### Endpoints

#### 1. Upload Video

```http
POST /upload
Content-Type: multipart/form-data

Parameters:
  - file: Video file (mp4, mov, mkv, avi, webm, flv)
  - max_size: 5GB

Response 200:
{
  "file_id": "abc123",
  "filename": "video.mp4",
  "message": "File uploaded successfully",
  "size": 104857600
}

Response 400:
{
  "error": "No file selected" | "Unsupported file type"
}
```

#### 2. Extract Audio

```http
POST /extract-audio
Content-Type: application/json

Request:
{
  "file_id": "abc123"
}

Response 200:
{
  "audio_id": "abc123",
  "audio_path": "audio/abc123.mp3",
  "duration": 120.5,
  "message": "Audio extracted successfully"
}

Response 404:
{
  "error": "Video file not found"
}
```

#### 3. Generate Subtitles

```http
POST /generate-subtitles
Content-Type: application/json

Request:
{
  "file_id": "abc123",
  "source_language": "auto",  // or specific code like "en-US"
  "target_languages": ["es", "fr", "hi"],
  "language_options": ["en-US", "es-ES", "fr-FR"]  // for auto-detection
}

Response 200:
{
  "file_id": "abc123",
  "detected_language": "en-US",
  "subtitles": [
    {
      "languageCode": "en",
      "languageLabel": "English",
      "srtPath": "outputs/subtitles/abc123_en.srt",
      "vttPath": "outputs/subtitles/abc123_en.vtt",
      "srtUrl": "/download/abc123?lang=en&format=srt",
      "vttUrl": "/download/abc123?lang=en&format=vtt"
    },
    {
      "languageCode": "es",
      "languageLabel": "Spanish",
      "srtPath": "outputs/subtitles/abc123_es.srt",
      "vttPath": "outputs/subtitles/abc123_es.vtt",
      "srtUrl": "/download/abc123?lang=es&format=srt",
      "vttUrl": "/download/abc123?lang=es&format=vtt"
    }
  ],
  "segments": [
    {
      "index": 1,
      "start_time": 0.0,
      "end_time": 5.24,
      "text": "This is the first subtitle segment with approximately twelve words."
    }
  ],
  "accuracy": {
    "audioDuration": 120.5,
    "subtitleDuration": 119.8,
    "driftSeconds": 0.7,
    "withinThreshold": true
  }
}

Response 400:
{
  "error": "AWS Transcribe is not configured. Please set AWS credentials and S3 bucket."
}
```

#### 4. Get Progress

```http
GET /progress/<file_id>

Response 200:
{
  "progress": 75,
  "message": "AWS Transcribe job in progress…",
  "stage": "transcribe",
  "detected_language": "en-US",
  "available_source_languages": ["en-US", "es-ES"],
  "readyForTranscription": true,
  "subtitlesInProgress": true,
  "subtitlesAvailable": false
}
```

#### 5. Download Subtitle

```http
GET /download/<file_id>?lang=<language_code>&format=<srt|vtt>

Response 200:
Content-Type: text/plain; charset=utf-8
Content-Disposition: attachment; filename="subtitles_en.srt"

1
00:00:00,000 --> 00:00:05,240
This is the first subtitle segment.
```

#### 6. Stream Audio

```http
GET /stream-audio/<file_id>
Range: bytes=0-1024

Response 206 Partial Content:
Content-Type: audio/mpeg
Content-Range: bytes 0-1024/104857600
Accept-Ranges: bytes

<binary audio data>
```

#### 7. Health Check

```http
GET /health

Response 200:
{
  "status": "healthy",
  "ffmpeg": true,
  "ffprobe": true,
  "aws_configured": true,
  "services": {
    "s3": true,
    "transcribe": true,
    "translate": true
  }
}
```

#### 8. API Status

```http
GET /api-status

Response 200:
{
  "service": "AI Subtitle Service",
  "version": "1.0",
  "status": "running",
  "capabilities": {
    "audio_extraction": true,
    "aws_transcribe": true,
    "aws_translate": true,
    "streaming": true
  },
  "supported_formats": ["mp4", "mov", "mkv", "avi", "webm", "flv"],
  "max_file_size": 5368709120,
  "supported_languages": {
    "transcribe": 40,
    "translate": 75
  }
}
```

---

## Configuration

### Environment Variables

```bash
# AWS Credentials (Required for AWS features)
AWS_ACCESS_KEY_ID=your_access_key
AWS_SECRET_ACCESS_KEY=your_secret_key
AWS_REGION=us-east-1
AWS_S3_BUCKET=your-bucket-name

# FFmpeg Binary Paths (Optional - auto-detected)
FFMPEG_BINARY=/opt/homebrew/bin/ffmpeg
FFMPEG_PATH=/usr/local/bin/ffmpeg
FFPROBE_BINARY=/opt/homebrew/bin/ffprobe
FFPROBE_PATH=/usr/local/bin/ffprobe

# Service Configuration
SUBTITLE_SERVICE_PORT=5001
MAX_CONTENT_LENGTH=5368709120  # 5GB
CORS_ALLOWED_ORIGINS=http://localhost:3000,http://192.168.1.100:3000

# Processing Defaults
DEFAULT_WORDS_PER_SEGMENT=12
TRANSCRIBE_POLL_INTERVAL=2
TRANSCRIBE_MAX_WAIT_TIME=300
```

### Frontend Configuration

```bash
# React Environment Variables (.env)
REACT_APP_SUBTITLE_API_BASE=http://localhost:5001
REACT_APP_API_BASE=http://localhost:3000
```

---

## Deployment

### Prerequisites

1. **System Requirements**
   - Python 3.11 or higher
   - FFmpeg 4.0+ with libx264 and AAC support
   - 4GB RAM minimum (8GB recommended)
   - 50GB disk space for media storage

2. **AWS Setup**
   - IAM user with S3, Transcribe, and Translate permissions
   - S3 bucket for audio and transcription storage
   - Region with Transcribe support (us-east-1, eu-west-1, etc.)

3. **Network Requirements**
   - Outbound HTTPS (443) to AWS services
   - Inbound HTTP (5001) for API access

### Installation Steps

```bash
# 1. Clone repository
cd /path/to/mediaGenAI/aiSubtitle

# 2. Create virtual environment
python3 -m venv .venv
source .venv/bin/activate  # macOS/Linux
# .venv\Scripts\activate  # Windows

# 3. Install dependencies
pip install -r requirements.txt

# 4. Configure environment
cp .env.example .env
# Edit .env with your AWS credentials

# 5. Verify FFmpeg installation
ffmpeg -version
ffprobe -version

# 6. Test the service
python aiSubtitle.py

# 7. Access the service
# Backend: http://localhost:5001
# Health check: http://localhost:5001/health
```

### Production Deployment

**Using systemd (Linux)**:

```ini
# /etc/systemd/system/ai-subtitle.service
[Unit]
Description=AI Subtitle Service
After=network.target

[Service]
Type=simple
User=www-data
WorkingDirectory=/opt/mediaGenAI/aiSubtitle
Environment="PATH=/opt/mediaGenAI/.venv/bin:/usr/local/bin:/usr/bin"
ExecStart=/opt/mediaGenAI/.venv/bin/python aiSubtitle.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl daemon-reload
sudo systemctl enable ai-subtitle
sudo systemctl start ai-subtitle
sudo systemctl status ai-subtitle
```

**Using the provided scripts**:

```bash
# Start all services
./start-all.sh

# Start only backend services
./start-backend.sh

# Stop all services
./stop-all.sh

# Check logs
tail -f ai-subtitle.log
```

---

## Troubleshooting

### Common Issues

#### 1. FFmpeg Not Found

**Symptoms**:
```
FFmpeg binary not configured or found on PATH.
```

**Solutions**:
```bash
# macOS (Homebrew)
brew install ffmpeg

# Ubuntu/Debian
sudo apt-get update
sudo apt-get install ffmpeg

# Set explicit path
export FFMPEG_BINARY=/usr/local/bin/ffmpeg
export FFPROBE_BINARY=/usr/local/bin/ffprobe
```

#### 2. AWS Credentials Not Working

**Symptoms**:
```
AWS Transcribe is not configured. Please set AWS credentials and S3 bucket.
```

**Solutions**:
```bash
# Verify credentials
aws sts get-caller-identity

# Check .env file
cat .env | grep AWS

# Ensure all required variables are set
AWS_ACCESS_KEY_ID=AKIA...
AWS_SECRET_ACCESS_KEY=...
AWS_S3_BUCKET=your-bucket-name
```

#### 3. Zero-Byte Audio File

**Symptoms**:
```
Extracted audio file is empty; removing the zero-byte file
```

**Solutions**:
- Check if video has audio track: `ffprobe -i video.mp4`
- Verify FFmpeg audio codecs: `ffmpeg -codecs | grep mp3`
- Try different video file
- Check disk space: `df -h`

#### 4. Transcription Job Timeout

**Symptoms**:
```
Transcription job exceeded maximum wait time (300 seconds)
```

**Solutions**:
- Increase timeout: `TRANSCRIBE_MAX_WAIT_TIME=600`
- Check AWS Transcribe console for job status
- Verify S3 bucket permissions
- Check AWS service health: https://status.aws.amazon.com/

#### 5. CORS Errors in Browser

**Symptoms**:
```
Access to XMLHttpRequest blocked by CORS policy
```

**Solutions**:
```python
# Update CORS configuration in aiSubtitle.py
CORS(app, 
     origins=['http://localhost:3000', 'http://your-domain.com'],
     methods=['GET', 'POST', 'OPTIONS'],
     allow_headers=['Content-Type', 'Range'],
     expose_headers=['Accept-Ranges', 'Content-Range', 'Content-Length']
)
```

#### 6. Large File Upload Failures

**Symptoms**:
```
413 Request Entity Too Large
```

**Solutions**:
```python
# Increase max upload size in aiSubtitle.py
app.config['MAX_CONTENT_LENGTH'] = 10 * 1024 * 1024 * 1024  # 10GB
```

#### 7. Subtitle Timing Drift

**Symptoms**:
- Subtitles out of sync with audio
- `withinThreshold: false` in accuracy metrics

**Solutions**:
- Adjust `words_per_segment` (default 12)
- Check audio extraction quality
- Verify video frame rate consistency
- Use higher quality source video

---

## Performance Optimization

### Backend Optimizations

1. **Multipart Upload Tuning**
   ```python
   # Adjust part size based on network speed
   part_size = 50 * 1024 * 1024   # 50MB for slower connections
   part_size = 200 * 1024 * 1024  # 200MB for fast connections
   ```

2. **FFmpeg Preset Optimization**
   ```bash
   # Faster extraction (lower quality)
   -preset ultrafast
   
   # Balanced (recommended)
   -preset veryfast
   
   # Better quality (slower)
   -preset medium
   ```

3. **Concurrent Translation**
   ```python
   # Use ThreadPoolExecutor for parallel translation
   from concurrent.futures import ThreadPoolExecutor
   
   with ThreadPoolExecutor(max_workers=5) as executor:
       futures = [
           executor.submit(translate_segments, segments, src, tgt)
           for tgt in target_languages
       ]
       results = [f.result() for f in futures]
   ```

4. **Progress Update Throttling**
   ```python
   # Update progress max once per second
   last_update = 0
   if time.time() - last_update > 1.0:
       update_progress(file_id, progress)
       last_update = time.time()
   ```

### Frontend Optimizations

1. **Debounce Progress Polling**
   ```javascript
   // Poll every 2 seconds instead of 1 second
   const interval = setInterval(pollProgress, 2000);
   ```

2. **Lazy Load Video Player**
   ```javascript
   // Only load HLS.js when video is ready
   import('hls.js').then(({ default: Hls }) => {
       if (Hls.isSupported()) {
           const hls = new Hls();
           // ...
       }
   });
   ```

3. **Memoize Language Options**
   ```javascript
   const languageOptions = useMemo(() => 
       TRANSLATE_LANGUAGE_OPTIONS.filter(option => 
           selectedLanguages.includes(option.value)
       ),
       [selectedLanguages]
   );
   ```

4. **Virtual Scrolling for Large Subtitle Lists**
   ```javascript
   // Use react-window for 100+ subtitle entries
   import { FixedSizeList } from 'react-window';
   ```

### Caching Strategies

1. **Browser Caching**
   ```python
   # Set cache headers for static files
   @app.after_request
   def add_cache_headers(response):
       if request.path.startswith('/download/'):
           response.cache_control.max_age = 3600  # 1 hour
       return response
   ```

2. **CDN Integration**
   - Serve HLS/DASH segments from CloudFront
   - Cache subtitle files (SRT/VTT)
   - Edge caching for API responses

3. **Local Storage**
   ```javascript
   // Cache generated subtitles in browser
   localStorage.setItem(`subtitles_${fileId}`, JSON.stringify(subtitles));
   ```

---

## Security Considerations

### Backend Security

1. **File Upload Validation**
   ```python
   # Validate MIME type, not just extension
   import magic
   mime = magic.from_file(filepath, mime=True)
   if mime not in ['video/mp4', 'video/quicktime']:
       raise ValueError('Invalid file type')
   ```

2. **Path Traversal Prevention**
   ```python
   # Sanitize filenames
   filename = secure_filename(filename)
   # Prevent directory traversal
   filepath = os.path.abspath(os.path.join(UPLOAD_FOLDER, filename))
   if not filepath.startswith(UPLOAD_FOLDER):
       raise ValueError('Invalid path')
   ```

3. **Rate Limiting**
   ```python
   from flask_limiter import Limiter
   
   limiter = Limiter(app, key_func=get_remote_address)
   
   @app.route('/upload')
   @limiter.limit("10 per hour")
   def upload():
       # ...
   ```

4. **AWS Credentials Protection**
   - Never commit `.env` files
   - Use IAM roles when deployed on EC2
   - Rotate credentials regularly
   - Use least-privilege permissions

### Frontend Security

1. **XSS Prevention**
   ```javascript
   // React automatically escapes text content
   <div>{userInput}</div>  // Safe
   
   // Never use dangerouslySetInnerHTML with user input
   <div dangerouslySetInnerHTML={{ __html: userInput }} />  // Unsafe
   ```

2. **HTTPS Enforcement**
   ```javascript
   if (window.location.protocol === 'http:' && 
       window.location.hostname !== 'localhost') {
       window.location.protocol = 'https:';
   }
   ```

---

## Monitoring & Logging

### Backend Logging

```python
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('ai-subtitle.log'),
        logging.StreamHandler()
    ]
)

# Log important events
app.logger.info(f"Video uploaded: {filename} ({file_size} bytes)")
app.logger.info(f"Transcription job started: {job_name}")
app.logger.error(f"FFmpeg extraction failed: {error}")
```

### Metrics to Monitor

1. **Upload Metrics**
   - Upload success rate
   - Average upload time
   - File size distribution

2. **Processing Metrics**
   - Audio extraction success rate
   - Average transcription time
   - Translation success rate

3. **AWS Metrics**
   - S3 upload success rate
   - Transcribe job completion time
   - Translate API latency

4. **Resource Metrics**
   - Disk usage (uploads, audio, outputs)
   - Memory usage
   - CPU usage during FFmpeg processing

---

## Testing

### Backend Unit Tests

```python
import unittest
from aiSubtitle import extract_audio_from_video, segments_to_srt

class TestSubtitleService(unittest.TestCase):
    
    def test_audio_extraction(self):
        result = extract_audio_from_video('test_video.mp4', 'test_audio.mp3')
        self.assertTrue(result)
        self.assertTrue(os.path.exists('test_audio.mp3'))
    
    def test_srt_formatting(self):
        segments = [
            {'index': 1, 'start_time': 0.0, 'end_time': 5.24, 'text': 'Hello world'}
        ]
        srt = segments_to_srt(segments)
        self.assertIn('00:00:00,000 --> 00:00:05,240', srt)
        self.assertIn('Hello world', srt)
    
    def test_vtt_conversion(self):
        srt = "1\n00:00:00,000 --> 00:00:05,240\nHello world"
        vtt = convert_srt_to_vtt(srt)
        self.assertTrue(vtt.startswith('WEBVTT'))
        self.assertIn('00:00:00.000 --> 00:00:05.240', vtt)

if __name__ == '__main__':
    unittest.main()
```

### Frontend Tests

```javascript
import { render, screen, fireEvent } from '@testing-library/react';
import AISubtitling from './AISubtitling';

test('renders upload button', () => {
    render(<AISubtitling />);
    const uploadButton = screen.getByText(/upload video/i);
    expect(uploadButton).toBeInTheDocument();
});

test('shows progress bar during processing', () => {
    render(<AISubtitling />);
    // Simulate file upload
    const fileInput = screen.getByLabelText(/select video/i);
    fireEvent.change(fileInput, { target: { files: [new File([], 'test.mp4')] } });
    // Check progress bar appears
    expect(screen.getByRole('progressbar')).toBeInTheDocument();
});
```

---

## Appendix

### Supported Languages

**AWS Transcribe** (40+ languages):
- English (US, UK, Australia, India, Ireland, New Zealand)
- Spanish (Spain, US)
- French (France, Canada)
- German, Italian, Portuguese (Brazil, Portugal)
- Chinese (Simplified, Traditional)
- Japanese, Korean, Hindi, Arabic, Russian
- And 25+ more...

**AWS Translate** (75+ languages):
- All major European languages
- Asian languages (Chinese, Japanese, Korean, Hindi, etc.)
- Middle Eastern languages (Arabic, Hebrew, Farsi)
- African languages (Swahili, Zulu, Yoruba, etc.)
- And many more...

### File Size Limits

- **Maximum upload**: 5GB (configurable)
- **Recommended**: <2GB for faster processing
- **Multipart threshold**: 100MB
- **S3 single upload limit**: 5GB
- **S3 multipart upload limit**: 5TB

### Subtitle Formats

**SRT (SubRip)**:
- Most widely supported
- Simple text format
- Comma for milliseconds (00:00:05,240)
- Numbered sequences

**VTT (WebVTT)**:
- Web standard (HTML5 video)
- Period for milliseconds (00:00:05.240)
- Supports styling and positioning
- WEBVTT header required

### FFmpeg Codec Requirements

**Required codecs**:
- libx264 (H.264 video encoding)
- AAC (audio encoding)
- libmp3lame (MP3 encoding)

**Check codec availability**:
```bash
ffmpeg -codecs | grep -i "h264\|aac\|mp3"
```

---

## Quick Reference Commands

### Service Management

```bash
# Start service
python aiSubtitle.py

# Using scripts
./start-backend.sh         # All backend services
./start-all.sh            # Backend + frontend

# Stop services
./stop-backend.sh
./stop-all.sh

# View logs
tail -f ai-subtitle.log

# Check health
curl http://localhost:5001/health
```

### Testing

```bash
# Upload video
curl -X POST http://localhost:5001/upload \
  -F "file=@video.mp4"

# Extract audio
curl -X POST http://localhost:5001/extract-audio \
  -H "Content-Type: application/json" \
  -d '{"file_id":"abc123"}'

# Generate subtitles
curl -X POST http://localhost:5001/generate-subtitles \
  -H "Content-Type: application/json" \
  -d '{
    "file_id":"abc123",
    "source_language":"auto",
    "target_languages":["es","fr","hi"]
  }'

# Check progress
curl http://localhost:5001/progress/abc123

# Download subtitle
curl "http://localhost:5001/download/abc123?lang=en&format=srt" -o subtitle.srt
```

### Debugging

```bash
# Check FFmpeg
which ffmpeg
ffmpeg -version

# Check Python environment
python --version
pip list | grep -i "flask\|boto3"

# Check AWS credentials
aws sts get-caller-identity
aws s3 ls s3://your-bucket-name

# Test audio extraction
ffmpeg -i video.mp4 -acodec mp3 -ab 128k -ac 2 -ar 44100 -vn test.mp3

# Check disk space
df -h
du -sh uploads/ audio/ outputs/
```

---

**End of AI Subtitle Service Reference Guide**
