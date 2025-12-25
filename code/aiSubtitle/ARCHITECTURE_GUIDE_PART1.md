# AI Subtitle/Dubbing System - Architecture & Logic Guide
## Part 1: System Overview & Architecture

**Document Version:** 1.0  
**Last Updated:** October 24, 2025  
**System:** MediaGenAI - AI Subtitle Generation & Translation Service

---

## Table of Contents (Part 1)

1. [Executive Summary](#executive-summary)
2. [System Architecture Overview](#system-architecture-overview)
3. [Technology Stack](#technology-stack)
4. [Core Components](#core-components)
5. [Data Flow Architecture](#data-flow-architecture)
6. [AWS Services Integration](#aws-services-integration)

---

## Executive Summary

The AI Subtitle/Dubbing System is a comprehensive video processing platform that provides:

- **Automatic Speech Recognition (ASR)** using AWS Transcribe
- **Multi-language Translation** using AWS Translate
- **Video Processing** with FFmpeg
- **Adaptive Streaming** via HLS/DASH protocols
- **Real-time Progress Tracking** with WebSocket-like updates
- **Multi-format Subtitle Generation** (SRT, VTT, TTML, DFXP)

### Key Capabilities

✅ **Video Upload & Processing** - Handles videos up to 5GB  
✅ **Audio Extraction** - MP3 conversion with configurable quality  
✅ **Speech-to-Text** - AWS Transcribe with 40+ language support  
✅ **Translation** - AWS Translate for 75+ target languages  
✅ **Adaptive Streaming** - HLS (HTTP Live Streaming) for efficient delivery  
✅ **Subtitle Formats** - SRT, WebVTT, TTML, DFXP support  
✅ **Progress Tracking** - Real-time status updates during processing  

---

## System Architecture Overview

### High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                     CLIENT LAYER (React)                         │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐         │
│  │ Video Upload │  │ Player UI    │  │ Subtitle Mgmt│         │
│  └──────────────┘  └──────────────┘  └──────────────┘         │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                  APPLICATION LAYER (Flask)                       │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐         │
│  │ REST API     │  │ File Handler │  │ Progress Mgr │         │
│  └──────────────┘  └──────────────┘  └──────────────┘         │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                   PROCESSING LAYER (FFmpeg)                      │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐         │
│  │ Audio Extract│  │ Video Segment│  │ Stream Gen   │         │
│  └──────────────┘  └──────────────┘  └──────────────┘         │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                     AWS SERVICES LAYER                           │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐         │
│  │ S3 Storage   │  │ Transcribe   │  │ Translate    │         │
│  └──────────────┘  └──────────────┘  └──────────────┘         │
└─────────────────────────────────────────────────────────────────┘
```

### Architectural Layers

#### 1. **Client Layer** (Frontend - React)
- Single Page Application (SPA) using React 18
- Styled Components for UI styling
- Axios for HTTP communication
- HLS.js and dash.js for adaptive streaming
- Real-time progress polling

#### 2. **Application Layer** (Backend - Flask)
- RESTful API endpoints
- File upload/download handling
- Progress tracking system
- CORS middleware for cross-origin requests
- Session management

#### 3. **Processing Layer** (FFmpeg)
- Audio extraction (MP3)
- Video segmentation
- HLS playlist generation
- Format conversion

#### 4. **AWS Services Layer**
- **S3**: Audio file storage for transcription
- **Transcribe**: Speech-to-text conversion
- **Translate**: Multi-language translation

---

## Technology Stack

### Backend Technologies

| Component | Technology | Version | Purpose |
|-----------|-----------|---------|---------|
| **Runtime** | Python | 3.11+ | Core backend language |
| **Web Framework** | Flask | 3.0+ | REST API server |
| **CORS** | Flask-CORS | 4.0+ | Cross-origin resource sharing |
| **AWS SDK** | boto3 | 1.40+ | AWS service integration |
| **Video Processing** | FFmpeg | 6.0+ | Media transcoding |
| **Environment** | python-dotenv | 1.0+ | Configuration management |

### Frontend Technologies

| Component | Technology | Version | Purpose |
|-----------|-----------|---------|---------|
| **Framework** | React | 18.2+ | UI framework |
| **Styling** | styled-components | 6.1+ | CSS-in-JS styling |
| **HTTP Client** | axios | 1.6+ | API communication |
| **HLS Player** | hls.js | 1.5+ | HTTP Live Streaming |
| **DASH Player** | dashjs | 4.7+ | MPEG-DASH streaming |
| **State Management** | React Hooks | Built-in | Component state |

### Infrastructure Requirements

```yaml
System Requirements:
  CPU: 4+ cores recommended
  RAM: 8GB+ recommended
  Storage: 100GB+ for video processing
  Network: High-speed internet for AWS API calls

Software Requirements:
  Python: 3.11+
  Node.js: 18+
  FFmpeg: 6.0+
  
AWS Requirements:
  S3 Bucket: For audio file storage
  IAM Credentials: With Transcribe, Translate, S3 permissions
  Region: us-east-1 (or configured region)
```

---

## Core Components

### Backend Components (`aiSubtitle.py`)

#### 1. **Flask Application Core**

```python
app = Flask(__name__)
CORS(app, 
     origins=['http://localhost:3000'],
     methods=['GET', 'POST', 'OPTIONS'],
     allow_headers=['Content-Type', 'Range'],
     expose_headers=['Accept-Ranges', 'Content-Range', 'Content-Length']
)
```

**Configuration:**
- Max file size: 5GB
- Upload folder: `uploads/`
- Output folder: `outputs/`
- Supported formats: MP4, AVI, MOV, MKV, WebM, FLV

#### 2. **AWS Service Clients**

```python
# AWS Transcribe Client
transcribe_client = boto3.client(
    'transcribe',
    aws_access_key_id=aws_access_key,
    aws_secret_access_key=aws_secret_key,
    region_name=aws_region
)

# AWS S3 Client
s3_client = boto3.client('s3', ...)

# AWS Translate Client
translate_client = boto3.client('translate', ...)
```

#### 3. **Progress Tracking System**

```python
progress_data = {}  # In-memory progress store
progress_lock = threading.Lock()  # Thread-safe access

def update_progress(file_id, progress, message=None, **extra):
    """Update progress for a specific file_id."""
    with progress_lock:
        entry = progress_data.get(file_id, {})
        entry['progress'] = progress
        if message is not None:
            entry['message'] = message
        progress_data[file_id] = entry
```

#### 4. **FFmpeg Integration**

```python
FFMPEG_BINARY = _resolve_binary(
    'ffmpeg',
    ('FFMPEG_BINARY', 'FFMPEG_PATH'),
    ('/opt/homebrew/bin/ffmpeg', '/usr/local/bin/ffmpeg')
)
```

**Binary Resolution Strategy:**
1. Check environment variables
2. Search system PATH
3. Check common installation locations
4. Fallback to None (graceful degradation)

---

## Data Flow Architecture

### End-to-End Processing Flow

```
┌─────────────┐
│   User      │
│ Uploads     │
│   Video     │
└──────┬──────┘
       │
       ▼
┌─────────────────────────────────────────────┐
│ Step 1: File Upload & Validation            │
│ • Check file size (<5GB)                    │
│ • Validate extension (mp4, avi, mov, etc)   │
│ • Generate unique file_id (UUID)            │
│ • Save to uploads/ directory                │
└──────┬──────────────────────────────────────┘
       │
       ▼
┌─────────────────────────────────────────────┐
│ Step 2: Audio Extraction                    │
│ • FFmpeg extracts audio track               │
│ • Convert to MP3 format                     │
│ • Save to audio/ directory                  │
│ • Progress: 10% → 20%                       │
└──────┬──────────────────────────────────────┘
       │
       ▼
┌─────────────────────────────────────────────┐
│ Step 3: AWS S3 Upload                       │
│ • Upload MP3 to S3 bucket                   │
│ • Generate S3 URI                           │
│ • Set public-read ACL                       │
│ • Progress: 20% → 30%                       │
└──────┬──────────────────────────────────────┘
       │
       ▼
┌─────────────────────────────────────────────┐
│ Step 4: AWS Transcribe Job                  │
│ • Create transcription job                  │
│ • Configure language (auto or specified)    │
│ • Poll for completion (async)               │
│ • Progress: 30% → 70%                       │
└──────┬──────────────────────────────────────┘
       │
       ▼
┌─────────────────────────────────────────────┐
│ Step 5: Subtitle Generation                 │
│ • Download transcription JSON               │
│ • Parse segments and timestamps             │
│ • Generate SRT format                       │
│ • Save to outputs/subtitles/                │
│ • Progress: 70% → 80%                       │
└──────┬──────────────────────────────────────┘
       │
       ▼
┌─────────────────────────────────────────────┐
│ Step 6: HLS Streaming (Optional)            │
│ • Segment video into .ts chunks             │
│ • Generate m3u8 playlist                    │
│ • Save to outputs/streams/                  │
│ • Progress: 80% → 90%                       │
└──────┬──────────────────────────────────────┘
       │
       ▼
┌─────────────────────────────────────────────┐
│ Step 7: Translation (Optional)              │
│ • Read original SRT file                    │
│ • Translate each subtitle segment           │
│ • Generate new SRT for target language      │
│ • Progress: 90% → 100%                      │
└──────┬──────────────────────────────────────┘
       │
       ▼
┌─────────────┐
│   Results   │
│  Available  │
│  for User   │
└─────────────┘
```

---

## AWS Services Integration

### AWS Transcribe Configuration

**Service:** Amazon Transcribe  
**Purpose:** Convert speech in audio to text  
**API Version:** 2017-10-26

#### Transcription Job Parameters

```python
job_params = {
    'TranscriptionJobName': f'subtitle-job-{file_id}-{timestamp}',
    'LanguageCode': language_code,  # or 'en-US', 'es-ES', etc.
    'MediaFormat': 'mp3',
    'Media': {
        'MediaFileUri': s3_audio_uri
    },
    'OutputBucketName': aws_s3_bucket,
    'Settings': {
        'ShowSpeakerLabels': False,
        'MaxSpeakerLabels': 2
    }
}
```

#### Language Detection

- **Auto-detect mode:** LanguageCode not specified
- **Specified mode:** Use AWS Transcribe language codes (e.g., `en-US`, `es-ES`)
- **Supported languages:** 40+ including English, Spanish, French, German, Hindi, Japanese, etc.

### AWS Translate Configuration

**Service:** Amazon Translate  
**Purpose:** Translate subtitle text between languages  
**API Version:** 2017-07-01

#### Translation Parameters

```python
translate_params = {
    'Text': subtitle_text,
    'SourceLanguageCode': source_language,  # e.g., 'en'
    'TargetLanguageCode': target_language   # e.g., 'es'
}
```

#### Supported Languages

- **75+ languages** including:
  - European: English, Spanish, French, German, Italian, Portuguese
  - Asian: Chinese, Japanese, Korean, Hindi, Thai, Vietnamese
  - Middle Eastern: Arabic, Hebrew, Farsi
  - And many more...

### AWS S3 Storage Pattern

**Bucket Structure:**
```
s3://your-bucket/
├── audio/
│   └── audio_{file_id}.mp3
├── transcriptions/
│   └── job_{job_name}.json
└── outputs/
    └── subtitles_{file_id}.srt
```

**Access Pattern:**
- **Upload:** Public-read ACL for Transcribe access
- **Download:** Pre-signed URLs for temporary access
- **Cleanup:** Manual or lifecycle policies

---

## Next Document

➡️ **Part 2: API Endpoints & Backend Logic**  
Covers detailed API specifications, request/response formats, and backend processing logic.

---

*End of Part 1*
