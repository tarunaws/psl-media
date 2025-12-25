# Scene Summarization Service - Complete Technical Reference
## Part 1 of 4: Executive Summary & Backend Architecture

**MediaGenAI Platform - Service Documentation**  
**Document Version:** 1.0  
**Service Port:** 5005  
**Last Updated:** October 21, 2025

---

## Document Navigation

- **Part 1** (this document): Executive Summary, Architecture Overview, Backend Deep Dive
- **Part 2**: LLM Integration, TTS Synthesis, Result Storage
- **Part 3**: Frontend Architecture, Processing Phases, UI Components
- **Part 4**: AWS Integration, API Reference, Configuration, Deployment, Troubleshooting

---

## Table of Contents - Part 1

1. [Executive Summary](#1-executive-summary)
2. [Architecture Overview](#2-architecture-overview)
3. [System Components](#3-system-components)
4. [Backend Architecture - File Upload & Validation](#4-backend-architecture---file-upload--validation)
5. [Backend Architecture - Media Processing](#5-backend-architecture---media-processing)
6. [Backend Architecture - Vision Analysis](#6-backend-architecture---vision-analysis)

---

## 1. Executive Summary

### 1.1 Service Purpose

The Scene Summarization Service is an intelligent video/image analysis platform that combines computer vision, large language models, and neural text-to-speech to automatically generate rich narrative summaries of visual media. It extracts comprehensive scene metadata, composes natural-language recaps, and renders voiceover audio—all in a single automated pipeline.

**Core Capabilities:**
- **Multi-Modal Input**: Accepts images (JPG, PNG, WebP, GIF, BMP, TIFF) and videos (MP4, MOV, AVI, MKV, WebM, FLV, WMV, MPEG)
- **Computer Vision Analysis**: AWS Rekognition for label detection, face analysis, celebrity recognition, text detection
- **Frame Extraction**: FFmpeg-powered video sampling at configurable intervals (default: 1.7s stride, max 120 frames)
- **Intelligent Aggregation**: Context-aware classification of objects, scenes, activities with confidence scoring
- **LLM Summarization**: AWS Bedrock (Llama3-70B) generates natural-language summaries with highlights and SSML
- **Neural TTS**: AWS Polly synthesizes voiceover audio from generated SSML scripts
- **S3 Integration**: Optional video upload to S3 for long-term storage and reference

**Use Cases:**
1. **Content Cataloging**: Automatically tag and summarize video libraries
2. **Accessibility**: Generate audio descriptions for visual content
3. **Media Production**: Quick scene breakdowns for editing workflows
4. **Social Media**: Create engaging narrative previews from video clips
5. **Surveillance/Security**: Summarize security footage with context
6. **Education**: Generate descriptive summaries of educational videos

### 1.2 Technology Stack

**Backend Components:**
- **Framework**: Flask 3.0+ (Python 3.8+)
- **AWS Services**: 
  - Rekognition (computer vision - us-east-1)
  - Bedrock Runtime (LLM inference - us-east-1)
  - Polly (neural TTS - us-west-2)
  - S3 (optional video storage - us-east-1)
- **Media Processing**: FFmpeg 4.0+, FFprobe for video metadata
- **Key Libraries**: 
  - boto3 (AWS SDK)
  - werkzeug (secure file handling)
  - flask-cors (cross-origin requests)
  - python-dotenv (environment configuration)

**Frontend Components:**
- **Framework**: React 18+ with Hooks
- **Styling**: styled-components 5.3+
- **HTTP Client**: axios with upload progress tracking
- **Features**: 
  - Drag-and-drop file upload
  - Real-time progress tracking (5-phase timeline)
  - Audio playback with download
  - Metadata visualization (cards, tags, JSON)

### 1.3 Key Features

#### 1.3.1 Comprehensive Vision Analysis

**Label Detection:**
- AWS Rekognition `detect_labels` API
- Up to 25 labels per frame
- 55% minimum confidence threshold
- Parent hierarchy tracking (e.g., "Dog" → parent: "Animal", "Pet")
- Categories: Objects, Scenes, Activities

**Face Analysis:**
- AWS Rekognition `detect_faces` API with ALL attributes
- Demographics: Gender, age range estimation
- Emotions: 7 types (HAPPY, SAD, ANGRY, CONFUSED, DISGUSTED, SURPRISED, CALM)
- Attributes: Beard, mustache, sunglasses, smile
- Confidence scoring for all detections

**Celebrity Recognition:**
- AWS Rekognition `recognize_celebrities` API
- Match confidence percentage
- Reference URLs (Wikipedia, IMDB, etc.)
- Up to 3 URLs per celebrity

**Text Detection (OCR):**
- AWS Rekognition `detect_text` API
- LINE-type detections only (filters out individual words)
- Unique text lines across all frames
- On-screen text capture for titles, subtitles, signage

#### 1.3.2 Intelligent Frame Sampling

**Video Processing:**
```
Frame Extraction Logic:
1. Probe video duration with FFprobe
2. Calculate stride: max(0.5s, FRAME_STRIDE_SECONDS)
3. Estimate frame count: ceil(duration / stride)
4. Cap at MAX_SCENE_FRAMES (120 frames)
5. Extract frames at regular intervals using FFmpeg
6. Save as JPEG (quality level 2)
7. Return list of frame paths for analysis
```

**Configuration:**
- `FRAME_STRIDE_SECONDS`: Default 1.7s (configurable via env var)
- `MAX_SCENE_FRAMES`: Default 120 frames (configurable via env var)
- Minimum stride: 0.5s (safety floor)
- Frame format: JPEG with quality=2 (high quality, 1-5 scale)

**Example:**
- 60-second video with 1.7s stride = ~36 frames
- 300-second video with 1.7s stride = 120 frames (capped)
- 10-second video with 1.7s stride = 6 frames

#### 1.3.3 Smart Aggregation & Context Detection

**Label Bucketing:**
```python
Categories:
- Objects: Physical items (person, car, building, food, etc.)
- Scenes: Environments (beach, office, stadium, street, etc.)
- Activities: Actions (running, talking, fighting, celebration, etc.)

Classification Logic:
1. Check label parent hierarchy for "Activity" → Activities bucket
2. Check parent hierarchy for "Scene" → Scenes bucket
3. Check hint sets (ACTION_HINTS, DIALOGUE_HINTS) → Activities bucket
4. Check hint sets (INDOOR_HINTS, OUTDOOR_HINTS) → Scenes bucket
5. Default → Objects bucket
```

**Context Inference:**
```python
Environment Detection:
- Indoor hints: {"indoors", "interior", "room", "office", "studio", "kitchen"}
- Outdoor hints: {"outdoors", "outdoor", "nature", "urban", "street", "forest"}
- Result: "indoor" | "outdoor" | "unknown"

Activity Focus:
- Action hints: {"action", "fight", "battle", "sports", "running", "explosion"}
- Dialogue hints: {"conversation", "talk", "speech", "interview", "meeting"}
- Result: "action" | "dialogue" | "unclear"

Lighting Detection:
- Hints: {"spotlight", "stage", "dark", "night", "day", "sunset", "sunrise"}
- Result: Most common lighting keyword or null

Crowd Indicator:
- Hints: {"crowd", "audience", "group", "team", "people"}
- Result: Most common crowd keyword or null
```

**Confidence Tracking:**
- Per-label max confidence across all frames
- Frame occurrence count (how many frames contain this label)
- Sorted by confidence (descending)
- Top N results returned (10 objects, 6 activities, 6 scenes)

#### 1.3.4 LLM-Powered Summarization

**Bedrock Integration:**
- Model: `meta.llama3-70b-instruct-v1:0`
- Temperature: 0.4 (balanced creativity/consistency)
- Top-P: 0.9 (nucleus sampling)
- Max tokens: 600 (sufficient for summary + highlights + SSML)

**Structured Prompt:**
```json
{
  "mediaType": "video",
  "framesAnalysed": 36,
  "objects": [{"label": "Person", "confidence": 99.8, "frameOccurrences": 36}],
  "activities": [{"label": "Running", "confidence": 95.2, "frameOccurrences": 24}],
  "scenes": [{"label": "Outdoor", "confidence": 98.5, "frameOccurrences": 36}],
  "context": {
    "environment": "outdoor",
    "activityFocus": "action",
    "lighting": "day",
    "crowdIndicator": null
  },
  "people": [{"gender": "Male", "ageRange": {"Low": 25, "High": 35}}],
  "celebrities": [],
  "textDetections": ["FINISH LINE"]
}
```

**Expected JSON Response:**
```json
{
  "summary": "Natural language summary under 120 words...",
  "highlights": [
    "Key insight 1",
    "Key insight 2",
    "Key insight 3"
  ],
  "ssml": "<speak><p>Natural language summary...</p></speak>"
}
```

**Fallback Template:**
When LLM fails or response is unparseable:
```json
{
  "summary": "This [video/image] features [top 3 objects]. The scene appears to be [environment] with [activity focus] activity. [Face count] people detected with emotions: [dominant emotions].",
  "highlights": [
    "Top objects: [comma-separated list]",
    "Scene type: [environment]",
    "Detected emotions: [emotion list]"
  ],
  "ssml": "<speak><p>Fallback summary text</p></speak>"
}
```

#### 1.3.5 Voiceover Generation

**AWS Polly Integration:**
- Voice: Configurable (default: Joanna - US English Neural)
- Engine: Neural (superior quality vs standard)
- Output format: MP3 with 24kHz sample rate
- SSML support: Full markup parsing (emphasis, breaks, paragraphs)

**Voice Options (Frontend):**
```javascript
const voiceOptions = [
  { value: 'Joanna', label: 'Joanna (US, Female, Neural)' },
  { value: 'Matthew', label: 'Matthew (US, Male, Neural)' },
  { value: 'Amy', label: 'Amy (British, Female, Neural)' },
  { value: 'Brian', label: 'Brian (British, Male, Neural)' },
  { value: 'Olivia', label: 'Olivia (Australian, Female, Neural)' },
];
```

**SSML Processing:**
```xml
<speak>
  <p>This video shows an exciting outdoor race.</p>
  <break time="500ms"/>
  <p>A male runner, <emphasis level="strong">age 25 to 35</emphasis>, 
     sprints toward the finish line.</p>
  <p>The scene captures <emphasis>intense athletic action</emphasis> 
     in broad daylight.</p>
</speak>
```

#### 1.3.6 S3 Storage Integration

**Video Upload Flow:**
```python
if video_file and SCENE_S3_BUCKET:
    key = f"{SCENE_S3_PREFIX}{file_id}/{secure_filename(video_file.filename)}"
    s3.upload_fileobj(video_file, SCENE_S3_BUCKET, key)
    source_video = {
        "bucket": SCENE_S3_BUCKET,
        "key": key,
        "uri": f"s3://{SCENE_S3_BUCKET}/{key}"
    }
```

**Configuration:**
- `SCENE_S3_BUCKET`: Target bucket name (optional)
- `SCENE_S3_PREFIX`: Key prefix for organization (default: "scene-videos/")
- Upload only occurs for video files (images not uploaded)
- Skipped if bucket not configured or S3 client unavailable

---

## 2. Architecture Overview

### 2.1 High-Level Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────┐
│                  SCENE SUMMARIZATION SERVICE                         │
│                         (Port 5005)                                  │
├─────────────────────────────────────────────────────────────────────┤
│                                                                       │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │                    FRONTEND (React)                           │  │
│  │                  Served via Port 3000                         │  │
│  ├──────────────────────────────────────────────────────────────┤  │
│  │  • Drag-and-Drop File Upload (2GB limit)                     │  │
│  │  • Image/Video Preview (HTML5 video element)                 │  │
│  │  • Progress Tracking (5-phase timeline)                      │  │
│  │  • Voice Selection (5 neural voice options)                  │  │
│  │  • Result Display (cards, tags, audio player)                │  │
│  │  • Audio Player with Download                                │  │
│  │  • Metadata Visualization (JSON, SSML)                       │  │
│  └──────────────────────────────────────────────────────────────┘  │
│                              │                                       │
│                              │ HTTP/JSON + multipart/form-data       │
│                              ↓                                       │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │                    FLASK API LAYER                            │  │
│  │                      Port 5005                                │  │
│  ├──────────────────────────────────────────────────────────────┤  │
│  │  Routes:                                                      │  │
│  │    POST /summarize    (file upload + processing)             │  │
│  │    GET  /result/:id   (retrieve JSON metadata)               │  │
│  │    GET  /audio/:id    (stream MP3 audio)                     │  │
│  │    GET  /health       (service status check)                 │  │
│  │                                                               │  │
│  │  CORS: Dynamic origin resolution                             │  │
│  │  File Handling: werkzeug secure_filename                     │  │
│  │  Upload Directory: ./uploads/                                │  │
│  │  Output Directories: ./outputs/metadata/, ./outputs/audio/   │  │
│  └──────────────────────────────────────────────────────────────┘  │
│                              │                                       │
│                              │                                       │
│         ┌────────────────────┼────────────────────┐                 │
│         │                    │                    │                 │
│         ↓                    ↓                    ↓                 │
│  ┌─────────────┐     ┌──────────────┐     ┌──────────────┐        │
│  │   FRAME     │     │   VISION     │     │     LLM      │        │
│  │ EXTRACTION  │     │  ANALYSIS    │     │ SUMMARIZATION│        │
│  │  (FFmpeg)   │     │(Rekognition) │     │  (Bedrock)   │        │
│  ├─────────────┤     ├──────────────┤     ├──────────────┤        │
│  │ • Probe     │     │ • Labels     │     │ • Prompt     │        │
│  │   duration  │     │   (25 max)   │     │   builder    │        │
│  │ • Calculate │     │ • Faces      │     │ • JSON parse │        │
│  │   stride    │     │   (emotions) │     │ • Fallback   │        │
│  │ • Extract   │     │ • Celebrities│     │   template   │        │
│  │   frames    │     │ • Text (OCR) │     │              │        │
│  │ • Cleanup   │     │ • Per-frame  │     │              │        │
│  └─────────────┘     └──────────────┘     └──────────────┘        │
│         │                    │                      │               │
│         │                    │                      ↓               │
│         │                    │             ┌──────────────┐        │
│         │                    │             │     TTS      │        │
│         │                    │             │ SYNTHESIS    │        │
│         │                    │             │   (Polly)    │        │
│         │                    │             ├──────────────┤        │
│         │                    │             │ • SSML parse │        │
│         │                    │             │ • MP3 output │        │
│         │                    │             │ • Neural TTS │        │
│         │                    │             └──────────────┘        │
│         │                    │                      │               │
│         └────────────────────┴──────────────────────┘               │
│                              │                                       │
│                              ↓                                       │
│                    ┌───────────────────┐                            │
│                    │  RESULT STORAGE   │                            │
│                    ├───────────────────┤                            │
│                    │ • metadata.json   │                            │
│                    │ • audio.mp3       │                            │
│                    │ • File-based      │                            │
│                    └───────────────────┘                            │
│                                                                       │
└──────────────────────────────┬────────────────────────────────────────┘
                               │
                               ↓
                    ┌──────────────────────┐
                    │    AWS SERVICES      │
                    ├──────────────────────┤
                    │  • Rekognition       │
                    │    (us-east-1)       │
                    │    4 API calls/frame │
                    │  • Bedrock Runtime   │
                    │    (us-east-1)       │
                    │    Llama3-70B model  │
                    │  • Polly             │
                    │    (us-west-2)       │
                    │    Neural voices     │
                    │  • S3 (Optional)     │
                    │    (us-east-1)       │
                    │    Video storage     │
                    └──────────────────────┘
```

### 2.2 Processing Pipeline

**7-Stage Synchronous Pipeline:**

```
1. FILE UPLOAD
   ├─ Client uploads file via multipart/form-data
   ├─ Flask receives and validates file
   ├─ Save to ./uploads/ directory
   ├─ Detect media type (image vs video)
   └─ Generate unique file_id (UUID4)

2. FRAME EXTRACTION (Video only)
   ├─ Probe video duration with FFprobe
   ├─ Calculate frame stride and count
   ├─ Extract frames at intervals with FFmpeg
   ├─ Save frames to temporary directory
   └─ Return list of frame paths

3. VISION ANALYSIS
   ├─ For each frame/image:
   │  ├─ detect_labels (objects, scenes, activities)
   │  ├─ detect_faces (demographics, emotions)
   │  ├─ recognize_celebrities (if any)
   │  └─ detect_text (OCR for on-screen text)
   └─ Collect results per frame

4. AGGREGATION
   ├─ Bucket labels: objects, scenes, activities
   ├─ Track max confidence per label
   ├─ Count frame occurrences per label
   ├─ Aggregate emotions across all faces
   ├─ Collect unique text detections
   ├─ Infer context (environment, activity, lighting)
   └─ Rank and limit results

5. LLM SUMMARIZATION
   ├─ Build structured JSON prompt with metadata
   ├─ Invoke Bedrock with Llama3-70B model
   ├─ Parse response for JSON payload
   ├─ Extract: summary, highlights, ssml
   └─ Fallback to template if parsing fails

6. TTS SYNTHESIS
   ├─ Invoke Polly with SSML text
   ├─ Configure neural voice (user-selected)
   ├─ Receive MP3 audio stream
   ├─ Save to ./outputs/audio/{file_id}.mp3
   └─ Generate audio URL for response

7. RESULT STORAGE & DELIVERY
   ├─ Save metadata to ./outputs/metadata/{file_id}.json
   ├─ Optionally upload video to S3
   ├─ Build response JSON with all data
   ├─ Cleanup temporary frames
   └─ Return response to client
```

**Execution Time:**
- Image (single frame): 5-15 seconds
- Short video (30s, ~18 frames): 30-60 seconds
- Medium video (2min, ~71 frames): 2-4 minutes
- Long video (10min, 120 frames): 8-15 minutes

**Timeout Configuration:**
- Frontend default: 3 hours (10,800,000 ms)
- Frontend dynamic: 5× video duration (if detected)
- Backend: No explicit timeout (relies on client timeout)

### 2.3 Service Architecture Pattern

**Design Decisions:**

1. **Monolithic Service**
   - All processing in single Flask application
   - No microservices decomposition
   - No message queue or async workers
   - Rationale: Simplicity, ease of deployment, low traffic volume

2. **Synchronous Request-Response**
   - Long-lived HTTP connections (up to hours)
   - Client waits for complete processing
   - No polling or webhooks
   - Rationale: Simple client implementation, real-time progress

3. **File-Based Storage**
   - No database for metadata
   - JSON files in ./outputs/metadata/
   - MP3 files in ./outputs/audio/
   - Rationale: No persistence requirements, easy debugging

4. **Temporary Frame Caching**
   - Frames extracted to ./frames/ subdirectories
   - Cleanup after aggregation
   - No persistent frame storage
   - Rationale: Memory efficiency, privacy

5. **Stateless Vision Analysis**
   - No per-frame result storage
   - Immediate aggregation and disposal
   - Rationale: Memory efficiency for large videos

6. **AWS SDK Direct Integration**
   - boto3 clients initialized at module level
   - No wrapper services or queues
   - Synchronous API calls
   - Rationale: Simplicity, low latency

---

## 3. System Components

### 3.1 Backend File Structure

```
sceneSummarization/
├── app.py                          # Main Flask application (879 lines)
├── scene_summarization_service.py  # (Unused, legacy file)
├── README.md                       # Service documentation
├── __pycache__/                    # Python bytecode cache
├── uploads/                        # Incoming media files
│   └── [user-uploaded files]
├── outputs/
│   ├── metadata/                   # JSON result files
│   │   └── {file_id}.json
│   └── audio/                      # MP3 voiceover files
│       └── {file_id}.mp3
└── frames/                         # Temporary frame extraction
    └── frames_{uuid}/              # Auto-created, auto-cleaned
        ├── frame_0000.jpg
        ├── frame_0001.jpg
        └── ...
```

### 3.2 Backend Dependencies

**requirements.txt:**
```
flask>=3.0.0
flask-cors>=4.0.0
boto3>=1.34.0
python-dotenv>=1.0.0
werkzeug>=3.0.0
```

**System Dependencies:**
- FFmpeg 4.0+ (video frame extraction)
- FFprobe 4.0+ (video duration probing)
- Python 3.8+ (type hints, f-strings)

**AWS IAM Permissions Required:**
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "rekognition:DetectLabels",
        "rekognition:DetectFaces",
        "rekognition:RecognizeCelebrities",
        "rekognition:DetectText"
      ],
      "Resource": "*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "bedrock:InvokeModel"
      ],
      "Resource": "arn:aws:bedrock:*::foundation-model/meta.llama3-70b-instruct-v1:0"
    },
    {
      "Effect": "Allow",
      "Action": [
        "polly:SynthesizeSpeech"
      ],
      "Resource": "*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "s3:PutObject"
      ],
      "Resource": "arn:aws:s3:::YOUR_BUCKET/scene-videos/*"
    }
  ]
}
```

### 3.3 Frontend File Structure

```
frontend/src/
├── SceneSummarization.js           # Main component (1152 lines)
├── App.js                          # Routing integration
└── index.js                        # React root

Key Sections in SceneSummarization.js:
- Lines 1-200:    Imports, styled-components, constants
- Lines 200-400:  State management (useState hooks)
- Lines 400-600:  File handling (drag-drop, preview)
- Lines 600-800:  Processing phases, progress tracking
- Lines 800-1000: API call, error handling
- Lines 1000-1152: Result rendering (cards, metadata display)
```

### 3.4 Configuration Sources

**Backend Configuration:**

1. **Environment Variables (.env file or system env):**
```bash
# AWS Configuration
AWS_REGION=us-east-1
REKOGNITION_REGION=us-east-1
BEDROCK_REGION=us-east-1
POLLY_REGION=us-west-2
S3_REGION=us-east-1

# Service Configuration
SCENE_BEDROCK_MODEL_ID=meta.llama3-70b-instruct-v1:0
SCENE_POLLY_VOICE_ID=Joanna
SCENE_S3_BUCKET=my-video-bucket
SCENE_S3_PREFIX=scene-videos/

# Frame Extraction
FRAME_STRIDE_SECONDS=1.7
MAX_SCENE_FRAMES=120

# FFmpeg Paths (optional, auto-detected if in PATH)
FFMPEG_BINARY=/usr/local/bin/ffmpeg
FFPROBE_BINARY=/usr/local/bin/ffprobe
```

2. **Hardcoded Defaults (app.py):**
```python
REKOGNITION_REGION = os.getenv("REKOGNITION_REGION", "us-east-1")
BEDROCK_REGION = os.getenv("BEDROCK_REGION", "us-east-1")
POLLY_REGION = os.getenv("POLLY_REGION", "us-west-2")
S3_REGION = os.getenv("S3_REGION", "us-east-1")
SCENE_BEDROCK_MODEL_ID = os.getenv("SCENE_BEDROCK_MODEL_ID", "meta.llama3-70b-instruct-v1:0")
SCENE_POLLY_VOICE_ID = os.getenv("SCENE_POLLY_VOICE_ID", "Joanna")
FRAME_STRIDE_SECONDS = float(os.getenv("FRAME_STRIDE_SECONDS", "1.7"))
MAX_SCENE_FRAMES = int(os.getenv("MAX_SCENE_FRAMES", "120"))
```

**Frontend Configuration:**

```javascript
// API Base URL Resolution
const SCENE_API_BASE = process.env.REACT_APP_SCENE_API_BASE || resolveSceneApiBase();

function resolveSceneApiBase() {
  const hostname = window.location.hostname;
  if (hostname === 'localhost' || hostname === '127.0.0.1') {
    return 'http://localhost:5005';
  }
  // LAN/production: use hostname with port 5005
  return `http://${hostname}:5005`;
}

// Timeout Configuration
const DEFAULT_TIMEOUT_MS = 3 * 60 * 60 * 1000; // 3 hours
const DURATION_BASED_TIMEOUT_MULTIPLIER = 5; // 5× video duration
```

---

## 4. Backend Architecture - File Upload & Validation

### 4.1 Flask Application Setup

**app.py - Initialization:**

```python
import os
import shutil
import subprocess
import tempfile
import uuid
import json
import math
from pathlib import Path
from typing import Dict, Any, List, Optional
from collections import defaultdict, Counter

from flask import Flask, jsonify, request, send_file
from flask_cors import CORS
from werkzeug.utils import secure_filename
import boto3
from botocore.exceptions import BotoCoreError, ClientError
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Initialize Flask app
app = Flask(__name__)

# CORS Configuration - Dynamic origin resolution
def _cors_origin() -> str:
    """Resolve CORS origin dynamically for dev/production."""
    default_origins = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ]
    env_origin = os.getenv("CORS_ORIGIN")
    if env_origin:
        default_origins.append(env_origin)
    # In production, add server hostname
    # Example: "http://192.168.1.100:3000"
    return default_origins

CORS(app, origins=_cors_origin())

# Directory Setup
BASE_DIR = Path(__file__).resolve().parent
UPLOAD_FOLDER = BASE_DIR / "uploads"
OUTPUT_FOLDER = BASE_DIR / "outputs"
METADATA_FOLDER = OUTPUT_FOLDER / "metadata"
AUDIO_FOLDER = OUTPUT_FOLDER / "audio"
FRAME_CACHE = BASE_DIR / "frames"

# Create directories if not exist
for folder in [UPLOAD_FOLDER, METADATA_FOLDER, AUDIO_FOLDER, FRAME_CACHE]:
    folder.mkdir(parents=True, exist_ok=True)

# File Upload Constraints
ALLOWED_EXTENSIONS = {
    'jpg', 'jpeg', 'png', 'gif', 'bmp', 'tiff', 'webp',  # Images
    'mp4', 'mov', 'avi', 'mkv', 'webm', 'flv', 'wmv', 'mpeg', 'mpg'  # Videos
}
MAX_FILE_SIZE = 2 * 1024 * 1024 * 1024  # 2GB in bytes
```

**Binary Resolution:**

```python
def _resolve_binary(binary_name: str, env_var: str) -> Optional[str]:
    """
    Resolve binary path from environment variable or system PATH.
    
    Priority:
    1. Environment variable (FFMPEG_BINARY, FFPROBE_BINARY)
    2. System PATH (shutil.which)
    3. Common installation paths
    
    Args:
        binary_name: Name of binary (e.g., "ffmpeg")
        env_var: Environment variable name (e.g., "FFMPEG_BINARY")
    
    Returns:
        Absolute path to binary or None if not found
    """
    # Check environment variable
    env_path = os.getenv(env_var)
    if env_path and Path(env_path).is_file():
        return env_path
    
    # Check system PATH
    which_result = shutil.which(binary_name)
    if which_result:
        return which_result
    
    # Check common installation paths
    common_paths = [
        f"/usr/local/bin/{binary_name}",
        f"/usr/bin/{binary_name}",
        f"/opt/homebrew/bin/{binary_name}",  # macOS Homebrew
        f"C:\\ffmpeg\\bin\\{binary_name}.exe",  # Windows
    ]
    for path in common_paths:
        if Path(path).is_file():
            return path
    
    return None

FFMPEG_BINARY = _resolve_binary("ffmpeg", "FFMPEG_BINARY")
FFPROBE_BINARY = _resolve_binary("ffprobe", "FFPROBE_BINARY")

if not FFMPEG_BINARY:
    print("WARNING: FFmpeg not found. Video processing will fail.")
if not FFPROBE_BINARY:
    print("WARNING: FFprobe not found. Video duration detection unavailable.")
```

### 4.2 AWS Client Initialization

```python
def _safe_client(service_name: str, region_name: str):
    """
    Initialize AWS client with error handling.
    
    Returns None if client creation fails (missing credentials, invalid region, etc.)
    Service will degrade gracefully when clients are unavailable.
    """
    try:
        return boto3.client(service_name, region_name=region_name)
    except Exception as error:
        print(f"ERROR: Failed to create {service_name} client: {error}")
        return None

# Initialize AWS clients (module-level, reused across requests)
rekognition = _safe_client("rekognition", REKOGNITION_REGION)
bedrock_runtime = _safe_client("bedrock-runtime", BEDROCK_REGION)
polly = _safe_client("polly", POLLY_REGION)
s3 = _safe_client("s3", S3_REGION)

# Service availability check
def _check_aws_clients() -> Dict[str, bool]:
    """Check which AWS services are available."""
    return {
        "rekognition": rekognition is not None,
        "bedrock": bedrock_runtime is not None,
        "polly": polly is not None,
        "s3": s3 is not None,
    }
```

### 4.3 File Upload Handling

**POST /summarize Route:**

```python
@app.route("/summarize", methods=["POST"])
def summarize_scene():
    """
    Main endpoint: Upload media file and generate scene summary.
    
    Request:
        - Content-Type: multipart/form-data
        - Fields:
            * media: File (required) - Image or video file
            * voice_id: String (optional) - Polly voice ID (default: Joanna)
    
    Response:
        {
          "file_id": "uuid",
          "summary": "Natural language summary...",
          "highlights": ["Bullet 1", "Bullet 2", "Bullet 3"],
          "ssml": "<speak>...</speak>",
          "audio_url": "/audio/uuid.mp3",
          "voice_id": "Joanna",
          "metadata": {
            "mediaType": "video",
            "framesAnalysed": 36,
            "objects": [...],
            "activities": [...],
            "scenes": [...],
            "people": [...],
            "dominantEmotions": [...],
            "celebrities": [...],
            "textDetections": [...],
            "context": {...}
          },
          "source_video": {
            "bucket": "my-bucket",
            "key": "scene-videos/uuid/video.mp4",
            "uri": "s3://my-bucket/scene-videos/uuid/video.mp4"
          }
        }
    
    Errors:
        400: Missing file, invalid file type, file too large
        500: Processing error, AWS API failure
        503: AWS clients unavailable
    """
    # Validate AWS clients
    clients = _check_aws_clients()
    if not clients["rekognition"]:
        return jsonify({"error": "Rekognition client unavailable"}), 503
    if not clients["bedrock"]:
        return jsonify({"error": "Bedrock client unavailable"}), 503
    
    # Validate file presence
    if "media" not in request.files:
        return jsonify({"error": "No media file provided"}), 400
    
    media_file = request.files["media"]
    if media_file.filename == "":
        return jsonify({"error": "Empty filename"}), 400
    
    # Validate file extension
    file_extension = media_file.filename.rsplit(".", 1)[-1].lower()
    if file_extension not in ALLOWED_EXTENSIONS:
        return jsonify({
            "error": f"Invalid file type: .{file_extension}",
            "allowed": list(ALLOWED_EXTENSIONS)
        }), 400
    
    # Validate file size (approximate, content-length header)
    content_length = request.content_length
    if content_length and content_length > MAX_FILE_SIZE:
        return jsonify({
            "error": f"File too large: {content_length / (1024**3):.2f} GB",
            "max_size_gb": MAX_FILE_SIZE / (1024**3)
        }), 400
    
    # Generate unique file ID
    file_id = str(uuid.uuid4())
    
    # Secure filename and save to uploads/
    safe_filename = secure_filename(media_file.filename)
    if not safe_filename:
        safe_filename = f"{file_id}.{file_extension}"
    
    upload_path = UPLOAD_FOLDER / safe_filename
    media_file.save(str(upload_path))
    
    # Detect media type
    media_type = "image" if file_extension in {'jpg', 'jpeg', 'png', 'gif', 'bmp', 'tiff', 'webp'} else "video"
    
    # Extract voice_id parameter
    voice_id = request.form.get("voice_id", SCENE_POLLY_VOICE_ID)
    
    try:
        # Process media (next section: Media Processing)
        result = _process_media(str(upload_path), media_type, file_id, voice_id, media_file)
        return jsonify(result), 200
    
    except Exception as error:
        print(f"ERROR in /summarize: {error}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(error)}), 500
    
    finally:
        # Cleanup uploaded file
        if upload_path.exists():
            upload_path.unlink()
```

**File Validation Logic:**

```python
def allowed_file(filename: str) -> bool:
    """Check if filename has allowed extension."""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def estimate_file_size(file_storage) -> int:
    """
    Estimate file size without reading entire file.
    
    Methods:
    1. Check Content-Length header (if available)
    2. Seek to end and get position (fallback)
    """
    # Try Content-Length header first
    if hasattr(file_storage, 'content_length') and file_storage.content_length:
        return file_storage.content_length
    
    # Fallback: seek to end
    file_storage.seek(0, 2)  # Seek to end
    size = file_storage.tell()
    file_storage.seek(0)  # Reset to beginning
    return size
```

---

## 5. Backend Architecture - Media Processing

### 5.1 Video Duration Probing

**FFprobe Integration:**

```python
def _probe_video_duration(video_path: str) -> Optional[float]:
    """
    Use FFprobe to determine video duration in seconds.
    
    Command:
        ffprobe -v error -select_streams v:0 -show_entries stream=duration 
                -of default=noprint_wrappers=1:nokey=1 <video_path>
    
    Args:
        video_path: Absolute path to video file
    
    Returns:
        Duration in seconds (float) or None if probe fails
    
    Example Output:
        "125.483000" → 125.483 seconds
    """
    if not FFPROBE_BINARY:
        print("WARNING: FFprobe binary not available")
        return None
    
    try:
        command = [
            FFPROBE_BINARY,
            "-v", "error",  # Suppress info messages
            "-select_streams", "v:0",  # First video stream
            "-show_entries", "stream=duration",  # Extract duration field
            "-of", "default=noprint_wrappers=1:nokey=1",  # Plain output
            video_path,
        ]
        
        output = subprocess.check_output(
            command,
            stderr=subprocess.STDOUT,
            timeout=30  # 30-second timeout
        )
        
        duration_str = output.decode("utf-8", errors="ignore").strip()
        
        if duration_str and duration_str != "N/A":
            return float(duration_str)
        
        return None
    
    except subprocess.CalledProcessError as error:
        print(f"ERROR: FFprobe failed: {error}")
        return None
    
    except subprocess.TimeoutExpired:
        print("ERROR: FFprobe timeout after 30 seconds")
        return None
    
    except ValueError as error:
        print(f"ERROR: Invalid duration format: {duration_str}")
        return None
```

### 5.2 Frame Extraction

**FFmpeg-Based Extraction:**

```python
def _extract_frames_local(video_path: str) -> List[str]:
    """
    Extract frames from video at regular intervals using FFmpeg.
    
    Algorithm:
    1. Probe video duration with FFprobe
    2. Calculate stride = max(0.5, FRAME_STRIDE_SECONDS)
    3. Estimate frame count = ceil(duration / stride)
    4. Cap frame count at MAX_SCENE_FRAMES
    5. For each frame index:
        a. Calculate time offset = index * stride
        b. Extract single frame at offset with FFmpeg
        c. Save as JPEG with quality 2
    6. Return list of extracted frame paths
    
    Args:
        video_path: Absolute path to video file
    
    Returns:
        List of frame paths (JPEGs in temporary directory)
    
    Raises:
        subprocess.CalledProcessError: FFmpeg extraction failed
        FileNotFoundError: FFmpeg binary not found
    
    Example:
        video_path = "/uploads/video.mp4"
        duration = 60.0 seconds
        stride = 1.7 seconds
        estimated_frames = ceil(60.0 / 1.7) = 36 frames
        frame_count = min(120, 36) = 36 frames
        
        Extracted frames:
        - frame_0000.jpg at 0.0s
        - frame_0001.jpg at 1.7s
        - frame_0002.jpg at 3.4s
        - ...
        - frame_0035.jpg at 59.5s
    """
    if not FFMPEG_BINARY:
        raise FileNotFoundError("FFmpeg binary not found")
    
    extracted_frames: List[str] = []
    
    # Create temporary directory for frames
    tmp_dir = tempfile.mkdtemp(prefix="frames_", dir=str(FRAME_CACHE))
    print(f"Frame extraction directory: {tmp_dir}")
    
    # Probe duration
    duration = _probe_video_duration(video_path)
    
    # Calculate stride and frame count
    stride = max(0.5, FRAME_STRIDE_SECONDS)  # Minimum 0.5s
    
    if duration and duration > 0:
        estimated_frames = int(math.ceil(duration / stride))
        frame_count = max(1, min(MAX_SCENE_FRAMES, estimated_frames))
        print(f"Video duration: {duration:.2f}s, stride: {stride}s, frames: {frame_count}")
    else:
        # Fallback if duration unavailable
        frame_count = max(1, min(MAX_SCENE_FRAMES, 60))
        print(f"Duration unknown, extracting {frame_count} frames")
    
    # Extract frames
    for index in range(frame_count):
        output_path = os.path.join(tmp_dir, f"frame_{index:04d}.jpg")
        
        # Calculate time offset
        if duration:
            # Ensure last frame doesn't exceed duration
            time_offset = min(index * stride, max(duration - 0.5, 0.0))
        else:
            time_offset = index * stride
        
        command = [
            FFMPEG_BINARY,
            "-y",  # Overwrite output files
            "-hide_banner",  # Suppress banner
            "-loglevel", "error",  # Only show errors
            "-ss", str(time_offset),  # Seek to time offset
            "-i", video_path,  # Input file
            "-frames:v", "1",  # Extract 1 frame
            "-q:v", "2",  # Quality: 1-5 scale (lower = better)
            output_path,  # Output path
        ]
        
        try:
            subprocess.run(
                command,
                check=True,
                stderr=subprocess.PIPE,
                timeout=60  # 60-second timeout per frame
            )
            
            if os.path.exists(output_path):
                extracted_frames.append(output_path)
                print(f"Extracted frame {index+1}/{frame_count} at {time_offset:.2f}s")
            else:
                print(f"WARNING: Frame {index} not created")
        
        except subprocess.CalledProcessError as error:
            print(f"ERROR: FFmpeg failed for frame {index}: {error.stderr.decode()}")
        
        except subprocess.TimeoutExpired:
            print(f"ERROR: FFmpeg timeout for frame {index}")
    
    print(f"Total frames extracted: {len(extracted_frames)}")
    return extracted_frames
```

**Cleanup Strategy:**

```python
def _cleanup_frames(frame_dir: str):
    """
    Remove temporary frame directory and all contents.
    
    Called after aggregation to free disk space.
    """
    try:
        if os.path.exists(frame_dir):
            shutil.rmtree(frame_dir)
            print(f"Cleaned up frame directory: {frame_dir}")
    except Exception as error:
        print(f"ERROR: Failed to cleanup frames: {error}")
```

---

## 6. Backend Architecture - Vision Analysis

### 6.1 Rekognition Per-Frame Analysis

**_analyse_image_bytes Function:**

```python
def _analyse_image_bytes(image_bytes: bytes) -> Dict[str, Any]:
    """
    Analyze single image/frame with AWS Rekognition (4 API calls).
    
    APIs Called:
    1. detect_labels: Objects, scenes, activities
    2. detect_faces: Demographics, emotions, attributes
    3. recognize_celebrities: Celebrity detection
    4. detect_text: On-screen text (OCR)
    
    Args:
        image_bytes: Raw image bytes (JPEG, PNG, etc.)
    
    Returns:
        {
          "labels": [
            {
              "name": "Person",
              "confidence": 99.8,
              "parents": ["Human"]
            }
          ],
          "faces": [
            {
              "gender": "Male",
              "ageRange": {"Low": 25, "High": 35},
              "emotions": [
                {"type": "HAPPY", "confidence": 95.2},
                {"type": "CALM", "confidence": 4.8}
              ],
              "faceConfidence": 99.9,
              "beard": false,
              "mustache": false,
              "sunglasses": false,
              "smile": true
            }
          ],
          "celebrities": [
            {
              "name": "Tom Hanks",
              "confidence": 98.5,
              "urls": [
                "www.imdb.com/name/nm0000158",
                "en.wikipedia.org/wiki/Tom_Hanks"
              ]
            }
          ],
          "text": ["FINISH LINE", "ACME CORP"],
          "errors": []  // Optional, if any API failed
        }
    
    Error Handling:
        - Each API call wrapped in try/except
        - Failures logged to "errors" array
        - Partial results returned even if some APIs fail
    """
    frame_result = {
        "labels": [],
        "faces": [],
        "celebrities": [],
        "text": [],
    }
    
    # 1. LABEL DETECTION
    try:
        label_response = rekognition.detect_labels(
            Image={"Bytes": image_bytes},
            MaxLabels=25,  # Max labels per frame
            MinConfidence=55.0,  # 55% confidence threshold
        )
        
        for label in label_response.get("Labels", []):
            frame_result["labels"].append({
                "name": label.get("Name"),
                "confidence": label.get("Confidence"),
                "parents": [parent.get("Name") for parent in label.get("Parents", [])]
            })
    
    except (BotoCoreError, ClientError) as error:
        frame_result.setdefault("errors", []).append(f"detect_labels: {error}")
    
    # 2. FACE DETECTION
    try:
        face_response = rekognition.detect_faces(
            Image={"Bytes": image_bytes},
            Attributes=["ALL"]  # Request all face attributes
        )
        
        for face in face_response.get("FaceDetails", []):
            emotions = [
                {"type": emotion.get("Type"), "confidence": emotion.get("Confidence")}
                for emotion in face.get("Emotions", [])
            ]
            
            frame_result["faces"].append({
                "gender": face.get("Gender", {}).get("Value"),
                "ageRange": face.get("AgeRange"),  # {"Low": 25, "High": 35}
                "emotions": emotions,
                "faceConfidence": face.get("Confidence"),
                "beard": face.get("Beard", {}).get("Value"),
                "mustache": face.get("Mustache", {}).get("Value"),
                "sunglasses": face.get("Sunglasses", {}).get("Value"),
                "smile": face.get("Smile", {}).get("Value"),
            })
    
    except (BotoCoreError, ClientError) as error:
        frame_result.setdefault("errors", []).append(f"detect_faces: {error}")
    
    # 3. CELEBRITY RECOGNITION
    try:
        celeb_response = rekognition.recognize_celebrities(
            Image={"Bytes": image_bytes}
        )
        
        for celeb in celeb_response.get("CelebrityFaces", []):
            frame_result["celebrities"].append({
                "name": celeb.get("Name"),
                "confidence": celeb.get("MatchConfidence"),
                "urls": celeb.get("Urls", [])[:3],  # Limit to 3 URLs
            })
    
    except (BotoCoreError, ClientError) as error:
        frame_result.setdefault("errors", []).append(f"recognize_celebrities: {error}")
    
    # 4. TEXT DETECTION (OCR)
    try:
        text_response = rekognition.detect_text(
            Image={"Bytes": image_bytes}
        )
        
        # Extract LINE-type detections only (ignore individual WORD detections)
        unique_lines = []
        seen = set()
        
        for detection in text_response.get("TextDetections", []):
            if detection.get("Type") != "LINE":
                continue
            
            text = detection.get("DetectedText")
            if text and text not in seen:
                unique_lines.append(text)
                seen.add(text)
        
        frame_result["text"] = unique_lines
    
    except (BotoCoreError, ClientError) as error:
        frame_result.setdefault("errors", []).append(f"detect_text: {error}")
    
    return frame_result
```

### 6.2 Media Analysis Orchestration

**_analyse_media Function:**

```python
def _analyse_media(media_path: str, media_type: str) -> List[Dict[str, Any]]:
    """
    Orchestrate frame/image analysis.
    
    Workflow:
    - Image: Analyze single image
    - Video: Extract frames → analyze each frame
    
    Args:
        media_path: Path to media file
        media_type: "image" or "video"
    
    Returns:
        List of frame analysis results
    """
    frame_results = []
    
    if media_type == "video":
        # Extract frames
        frame_paths = _extract_frames_local(media_path)
        
        if not frame_paths:
            raise ValueError("No frames extracted from video")
        
        # Analyze each frame
        for frame_path in frame_paths:
            with open(frame_path, "rb") as frame_file:
                image_bytes = frame_file.read()
            
            frame_result = _analyse_image_bytes(image_bytes)
            frame_results.append(frame_result)
        
        # Cleanup frames
        frame_dir = os.path.dirname(frame_paths[0])
        _cleanup_frames(frame_dir)
    
    else:  # Image
        with open(media_path, "rb") as image_file:
            image_bytes = image_file.read()
        
        frame_result = _analyse_image_bytes(image_bytes)
        frame_results.append(frame_result)
    
    return frame_results
```

*Continued in Part 2...*

---

## Document Continuation

**Next Document:** `SCENE_SUMMARIZATION_PART2.md`

**Part 2 Contents:**
- Aggregation Logic & Context Detection
- LLM Integration (Bedrock)
- TTS Synthesis (Polly)
- Result Storage & Retrieval
- S3 Upload Logic

# Scene Summarization Service - Complete Technical Reference
## Part 2 of 4: Aggregation, LLM Integration & TTS Synthesis

**MediaGenAI Platform - Service Documentation**  
**Document Version:** 1.0  
**Service Port:** 5005  
**Last Updated:** October 21, 2025

---

## Document Navigation

- **Part 1**: Executive Summary, Architecture Overview, Backend Deep Dive (Media Processing, Vision Analysis)
- **Part 2** (this document): Aggregation Logic, LLM Integration, TTS Synthesis, Result Storage
- **Part 3**: Frontend Architecture, Processing Phases, UI Components
- **Part 4**: AWS Integration, API Reference, Configuration, Deployment, Troubleshooting

---

## Table of Contents - Part 2

1. [Result Aggregation & Context Detection](#1-result-aggregation--context-detection)
2. [LLM Integration - Bedrock](#2-llm-integration---bedrock)
3. [TTS Synthesis - Polly](#3-tts-synthesis---polly)
4. [Result Storage & Retrieval](#4-result-storage--retrieval)
5. [S3 Video Upload](#5-s3-video-upload)

---

## 1. Result Aggregation & Context Detection

### 1.1 Aggregation Architecture

**Purpose:**
Transform per-frame vision analysis results into unified scene metadata with:
- Label bucketing (objects, scenes, activities)
- Confidence tracking (max confidence per label)
- Frame occurrence counting (how many frames contain each label)
- Context inference (environment, activity focus, lighting, crowd)
- Emotion aggregation across all faces
- Unique text collection

**Input:**
```python
frame_results = [
    {
        "labels": [
            {"name": "Person", "confidence": 99.8, "parents": ["Human"]},
            {"name": "Running", "confidence": 95.2, "parents": ["Activity"]},
            {"name": "Outdoor", "confidence": 98.5, "parents": ["Scene"]}
        ],
        "faces": [
            {
                "gender": "Male",
                "ageRange": {"Low": 25, "High": 35},
                "emotions": [
                    {"type": "HAPPY", "confidence": 85.0},
                    {"type": "CALM", "confidence": 15.0}
                ]
            }
        ],
        "celebrities": [],
        "text": ["FINISH LINE"]
    },
    # ... more frames
]
```

**Output:**
```python
aggregated = {
    "mediaType": "video",
    "framesAnalysed": 36,
    "objects": [
        {"label": "Person", "confidence": 99.8, "frameOccurrences": 36}
    ],
    "activities": [
        {"label": "Running", "confidence": 95.2, "frameOccurrences": 24}
    ],
    "scenes": [
        {"label": "Outdoor", "confidence": 98.5, "frameOccurrences": 36}
    ],
    "context": {
        "environment": "outdoor",
        "activityFocus": "action",
        "lighting": "day",
        "crowdIndicator": null
    },
    "people": [
        {
            "gender": "Male",
            "ageRange": {"Low": 25, "High": 35},
            "dominantEmotions": ["HAPPY"]
        }
    ],
    "dominantEmotions": [
        {"emotion": "HAPPY", "score": 85.0}
    ],
    "celebrities": [],
    "textDetections": ["FINISH LINE"]
}
```

### 1.2 Label Bucketing Algorithm

**Classification Hint Sets:**

```python
# Environment Classification
INDOOR_HINTS = {
    "indoors", "interior", "room", "office", "studio", "kitchen", 
    "living room", "bedroom", "bathroom", "hallway", "lobby"
}

OUTDOOR_HINTS = {
    "outdoors", "outdoor", "nature", "urban", "street", "forest", 
    "beach", "stadium", "park", "garden", "mountain", "sky"
}

# Activity Classification
ACTION_HINTS = {
    "action", "fight", "battle", "sports", "running", "explosion", 
    "car chase", "race", "jumping", "climbing", "dancing"
}

DIALOGUE_HINTS = {
    "conversation", "talk", "speech", "interview", "meeting", 
    "discussion", "presentation", "lecture"
}

# Visual Attributes
LIGHTING_HINTS = {
    "spotlight", "stage", "dark", "night", "day", "sunset", 
    "sunrise", "shadow", "silhouette", "backlit"
}

CROWD_HINTS = {
    "crowd", "audience", "group", "team", "people", "gathering"
}
```

**Bucketing Logic:**

```python
def _classify_label(label_name: str, parents: List[str]) -> str:
    """
    Classify label into bucket: objects, scenes, or activities.
    
    Decision Tree:
    1. Check parent hierarchy for "Activity" or "Activities" → activities
    2. Check parent hierarchy for "Scene" → scenes
    3. Check if label name in ACTION_HINTS or DIALOGUE_HINTS → activities
    4. Check if label name in INDOOR_HINTS or OUTDOOR_HINTS → scenes
    5. Default → objects
    
    Args:
        label_name: Label text (e.g., "Running")
        parents: Parent categories (e.g., ["Activity"])
    
    Returns:
        "objects" | "scenes" | "activities"
    """
    name_lower = label_name.lower()
    parents_lower = {str(p).lower() for p in parents if p}
    
    # Check parent hierarchy
    if parents_lower & {"activity", "activities"}:
        return "activities"
    
    if "scene" in parents_lower:
        return "scenes"
    
    # Check hint sets
    if name_lower in ACTION_HINTS | DIALOGUE_HINTS:
        return "activities"
    
    if name_lower in INDOOR_HINTS | OUTDOOR_HINTS:
        return "scenes"
    
    # Default bucket
    return "objects"
```

### 1.3 Context Detection Algorithm

**Environment Detection:**

```python
def _detect_environment(context_flags: Dict) -> str:
    """
    Infer environment from label occurrences.
    
    Logic:
    - Count labels matching INDOOR_HINTS
    - Count labels matching OUTDOOR_HINTS
    - Return majority category or "unknown"
    
    Returns:
        "indoor" | "outdoor" | "unknown"
    """
    env_counts = context_flags["environment"]
    
    if not env_counts:
        return "unknown"
    
    indoor_count = env_counts.get("indoor", 0)
    outdoor_count = env_counts.get("outdoor", 0)
    
    if indoor_count > outdoor_count:
        return "indoor"
    elif outdoor_count > indoor_count:
        return "outdoor"
    else:
        # Tie or no strong signal
        return env_counts.most_common(1)[0][0] if env_counts else "unknown"
```

**Activity Focus Detection:**

```python
def _detect_activity_focus(context_flags: Dict) -> str:
    """
    Infer activity focus from label occurrences.
    
    Logic:
    - Count labels matching ACTION_HINTS
    - Count labels matching DIALOGUE_HINTS
    - Return dominant category or "unclear"
    
    Returns:
        "action" | "dialogue" | "unclear"
    """
    activity_counts = context_flags["activity"]
    
    if not activity_counts:
        return "unclear"
    
    # Return most common activity type
    return activity_counts.most_common(1)[0][0]
```

**Lighting & Crowd Detection:**

```python
def _detect_lighting(context_flags: Dict) -> Optional[str]:
    """
    Identify dominant lighting keyword.
    
    Returns most common lighting-related label or None.
    """
    lighting_counts = context_flags["lighting"]
    
    if not lighting_counts:
        return None
    
    return lighting_counts.most_common(1)[0][0]

def _detect_crowd(context_flags: Dict) -> Optional[str]:
    """
    Identify dominant crowd keyword.
    
    Returns most common crowd-related label or None.
    """
    crowd_counts = context_flags["crowd"]
    
    if not crowd_counts:
        return None
    
    return crowd_counts.most_common(1)[0][0]
```

### 1.4 Full Aggregation Function

**_aggregate_results Implementation:**

```python
def _aggregate_results(frame_results: List[Dict[str, Any]], media_type: str) -> Dict[str, Any]:
    """
    Aggregate frame-level vision results into unified scene metadata.
    
    Processing Steps:
    1. Initialize label buckets and counters
    2. Initialize context flag counters
    3. Iterate through all frames:
        a. Classify and bucket each label
        b. Track max confidence per label
        c. Count frame occurrences per label
        d. Update context flags
    4. Aggregate emotions across all faces
    5. Collect unique text detections
    6. Track celebrity appearances
    7. Summarize people (gender, age, dominant emotions)
    8. Infer context from flags
    9. Sort and limit results
    10. Return structured metadata
    
    Args:
        frame_results: List of per-frame Rekognition results
        media_type: "image" or "video"
    
    Returns:
        Aggregated metadata dictionary
    """
    # Initialize buckets
    label_buckets = {
        "objects": defaultdict(float),    # label → max confidence
        "scenes": defaultdict(float),
        "activities": defaultdict(float),
    }
    
    label_counts = {
        "objects": defaultdict(int),      # label → frame occurrence count
        "scenes": defaultdict(int),
        "activities": defaultdict(int),
    }
    
    # Initialize context flags
    context_flags = {
        "environment": Counter(),  # indoor/outdoor counts
        "lighting": Counter(),      # lighting keyword counts
        "crowd": Counter(),         # crowd-related counts
        "activity": Counter(),      # action/dialogue counts
    }
    
    # Initialize collections
    all_emotions = []           # All emotion detections
    text_lines = set()          # Unique text lines
    celebrities_dict = {}       # Celebrity name → confidence
    faces_data = []             # All face details
    
    # Process each frame
    for frame in frame_results:
        # LABEL PROCESSING
        for label in frame.get("labels", []):
            name = label.get("name", "").strip()
            if not name:
                continue
            
            name_lower = name.lower()
            parents = {str(p).lower() for p in label.get("parents", []) if p}
            confidence = float(label.get("confidence", 0.0))
            
            # Classify label into bucket
            bucket_key = _classify_label(name, list(parents))
            
            # Update context flags
            if name_lower in INDOOR_HINTS:
                context_flags["environment"]["indoor"] += 1
            if name_lower in OUTDOOR_HINTS:
                context_flags["environment"]["outdoor"] += 1
            if name_lower in ACTION_HINTS:
                context_flags["activity"]["action"] += 1
            if name_lower in DIALOGUE_HINTS:
                context_flags["activity"]["dialogue"] += 1
            if name_lower in LIGHTING_HINTS:
                context_flags["lighting"][name_lower] += 1
            if name_lower in CROWD_HINTS:
                context_flags["crowd"][name_lower] += 1
            
            # Track max confidence
            label_buckets[bucket_key][name] = max(
                label_buckets[bucket_key][name], 
                confidence
            )
            
            # Count frame occurrences
            label_counts[bucket_key][name] += 1
        
        # FACE PROCESSING
        for face in frame.get("faces", []):
            faces_data.append(face)
            
            # Collect emotions
            for emotion in face.get("emotions", []):
                all_emotions.append({
                    "type": emotion.get("type"),
                    "confidence": emotion.get("confidence")
                })
        
        # CELEBRITY PROCESSING
        for celeb in frame.get("celebrities", []):
            celeb_name = celeb.get("name")
            celeb_conf = celeb.get("confidence", 0.0)
            
            if celeb_name:
                # Track max confidence per celebrity
                celebrities_dict[celeb_name] = max(
                    celebrities_dict.get(celeb_name, 0.0),
                    celeb_conf
                )
        
        # TEXT PROCESSING
        for text_line in frame.get("text", []):
            if text_line:
                text_lines.add(text_line)
    
    # EMOTION AGGREGATION
    emotion_totals = defaultdict(float)
    for emotion in all_emotions:
        emotion_type = emotion.get("type")
        emotion_conf = emotion.get("confidence", 0.0)
        if emotion_type:
            emotion_totals[emotion_type] += emotion_conf
    
    # Sort emotions by total confidence
    emotions_overview = [
        {"emotion": emo, "score": round(score, 2)}
        for emo, score in sorted(
            emotion_totals.items(), 
            key=lambda x: x[1], 
            reverse=True
        )
    ][:5]  # Top 5 emotions
    
    # PEOPLE SUMMARIZATION
    people_summaries = []
    for face in faces_data[:10]:  # Limit to 10 people
        # Extract dominant emotions for this face
        face_emotions = face.get("emotions", [])
        sorted_emotions = sorted(
            face_emotions, 
            key=lambda e: e.get("confidence", 0), 
            reverse=True
        )
        dominant_emotions = [
            e.get("type") for e in sorted_emotions[:2]  # Top 2 emotions
        ]
        
        people_summaries.append({
            "gender": face.get("gender"),
            "ageRange": face.get("ageRange"),
            "dominantEmotions": dominant_emotions,
        })
    
    # CELEBRITY FORMATTING
    celebrities = [
        {"name": name, "confidence": round(conf, 2)}
        for name, conf in sorted(
            celebrities_dict.items(), 
            key=lambda x: x[1], 
            reverse=True
        )
    ][:10]  # Top 10 celebrities
    
    # CONTEXT INFERENCE
    environment = _detect_environment(context_flags)
    activity_focus = _detect_activity_focus(context_flags)
    lighting = _detect_lighting(context_flags)
    crowd_indicator = _detect_crowd(context_flags)
    
    # LABEL FORMATTING AND SORTING
    def _format_bucket(bucket_name: str, limit: int) -> List[Dict]:
        """Format and sort labels from bucket."""
        labels = label_buckets[bucket_name]
        counts = label_counts[bucket_name]
        
        items = [
            {
                "label": label,
                "confidence": round(conf, 2),
                "frameOccurrences": counts[label]
            }
            for label, conf in labels.items()
        ]
        
        # Sort by confidence (descending)
        items.sort(key=lambda x: x["confidence"], reverse=True)
        
        return items[:limit]
    
    # BUILD RESPONSE
    return {
        "mediaType": media_type,
        "framesAnalysed": len(frame_results),
        "objects": _format_bucket("objects", limit=10),
        "activities": _format_bucket("activities", limit=6),
        "scenes": _format_bucket("scenes", limit=6),
        "textDetections": sorted(text_lines),
        "celebrities": celebrities,
        "people": people_summaries,
        "dominantEmotions": emotions_overview,
        "context": {
            "environment": environment,
            "activityFocus": activity_focus,
            "lighting": lighting,
            "crowdIndicator": crowd_indicator,
        },
    }
```

---

## 2. LLM Integration - Bedrock

### 2.1 Bedrock Architecture

**Model Configuration:**
- **Model ID**: `meta.llama3-70b-instruct-v1:0`
- **Region**: us-east-1 (configurable via `BEDROCK_REGION`)
- **Temperature**: 0.4 (balance between creativity and consistency)
- **Top-P**: 0.9 (nucleus sampling for diversity)
- **Max Tokens**: 600 (sufficient for summary + highlights + SSML)

**Invocation Pattern:**
```
Aggregated Metadata (JSON)
          ↓
   Build Structured Prompt
          ↓
   Invoke Bedrock API
          ↓
   Parse Response (multiple formats)
          ↓
   Extract JSON Payload
          ↓
   Validate Structure
          ↓
   Return {summary, highlights, ssml}
          ↓ (if parsing fails)
   Fallback Template
```

### 2.2 Prompt Construction

**_build_bedrock_prompt Function:**

```python
def _build_bedrock_prompt(metadata: Dict[str, Any]) -> str:
    """
    Build structured prompt for Bedrock LLM.
    
    Prompt Structure:
    1. System instruction
    2. JSON metadata payload
    3. Output format specification
    4. Example output structure
    
    Args:
        metadata: Aggregated scene metadata
    
    Returns:
        Formatted prompt string
    """
    prompt = f"""You are an expert video/image analyst. Given the following scene analysis metadata in JSON format, generate:

1. A natural-language summary (under 120 words) capturing the essence of the scene
2. Three key highlights as bullet points
3. An SSML (Speech Synthesis Markup Language) version for voiceover narration

Metadata:
{json.dumps(metadata, indent=2)}

Return your response as a JSON object with this EXACT structure:
{{
  "summary": "Your concise summary here...",
  "highlights": [
    "First key insight",
    "Second key insight",
    "Third key insight"
  ],
  "ssml": "<speak><p>Your SSML-formatted narration here...</p></speak>"
}}

IMPORTANT:
- Summary must be under 120 words
- Use natural, engaging language
- Highlights should extract the most interesting or important aspects
- SSML should include appropriate tags for emphasis, pauses, and structure
- Return ONLY valid JSON, no additional text"""
    
    return prompt
```

**Example Prompt:**

```
You are an expert video/image analyst. Given the following scene analysis metadata in JSON format, generate:

1. A natural-language summary (under 120 words) capturing the essence of the scene
2. Three key highlights as bullet points
3. An SSML (Speech Synthesis Markup Language) version for voiceover narration

Metadata:
{
  "mediaType": "video",
  "framesAnalysed": 36,
  "objects": [
    {"label": "Person", "confidence": 99.8, "frameOccurrences": 36},
    {"label": "Clothing", "confidence": 98.5, "frameOccurrences": 36},
    {"label": "Athletic Shoe", "confidence": 95.2, "frameOccurrences": 32}
  ],
  "activities": [
    {"label": "Running", "confidence": 95.2, "frameOccurrences": 24},
    {"label": "Sport", "confidence": 88.7, "frameOccurrences": 20}
  ],
  "scenes": [
    {"label": "Outdoor", "confidence": 98.5, "frameOccurrences": 36},
    {"label": "Day", "confidence": 96.3, "frameOccurrences": 36}
  ],
  "context": {
    "environment": "outdoor",
    "activityFocus": "action",
    "lighting": "day",
    "crowdIndicator": null
  },
  "people": [
    {
      "gender": "Male",
      "ageRange": {"Low": 25, "High": 35},
      "dominantEmotions": ["HAPPY", "CALM"]
    }
  ],
  "dominantEmotions": [
    {"emotion": "HAPPY", "score": 85.0}
  ],
  "celebrities": [],
  "textDetections": ["FINISH LINE"]
}

Return your response as a JSON object with this EXACT structure:
{
  "summary": "Your concise summary here...",
  "highlights": [
    "First key insight",
    "Second key insight",
    "Third key insight"
  ],
  "ssml": "<speak><p>Your SSML-formatted narration here...</p></speak>"
}

IMPORTANT:
- Summary must be under 120 words
- Use natural, engaging language
- Highlights should extract the most interesting or important aspects
- SSML should include appropriate tags for emphasis, pauses, and structure
- Return ONLY valid JSON, no additional text
```

### 2.3 Bedrock Invocation

**_invoke_bedrock Function:**

```python
def _invoke_bedrock(prompt: str) -> str:
    """
    Invoke AWS Bedrock with Llama3-70B model.
    
    Args:
        prompt: Formatted prompt string
    
    Returns:
        Raw response text from model
    
    Raises:
        Exception: Bedrock API failure
    """
    if not bedrock_runtime:
        raise Exception("Bedrock client unavailable")
    
    # Build request payload
    request_body = {
        "prompt": prompt,
        "temperature": 0.4,
        "top_p": 0.9,
        "max_gen_len": 600,  # Max tokens
    }
    
    try:
        response = bedrock_runtime.invoke_model(
            modelId=SCENE_BEDROCK_MODEL_ID,
            contentType="application/json",
            accept="application/json",
            body=json.dumps(request_body)
        )
        
        # Parse response body
        response_body = json.loads(response["body"].read())
        
        # Extract generated text
        generated_text = response_body.get("generation", "")
        
        if not generated_text:
            raise Exception("Empty response from Bedrock")
        
        return generated_text
    
    except (BotoCoreError, ClientError) as error:
        raise Exception(f"Bedrock invocation failed: {error}")
```

### 2.4 Response Parsing

**Multi-Format Parser:**

```python
def _extract_text_from_bedrock_response(bedrock_response: str) -> str:
    """
    Extract text from Bedrock response (handles multiple formats).
    
    Bedrock may return:
    - Plain JSON string
    - JSON with "generation" key
    - JSON with "output" key
    - Markdown-wrapped JSON (```json ... ```)
    
    Args:
        bedrock_response: Raw Bedrock response
    
    Returns:
        Extracted text content
    """
    if not bedrock_response:
        return ""
    
    # Try parsing as JSON first
    try:
        parsed = json.loads(bedrock_response)
        
        # Check for common response keys
        if isinstance(parsed, dict):
            for key in ["generation", "output", "text", "content"]:
                if key in parsed and isinstance(parsed[key], str):
                    return parsed[key]
        
        # If parsed is already a dict with expected keys, return as-is
        if isinstance(parsed, dict) and "summary" in parsed:
            return json.dumps(parsed)
        
    except json.JSONDecodeError:
        pass
    
    # Return as-is (might be plain text or markdown-wrapped JSON)
    return bedrock_response
```

**JSON Payload Extraction:**

```python
def _parse_summary_payload(text: str) -> Dict[str, Any]:
    """
    Extract JSON payload from LLM response text.
    
    Handles:
    - Plain JSON
    - Markdown code fences (```json ... ```)
    - Markdown code fences (``` ... ```)
    - Text with JSON embedded
    
    Args:
        text: LLM response text
    
    Returns:
        Parsed JSON dictionary
    
    Raises:
        ValueError: No valid JSON found
    """
    if not text:
        raise ValueError("Empty response text")
    
    text = text.strip()
    
    # Remove markdown code fences
    if text.startswith("```json"):
        text = text[7:]  # Remove ```json
    elif text.startswith("```"):
        text = text[3:]   # Remove ```
    
    if text.endswith("```"):
        text = text[:-3]  # Remove trailing ```
    
    text = text.strip()
    
    # Try parsing directly
    try:
        payload = json.loads(text)
        
        # Validate structure
        if isinstance(payload, dict) and "summary" in payload:
            return payload
        
    except json.JSONDecodeError:
        pass
    
    # Try extracting JSON from text (find first { to last })
    start_idx = text.find("{")
    end_idx = text.rfind("}")
    
    if start_idx != -1 and end_idx != -1 and end_idx > start_idx:
        json_str = text[start_idx:end_idx+1]
        try:
            payload = json.loads(json_str)
            
            if isinstance(payload, dict) and "summary" in payload:
                return payload
        
        except json.JSONDecodeError:
            pass
    
    raise ValueError(f"Could not extract valid JSON from response: {text[:200]}...")
```

### 2.5 Fallback Template

**_fallback_summary Function:**

```python
def _fallback_summary(metadata: Dict[str, Any]) -> Dict[str, Any]:
    """
    Generate fallback summary when LLM fails or response is invalid.
    
    Template uses actual metadata values to construct basic summary.
    
    Args:
        metadata: Aggregated scene metadata
    
    Returns:
        Fallback response with summary, highlights, ssml
    """
    media_type = metadata.get("mediaType", "scene")
    frames_count = metadata.get("framesAnalysed", 0)
    
    # Extract top objects
    objects = metadata.get("objects", [])
    top_objects = [obj["label"] for obj in objects[:3]]
    objects_str = ", ".join(top_objects) if top_objects else "various elements"
    
    # Extract context
    context = metadata.get("context", {})
    environment = context.get("environment", "unknown")
    activity_focus = context.get("activityFocus", "unclear")
    
    # Extract people info
    people = metadata.get("people", [])
    people_count = len(people)
    
    # Extract emotions
    emotions = metadata.get("dominantEmotions", [])
    emotion_str = ", ".join([e["emotion"] for e in emotions[:3]]) if emotions else "not detected"
    
    # Build summary
    summary = (
        f"This {media_type} features {objects_str}. "
        f"The scene appears to be {environment} with {activity_focus} activity. "
        f"{people_count} {'person' if people_count == 1 else 'people'} detected "
        f"with emotions: {emotion_str}."
    )
    
    # Build highlights
    highlights = [
        f"Top objects: {objects_str}",
        f"Scene type: {environment}",
        f"Detected emotions: {emotion_str}",
    ]
    
    # Build SSML
    ssml = (
        f"<speak>"
        f"<p>{summary}</p>"
        f"</speak>"
    )
    
    return {
        "summary": summary,
        "highlights": highlights,
        "ssml": ssml,
    }
```

### 2.6 Summary Generation Orchestration

**_generate_summary Function:**

```python
def _generate_summary(metadata: Dict[str, Any]) -> Dict[str, Any]:
    """
    Generate summary using Bedrock LLM with fallback.
    
    Workflow:
    1. Build structured prompt
    2. Invoke Bedrock
    3. Parse response text
    4. Extract JSON payload
    5. Validate structure
    6. Return payload
    7. On failure → fallback template
    
    Args:
        metadata: Aggregated scene metadata
    
    Returns:
        {
          "summary": str,
          "highlights": [str],
          "ssml": str
        }
    """
    try:
        # Build prompt
        prompt = _build_bedrock_prompt(metadata)
        
        # Invoke Bedrock
        raw_response = _invoke_bedrock(prompt)
        
        # Extract text
        response_text = _extract_text_from_bedrock_response(raw_response)
        
        # Parse JSON payload
        payload = _parse_summary_payload(response_text)
        
        # Validate required fields
        if not isinstance(payload, dict):
            raise ValueError("Payload is not a dictionary")
        
        if "summary" not in payload:
            raise ValueError("Missing 'summary' field")
        
        # Ensure highlights is a list
        if "highlights" not in payload:
            payload["highlights"] = []
        elif not isinstance(payload["highlights"], list):
            payload["highlights"] = [str(payload["highlights"])]
        
        # Ensure ssml exists
        if "ssml" not in payload or not payload["ssml"]:
            # Generate basic SSML from summary
            payload["ssml"] = f"<speak><p>{payload['summary']}</p></speak>"
        
        return payload
    
    except Exception as error:
        print(f"ERROR in _generate_summary: {error}")
        print("Falling back to template summary")
        return _fallback_summary(metadata)
```

---

## 3. TTS Synthesis - Polly

### 3.1 Polly Architecture

**Configuration:**
- **Region**: us-west-2 (configurable via `POLLY_REGION`)
- **Engine**: Neural (superior quality vs standard)
- **Voice ID**: Configurable (default: Joanna)
- **Output Format**: MP3 with 24kHz sample rate
- **Input**: SSML markup language

**Available Neural Voices:**
- **US English**: Joanna (F), Matthew (M), Ivy (F, child), Joey (M, child)
- **British English**: Amy (F), Brian (M), Emma (F)
- **Australian English**: Olivia (F)
- **Indian English**: Kajal (F)
- **And 50+ more voices across languages**

### 3.2 SSML Processing

**Supported SSML Tags:**

```xml
<!-- Paragraph breaks -->
<p>This is a paragraph.</p>

<!-- Sentence breaks -->
<s>This is a sentence.</s>

<!-- Emphasis (strong, moderate, reduced) -->
<emphasis level="strong">emphasized text</emphasis>

<!-- Pauses -->
<break time="500ms"/>
<break strength="medium"/>

<!-- Prosody (rate, pitch, volume) -->
<prosody rate="slow">slower speech</prosody>
<prosody pitch="+10%">higher pitch</prosody>

<!-- Say-as (interpret text differently) -->
<say-as interpret-as="digits">123</say-as>
<say-as interpret-as="date" format="mdy">10/21/2025</say-as>
```

**Example SSML Generated by LLM:**

```xml
<speak>
  <p>This video shows an exciting outdoor race.</p>
  <break time="500ms"/>
  <p>A male runner, <emphasis level="strong">age 25 to 35</emphasis>, 
     sprints toward the finish line with determination.</p>
  <break time="300ms"/>
  <p>The scene captures <emphasis>intense athletic action</emphasis> 
     in broad daylight, with the runner displaying 
     <emphasis level="moderate">happiness and focus</emphasis>.</p>
  <break time="500ms"/>
  <p>The text "FINISH LINE" is visible on screen, marking the climactic moment.</p>
</speak>
```

### 3.3 Audio Synthesis Function

**_synth_audio Implementation:**

```python
def _synth_audio(ssml_text: str, voice_id: str, file_id: str) -> Optional[str]:
    """
    Synthesize audio from SSML using AWS Polly.
    
    Args:
        ssml_text: SSML markup text
        voice_id: Polly voice ID (e.g., "Joanna")
        file_id: Unique file ID for output filename
    
    Returns:
        Relative URL path to audio file (e.g., "/audio/uuid.mp3")
        Returns None if synthesis fails
    
    Side Effects:
        Saves MP3 file to ./outputs/audio/{file_id}.mp3
    """
    if not polly:
        print("WARNING: Polly client unavailable")
        return None
    
    if not ssml_text:
        print("WARNING: Empty SSML text")
        return None
    
    try:
        # Invoke Polly synthesize_speech
        response = polly.synthesize_speech(
            Text=ssml_text,
            TextType="ssml",  # SSML format (vs "text")
            VoiceId=voice_id,
            Engine="neural",  # Neural engine (vs "standard")
            OutputFormat="mp3",
            SampleRate="24000",  # 24kHz
        )
        
        # Read audio stream
        audio_stream = response.get("AudioStream")
        if not audio_stream:
            raise Exception("No audio stream in response")
        
        # Save to file
        audio_path = AUDIO_FOLDER / f"{file_id}.mp3"
        with open(audio_path, "wb") as audio_file:
            audio_file.write(audio_stream.read())
        
        print(f"Audio synthesized: {audio_path}")
        
        # Return relative URL
        return f"/audio/{file_id}.mp3"
    
    except (BotoCoreError, ClientError) as error:
        print(f"ERROR: Polly synthesis failed: {error}")
        return None
    
    except Exception as error:
        print(f"ERROR: Audio synthesis failed: {error}")
        return None
```

**Audio File Properties:**
- **Format**: MP3
- **Sample Rate**: 24 kHz
- **Bitrate**: ~48 kbps (variable, depends on content)
- **Typical Size**: ~12 KB per second of audio
- **Example**: 30-second narration ≈ 360 KB

---

## 4. Result Storage & Retrieval

### 4.1 File-Based Storage

**Storage Architecture:**

```
outputs/
├── metadata/
│   ├── a1b2c3d4-e5f6-7890-abcd-ef1234567890.json
│   ├── b2c3d4e5-f6g7-8901-bcde-fg2345678901.json
│   └── ...
└── audio/
    ├── a1b2c3d4-e5f6-7890-abcd-ef1234567890.mp3
    ├── b2c3d4e5-f6g7-8901-bcde-fg2345678901.mp3
    └── ...
```

**Metadata File Structure:**

```json
{
  "file_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "timestamp": "2025-10-21T14:30:45.123Z",
  "mediaType": "video",
  "framesAnalysed": 36,
  "objects": [
    {"label": "Person", "confidence": 99.8, "frameOccurrences": 36}
  ],
  "activities": [
    {"label": "Running", "confidence": 95.2, "frameOccurrences": 24}
  ],
  "scenes": [
    {"label": "Outdoor", "confidence": 98.5, "frameOccurrences": 36}
  ],
  "context": {
    "environment": "outdoor",
    "activityFocus": "action",
    "lighting": "day",
    "crowdIndicator": null
  },
  "people": [
    {
      "gender": "Male",
      "ageRange": {"Low": 25, "High": 35},
      "dominantEmotions": ["HAPPY", "CALM"]
    }
  ],
  "dominantEmotions": [
    {"emotion": "HAPPY", "score": 85.0}
  ],
  "celebrities": [],
  "textDetections": ["FINISH LINE"]
}
```

### 4.2 Result Saving

**Save Metadata:**

```python
def _save_metadata(file_id: str, metadata: Dict[str, Any]):
    """
    Save metadata to JSON file.
    
    Args:
        file_id: Unique file ID
        metadata: Complete metadata dictionary
    """
    metadata_path = METADATA_FOLDER / f"{file_id}.json"
    
    # Add timestamp
    metadata["timestamp"] = datetime.utcnow().isoformat() + "Z"
    metadata["file_id"] = file_id
    
    with open(metadata_path, "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2, ensure_ascii=False)
    
    print(f"Metadata saved: {metadata_path}")
```

### 4.3 Result Retrieval Endpoints

**GET /result/:file_id**

```python
@app.route("/result/<file_id>", methods=["GET"])
def get_result(file_id: str):
    """
    Retrieve stored result metadata by file ID.
    
    Args:
        file_id: UUID of processed file
    
    Returns:
        200: JSON metadata
        404: File not found
        500: Read error
    """
    metadata_path = METADATA_FOLDER / f"{file_id}.json"
    
    if not metadata_path.exists():
        return jsonify({"error": f"Result not found: {file_id}"}), 404
    
    try:
        with open(metadata_path, "r", encoding="utf-8") as f:
            metadata = json.load(f)
        
        return jsonify(metadata), 200
    
    except Exception as error:
        return jsonify({"error": f"Failed to read result: {error}"}), 500
```

**GET /audio/:file_id**

```python
@app.route("/audio/<file_id>", methods=["GET"])
def get_audio(file_id: str):
    """
    Stream audio file by file ID.
    
    Args:
        file_id: UUID of processed file (without .mp3 extension)
    
    Returns:
        200: MP3 audio stream
        404: File not found
    
    Headers:
        Content-Type: audio/mpeg
        Content-Disposition: inline; filename="{file_id}.mp3"
    """
    # Sanitize file_id (remove .mp3 if present)
    if file_id.endswith(".mp3"):
        file_id = file_id[:-4]
    
    audio_path = AUDIO_FOLDER / f"{file_id}.mp3"
    
    if not audio_path.exists():
        return jsonify({"error": f"Audio not found: {file_id}"}), 404
    
    return send_file(
        str(audio_path),
        mimetype="audio/mpeg",
        as_attachment=False,  # Inline playback (not download)
        download_name=f"{file_id}.mp3"
    )
```

---

## 5. S3 Video Upload

### 5.1 Upload Configuration

**Environment Variables:**
```bash
SCENE_S3_BUCKET=my-video-bucket
SCENE_S3_PREFIX=scene-videos/
S3_REGION=us-east-1
```

**Conditional Upload:**
- Only uploads if `SCENE_S3_BUCKET` is configured
- Only uploads video files (not images)
- Skipped silently if S3 client unavailable
- Does not block processing on failure

### 5.2 Upload Function

**_upload_to_s3 Implementation:**

```python
def _upload_to_s3(file_path: str, file_id: str, original_filename: str) -> Optional[Dict[str, str]]:
    """
    Upload video file to S3 bucket.
    
    Args:
        file_path: Local path to video file
        file_id: Unique file ID
        original_filename: Original uploaded filename
    
    Returns:
        {
          "bucket": "my-bucket",
          "key": "scene-videos/uuid/video.mp4",
          "uri": "s3://my-bucket/scene-videos/uuid/video.mp4"
        }
        Returns None if upload fails or not configured
    """
    if not s3:
        print("INFO: S3 client unavailable, skipping upload")
        return None
    
    if not SCENE_S3_BUCKET:
        print("INFO: S3 bucket not configured, skipping upload")
        return None
    
    try:
        # Build S3 key with file_id subdirectory
        safe_filename = secure_filename(original_filename)
        key = f"{SCENE_S3_PREFIX}{file_id}/{safe_filename}"
        
        # Upload file
        with open(file_path, "rb") as f:
            s3.upload_fileobj(
                f,
                SCENE_S3_BUCKET,
                key,
                ExtraArgs={
                    "ContentType": "video/mp4",  # Adjust based on actual type
                }
            )
        
        print(f"Uploaded to S3: s3://{SCENE_S3_BUCKET}/{key}")
        
        return {
            "bucket": SCENE_S3_BUCKET,
            "key": key,
            "uri": f"s3://{SCENE_S3_BUCKET}/{key}"
        }
    
    except (BotoCoreError, ClientError) as error:
        print(f"ERROR: S3 upload failed: {error}")
        return None
    
    except Exception as error:
        print(f"ERROR: S3 upload failed: {error}")
        return None
```

### 5.3 Integration in Main Processing

**_process_media Function (excerpt):**

```python
def _process_media(upload_path: str, media_type: str, file_id: str, 
                   voice_id: str, original_file) -> Dict[str, Any]:
    """
    Main processing orchestration.
    
    Steps:
    1. Analyze media (frames + vision)
    2. Aggregate results
    3. Generate summary (LLM)
    4. Synthesize audio (TTS)
    5. Upload to S3 (videos only)
    6. Save metadata
    7. Return response
    """
    # ... (analysis and aggregation steps)
    
    # Upload to S3 if video
    source_video = None
    if media_type == "video":
        source_video = _upload_to_s3(
            upload_path, 
            file_id, 
            original_file.filename
        )
    
    # Build response
    result = {
        "file_id": file_id,
        "summary": summary_payload.get("summary", ""),
        "highlights": summary_payload.get("highlights", []),
        "ssml": summary_payload.get("ssml", ""),
        "audio_url": audio_url,
        "voice_id": voice_id,
        "metadata": aggregated_metadata,
    }
    
    # Add source_video if available
    if source_video:
        result["source_video"] = source_video
    
    # Save metadata
    _save_metadata(file_id, aggregated_metadata)
    
    return result
```

---

*Continued in Part 3...*

## Document Continuation

**Next Document:** `SCENE_SUMMARIZATION_PART3.md`

**Part 3 Contents:**
- Frontend Architecture
- React Component Structure
- Processing Phases & Timeline
- UI Components & Styling
- File Upload & Preview Logic
- Result Display Components

# Scene Summarization Service - Complete Technical Reference
## Part 3 of 4: Frontend Architecture & UI Components

**MediaGenAI Platform - Service Documentation**  
**Document Version:** 1.0  
**Service Port:** 5005  
**Last Updated:** October 21, 2025

---

## Document Navigation

- **Part 1**: Executive Summary, Architecture Overview, Backend Deep Dive (Media Processing, Vision Analysis)
- **Part 2**: Aggregation Logic, LLM Integration, TTS Synthesis, Result Storage
- **Part 3** (this document): Frontend Architecture, Processing Phases, UI Components
- **Part 4**: AWS Integration, API Reference, Configuration, Deployment, Troubleshooting

---

## Table of Contents - Part 3

1. [Frontend Architecture Overview](#1-frontend-architecture-overview)
2. [Component Structure](#2-component-structure)
3. [State Management](#3-state-management)
4. [Processing Phases & Timeline](#4-processing-phases--timeline)
5. [File Upload & Preview](#5-file-upload--preview)
6. [API Integration](#6-api-integration)
7. [Result Display Components](#7-result-display-components)

---

## 1. Frontend Architecture Overview

### 1.1 Technology Stack

**Core Technologies:**
- **React**: 18+ with Hooks (useState, useEffect, useRef, useCallback)
- **styled-components**: CSS-in-JS styling solution
- **axios**: HTTP client with upload progress tracking
- **HTML5 APIs**: FileReader, Video element, URL.createObjectURL

**Component File**: `frontend/src/SceneSummarization.js` (1152 lines)

**Key Features:**
- Single-page component (no sub-components)
- Declarative state management with useState
- Side effects handled with useEffect
- Drag-and-drop file upload
- Real-time progress tracking
- Responsive UI with styled-components
- Audio playback integration
- Metadata visualization (cards, tags, JSON)

### 1.2 Component Architecture

```
SceneSummarization Component
├─ Styled Components (Lines 1-200)
│  ├─ Page, Title, Lead
│  ├─ UploadCard, PreviewWrap
│  ├─ ProgressContainer, PhaseList
│  ├─ Card, CardTitle, SectionSubhead
│  ├─ TagList, Tag, MetadataList
│  └─ AudioPlayer, JsonPre, SsmlPre
│
├─ State Management (Lines 200-300)
│  ├─ selectedFile (File object)
│  ├─ previewUrl (object URL)
│  ├─ processing (boolean)
│  ├─ processingPhase (enum: idle, uploading, analyzing, etc.)
│  ├─ uploadProgress (0-100 or null)
│  ├─ processingProgress (0-100)
│  ├─ status (string message)
│  ├─ error (string or null)
│  ├─ result (API response object)
│  ├─ voiceId (Polly voice selection)
│  ├─ dragOver (boolean for drag-drop)
│  └─ videoDuration (seconds or null)
│
├─ Event Handlers (Lines 300-600)
│  ├─ onDragOver, onDrop, onDragLeave
│  ├─ onFileInputChange
│  ├─ computeVideoDuration
│  ├─ handleFileSelection
│  └─ clearSelection
│
├─ Processing Logic (Lines 600-900)
│  ├─ updateProcessingPhase
│  ├─ scheduleProcessingPhases (fallback timers)
│  ├─ clearPhaseTimers
│  ├─ startUploadFallbackTimer
│  ├─ clearUploadFallbackTimer
│  └─ analyseScene (main API call)
│
└─ Render Logic (Lines 900-1152)
   ├─ Upload UI
   ├─ File metadata display
   ├─ Preview (image or video)
   ├─ Voice selection
   ├─ Action buttons
   ├─ Status messages
   ├─ Progress bars
   ├─ Phase timeline
   ├─ Result cards (5 cards)
   └─ SSML and JSON display
```

---

## 2. Component Structure

### 2.1 Styled Components

**Page Layout:**

```javascript
const Page = styled.div`
  max-width: 1400px;
  margin: 0 auto;
  padding: 2rem;
  font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
`;

const Title = styled.h1`
  font-size: 2.5rem;
  font-weight: 700;
  color: #1a1a1a;
  margin-bottom: 0.5rem;
`;

const Lead = styled.p`
  font-size: 1.125rem;
  line-height: 1.6;
  color: #666;
  margin-bottom: 2rem;
`;
```

**Upload Card:**

```javascript
const UploadCard = styled.label`
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 3rem 2rem;
  border: 2px dashed #cbd5e0;
  border-radius: 12px;
  background: #f7fafc;
  cursor: pointer;
  transition: all 0.2s ease;
  margin-bottom: 2rem;

  &:hover {
    border-color: #4299e1;
    background: #ebf8ff;
  }

  &.dragover {
    border-color: #3182ce;
    background: #bee3f8;
    transform: scale(1.02);
  }
`;

const UploadIcon = styled.div`
  font-size: 3rem;
  margin-bottom: 1rem;
`;

const UploadTitle = styled.div`
  font-size: 1.25rem;
  font-weight: 600;
  color: #2d3748;
  margin-bottom: 0.5rem;
`;

const UploadHint = styled.div`
  font-size: 0.875rem;
  color: #718096;
`;

const HiddenInput = styled.input`
  display: none;
`;
```

**Progress UI:**

```javascript
const ProgressContainer = styled.div`
  margin: 2rem 0;
  padding: 1.5rem;
  background: #f7fafc;
  border-radius: 8px;
  border: 1px solid #e2e8f0;
`;

const ProgressLabel = styled.div`
  font-size: 0.875rem;
  font-weight: 600;
  color: #2d3748;
  margin-bottom: 0.5rem;
`;

const ProgressTrack = styled.div`
  width: 100%;
  height: 8px;
  background: #e2e8f0;
  border-radius: 4px;
  overflow: hidden;
  margin-bottom: 1rem;
`;

const ProgressFill = styled.div`
  height: 100%;
  background: ${props => props.$error ? '#e53e3e' : '#4299e1'};
  width: ${props => props.$percent}%;
  transition: width 0.3s ease;
  border-radius: 4px;
`;
```

**Phase Timeline:**

```javascript
const PhaseList = styled.ul`
  list-style: none;
  padding: 0;
  margin: 1.5rem 0 0 0;
  display: flex;
  flex-wrap: wrap;
  gap: 1rem;
`;

const PhaseItem = styled.li`
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-size: 0.875rem;
  color: ${props => {
    if (props.$status === 'complete') return '#38a169';
    if (props.$status === 'active') return '#3182ce';
    if (props.$status === 'error') return '#e53e3e';
    return '#a0aec0';
  }};
  font-weight: ${props => props.$status === 'active' ? '600' : '400'};
`;

const PhaseDot = styled.span`
  width: 12px;
  height: 12px;
  border-radius: 50%;
  background: ${props => {
    if (props.$status === 'complete') return '#38a169';
    if (props.$status === 'active') return '#3182ce';
    if (props.$status === 'error') return '#e53e3e';
    return '#cbd5e0';
  }};
  border: 2px solid ${props => {
    if (props.$status === 'active') return '#3182ce';
    return 'transparent';
  }};
  animation: ${props => props.$status === 'active' ? 'pulse 1.5s ease-in-out infinite' : 'none'};

  @keyframes pulse {
    0%, 100% { opacity: 1; }
    50% { opacity: 0.5; }
  }
`;
```

**Result Cards:**

```javascript
const ResultGrid = styled.div`
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(400px, 1fr));
  gap: 1.5rem;
  margin-top: 2rem;
`;

const Card = styled.div`
  background: white;
  border-radius: 12px;
  padding: 1.5rem;
  box-shadow: 0 1px 3px rgba(0,0,0,0.1);
  border: 1px solid #e2e8f0;
`;

const CardTitle = styled.h3`
  font-size: 1.25rem;
  font-weight: 700;
  color: #1a1a1a;
  margin: 0 0 1rem 0;
`;

const SectionSubhead = styled.h4`
  font-size: 0.875rem;
  font-weight: 600;
  color: #4a5568;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  margin: 1.5rem 0 0.75rem 0;
`;
```

**Metadata Display:**

```javascript
const TagList = styled.div`
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
  margin-top: 0.5rem;
`;

const Tag = styled.span`
  display: inline-block;
  padding: 0.25rem 0.75rem;
  background: #ebf8ff;
  color: #2c5282;
  border-radius: 16px;
  font-size: 0.875rem;
  font-weight: 500;
`;

const MetadataList = styled.ul`
  list-style: none;
  padding: 0;
  margin: 0.5rem 0 0 0;
`;

const MetadataItem = styled.li`
  padding: 0.5rem 0;
  border-bottom: 1px solid #f7fafc;
  font-size: 0.875rem;
  color: #4a5568;

  &:last-child {
    border-bottom: none;
  }

  strong {
    color: #2d3748;
    font-weight: 600;
  }
`;
```

**Code Display:**

```javascript
const JsonPre = styled.pre`
  background: #2d3748;
  color: #e2e8f0;
  padding: 1rem;
  border-radius: 8px;
  overflow-x: auto;
  font-size: 0.75rem;
  line-height: 1.5;
  font-family: 'Courier New', monospace;
`;

const SsmlPre = styled.pre`
  background: #f7fafc;
  color: #2d3748;
  padding: 1rem;
  border-radius: 8px;
  overflow-x: auto;
  font-size: 0.875rem;
  line-height: 1.6;
  font-family: 'Courier New', monospace;
  border: 1px solid #e2e8f0;
`;

const AudioPlayer = styled.audio`
  width: 100%;
  margin-top: 1rem;
`;
```

---

## 3. State Management

### 3.1 State Variables

**File State:**

```javascript
const [selectedFile, setSelectedFile] = useState(null);  // File object
const [previewUrl, setPreviewUrl] = useState('');        // Object URL for preview
const [dragOver, setDragOver] = useState(false);         // Drag-drop state
const [videoDuration, setVideoDuration] = useState(null); // Video duration in seconds
```

**Processing State:**

```javascript
const [processing, setProcessing] = useState(false);              // Global processing flag
const [processingPhase, setProcessingPhase] = useState('idle');   // Current phase
const [uploadProgress, setUploadProgress] = useState(null);       // Upload % or null
const [processingProgress, setProcessingProgress] = useState(0);  // Overall % (0-100)
```

**Processing Phases:**
```javascript
const PHASES = {
  IDLE: 'idle',
  UPLOADING: 'uploading',
  ANALYSING: 'analysing',
  SUMMARISING: 'summarising',
  SYNTHESISING: 'synthesising',
  COMPLETE: 'complete',
  ERROR: 'error',
};
```

**Result State:**

```javascript
const [result, setResult] = useState(null);  // API response object
const [status, setStatus] = useState('');    // Status message string
const [error, setError] = useState('');      // Error message string
```

**Configuration State:**

```javascript
const [voiceId, setVoiceId] = useState('Joanna');  // Selected Polly voice

const voiceOptions = [
  { value: 'Joanna', label: 'Joanna (US, Female, Neural)' },
  { value: 'Matthew', label: 'Matthew (US, Male, Neural)' },
  { value: 'Amy', label: 'Amy (British, Female, Neural)' },
  { value: 'Brian', label: 'Brian (British, Male, Neural)' },
  { value: 'Olivia', label: 'Olivia (Australian, Female, Neural)' },
];
```

**Refs (for timer management):**

```javascript
const phaseTimersRef = useRef([]);           // Array of timeout IDs for phase progression
const uploadFallbackTimerRef = useRef(null); // Timeout ID for upload fallback
const timelineScheduledRef = useRef(false);  // Flag to prevent duplicate scheduling
```

### 3.2 Derived State

**Phase Labels:**

```javascript
const PHASE_LABEL_MAP = {
  idle: 'Ready to analyse',
  uploading: 'Uploading media…',
  analysing: 'Analyzing frames with Rekognition…',
  summarising: 'Generating summary with Bedrock…',
  synthesising: 'Synthesizing voiceover with Polly…',
  complete: 'Scene analysis complete!',
  error: 'Processing failed',
};

const currentPhaseLabel = PHASE_LABEL_MAP[processingPhase] || 'Processing…';
```

**Timeout Calculation:**

```javascript
const DEFAULT_TIMEOUT_MS = 3 * 60 * 60 * 1000;  // 3 hours
const DURATION_BASED_TIMEOUT_MULTIPLIER = 5;     // 5× video duration

const derivedTimeoutMs = useMemo(() => {
  if (videoDuration && videoDuration > 0) {
    return Math.max(
      30 * 1000,  // Minimum 30 seconds
      videoDuration * DURATION_BASED_TIMEOUT_MULTIPLIER * 1000
    );
  }
  return DEFAULT_TIMEOUT_MS;
}, [videoDuration]);

const usingDurationTimeout = Boolean(videoDuration && videoDuration > 0);

const formattedTimeout = useMemo(() => {
  const totalSeconds = Math.floor(derivedTimeoutMs / 1000);
  if (totalSeconds < 60) return `${totalSeconds}s`;
  if (totalSeconds < 3600) return `${Math.floor(totalSeconds / 60)}min`;
  return `${Math.floor(totalSeconds / 3600)}h`;
}, [derivedTimeoutMs]);
```

**Progress Bar Display:**

```javascript
const showProgressUI = processing || processingPhase === 'complete' || processingPhase === 'error';

const showUploadBar = uploadProgress !== null && uploadProgress < 100;

const progressBarPercent = processingPhase === 'error' ? 0 : processingProgress;
```

**Phase Timeline Items:**

```javascript
const phaseItems = [
  { key: 'uploading', label: 'Upload', status: getPhaseStatus('uploading') },
  { key: 'analysing', label: 'Analyse', status: getPhaseStatus('analysing') },
  { key: 'summarising', label: 'Summarise', status: getPhaseStatus('summarising') },
  { key: 'synthesising', label: 'Synthesise', status: getPhaseStatus('synthesising') },
  { key: 'complete', label: 'Complete', status: getPhaseStatus('complete') },
];

function getPhaseStatus(phase) {
  const phaseOrder = ['uploading', 'analysing', 'summarising', 'synthesising', 'complete'];
  const currentIndex = phaseOrder.indexOf(processingPhase);
  const targetIndex = phaseOrder.indexOf(phase);
  
  if (processingPhase === 'error') return 'error';
  if (targetIndex < currentIndex) return 'complete';
  if (targetIndex === currentIndex) return 'active';
  return 'pending';
}
```

---

## 4. Processing Phases & Timeline

### 4.1 Phase Progression Model

**Phase Order:**
```
idle → uploading → analysing → summarising → synthesising → complete
                                                              ↓
                                                            error
```

**Phase Durations (Fallback Timers):**
- **Upload → Analyse**: 4.5 seconds after upload completes
- **Analyse → Summarise**: 9 seconds after analyse starts
- **Summarise → Synthesise**: 13 seconds after summarise starts
- **Synthesise → Complete**: Set by server response

**Why Fallback Timers?**
Backend is synchronous and doesn't send real-time updates. Frontend schedules phase transitions to provide visual feedback even without server communication.

### 4.2 Phase Update Function

```javascript
const updateProcessingPhase = useCallback((newPhase) => {
  setProcessingPhase(newPhase);
  setStatus(PHASE_LABEL_MAP[newPhase] || '');
  
  // Update progress percentage based on phase
  const phaseProgressMap = {
    idle: 0,
    uploading: 0,
    analysing: 55,
    summarising: 75,
    synthesising: 90,
    complete: 100,
    error: 0,
  };
  
  const targetProgress = phaseProgressMap[newPhase] || 0;
  setProcessingProgress((prev) => Math.max(prev, targetProgress));
}, []);
```

### 4.3 Fallback Timer Scheduling

**Main Scheduling Function:**

```javascript
const scheduleProcessingPhases = useCallback(() => {
  if (timelineScheduledRef.current) {
    return;  // Already scheduled
  }
  
  timelineScheduledRef.current = true;
  
  // Clear any existing timers
  clearPhaseTimers();
  
  // Schedule phase transitions
  const timers = [
    // Analyse → Summarise (9 seconds)
    setTimeout(() => {
      setProcessingPhase((current) => {
        if (current === 'analysing') {
          updateProcessingPhase('summarising');
        }
        return current;
      });
    }, 9000),
    
    // Summarise → Synthesise (13 seconds after analyse start)
    setTimeout(() => {
      setProcessingPhase((current) => {
        if (current === 'summarising') {
          updateProcessingPhase('synthesising');
        }
        return current;
      });
    }, 13000),
  ];
  
  phaseTimersRef.current = timers;
}, [updateProcessingPhase]);
```

**Upload Fallback Timer:**

```javascript
const startUploadFallbackTimer = useCallback(() => {
  clearUploadFallbackTimer();
  
  // If upload doesn't complete in 4.5 seconds, move to analyse phase
  const timer = setTimeout(() => {
    setProcessingPhase((current) => {
      if (current === 'uploading') {
        updateProcessingPhase('analysing');
        setProcessingProgress((prev) => Math.max(prev, 55));
        scheduleProcessingPhases();
      }
      return current;
    });
  }, 4500);
  
  uploadFallbackTimerRef.current = timer;
}, [updateProcessingPhase, scheduleProcessingPhases]);
```

**Timer Cleanup:**

```javascript
const clearPhaseTimers = useCallback(() => {
  phaseTimersRef.current.forEach((timer) => clearTimeout(timer));
  phaseTimersRef.current = [];
  timelineScheduledRef.current = false;
}, []);

const clearUploadFallbackTimer = useCallback(() => {
  if (uploadFallbackTimerRef.current) {
    clearTimeout(uploadFallbackTimerRef.current);
    uploadFallbackTimerRef.current = null;
  }
}, []);
```

### 4.4 Progress Percentage Mapping

**Upload Progress Contribution:**
Upload progress (0-100%) contributes 40% to overall progress:
```javascript
const uploadContribution = Math.round(uploadProgress * 0.4);
setProcessingProgress((prev) => Math.max(prev, uploadContribution));
```

**Phase-Based Progress:**
- **Idle**: 0%
- **Uploading**: 0-40% (based on actual upload progress)
- **Analysing**: 55%
- **Summarising**: 75%
- **Synthesising**: 90%
- **Complete**: 100%
- **Error**: 0%

---

## 5. File Upload & Preview

### 5.1 Drag-and-Drop Handlers

**Drag Over:**

```javascript
const onDragOver = useCallback((event) => {
  event.preventDefault();
  event.stopPropagation();
  setDragOver(true);
}, []);
```

**Drag Leave:**

```javascript
const onDragLeave = useCallback((event) => {
  event.preventDefault();
  event.stopPropagation();
  setDragOver(false);
}, []);
```

**Drop:**

```javascript
const onDrop = useCallback((event) => {
  event.preventDefault();
  event.stopPropagation();
  setDragOver(false);
  
  const files = event.dataTransfer.files;
  if (files && files.length > 0) {
    handleFileSelection(files[0]);
  }
}, []);
```

### 5.2 File Input Handler

```javascript
const onFileInputChange = useCallback((event) => {
  const files = event.target.files;
  if (files && files.length > 0) {
    handleFileSelection(files[0]);
  }
  // Reset input to allow re-selecting same file
  event.target.value = '';
}, []);
```

### 5.3 File Selection Logic

```javascript
const handleFileSelection = useCallback((file) => {
  if (!file) return;
  
  // Validate file size (2GB limit)
  const MAX_SIZE = 2 * 1024 * 1024 * 1024;
  if (file.size > MAX_SIZE) {
    setError(`File too large: ${(file.size / (1024**3)).toFixed(2)} GB. Max size: 2 GB.`);
    return;
  }
  
  // Clear previous state
  resetState();
  
  // Set selected file
  setSelectedFile(file);
  
  // Generate preview URL
  const objectUrl = URL.createObjectURL(file);
  setPreviewUrl(objectUrl);
  
  // Compute video duration (if video)
  if (file.type.startsWith('video/')) {
    computeVideoDuration(objectUrl);
  }
}, []);
```

### 5.4 Video Duration Computation

```javascript
const computeVideoDuration = useCallback((videoUrl) => {
  const videoElement = document.createElement('video');
  
  videoElement.addEventListener('loadedmetadata', () => {
    const duration = videoElement.duration;
    if (duration && isFinite(duration)) {
      setVideoDuration(duration);
      console.log(`Video duration: ${duration.toFixed(2)}s`);
    }
    URL.revokeObjectURL(videoUrl);  // Cleanup
  });
  
  videoElement.addEventListener('error', () => {
    console.warn('Failed to load video metadata');
    setVideoDuration(null);
    URL.revokeObjectURL(videoUrl);
  });
  
  videoElement.src = videoUrl;
}, []);
```

### 5.5 Preview Component

**Image Preview:**

```javascript
{selectedFile?.type.startsWith('image/') && (
  <PreviewImage src={previewUrl} alt="Scene preview" />
)}
```

**Video Preview:**

```javascript
{selectedFile?.type.startsWith('video/') && (
  <PreviewVideo src={previewUrl} controls preload="metadata" />
)}
```

**Styled Components:**

```javascript
const PreviewWrap = styled.div`
  margin: 1.5rem 0;
  text-align: center;
  
  span {
    display: block;
    margin-top: 0.5rem;
    font-size: 0.875rem;
    color: #718096;
  }
`;

const PreviewImage = styled.img`
  max-width: 100%;
  max-height: 400px;
  border-radius: 8px;
  box-shadow: 0 4px 6px rgba(0,0,0,0.1);
`;

const PreviewVideo = styled.video`
  max-width: 100%;
  max-height: 400px;
  border-radius: 8px;
  box-shadow: 0 4px 6px rgba(0,0,0,0.1);
`;
```

### 5.6 Clear Selection

```javascript
const clearSelection = useCallback(() => {
  setSelectedFile(null);
  if (previewUrl) {
    URL.revokeObjectURL(previewUrl);
    setPreviewUrl('');
  }
  resetState();
}, [previewUrl]);

const resetState = useCallback(() => {
  setProcessing(false);
  setProcessingPhase('idle');
  setUploadProgress(null);
  setProcessingProgress(0);
  setStatus('');
  setError('');
  setResult(null);
  setVideoDuration(null);
  clearPhaseTimers();
  clearUploadFallbackTimer();
}, [clearPhaseTimers, clearUploadFallbackTimer]);
```

### 5.7 Preview Cleanup (useEffect)

```javascript
useEffect(() => {
  // Cleanup preview URL on unmount or file change
  return () => {
    if (previewUrl) {
      URL.revokeObjectURL(previewUrl);
    }
  };
}, [previewUrl]);
```

---

## 6. API Integration

### 6.1 API Base URL Resolution

```javascript
const SCENE_API_BASE = process.env.REACT_APP_SCENE_API_BASE || resolveSceneApiBase();

function resolveSceneApiBase() {
  const hostname = window.location.hostname;
  
  // Localhost development
  if (hostname === 'localhost' || hostname === '127.0.0.1') {
    return 'http://localhost:5005';
  }
  
  // LAN or production deployment
  return `http://${hostname}:5005`;
}
```

**Examples:**
- Local dev: `http://localhost:5005`
- LAN: `http://192.168.1.100:5005`
- Production: `http://myserver.com:5005`

### 6.2 Main API Call (analyseScene)

```javascript
const analyseScene = async () => {
  if (!selectedFile) {
    setError('Select a video or image to begin.');
    return;
  }

  // Reset state
  clearPhaseTimers();
  clearUploadFallbackTimer();
  updateProcessingPhase('uploading');
  timelineScheduledRef.current = false;
  setProcessingProgress(0);
  setProcessing(true);
  setStatus(PHASE_LABEL_MAP.uploading);
  setError('');
  setResult(null);
  setUploadProgress(0);
  startUploadFallbackTimer();

  // Build form data
  const formData = new FormData();
  formData.append('media', selectedFile);
  formData.append('voice_id', voiceId);

  try {
    const endpoint = SCENE_API_BASE ? `${SCENE_API_BASE}/summarize` : '/summarize';
    const computedTimeout = derivedTimeoutMs || DEFAULT_TIMEOUT_MS;

    const { data } = await axios.post(endpoint, formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
      timeout: computedTimeout,
      maxBodyLength: Infinity,
      maxContentLength: Infinity,
      onUploadProgress: (progressEvent) => {
        if (!progressEvent.total) {
          setUploadProgress(null);
          return;
        }
        
        const percent = Math.min(100, Math.round((progressEvent.loaded / progressEvent.total) * 100));
        setUploadProgress(percent);
        
        // Update overall progress (upload = 40% of total)
        setProcessingProgress((prev) => {
          const uploadContribution = Math.round(percent * 0.4);
          return uploadContribution > prev ? uploadContribution : prev;
        });
        
        // Transition to analysing when upload complete
        if (percent >= 100) {
          clearUploadFallbackTimer();
          updateProcessingPhase('analysing');
          setProcessingProgress((prev) => (prev < 55 ? 55 : prev));
          setStatus(PHASE_LABEL_MAP.analysing);
          scheduleProcessingPhases();
        }
      },
    });
    
    // Success
    clearPhaseTimers();
    clearUploadFallbackTimer();
    updateProcessingPhase('complete');
    setProcessingProgress(100);
    setResult(data);
    setStatus('Scene summary generated successfully.');
    
  } catch (requestError) {
    // Error handling
    clearPhaseTimers();
    clearUploadFallbackTimer();
    updateProcessingPhase('error');
    setProcessingProgress((prev) => (prev > 0 ? prev : 0));
    
    const backendMessage = requestError.response?.data?.error || requestError.message;
    setError(`Failed to summarise scene: ${backendMessage}`);
    setStatus(PHASE_LABEL_MAP.error);
    
  } finally {
    setProcessing(false);
    setUploadProgress(null);
  }
};
```

### 6.3 URL Resolution Helper

```javascript
function resolveUrl(relativePath) {
  if (!relativePath) return '';
  
  // Already absolute URL
  if (relativePath.startsWith('http://') || relativePath.startsWith('https://')) {
    return relativePath;
  }
  
  // Relative path - prepend API base
  return `${SCENE_API_BASE}${relativePath}`;
}
```

**Usage:**
```javascript
<AudioPlayer controls src={resolveUrl(result.audio_url)} />
// Resolves "/audio/uuid.mp3" → "http://localhost:5005/audio/uuid.mp3"
```

---

## 7. Result Display Components

### 7.1 Result Structure

```javascript
result = {
  file_id: "a1b2c3d4-...",
  summary: "Natural language summary...",
  highlights: ["Highlight 1", "Highlight 2", "Highlight 3"],
  ssml: "<speak>...</speak>",
  audio_url: "/audio/uuid.mp3",
  voice_id: "Joanna",
  metadata: {
    mediaType: "video",
    framesAnalysed: 36,
    objects: [{label: "Person", confidence: 99.8, frameOccurrences: 36}],
    activities: [...],
    scenes: [...],
    people: [...],
    dominantEmotions: [...],
    celebrities: [...],
    textDetections: [...],
    context: {...}
  },
  source_video: {
    bucket: "my-bucket",
    key: "scene-videos/uuid/video.mp4",
    uri: "s3://..."
  }
}
```

### 7.2 Card 1: Story Beat

```javascript
<Card>
  <CardTitle>Story Beat</CardTitle>
  <SummaryText>{result.summary}</SummaryText>
  
  {Array.isArray(result.highlights) && result.highlights.length > 0 && (
    <>
      <SectionSubhead>Highlights</SectionSubhead>
      <HighlightList>
        {result.highlights.map((item, index) => (
          <HighlightItem key={index}>{item}</HighlightItem>
        ))}
      </HighlightList>
    </>
  )}
  
  {result.audio_url && (
    <>
      <SectionSubhead>Voiceover Preview</SectionSubhead>
      <AudioPlayer controls src={resolveUrl(result.audio_url)} />
      <AudioNote>
        Narrated with neural voice {result.voice_id}. 
        Use the download option in the player to save locally.
      </AudioNote>
    </>
  )}
</Card>
```

### 7.3 Card 2: Scene Intelligence

```javascript
<Card>
  <CardTitle>Scene Intelligence</CardTitle>
  
  <SectionSubhead>Environment</SectionSubhead>
  <MetadataList>
    <MetadataItem><strong>Setting:</strong> {context.environment || 'Unknown'}</MetadataItem>
    <MetadataItem><strong>Activity focus:</strong> {context.activityFocus || 'Unclear'}</MetadataItem>
    <MetadataItem><strong>Lighting hint:</strong> {context.lighting || 'Not detected'}</MetadataItem>
    <MetadataItem><strong>Crowd indicator:</strong> {context.crowdIndicator || 'Not detected'}</MetadataItem>
    <MetadataItem><strong>Frames analysed:</strong> {metadata.framesAnalysed || 1}</MetadataItem>
  </MetadataList>
  
  {result.source_video && (
    <>
      <SectionSubhead>Source Video</SectionSubhead>
      <MetadataList>
        <MetadataItem><strong>Bucket:</strong> {result.source_video.bucket || '—'}</MetadataItem>
        <MetadataItem><strong>Key:</strong> {result.source_video.key || '—'}</MetadataItem>
        {result.source_video.uri && (
          <MetadataItem><strong>URI:</strong> {result.source_video.uri}</MetadataItem>
        )}
      </MetadataList>
    </>
  )}
  
  {objects.length > 0 && (
    <>
      <SectionSubhead>Key Objects</SectionSubhead>
      <TagList>
        {objects.slice(0, 10).map((entry) => (
          <Tag key={`object-${entry.label}`}>{metadataLabel(entry)}</Tag>
        ))}
      </TagList>
    </>
  )}
  
  {/* Similar sections for activities, scenes, celebrities */}
</Card>
```

**Helper Function:**

```javascript
function metadataLabel(entry) {
  return `${entry.label} (${Math.round(entry.confidence)}%, ${entry.frameOccurrences}×)`;
}
// Output: "Person (100%, 36×)"
```

### 7.4 Card 3: People & Emotion

```javascript
<Card>
  <CardTitle>People & Emotion</CardTitle>
  
  {people.length > 0 ? (
    <MetadataList>
      {people.map((person, index) => (
        <MetadataItem key={`person-${index}`}>
          <strong>Subject {index + 1}:</strong> {person.gender || 'Unknown gender'}; 
          age range {person.ageRange?.Low || '?'}-{person.ageRange?.High || '?'}; 
          emotions {person.dominantEmotions?.length 
            ? person.dominantEmotions.join(', ') 
            : 'not detected'}
        </MetadataItem>
      ))}
    </MetadataList>
  ) : (
    <SummaryText>No faces detected in this scene.</SummaryText>
  )}
  
  {dominantEmotions.length > 0 && (
    <>
      <SectionSubhead>Dominant Emotions</SectionSubhead>
      <TagList>
        {dominantEmotions.map((emotion) => (
          <Tag key={`emotion-${emotion.emotion}`}>
            {emotion.emotion} ({Math.round(emotion.score)})
          </Tag>
        ))}
      </TagList>
    </>
  )}
  
  {textDetections.length > 0 && (
    <>
      <SectionSubhead>Text On Screen</SectionSubhead>
      <MetadataList>
        {textDetections.slice(0, 6).map((textLine, index) => (
          <MetadataItem key={`text-${index}`}>
            "{textLine}"
          </MetadataItem>
        ))}
      </MetadataList>
    </>
  )}
</Card>
```

### 7.5 Card 4: SSML Blueprint

```javascript
<Card>
  <CardTitle>SSML Blueprint</CardTitle>
  <SsmlPre>{result.ssml}</SsmlPre>
</Card>
```

### 7.6 Card 5: Structured Metadata

```javascript
<Card>
  <CardTitle>Structured Metadata</CardTitle>
  <JsonPre>{JSON.stringify(metadata, null, 2)}</JsonPre>
</Card>
```

---

*Continued in Part 4...*

## Document Continuation

**Next Document:** `SCENE_SUMMARIZATION_PART4.md`

**Part 4 Contents:**
- AWS Integration Details
- Complete API Reference
- Configuration Guide
- Deployment Instructions
- Troubleshooting Guide
- Performance Optimization
- Monitoring & Logging
- Security Best Practices

# Scene Summarization Service - Complete Technical Reference
## Part 4 of 4: AWS Integration, API Reference, Deployment & Operations

**MediaGenAI Platform - Service Documentation**  
**Document Version:** 1.0  
**Service Port:** 5005  
**Last Updated:** October 21, 2025

---

## Document Navigation

- **Part 1**: Executive Summary, Architecture Overview, Backend Deep Dive (Media Processing, Vision Analysis)
- **Part 2**: Aggregation Logic, LLM Integration, TTS Synthesis, Result Storage
- **Part 3**: Frontend Architecture, Processing Phases, UI Components
- **Part 4** (this document): AWS Integration, API Reference, Configuration, Deployment, Troubleshooting

---

## Table of Contents - Part 4

1. [AWS Service Integration](#1-aws-service-integration)
2. [Complete API Reference](#2-complete-api-reference)
3. [Configuration Guide](#3-configuration-guide)
4. [Deployment Instructions](#4-deployment-instructions)
5. [Troubleshooting Guide](#5-troubleshooting-guide)
6. [Performance Optimization](#6-performance-optimization)
7. [Monitoring & Logging](#7-monitoring--logging)
8. [Security Best Practices](#8-security-best-practices)

---

## 1. AWS Service Integration

### 1.1 AWS Rekognition

**Service Details:**
- **Purpose**: Computer vision analysis (labels, faces, celebrities, text)
- **Region**: us-east-1 (configurable via `REKOGNITION_REGION`)
- **Pricing**: Per-image API call
  - detect_labels: $0.001 per image
  - detect_faces: $0.001 per image
  - recognize_celebrities: $0.006 per image
  - detect_text: $0.001 per image
  - **Total per frame**: ~$0.009 (all 4 APIs)

**API Call Pattern:**
```python
# 1. Label Detection
rekognition.detect_labels(
    Image={"Bytes": image_bytes},
    MaxLabels=25,
    MinConfidence=55.0,
)

# 2. Face Detection
rekognition.detect_faces(
    Image={"Bytes": image_bytes},
    Attributes=["ALL"]
)

# 3. Celebrity Recognition
rekognition.recognize_celebrities(
    Image={"Bytes": image_bytes}
)

# 4. Text Detection
rekognition.detect_text(
    Image={"Bytes": image_bytes}
)
```

**Rate Limits:**
- **Transactions per second**: 50 (can request increase)
- **Concurrent requests**: 5 (default)
- **Image size**: Max 15 MB
- **Image dimensions**: Min 80×80 pixels, max 15000×15000 pixels

**Cost Example:**
- 60-second video at 1.7s stride = 36 frames
- 36 frames × 4 APIs × $0.001 = $0.144 per video
- 100 videos/day = $14.40/day = $432/month

**Optimization Tips:**
1. Increase stride for longer videos (e.g., 2.5s for 10-min videos)
2. Cap max frames at 120 (current default)
3. Skip celebrity recognition if not needed (saves 67% of Rekognition cost)
4. Cache results for repeated analysis

### 1.2 AWS Bedrock

**Service Details:**
- **Purpose**: LLM-powered summarization
- **Region**: us-east-1 (configurable via `BEDROCK_REGION`)
- **Model**: meta.llama3-70b-instruct-v1:0
- **Pricing**: 
  - Input tokens: $0.00265 per 1K tokens
  - Output tokens: $0.0035 per 1K tokens

**Invocation Pattern:**
```python
bedrock_runtime.invoke_model(
    modelId="meta.llama3-70b-instruct-v1:0",
    contentType="application/json",
    accept="application/json",
    body=json.dumps({
        "prompt": structured_prompt,
        "temperature": 0.4,
        "top_p": 0.9,
        "max_gen_len": 600,
    })
)
```

**Token Estimation:**
- **Input tokens**: 500-1500 tokens (depends on metadata complexity)
  - Small scene (10 objects, 2 people): ~500 tokens
  - Complex scene (25 objects, 10 people, celebrities, text): ~1500 tokens
- **Output tokens**: 200-400 tokens (summary + highlights + SSML)
- **Average cost per request**: $0.002-$0.006

**Rate Limits:**
- **Requests per minute**: 200 (can request increase)
- **Tokens per minute**: 100,000 input + 100,000 output

**Alternative Models:**
```python
# Cheaper, faster (but lower quality)
SCENE_BEDROCK_MODEL_ID = "anthropic.claude-3-haiku-20240307-v1:0"

# Higher quality (but more expensive)
SCENE_BEDROCK_MODEL_ID = "anthropic.claude-3-opus-20240229-v1:0"
```

### 1.3 AWS Polly

**Service Details:**
- **Purpose**: Neural text-to-speech synthesis
- **Region**: us-west-2 (configurable via `POLLY_REGION`)
- **Engine**: Neural
- **Pricing**: $16.00 per 1 million characters

**Synthesis Pattern:**
```python
polly.synthesize_speech(
    Text=ssml_text,
    TextType="ssml",
    VoiceId="Joanna",
    Engine="neural",
    OutputFormat="mp3",
    SampleRate="24000",
)
```

**Cost Estimation:**
- Average summary SSML: 300-600 characters
- Average cost per synthesis: $0.005-$0.010
- 100 requests/day = $0.50-$1.00/day = $15-$30/month

**Available Neural Voices:**

| Language | Voice ID | Gender | Description |
|----------|----------|--------|-------------|
| US English | Joanna | Female | Warm, professional (default) |
| US English | Matthew | Male | Clear, authoritative |
| US English | Ivy | Female | Young adult, friendly |
| US English | Joey | Male | Young adult, casual |
| British English | Amy | Female | Refined, clear |
| British English | Brian | Male | Professional, trustworthy |
| British English | Emma | Female | Warm, conversational |
| Australian English | Olivia | Female | Friendly, clear |
| Indian English | Kajal | Female | Clear, professional |

**Rate Limits:**
- **Requests per second**: 100
- **Character limit per request**: 3,000 for SSML

### 1.4 AWS S3 (Optional)

**Service Details:**
- **Purpose**: Video file storage
- **Region**: us-east-1 (configurable via `S3_REGION`)
- **Pricing**: 
  - Storage: $0.023 per GB/month (Standard)
  - PUT requests: $0.005 per 1,000 requests
  - GET requests: $0.0004 per 1,000 requests

**Upload Pattern:**
```python
s3.upload_fileobj(
    video_file,
    SCENE_S3_BUCKET,
    f"{SCENE_S3_PREFIX}{file_id}/{filename}",
    ExtraArgs={"ContentType": "video/mp4"}
)
```

**Cost Estimation:**
- Average video: 50 MB
- Storage: $0.0012 per video per month
- 100 videos/month = $0.12/month storage + $0.0005 upload = $0.12/month

**Bucket Policy Example:**
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {"AWS": "arn:aws:iam::ACCOUNT_ID:role/scene-service-role"},
      "Action": [
        "s3:PutObject",
        "s3:GetObject"
      ],
      "Resource": "arn:aws:s3:::my-video-bucket/scene-videos/*"
    }
  ]
}
```

### 1.5 Total Cost Breakdown

**Per-Request Costs:**
| Component | Cost |
|-----------|------|
| Rekognition (36 frames) | $0.144 |
| Bedrock (Llama3-70B) | $0.004 |
| Polly (400 chars) | $0.006 |
| S3 Upload (50 MB) | $0.000 |
| **Total** | **$0.154** |

**Monthly Cost (100 videos/day):**
- 3,000 videos/month × $0.154 = $462/month
- S3 storage (150 GB): $3.45/month
- **Total**: ~$465/month

**Cost Optimization Strategies:**
1. Increase frame stride to 2.5s (reduce Rekognition cost by 32%)
2. Use Claude Haiku instead of Llama3-70B (reduce Bedrock cost by 90%)
3. Skip celebrity recognition (reduce Rekognition cost by 67%)
4. Use S3 Intelligent-Tiering (reduce storage cost by 30-70%)

---

## 2. Complete API Reference

### 2.1 POST /summarize

**Description**: Upload media file and generate scene summary.

**Endpoint**: `POST http://localhost:5005/summarize`

**Request:**
```http
POST /summarize HTTP/1.1
Host: localhost:5005
Content-Type: multipart/form-data; boundary=----WebKitFormBoundary

------WebKitFormBoundary
Content-Disposition: form-data; name="media"; filename="video.mp4"
Content-Type: video/mp4

<binary file data>
------WebKitFormBoundary
Content-Disposition: form-data; name="voice_id"

Joanna
------WebKitFormBoundary--
```

**Request Fields:**
- `media` (File, required): Image or video file
  - Allowed formats: JPG, PNG, GIF, BMP, TIFF, WEBP, MP4, MOV, AVI, MKV, WEBM, FLV, WMV, MPEG
  - Max size: 2 GB
- `voice_id` (String, optional): Polly voice ID (default: "Joanna")
  - Options: "Joanna", "Matthew", "Amy", "Brian", "Olivia"

**Response (200 OK):**
```json
{
  "file_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "summary": "This video shows an exciting outdoor race. A male runner, age 25 to 35, sprints toward the finish line with determination. The scene captures intense athletic action in broad daylight.",
  "highlights": [
    "Male athlete engaged in high-intensity running",
    "Outdoor setting with clear daytime lighting",
    "FINISH LINE text visible on screen"
  ],
  "ssml": "<speak><p>This video shows an exciting outdoor race.</p><break time=\"500ms\"/><p>A male runner, <emphasis level=\"strong\">age 25 to 35</emphasis>, sprints toward the finish line.</p></speak>",
  "audio_url": "/audio/a1b2c3d4-e5f6-7890-abcd-ef1234567890.mp3",
  "voice_id": "Joanna",
  "metadata": {
    "mediaType": "video",
    "framesAnalysed": 36,
    "objects": [
      {"label": "Person", "confidence": 99.8, "frameOccurrences": 36},
      {"label": "Clothing", "confidence": 98.5, "frameOccurrences": 36},
      {"label": "Athletic Shoe", "confidence": 95.2, "frameOccurrences": 32}
    ],
    "activities": [
      {"label": "Running", "confidence": 95.2, "frameOccurrences": 24},
      {"label": "Sport", "confidence": 88.7, "frameOccurrences": 20}
    ],
    "scenes": [
      {"label": "Outdoor", "confidence": 98.5, "frameOccurrences": 36},
      {"label": "Day", "confidence": 96.3, "frameOccurrences": 36}
    ],
    "context": {
      "environment": "outdoor",
      "activityFocus": "action",
      "lighting": "day",
      "crowdIndicator": null
    },
    "people": [
      {
        "gender": "Male",
        "ageRange": {"Low": 25, "High": 35},
        "dominantEmotions": ["HAPPY", "CALM"]
      }
    ],
    "dominantEmotions": [
      {"emotion": "HAPPY", "score": 85.0},
      {"emotion": "CALM", "score": 15.0}
    ],
    "celebrities": [],
    "textDetections": ["FINISH LINE"]
  },
  "source_video": {
    "bucket": "my-video-bucket",
    "key": "scene-videos/a1b2c3d4-e5f6-7890-abcd-ef1234567890/video.mp4",
    "uri": "s3://my-video-bucket/scene-videos/a1b2c3d4-e5f6-7890-abcd-ef1234567890/video.mp4"
  }
}
```

**Error Responses:**

```json
// 400 Bad Request - Missing file
{
  "error": "No media file provided"
}

// 400 Bad Request - Invalid file type
{
  "error": "Invalid file type: .txt",
  "allowed": ["jpg", "jpeg", "png", "mp4", "mov", ...]
}

// 400 Bad Request - File too large
{
  "error": "File too large: 2.5 GB",
  "max_size_gb": 2.0
}

// 500 Internal Server Error - Processing failure
{
  "error": "FFmpeg extraction failed: [error details]"
}

// 503 Service Unavailable - AWS clients unavailable
{
  "error": "Rekognition client unavailable"
}
```

**cURL Example:**
```bash
curl -X POST http://localhost:5005/summarize \
  -F "media=@/path/to/video.mp4" \
  -F "voice_id=Matthew" \
  --max-time 3600
```

**Python Example:**
```python
import requests

files = {'media': open('video.mp4', 'rb')}
data = {'voice_id': 'Joanna'}

response = requests.post(
    'http://localhost:5005/summarize',
    files=files,
    data=data,
    timeout=3600
)

result = response.json()
print(f"Summary: {result['summary']}")
print(f"Audio URL: {result['audio_url']}")
```

### 2.2 GET /result/:file_id

**Description**: Retrieve stored result metadata by file ID.

**Endpoint**: `GET http://localhost:5005/result/{file_id}`

**Request:**
```http
GET /result/a1b2c3d4-e5f6-7890-abcd-ef1234567890 HTTP/1.1
Host: localhost:5005
```

**Response (200 OK):**
```json
{
  "file_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "timestamp": "2025-10-21T14:30:45.123Z",
  "mediaType": "video",
  "framesAnalysed": 36,
  "objects": [...],
  "activities": [...],
  "scenes": [...],
  "people": [...],
  "dominantEmotions": [...],
  "celebrities": [],
  "textDetections": ["FINISH LINE"],
  "context": {
    "environment": "outdoor",
    "activityFocus": "action",
    "lighting": "day",
    "crowdIndicator": null
  }
}
```

**Error Response (404):**
```json
{
  "error": "Result not found: a1b2c3d4-e5f6-7890-abcd-ef1234567890"
}
```

**cURL Example:**
```bash
curl http://localhost:5005/result/a1b2c3d4-e5f6-7890-abcd-ef1234567890
```

### 2.3 GET /audio/:file_id

**Description**: Stream audio file by file ID.

**Endpoint**: `GET http://localhost:5005/audio/{file_id}.mp3`

**Request:**
```http
GET /audio/a1b2c3d4-e5f6-7890-abcd-ef1234567890.mp3 HTTP/1.1
Host: localhost:5005
```

**Response (200 OK):**
```http
HTTP/1.1 200 OK
Content-Type: audio/mpeg
Content-Disposition: inline; filename="a1b2c3d4-e5f6-7890-abcd-ef1234567890.mp3"
Content-Length: 48576

<binary MP3 data>
```

**Error Response (404):**
```json
{
  "error": "Audio not found: a1b2c3d4-e5f6-7890-abcd-ef1234567890"
}
```

**Browser Usage:**
```html
<audio controls src="http://localhost:5005/audio/a1b2c3d4-e5f6-7890-abcd-ef1234567890.mp3"></audio>
```

**Download with cURL:**
```bash
curl -O http://localhost:5005/audio/a1b2c3d4-e5f6-7890-abcd-ef1234567890.mp3
```

### 2.4 GET /health

**Description**: Service health check.

**Endpoint**: `GET http://localhost:5005/health`

**Response (200 OK):**
```json
{
  "status": "healthy",
  "service": "Scene Summarization Service",
  "version": "1.0",
  "aws_clients": {
    "rekognition": true,
    "bedrock": true,
    "polly": true,
    "s3": true
  },
  "ffmpeg_available": true,
  "ffprobe_available": true
}
```

**cURL Example:**
```bash
curl http://localhost:5005/health
```

---

## 3. Configuration Guide

### 3.1 Environment Variables

**Create `.env` file:**

```bash
# AWS Configuration
AWS_REGION=us-east-1
REKOGNITION_REGION=us-east-1
BEDROCK_REGION=us-east-1
POLLY_REGION=us-west-2
S3_REGION=us-east-1

# Bedrock Configuration
SCENE_BEDROCK_MODEL_ID=meta.llama3-70b-instruct-v1:0

# Polly Configuration
SCENE_POLLY_VOICE_ID=Joanna

# S3 Configuration (Optional)
SCENE_S3_BUCKET=my-video-bucket
SCENE_S3_PREFIX=scene-videos/

# Frame Extraction Configuration
FRAME_STRIDE_SECONDS=1.7
MAX_SCENE_FRAMES=120

# FFmpeg Paths (Optional, auto-detected if in PATH)
FFMPEG_BINARY=/usr/local/bin/ffmpeg
FFPROBE_BINARY=/usr/local/bin/ffprobe

# CORS Configuration (Optional)
CORS_ORIGIN=http://192.168.1.100:3000
```

### 3.2 AWS Credentials Configuration

**Method 1: AWS CLI Configuration**
```bash
aws configure
# AWS Access Key ID: YOUR_ACCESS_KEY
# AWS Secret Access Key: YOUR_SECRET_KEY
# Default region name: us-east-1
# Default output format: json
```

**Method 2: Environment Variables**
```bash
export AWS_ACCESS_KEY_ID=YOUR_ACCESS_KEY
export AWS_SECRET_ACCESS_KEY=YOUR_SECRET_KEY
export AWS_DEFAULT_REGION=us-east-1
```

**Method 3: IAM Role (EC2/ECS)**
- Attach IAM role to EC2 instance or ECS task
- boto3 automatically uses instance credentials
- Most secure for production

### 3.3 IAM Policy

**Required Permissions:**

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "RekognitionAccess",
      "Effect": "Allow",
      "Action": [
        "rekognition:DetectLabels",
        "rekognition:DetectFaces",
        "rekognition:RecognizeCelebrities",
        "rekognition:DetectText"
      ],
      "Resource": "*"
    },
    {
      "Sid": "BedrockAccess",
      "Effect": "Allow",
      "Action": [
        "bedrock:InvokeModel"
      ],
      "Resource": [
        "arn:aws:bedrock:*::foundation-model/meta.llama3-70b-instruct-v1:0",
        "arn:aws:bedrock:*::foundation-model/anthropic.claude-*"
      ]
    },
    {
      "Sid": "PollyAccess",
      "Effect": "Allow",
      "Action": [
        "polly:SynthesizeSpeech"
      ],
      "Resource": "*"
    },
    {
      "Sid": "S3Access",
      "Effect": "Allow",
      "Action": [
        "s3:PutObject",
        "s3:GetObject"
      ],
      "Resource": [
        "arn:aws:s3:::my-video-bucket/scene-videos/*"
      ]
    }
  ]
}
```

### 3.4 FFmpeg Installation

**macOS (Homebrew):**
```bash
brew install ffmpeg
```

**Ubuntu/Debian:**
```bash
sudo apt update
sudo apt install ffmpeg
```

**CentOS/RHEL:**
```bash
sudo yum install epel-release
sudo yum install ffmpeg
```

**Windows:**
1. Download from https://ffmpeg.org/download.html
2. Extract to `C:\ffmpeg`
3. Add `C:\ffmpeg\bin` to PATH
4. Or set `FFMPEG_BINARY=C:\ffmpeg\bin\ffmpeg.exe` in `.env`

**Verify Installation:**
```bash
ffmpeg -version
ffprobe -version
```

### 3.5 Frontend Configuration

**Environment Variables (.env.local):**

```bash
# API Base URL (optional, auto-detected if not set)
REACT_APP_SCENE_API_BASE=http://localhost:5005

# Or for production
REACT_APP_SCENE_API_BASE=http://myserver.com:5005
```

**Build-Time Configuration:**
```bash
# Development
npm start

# Production build
npm run build
# Output: build/ directory with static files
```

---

## 4. Deployment Instructions

### 4.1 Local Development Setup

**Backend:**

```bash
# Navigate to service directory
cd sceneSummarization

# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Create .env file
cp .env.example .env
# Edit .env with your AWS credentials and configuration

# Install FFmpeg (if not already installed)
brew install ffmpeg  # macOS
# sudo apt install ffmpeg  # Ubuntu

# Run service
python app.py
# Service starts on http://localhost:5005
```

**Frontend:**

```bash
# Navigate to frontend directory
cd frontend

# Install dependencies
npm install

# Start development server
npm start
# Frontend starts on http://localhost:3000
```

**Access Application:**
- Open browser: http://localhost:3000
- Frontend automatically connects to backend at http://localhost:5005

### 4.2 Production Deployment (EC2)

**1. Provision EC2 Instance:**
```bash
# Launch EC2 instance
# - AMI: Ubuntu 22.04 LTS
# - Instance type: t3.large (2 vCPU, 8 GB RAM)
# - Storage: 50 GB GP3
# - Security group: Allow 22 (SSH), 5005 (Backend), 3000 (Frontend), 80 (HTTP)
# - IAM role: Attach role with Scene Summarization policy
```

**2. Install Dependencies:**
```bash
# Connect to instance
ssh -i keypair.pem ubuntu@ec2-public-ip

# Update system
sudo apt update && sudo apt upgrade -y

# Install Python 3.11
sudo apt install python3.11 python3.11-venv python3-pip -y

# Install FFmpeg
sudo apt install ffmpeg -y

# Install Node.js 18
curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash -
sudo apt install -y nodejs

# Install Nginx (for frontend)
sudo apt install nginx -y
```

**3. Deploy Backend:**
```bash
# Clone repository
git clone https://github.com/your-org/mediaGenAI.git
cd mediaGenAI/sceneSummarization

# Create virtual environment
python3.11 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Create .env file
nano .env
# Add AWS region configuration (credentials via IAM role)

# Create systemd service
sudo nano /etc/systemd/system/scene-summarization.service
```

**systemd Service File:**
```ini
[Unit]
Description=Scene Summarization Service
After=network.target

[Service]
Type=simple
User=ubuntu
WorkingDirectory=/home/ubuntu/mediaGenAI/sceneSummarization
Environment="PATH=/home/ubuntu/mediaGenAI/sceneSummarization/venv/bin"
ExecStart=/home/ubuntu/mediaGenAI/sceneSummarization/venv/bin/python app.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

**Start Service:**
```bash
sudo systemctl daemon-reload
sudo systemctl enable scene-summarization
sudo systemctl start scene-summarization
sudo systemctl status scene-summarization
```

**4. Deploy Frontend:**
```bash
cd /home/ubuntu/mediaGenAI/frontend

# Set production API URL
echo "REACT_APP_SCENE_API_BASE=http://$(curl -s http://169.254.169.254/latest/meta-data/public-ipv4):5005" > .env.production

# Install dependencies
npm install

# Build production bundle
npm run build

# Copy to Nginx
sudo rm -rf /var/www/html/*
sudo cp -r build/* /var/www/html/

# Configure Nginx
sudo nano /etc/nginx/sites-available/default
```

**Nginx Configuration:**
```nginx
server {
    listen 80;
    server_name _;
    root /var/www/html;
    index index.html;

    location / {
        try_files $uri $uri/ /index.html;
    }

    # Backend proxy (optional, if same domain)
    location /api/ {
        proxy_pass http://localhost:5005/;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_cache_bypass $http_upgrade;
        proxy_read_timeout 3600s;
    }
}
```

**Restart Nginx:**
```bash
sudo nginx -t
sudo systemctl restart nginx
```

**5. Access Application:**
- Frontend: http://ec2-public-ip
- Backend: http://ec2-public-ip:5005
- Health check: http://ec2-public-ip:5005/health

### 4.3 Docker Deployment

**Backend Dockerfile:**

```dockerfile
FROM python:3.11-slim

# Install FFmpeg
RUN apt-get update && \
    apt-get install -y ffmpeg && \
    rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY . .

# Create directories
RUN mkdir -p uploads outputs/metadata outputs/audio frames

# Expose port
EXPOSE 5005

# Run application
CMD ["python", "app.py"]
```

**docker-compose.yml:**

```yaml
version: '3.8'

services:
  backend:
    build: ./sceneSummarization
    ports:
      - "5005:5005"
    environment:
      - AWS_REGION=us-east-1
      - REKOGNITION_REGION=us-east-1
      - BEDROCK_REGION=us-east-1
      - POLLY_REGION=us-west-2
      - SCENE_BEDROCK_MODEL_ID=meta.llama3-70b-instruct-v1:0
      - SCENE_POLLY_VOICE_ID=Joanna
      - FRAME_STRIDE_SECONDS=1.7
      - MAX_SCENE_FRAMES=120
    volumes:
      - ./sceneSummarization/uploads:/app/uploads
      - ./sceneSummarization/outputs:/app/outputs
      - ./sceneSummarization/frames:/app/frames
    restart: always

  frontend:
    build: ./frontend
    ports:
      - "3000:80"
    environment:
      - REACT_APP_SCENE_API_BASE=http://localhost:5005
    depends_on:
      - backend
    restart: always
```

**Build and Run:**
```bash
docker-compose up -d
docker-compose logs -f  # View logs
docker-compose ps       # Check status
```

---

## 5. Troubleshooting Guide

### 5.1 Common Backend Issues

**Issue: "FFmpeg binary not found"**

**Symptoms:**
```
WARNING: FFmpeg not found. Video processing will fail.
ERROR: FFmpeg extraction failed: FileNotFoundError
```

**Solutions:**
```bash
# Verify FFmpeg installation
which ffmpeg
ffmpeg -version

# Install FFmpeg
brew install ffmpeg  # macOS
sudo apt install ffmpeg  # Ubuntu

# Set explicit path in .env
FFMPEG_BINARY=/usr/local/bin/ffmpeg
FFPROBE_BINARY=/usr/local/bin/ffprobe
```

---

**Issue: "Rekognition client unavailable"**

**Symptoms:**
```
ERROR: Failed to create rekognition client: NoCredentialsError
503 Service Unavailable: {"error": "Rekognition client unavailable"}
```

**Solutions:**
```bash
# Check AWS credentials
aws sts get-caller-identity

# Configure credentials
aws configure

# Or set environment variables
export AWS_ACCESS_KEY_ID=your_key
export AWS_SECRET_ACCESS_KEY=your_secret

# Verify region configuration
export AWS_REGION=us-east-1
```

---

**Issue: "Bedrock invocation failed: AccessDeniedException"**

**Symptoms:**
```
ERROR: Bedrock invocation failed: An error occurred (AccessDeniedException) when calling the InvokeModel operation
```

**Solutions:**
```bash
# Request Bedrock model access
# 1. Go to AWS Console → Bedrock → Model access
# 2. Request access to Llama 3 70B Instruct
# 3. Wait for approval (usually instant)

# Verify IAM permissions
aws iam get-user-policy --user-name your-user --policy-name BedrockAccess

# Or use alternative model
export SCENE_BEDROCK_MODEL_ID=anthropic.claude-3-haiku-20240307-v1:0
```

---

**Issue: "File too large: 2.5 GB"**

**Symptoms:**
```
400 Bad Request: {"error": "File too large: 2.5 GB", "max_size_gb": 2.0}
```

**Solutions:**
```bash
# Compress video before upload
ffmpeg -i input.mp4 -vcodec libx264 -crf 28 output.mp4

# Or increase MAX_FILE_SIZE in app.py (not recommended)
MAX_FILE_SIZE = 5 * 1024 * 1024 * 1024  # 5 GB
```

---

**Issue: "No frames extracted from video"**

**Symptoms:**
```
ERROR: ValueError: No frames extracted from video
```

**Solutions:**
```bash
# Test FFmpeg manually
ffmpeg -i video.mp4 -vf fps=1/1.7 -q:v 2 frame_%04d.jpg

# Check video codec
ffprobe video.mp4

# Re-encode video to compatible format
ffmpeg -i video.mp4 -vcodec libx264 -acodec aac video_reencoded.mp4

# Reduce FRAME_STRIDE_SECONDS
export FRAME_STRIDE_SECONDS=1.0
```

---

**Issue: "LLM response parsing failed"**

**Symptoms:**
```
ERROR: Could not extract valid JSON from response: ```json...
INFO: Falling back to template summary
```

**Solutions:**
```python
# This is expected behavior - fallback template is generated
# To reduce fallback frequency:

# 1. Check Bedrock model availability
aws bedrock list-foundation-models --region us-east-1

# 2. Increase temperature for more structured responses
BEDROCK_TEMPERATURE = 0.3  # Lower = more deterministic

# 3. Use Claude models (better JSON adherence)
SCENE_BEDROCK_MODEL_ID = "anthropic.claude-3-sonnet-20240229-v1:0"
```

### 5.2 Common Frontend Issues

**Issue: "Failed to summarise scene: Network Error"**

**Symptoms:**
```
Frontend error: "Failed to summarise scene: Network Error"
Backend not responding
```

**Solutions:**
```bash
# Check backend is running
curl http://localhost:5005/health

# Check CORS configuration
# In app.py, verify CORS origins include frontend URL

# Check firewall rules
sudo ufw status
sudo ufw allow 5005/tcp

# Restart backend
sudo systemctl restart scene-summarization
```

---

**Issue: "Request timeout after 3 hours"**

**Symptoms:**
```
axios.post timeout error after 10800000ms
```

**Solutions:**
```javascript
# Video too long - reduce frame count
export MAX_SCENE_FRAMES=60
export FRAME_STRIDE_SECONDS=3.0

# Or increase frontend timeout
const DEFAULT_TIMEOUT_MS = 6 * 60 * 60 * 1000;  // 6 hours
```

---

**Issue: "Audio player shows 404 error"**

**Symptoms:**
```
GET http://localhost:5005/audio/uuid.mp3 → 404 Not Found
```

**Solutions:**
```bash
# Check audio file exists
ls -lh sceneSummarization/outputs/audio/

# Check Polly synthesis logs
tail -f sceneSummarization/app.log

# Verify Polly permissions
aws polly synthesize-speech \
  --text "Test" \
  --output-format mp3 \
  --voice-id Joanna \
  test.mp3
```

### 5.3 Performance Issues

**Issue: "Processing takes too long (>10 minutes)"**

**Diagnosis:**
```bash
# Check which stage is slow
tail -f sceneSummarization/app.log

# Typical timings:
# - Frame extraction: 1-3 seconds per 60 seconds of video
# - Rekognition: 2-4 seconds per frame
# - Bedrock: 3-8 seconds
# - Polly: 1-2 seconds
```

**Solutions:**
```bash
# 1. Reduce frame count
export FRAME_STRIDE_SECONDS=2.5
export MAX_SCENE_FRAMES=80

# 2. Use faster Bedrock model
export SCENE_BEDROCK_MODEL_ID=anthropic.claude-3-haiku-20240307-v1:0

# 3. Skip celebrity recognition (modify app.py)
# Comment out: rekognition.recognize_celebrities()

# 4. Upgrade EC2 instance
# From t3.medium (2 vCPU) to c5.xlarge (4 vCPU)
```

---

## 6. Performance Optimization

### 6.1 Frame Extraction Optimization

**Current Implementation:**
- Sequential frame extraction with FFmpeg
- Each frame extracted with separate FFmpeg call

**Optimization 1: Batch Extraction**

```python
def _extract_frames_batch(video_path: str, frame_count: int) -> List[str]:
    """
    Extract all frames in single FFmpeg call.
    ~3x faster than sequential extraction.
    """
    tmp_dir = tempfile.mkdtemp(prefix="frames_", dir=str(FRAME_CACHE))
    output_pattern = os.path.join(tmp_dir, "frame_%04d.jpg")
    
    command = [
        FFMPEG_BINARY,
        "-i", video_path,
        "-vf", f"fps=1/{FRAME_STRIDE_SECONDS}",
        "-frames:v", str(frame_count),
        "-q:v", "2",
        output_pattern
    ]
    
    subprocess.run(command, check=True)
    
    return sorted(glob.glob(os.path.join(tmp_dir, "frame_*.jpg")))
```

**Optimization 2: Lower Quality Frames**

```python
# Current: -q:v 2 (high quality, larger files)
# Optimized: -q:v 5 (medium quality, 50% smaller files)
"-q:v", "5"

# Or use lower resolution
"-vf", "scale=1280:-1,fps=1/1.7"  # Max width 1280px
```

### 6.2 Rekognition Optimization

**Current Implementation:**
- 4 API calls per frame
- Total: 144 API calls for 36-frame video

**Optimization 1: Selective API Usage**

```python
# Skip celebrity recognition for non-entertainment content
ENABLE_CELEBRITY_RECOGNITION = os.getenv("ENABLE_CELEBRITY_RECOGNITION", "false").lower() == "true"

if ENABLE_CELEBRITY_RECOGNITION:
    celeb_response = rekognition.recognize_celebrities(...)
```

**Optimization 2: Parallel API Calls**

```python
import concurrent.futures

def _analyse_image_bytes_parallel(image_bytes: bytes) -> Dict[str, Any]:
    """
    Execute 4 Rekognition APIs in parallel.
    ~4x faster than sequential calls.
    """
    frame_result = {"labels": [], "faces": [], "celebrities": [], "text": []}
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
        futures = {
            executor.submit(rekognition.detect_labels, Image={"Bytes": image_bytes}, MaxLabels=25): "labels",
            executor.submit(rekognition.detect_faces, Image={"Bytes": image_bytes}, Attributes=["ALL"]): "faces",
            executor.submit(rekognition.recognize_celebrities, Image={"Bytes": image_bytes}): "celebrities",
            executor.submit(rekognition.detect_text, Image={"Bytes": image_bytes}): "text",
        }
        
        for future in concurrent.futures.as_completed(futures):
            api_name = futures[future]
            try:
                response = future.result()
                # Parse response based on api_name
                frame_result[api_name] = parse_response(response, api_name)
            except Exception as error:
                print(f"ERROR: {api_name} failed: {error}")
    
    return frame_result
```

### 6.3 Caching Strategy

**Result Caching:**

```python
import hashlib

def _compute_file_hash(file_path: str) -> str:
    """Compute SHA256 hash of file for cache key."""
    sha256 = hashlib.sha256()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            sha256.update(chunk)
    return sha256.hexdigest()

def _process_media_cached(upload_path: str, media_type: str, voice_id: str) -> Dict[str, Any]:
    """Check cache before processing."""
    file_hash = _compute_file_hash(upload_path)
    cache_key = f"{file_hash}_{voice_id}"
    cache_path = METADATA_FOLDER / f"cache_{cache_key}.json"
    
    # Check cache
    if cache_path.exists():
        print(f"Cache hit: {cache_key}")
        with open(cache_path, "r") as f:
            return json.load(f)
    
    # Process media
    result = _process_media(upload_path, media_type, voice_id)
    
    # Save to cache
    with open(cache_path, "w") as f:
        json.dump(result, f)
    
    return result
```

### 6.4 Database Integration (Optional)

**Current**: File-based storage (JSON + MP3)  
**Optimized**: PostgreSQL + S3

**Benefits:**
- Faster result retrieval
- Query capabilities (search by labels, date, etc.)
- Metadata indexing
- User tracking

**Schema Example:**

```sql
CREATE TABLE scene_analysis (
    file_id UUID PRIMARY KEY,
    created_at TIMESTAMP DEFAULT NOW(),
    media_type VARCHAR(10),
    frames_analysed INTEGER,
    summary TEXT,
    highlights JSONB,
    ssml TEXT,
    audio_s3_key VARCHAR(255),
    metadata JSONB,
    source_video_uri VARCHAR(255)
);

CREATE INDEX idx_created_at ON scene_analysis(created_at);
CREATE INDEX idx_media_type ON scene_analysis(media_type);
CREATE INDEX idx_metadata_gin ON scene_analysis USING gin(metadata);
```

---

## 7. Monitoring & Logging

### 7.1 Application Logging

**Enhanced Logging Configuration:**

```python
import logging
from logging.handlers import RotatingFileHandler

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        RotatingFileHandler(
            'scene_summarization.log',
            maxBytes=10*1024*1024,  # 10 MB
            backupCount=5
        ),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

# Usage in code
logger.info(f"Processing video: {filename}")
logger.error(f"Rekognition failed: {error}")
logger.warning(f"Falling back to template summary")
```

### 7.2 Metrics Collection

**Key Metrics to Track:**

```python
import time
from collections import defaultdict

metrics = defaultdict(list)

def track_metric(metric_name: str, value: float):
    metrics[metric_name].append({
        "timestamp": time.time(),
        "value": value
    })

# Usage
start_time = time.time()
_extract_frames_local(video_path)
track_metric("frame_extraction_duration", time.time() - start_time)

# Report metrics
def get_metrics_summary():
    summary = {}
    for metric_name, values in metrics.items():
        summary[metric_name] = {
            "count": len(values),
            "avg": sum(v["value"] for v in values) / len(values),
            "min": min(v["value"] for v in values),
            "max": max(v["value"] for v in values)
        }
    return summary
```

### 7.3 CloudWatch Integration

**Send Metrics to CloudWatch:**

```python
import boto3

cloudwatch = boto3.client('cloudwatch', region_name='us-east-1')

def send_cloudwatch_metric(metric_name: str, value: float, unit: str = 'None'):
    cloudwatch.put_metric_data(
        Namespace='SceneSummarization',
        MetricData=[
            {
                'MetricName': metric_name,
                'Value': value,
                'Unit': unit,
                'Timestamp': datetime.utcnow()
            }
        ]
    )

# Usage
send_cloudwatch_metric('ProcessingDuration', 45.3, 'Seconds')
send_cloudwatch_metric('FrameCount', 36, 'Count')
send_cloudwatch_metric('RekognitionCost', 0.144, 'None')
```

---

## 8. Security Best Practices

### 8.1 Input Validation

**Current Implementation:**
- File extension validation
- File size validation (2 GB limit)

**Enhanced Validation:**

```python
import magic  # python-magic library

def validate_file_content(file_path: str) -> bool:
    """
    Validate file content matches extension (prevent malicious uploads).
    """
    mime = magic.from_file(file_path, mime=True)
    
    valid_mimes = {
        'image/jpeg', 'image/png', 'image/gif', 'image/bmp', 
        'image/tiff', 'image/webp',
        'video/mp4', 'video/quicktime', 'video/x-msvideo', 
        'video/x-matroska', 'video/webm'
    }
    
    return mime in valid_mimes
```

### 8.2 Rate Limiting

**Per-IP Rate Limiting:**

```python
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

limiter = Limiter(
    app=app,
    key_func=get_remote_address,
    default_limits=["100 per hour"]
)

@app.route("/summarize", methods=["POST"])
@limiter.limit("10 per hour")  # Max 10 requests per hour per IP
def summarize_scene():
    # ... existing code
```

### 8.3 Secure File Handling

**Prevent Path Traversal:**

```python
from werkzeug.utils import secure_filename
import os

def save_uploaded_file(uploaded_file, file_id: str) -> str:
    """
    Securely save uploaded file.
    """
    # Sanitize filename
    filename = secure_filename(uploaded_file.filename)
    
    # Ensure filename is not empty after sanitization
    if not filename:
        filename = f"{file_id}.bin"
    
    # Build full path
    file_path = UPLOAD_FOLDER / filename
    
    # Ensure path is within UPLOAD_FOLDER (prevent directory traversal)
    if not file_path.resolve().is_relative_to(UPLOAD_FOLDER.resolve()):
        raise ValueError("Invalid file path")
    
    # Save file
    uploaded_file.save(str(file_path))
    
    return str(file_path)
```

### 8.4 HTTPS Configuration

**Nginx HTTPS Setup:**

```bash
# Install Certbot
sudo apt install certbot python3-certbot-nginx

# Obtain certificate
sudo certbot --nginx -d yourdomain.com

# Certificate auto-renewal
sudo certbot renew --dry-run
```

**Updated Nginx Config:**

```nginx
server {
    listen 80;
    server_name yourdomain.com;
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name yourdomain.com;

    ssl_certificate /etc/letsencrypt/live/yourdomain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/yourdomain.com/privkey.pem;
    
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;

    root /var/www/html;
    index index.html;

    location / {
        try_files $uri $uri/ /index.html;
    }

    location /api/ {
        proxy_pass http://localhost:5005/;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_cache_bypass $http_upgrade;
        proxy_read_timeout 3600s;
    }
}
```

---

## Appendices

### A. Service Startup Scripts

**start-scene-service.sh:**

```bash
#!/bin/bash
set -e

echo "Starting Scene Summarization Service..."

# Activate virtual environment
cd /home/ubuntu/mediaGenAI/sceneSummarization
source venv/bin/activate

# Check FFmpeg
if ! command -v ffmpeg &> /dev/null; then
    echo "ERROR: FFmpeg not found"
    exit 1
fi

# Check AWS credentials
if ! aws sts get-caller-identity &> /dev/null; then
    echo "ERROR: AWS credentials not configured"
    exit 1
fi

# Start service
python app.py > scene-service.log 2>&1 &
echo $! > scene-service.pid

echo "Service started with PID $(cat scene-service.pid)"
echo "Logs: tail -f scene-service.log"
```

**stop-scene-service.sh:**

```bash
#!/bin/bash

if [ -f scene-service.pid ]; then
    PID=$(cat scene-service.pid)
    echo "Stopping Scene Summarization Service (PID: $PID)..."
    kill $PID
    rm scene-service.pid
    echo "Service stopped"
else
    echo "PID file not found. Service may not be running."
fi
```

### B. Useful Commands

**Check Service Status:**
```bash
# Systemd
sudo systemctl status scene-summarization

# Process
ps aux | grep "python app.py"

# Logs
tail -f /var/log/scene-summarization.log
journalctl -u scene-summarization -f
```

**Monitor Resources:**
```bash
# CPU and memory
htop

# Disk usage
df -h
du -sh sceneSummarization/outputs/*

# Network
netstat -tulpn | grep :5005
```

**Test Endpoints:**
```bash
# Health check
curl http://localhost:5005/health | jq

# Upload test
curl -X POST http://localhost:5005/summarize \
  -F "media=@test_video.mp4" \
  -F "voice_id=Joanna" \
  --max-time 600 | jq

# Retrieve result
curl http://localhost:5005/result/UUID | jq

# Download audio
curl -O http://localhost:5005/audio/UUID.mp3
```

---

## Document Complete

This completes the Scene Summarization Service technical reference documentation.

**Total Documentation:**
- Part 1: 45 pages (Executive Summary, Architecture, Media Processing, Vision Analysis)
- Part 2: 40 pages (Aggregation, LLM Integration, TTS, Storage)
- Part 3: 38 pages (Frontend Architecture, Processing Phases, UI Components)
- Part 4: 42 pages (AWS Integration, API Reference, Deployment, Operations)

**Total: ~165 pages of comprehensive technical documentation**

---

## Related Documents

- **Part 1**: `SCENE_SUMMARIZATION_PART1.md`
- **Part 2**: `SCENE_SUMMARIZATION_PART2.md`
- **Part 3**: `SCENE_SUMMARIZATION_PART3.md`
- **Master Index**: `DOCUMENTATION_INDEX.md`
- **Other Services**: AI Subtitle, Image Creation, Synthetic Voiceover references