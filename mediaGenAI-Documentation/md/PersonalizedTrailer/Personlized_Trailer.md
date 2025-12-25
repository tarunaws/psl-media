# Personalized Trailer System - Architecture & Logic Guide
## Part 1: System Overview & Architecture

**Document Version:** 1.0  
**Last Updated:** October 24, 2025  
**System:** MediaGenAI - AI-Powered Personalized Trailer Generation

---

## Table of Contents (Part 1)

1. [Executive Summary](#executive-summary)
2. [System Architecture Overview](#system-architecture-overview)
3. [Technology Stack](#technology-stack)
4. [Core Components](#core-components)
5. [Pipeline Modes](#pipeline-modes)
6. [Data Flow Architecture](#data-flow-architecture)
7. [AWS Services Integration](#aws-services-integration)

---

## Executive Summary

### What is the Personalized Trailer System?

The Personalized Trailer System is an AI-powered video orchestration service that analyzes hero footage, applies viewer preference models, and automatically generates personalized movie trailers tailored to specific audience profiles. The system can operate in both **mock mode** (for local demos) and **AWS mode** (for production with real AI services).

### Key Capabilities

| Capability | Description |
|------------|-------------|
| **Video Analysis** | Automatic scene detection, emotion analysis, object/label recognition, and face detection |
| **Profile-Based Personalization** | 4 viewer profiles (Action Enthusiast, Family Viewer, Thriller Buff, Romance Devotee) |
| **Multi-Variant Generation** | Creates multiple trailer versions optimized for different audience segments |
| **Adaptive Duration** | Generates trailers in multiple lengths (15s, 30s, 45s, 60s, 90s) |
| **Multi-Language Support** | Audio and subtitle localization in 6+ languages (en, es, fr, hi, de, ja) |
| **Format Flexibility** | Outputs in MP4 and MOV formats with multiple renditions |
| **Caption Integration** | Automatic subtitle generation with WebVTT format |
| **Storyboard Export** | JSON storyboard with scene metadata and timelines |

### Key Features

- **Dual-Mode Operation**: Mock mode (no AWS) and AWS mode (full AI pipeline)
- **Intelligent Scene Selection**: AI-powered ranking based on viewer preferences
- **Emotion-Driven Editing**: Matches scene emotions to audience profiles
- **FFmpeg Integration**: Video processing, segmentation, and assembly
- **RESTful API**: Complete HTTP API for frontend integration
- **Real-Time Progress**: Job status tracking and deliverable management
- **Variant Distribution**: Multiple trailer versions with different scene selections

---

## System Architecture Overview

### High-Level Architecture

```
┌──────────────────────────────────────────────────────────────────┐
│                       Frontend Layer (React)                      │
│  • Profile selection UI                                           │
│  • Video upload with drag & drop                                  │
│  • Configuration controls (language, duration, format)            │
│  • Job status monitoring                                          │
│  • Video player with deliverables                                 │
└────────────────┬─────────────────────────────────────────────────┘
                 │ HTTP/REST API
                 ▼
┌──────────────────────────────────────────────────────────────────┐
│                    Application Layer (Flask)                      │
│  • REST API endpoints (/generate, /jobs, /profiles)               │
│  • File upload handling (2GB limit)                               │
│  • Job orchestration and state management                         │
│  • CORS configuration                                             │
└────────────────┬─────────────────────────────────────────────────┘
                 │
                 ▼
┌──────────────────────────────────────────────────────────────────┐
│                   Processing Pipeline Layer                       │
│  ┌───────────────┐  ┌────────────────┐  ┌──────────────────┐    │
│  │   Analysis    │  │ Personalization│  │    Assembly      │    │
│  │   Stage       │→ │    Stage       │→ │    Stage         │    │
│  └───────────────┘  └────────────────┘  └──────────────────┘    │
│                                                                    │
│  • Video probing (FFprobe)                                        │
│  • Scene detection & labeling                                     │
│  • Emotion & face analysis                                        │
│  • Profile-based scene ranking                                    │
│  • Multi-variant generation                                       │
│  • FFmpeg video assembly                                          │
│  • Subtitle generation (VTT)                                      │
└────────────────┬─────────────────────────────────────────────────┘
                 │
                 ▼
┌──────────────────────────────────────────────────────────────────┐
│                   AWS Services Layer (Optional)                   │
│  • Amazon Rekognition — Video/image analysis                      │
│  • Amazon Personalize — Preference ranking                        │
│  • AWS Elemental MediaConvert — Video transcoding                 │
│  • Amazon S3 — Media storage                                      │
│  • Amazon Transcribe — Speech-to-text                             │
│  • Amazon Translate — Multi-language localization                 │
│  • Amazon SageMaker — Custom ML models                            │
│  • AWS Lambda — Workflow automation                               │
└──────────────────────────────────────────────────────────────────┘
```

### 4-Layer Architecture Breakdown

#### **Layer 1: Frontend (React SPA)**
- **Purpose**: User interaction and result visualization
- **Technology**: React 18.2+, styled-components, axios
- **Responsibilities**:
  - Profile selection (4 predefined profiles)
  - Video file upload (drag & drop)
  - Configuration (language, duration, format, captions)
  - Job submission and polling
  - Video playback with multiple variants
  - Deliverable downloads (trailer, storyboard)

#### **Layer 2: Application (Flask REST API)**
- **Purpose**: Request handling and orchestration
- **Technology**: Flask 3.0+, Flask-CORS
- **Responsibilities**:
  - API endpoint routing
  - File upload validation (format, size)
  - Job ID generation and storage
  - Pipeline invocation
  - Deliverable streaming
  - Health checks

#### **Layer 3: Processing Pipeline**
- **Purpose**: Video analysis, personalization, and assembly
- **Technology**: Python 3.11+, FFmpeg 6.0+, boto3 (optional)
- **Responsibilities**:
  - Video duration probing
  - Scene detection and segmentation
  - Emotion and label analysis
  - Profile-based scene ranking
  - Multi-variant generation
  - Video assembly with FFmpeg
  - Subtitle generation (VTT format)

#### **Layer 4: AWS Services (Optional)**
- **Purpose**: AI/ML processing and media operations
- **Technology**: AWS SDK (boto3)
- **Responsibilities**:
  - Amazon Rekognition: Label detection, face analysis, emotion recognition
  - Amazon Personalize: Scene scoring based on viewer preferences
  - AWS Elemental MediaConvert: Professional video transcoding
  - Amazon S3: Scalable media storage
  - Amazon Transcribe: Audio-to-text conversion
  - Amazon Translate: Multi-language localization

---

## Technology Stack

### Backend Technologies

| Component | Technology | Version | Purpose |
|-----------|-----------|---------|---------|
| **Runtime** | Python | 3.11+ | Core backend language |
| **Web Framework** | Flask | 3.0+ | REST API server |
| **CORS** | Flask-CORS | 4.0+ | Cross-origin requests |
| **AWS SDK** | boto3 | 1.28+ | AWS service integration (optional) |
| **Video Processing** | FFmpeg | 6.0+ | Video analysis & assembly |
| **Video Probing** | FFprobe | 6.0+ | Media duration extraction |

### Frontend Technologies

| Component | Technology | Version | Purpose |
|-----------|-----------|---------|---------|
| **Framework** | React | 18.2+ | UI component framework |
| **Styling** | styled-components | 6.1+ | CSS-in-JS styling |
| **HTTP Client** | axios | 1.6+ | API communication |
| **State Management** | React Hooks | Built-in | Component state |
| **Routing** | React Router | 6.0+ | Client-side routing |

### Infrastructure Requirements

| Requirement | Specification |
|-------------|--------------|
| **Operating System** | macOS, Linux, Windows (WSL2) |
| **Memory** | 8GB+ RAM (16GB recommended) |
| **Storage** | 100GB+ available (for video processing) |
| **FFmpeg** | 6.0+ with libx264, aac codecs |
| **Network** | High-speed connection for AWS integration |

### AWS Services (Production Mode)

| Service | Purpose | Tier |
|---------|---------|------|
| **Amazon Rekognition** | Video/image analysis | Pay-per-use |
| **Amazon Personalize** | Recommendation engine | Pay-per-use |
| **AWS Elemental MediaConvert** | Video transcoding | Pay-per-minute |
| **Amazon S3** | Object storage | Storage + requests |
| **Amazon Transcribe** | Speech-to-text | Pay-per-second |
| **Amazon Translate** | Text translation | Pay-per-character |
| **Amazon SageMaker** | Custom ML models | Instance-based |
| **AWS Lambda** | Serverless compute | Invocation-based |

---

## Core Components

### Backend Components

#### 1. Flask Application (`app.py`)

**Location**: `personalizedTrailer/app.py` (18 lines)

**Purpose**: Entry point for the service

```python
def main() -> None:
    flask_app = app if app is not None else create_app()
    port = int(os.getenv("PERSONALIZED_TRAILER_PORT", "5007"))
    flask_app.run(host="0.0.0.0", port=port, debug=False)
```

#### 2. Core Service (`personalized_trailer_service.py`)

**Location**: `personalizedTrailer/personalized_trailer_service.py` (1804 lines)

**Purpose**: Main orchestration service with all pipeline logic

**Key Functions**:

| Function | Lines | Purpose |
|----------|-------|---------|
| `_create_app()` | 113-133 | Flask app initialization & CORS |
| `_register_routes()` | 153-334 | API endpoint registration |
| `_run_pipeline()` | 345-477 | Main pipeline orchestration |
| `_probe_media_duration()` | 479-498 | Video duration extraction |
| `_aws_rekognition_analysis()` | 500-728 | AWS video analysis |
| `_mock_rekognition_analysis()` | 730-866 | Mock scene detection |
| `_mock_personalize_scenes()` | 868-1150 | Scene ranking & selection |
| `_mock_assemble_trailer()` | 1275-1389 | Trailer assembly logic |
| `_generate_deliverables_multivariant()` | 1391-1527 | Multi-variant generation |
| `_render_trailer_ffmpeg()` | 1634-1770 | FFmpeg video rendering |
| `_mock_vtt()` | 1772-1782 | Subtitle generation |

#### 3. Profile Presets

**Location**: Lines 69-111 in `personalized_trailer_service.py`

**4 Predefined Profiles**:

```python
PROFILE_PRESETS = [
    {
        "id": "action_enthusiast",
        "label": "Action Enthusiast",
        "summary": "High-intensity pacing, heroic set pieces, adrenaline-fueled score.",
        "preferences": {
            "dominantEmotions": ["Excited", "Tense"],
            "foregroundTags": ["Explosion", "Chase", "Hero"],
            "audioStyle": "orchestral-hybrid",
        },
    },
    {
        "id": "family_viewer",
        "label": "Family Viewer",
        "summary": "Humor, warmth, ensemble moments, inclusive storytelling.",
        "preferences": {
            "dominantEmotions": ["Joy", "Calm"],
            "foregroundTags": ["Family", "Friendship", "Heartwarming"],
            "audioStyle": "uplifting-pop",
        },
    },
    {
        "id": "thriller_buff",
        "label": "Thriller Buff",
        "summary": "Mystery hooks, dramatic reveals, escalating tension.",
        "preferences": {
            "dominantEmotions": ["Fear", "Surprise"],
            "foregroundTags": ["Mystery", "Plot Twist", "Shadow"],
            "audioStyle": "pulse-synth",
        },
    },
    {
        "id": "romance_devotee",
        "label": "Romance Devotee",
        "summary": "Intimate character moments, sweeping vistas, emotive dialogue.",
        "preferences": {
            "dominantEmotions": ["Love", "Hope"],
            "foregroundTags": ["Couple", "Sunset", "Monologue"],
            "audioStyle": "piano-ambient",
        },
    },
]
```

### Frontend Components

#### Main Component: `PersonalizedTrailer.js`

**Location**: `frontend/src/PersonalizedTrailer.js` (1145 lines)

**Purpose**: Complete UI for trailer generation workflow

**Key Sections**:
- Lines 1-65: Imports, constants, and utility functions
- Lines 67-427: Styled components (UI elements)
- Lines 461-1145: Main React component logic

---

## Pipeline Modes

### Mock Mode (Default)

**Configuration**:
```bash
PERSONALIZED_TRAILER_PIPELINE_MODE=mock
```

**Characteristics**:
- ✅ No AWS credentials required
- ✅ Deterministic scene generation (seeded randomness)
- ✅ Fast processing (no network calls)
- ✅ Perfect for local development and demos
- ⚠️ Uses simulated AI analysis
- ⚠️ Scene detection is rule-based

**Use Cases**:
- Local development
- Frontend integration testing
- Demo environments
- CI/CD pipelines

### AWS Mode (Production)

**Configuration**:
```bash
PERSONALIZED_TRAILER_PIPELINE_MODE=aws
AWS_REGION=us-east-1
PERSONALIZED_TRAILER_S3_BUCKET=my-trailer-bucket
```

**Characteristics**:
- ✅ Real AI-powered analysis
- ✅ High accuracy scene detection
- ✅ Production-grade quality
- ⚠️ Requires AWS credentials
- ⚠️ Incurs AWS costs
- ⚠️ Network-dependent

**Use Cases**:
- Production deployments
- High-quality trailer generation
- Enterprise applications

---

## Data Flow Architecture

### Complete Workflow (7 Stages)

```
┌─────────────────────────────────────────────────────────────────┐
│ Stage 1: Video Upload                                            │
│  • User selects profile (action, family, thriller, romance)      │
│  • Uploads hero footage (MP4, MOV, MKV, AVI, WebM)              │
│  • Configures duration (15s-90s), language, format, captions     │
│  • Frontend sends POST /generate with multipart form             │
└────────────────┬────────────────────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────────────────────┐
│ Stage 2: Video Analysis                                          │
│  • FFprobe extracts video duration                               │
│  • Mode check: mock or AWS                                       │
│  • Mock: Rule-based scene generation with randomness             │
│  • AWS: Amazon Rekognition frame-by-frame analysis               │
│  • Output: Scenes with labels, emotions, characters, timestamps  │
└────────────────┬────────────────────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────────────────────┐
│ Stage 3: Scene Personalization                                   │
│  • Retrieve viewer profile preferences                           │
│  • Score each scene based on emotion match                       │
│  • Score based on label/tag match                                │
│  • Rank scenes by composite score                                │
│  • Select top N scenes to fit target duration                    │
│  • Generate multiple variants (different scene selections)       │
└────────────────┬────────────────────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────────────────────┐
│ Stage 4: Trailer Assembly Planning                               │
│  • Create timeline from selected scenes                          │
│  • Apply transition rules (fade, cut, dissolve)                  │
│  • Calculate total duration (must fit target ±2s)                │
│  • Generate rendition specs (multiple resolutions)               │
│  • Plan audio track (match profile's audioStyle)                 │
└────────────────┬────────────────────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────────────────────┐
│ Stage 5: Video Rendering                                         │
│  • FFmpeg: Extract scene segments from source                    │
│  • FFmpeg: Apply filters (scale, fade, speedup)                  │
│  • FFmpeg: Concatenate segments with transitions                 │
│  • FFmpeg: Encode to target format (MP4/MOV)                     │
│  • Generate multiple renditions (1080p, 720p, 480p)              │
│  • Repeat for each variant                                       │
└────────────────┬────────────────────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────────────────────┐
│ Stage 6: Deliverable Generation                                  │
│  • Generate WebVTT subtitles for each variant                    │
│  • Create storyboard JSON (timeline + metadata)                  │
│  • Package all deliverables (videos + subs + storyboard)         │
│  • Calculate file sizes and durations                            │
│  • Generate streaming URLs                                       │
└────────────────┬────────────────────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────────────────────┐
│ Stage 7: Job Completion                                          │
│  • Store job metadata as JSON                                    │
│  • Return job object with deliverables to frontend               │
│  • Frontend displays video player with variants                  │
│  • User can download trailers, subtitles, storyboard             │
└─────────────────────────────────────────────────────────────────┘
```

### Processing Time Estimates

| Stage | Mock Mode | AWS Mode |
|-------|-----------|----------|
| Upload | 2-10s | 2-10s |
| Analysis | 5-15s | 30-120s |
| Personalization | 1-3s | 5-15s |
| Assembly Planning | 1-2s | 1-2s |
| Video Rendering | 10-60s | 10-60s |
| Deliverables | 2-5s | 2-5s |
| **Total** | **21-95s** | **50-210s** |

---

## AWS Services Integration

### Amazon Rekognition

**Purpose**: Video and image analysis

**Features Used**:
- `detect_labels()`: Object, scene, activity detection
- `detect_faces()`: Face detection with emotion analysis
- `recognize_celebrities()`: Celebrity identification

**Input**: Video frames extracted at intervals (2-5 seconds)

**Output**: 
```json
{
  "scenes": [
    {
      "sceneId": "scene_1",
      "start": 0.0,
      "end": 12.5,
      "emotions": ["Excited", "Happy"],
      "labels": ["Action", "Chase", "Car"],
      "characters": [
        {
          "name": "Person",
          "confidence": 92.5,
          "emotion": "Excited",
          "ageRange": "25-35",
          "gender": "Male"
        }
      ]
    }
  ]
}
```

### Amazon Personalize

**Purpose**: Scene ranking based on viewer preferences

**Implementation**: Scores scenes using profile preferences

**Algorithm**:
1. Calculate emotion match score (0-100)
2. Calculate tag/label match score (0-100)
3. Composite score = (emotion_score × 0.6) + (tag_score × 0.4)
4. Rank scenes by composite score
5. Select top N scenes fitting target duration

### AWS Elemental MediaConvert

**Purpose**: Professional video transcoding (future enhancement)

**Planned Features**:
- Multiple rendition creation
- Adaptive bitrate streaming (HLS/DASH)
- Professional codecs (HEVC, ProRes)

### Other AWS Services

| Service | Integration Status | Purpose |
|---------|-------------------|---------|
| Amazon S3 | Planned | Media storage and CDN delivery |
| Amazon Transcribe | Planned | Audio-to-text for captions |
| Amazon Translate | Planned | Multi-language subtitle generation |
| Amazon SageMaker | Planned | Custom engagement scoring models |
| AWS Lambda | Planned | Event-driven workflow automation |

---

## Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `PERSONALIZED_TRAILER_PORT` | `5007` | Service port |
| `PERSONALIZED_TRAILER_PIPELINE_MODE` | `mock` | Pipeline mode (mock/aws) |
| `PERSONALIZED_TRAILER_REGION` | `us-east-1` | AWS region |
| `PERSONALIZED_TRAILER_S3_BUCKET` | None | S3 bucket for media |
| `PERSONALIZED_TRAILER_PREFIX` | `personalized-trailers` | S3 prefix |
| `PERSONALIZED_TRAILER_MAX_UPLOAD_BYTES` | `2GB` | Max upload size |
| `PERSONALIZED_TRAILER_ALLOWED_ORIGINS` | localhost | CORS origins |
| `AWS_REGION` | `us-east-1` | AWS SDK region |

### File Structure

```
personalizedTrailer/
├── app.py                              # Entry point (18 lines)
├── personalized_trailer_service.py     # Core service (1804 lines)
├── uploads/                            # Uploaded videos
├── outputs/                            # Generated trailers
│   ├── {job_id}_trailer_variant_0.mp4
│   ├── {job_id}_trailer_variant_1.mp4
│   ├── {job_id}_subtitles_en.vtt
│   └── {job_id}_storyboard.json
└── jobs/                               # Job metadata
    └── {job_id}.json
```

---

## Next Document

➡️ **Part 2: API Endpoints & Backend Processing Logic**  
Covers REST API specifications, pipeline stages, and scene selection algorithms.

---

*End of Part 1*
# Personalized Trailer System - Architecture & Logic Guide
## Part 2: API Endpoints & Backend Processing

**Document Version:** 1.0  
**Last Updated:** October 24, 2025  
**System:** MediaGenAI - AI-Powered Personalized Trailer Generation

---

## Table of Contents (Part 2)

1. [API Endpoints Overview](#api-endpoints-overview)
2. [Generation Pipeline](#generation-pipeline)
3. [Scene Analysis Logic](#scene-analysis-logic)
4. [Personalization Algorithm](#personalization-algorithm)
5. [Multi-Variant Generation](#multi-variant-generation)
6. [Video Assembly Process](#video-assembly-process)
7. [Deliverable Generation](#deliverable-generation)

---

## API Endpoints Overview

### Base URL
```
http://localhost:5007
```

### API Endpoint Summary

| Endpoint | Method | Purpose | Auth |
|----------|--------|---------|------|
| `/health` | GET | Health check & service status | None |
| `/profiles` | GET | List viewer profiles & defaults | None |
| `/options` | GET | List configuration options | None |
| `/generate` | POST | Generate personalized trailer | None |
| `/jobs/<job_id>` | GET | Get job status & deliverables | None |
| `/jobs/<job_id>/deliverables/<artifact>` | GET | Stream/download deliverable | None |
| `/jobs/<job_id>/storyboard` | GET | Download storyboard JSON | None |

---

## Detailed API Specifications

### GET `/health`

**Purpose:** Service health check and configuration info

#### Response Format (200 OK)

```json
{
  "status": "ok",
  "mode": "mock",
  "region": "us-east-1",
  "services": {
    "rekognition": false,
    "personalize": false,
    "mediaconvert": false,
    "s3": false,
    "sagemaker": false,
    "transcribe": false,
    "translate": false
  },
  "bucket": null
}
```

**Service Status Indicators**:
- `true`: AWS service integration active
- `false`: Mock mode or service disabled

---

### GET `/profiles`

**Purpose:** List available viewer profiles and default options

#### Response Format (200 OK)

```json
{
  "profiles": [
    {
      "id": "action_enthusiast",
      "label": "Action Enthusiast",
      "summary": "High-intensity pacing, heroic set pieces, and adrenaline-fueled score cues.",
      "preferences": {
        "dominantEmotions": ["Excited", "Tense"],
        "foregroundTags": ["Explosion", "Chase", "Hero"],
        "audioStyle": "orchestral-hybrid"
      }
    },
    {
      "id": "family_viewer",
      "label": "Family Viewer",
      "summary": "Humor, warmth, ensemble moments, and inclusive storytelling arcs.",
      "preferences": {
        "dominantEmotions": ["Joy", "Calm"],
        "foregroundTags": ["Family", "Friendship", "Heartwarming"],
        "audioStyle": "uplifting-pop"
      }
    },
    {
      "id": "thriller_buff",
      "label": "Thriller Buff",
      "summary": "Mystery hooks, dramatic reveals, and escalating tension beats.",
      "preferences": {
        "dominantEmotions": ["Fear", "Surprise"],
        "foregroundTags": ["Mystery", "Plot Twist", "Shadow"],
        "audioStyle": "pulse-synth"
      }
    },
    {
      "id": "romance_devotee",
      "label": "Romance Devotee",
      "summary": "Intimate character moments, sweeping vistas, and emotive dialogue.",
      "preferences": {
        "dominantEmotions": ["Love", "Hope"],
        "foregroundTags": ["Couple", "Sunset", "Monologue"],
        "audioStyle": "piano-ambient"
      }
    }
  ],
  "defaults": {
    "languages": ["en", "es", "fr", "hi", "de", "ja"],
    "durations": [15, 30, 45, 60, 90],
    "outputFormats": ["mp4", "mov"]
  }
}
```

---

### GET `/options`

**Purpose:** Get available configuration options

#### Response Format (200 OK)

```json
{
  "languages": ["en", "es", "fr", "hi", "de", "ja"],
  "durations": [15, 30, 45, 60, 90],
  "outputFormats": ["mp4", "mov"],
  "subtitleLanguages": ["en", "es", "fr", "hi", "de", "ja"]
}
```

---

### POST `/generate`

**Purpose:** Upload video and generate personalized trailer

#### Request Format

**Content-Type:** `multipart/form-data`

**Form Fields:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `video` | File | Yes | Video file (MP4, MOV, MKV, AVI, WebM) |
| `profile_id` | String | Yes | Viewer profile ID |
| `target_language` | String | No | Audio language (default: `en`) |
| `subtitle_language` | String | No | Subtitle language (default: same as target_language) |
| `max_duration` | Integer | No | Trailer duration in seconds (default: `60`) |
| `output_format` | String | No | Output format: `mp4` or `mov` (default: `mp4`) |
| `include_captions` | Boolean | No | Generate subtitles (default: `true`) |
| `include_storyboard` | Boolean | No | Generate storyboard JSON (default: `true`) |

**cURL Example:**

```bash
curl -X POST http://localhost:5007/generate \
  -F "video=@hero_footage.mp4" \
  -F "profile_id=action_enthusiast" \
  -F "target_language=en" \
  -F "subtitle_language=en" \
  -F "max_duration=60" \
  -F "output_format=mp4" \
  -F "include_captions=true" \
  -F "include_storyboard=true"
```

#### Response Format (200 OK)

```json
{
  "job": {
    "jobId": "a1b2c3d4e5f6",
    "status": "completed",
    "submittedAt": "2025-10-24T10:30:00Z",
    "completedAt": "2025-10-24T10:31:45Z",
    "mode": "mock",
    "input": {
      "sourceFile": "hero_footage.mp4",
      "profile": { 
        "id": "action_enthusiast",
        "label": "Action Enthusiast",
        "summary": "High-intensity pacing...",
        "preferences": {
          "dominantEmotions": ["Excited", "Tense"],
          "foregroundTags": ["Explosion", "Chase", "Hero"],
          "audioStyle": "orchestral-hybrid"
        }
      },
      "targetLanguage": "en",
      "subtitleLanguage": "en",
      "maxDurationSeconds": 60,
      "outputFormat": "mp4"
    },
    "providers": {
      "rekognition": {
        "mode": "mock",
        "region": "us-east-1",
        "analysisMs": 1250
      },
      "personalize": {
        "mode": "mock",
        "selectedScenes": 12
      },
      "mediaconvert": {
        "mode": "mock",
        "renditions": 2
      }
    },
    "analysis": {
      "video": "hero_footage.mp4",
      "totalDuration": 120.5,
      "scenes": [ /* scene array */ ],
      "dominantEmotions": ["Excited", "Tense"],
      "metrics": {
        "analysisMs": 1250,
        "detectedPeople": 8,
        "detectedLocations": 4,
        "detectedObjects": 15,
        "coverageSeconds": 118.2,
        "coverageRatio": 0.981
      }
    },
    "personalization": {
      "rankedScenes": [ /* ranked scenes */ ],
      "selectedScenes": [ /* selected scenes */ ],
      "variants": [ /* variant definitions */ ],
      "targetDuration": 60,
      "estimatedDuration": 58.5
    },
    "assembly": {
      "timeline": [ /* timeline entries */ ],
      "renditions": [ /* rendition specs */ ],
      "estimatedDuration": 58.5
    },
    "assemblies": [ /* variant assemblies */ ],
    "deliverables": {
      "trailer_variant_0": {
        "path": "outputs/a1b2c3d4e5f6_trailer_variant_0.mp4",
        "mimeType": "video/mp4",
        "sizeBytes": 15728640,
        "durationSeconds": 58.5,
        "url": "/jobs/a1b2c3d4e5f6/deliverables/trailer_variant_0"
      },
      "subtitles_variant_0_en": {
        "path": "outputs/a1b2c3d4e5f6_subtitles_variant_0_en.vtt",
        "mimeType": "text/vtt",
        "sizeBytes": 2048,
        "url": "/jobs/a1b2c3d4e5f6/deliverables/subtitles_variant_0_en"
      },
      "storyboard": {
        "path": "outputs/a1b2c3d4e5f6_storyboard.json",
        "mimeType": "application/json",
        "sizeBytes": 8192,
        "url": "/jobs/a1b2c3d4e5f6/storyboard"
      }
    }
  }
}
```

#### Error Responses

**400 Bad Request:**
```json
{
  "error": "Video file is required."
}
```

**400 Bad Request:**
```json
{
  "error": "Unknown profile selection."
}
```

**413 Payload Too Large:**
```json
{
  "error": "File exceeds maximum size of 2GB."
}
```

---

### GET `/jobs/<job_id>`

**Purpose:** Retrieve job status and deliverables

#### Response Format (200 OK)

Same as POST `/generate` response format.

#### Error Responses

**404 Not Found:**
```json
{
  "error": "Job not found"
}
```

---

### GET `/jobs/<job_id>/deliverables/<artifact>`

**Purpose:** Stream or download a specific deliverable

**URL Parameters:**
- `job_id`: Job identifier
- `artifact`: Deliverable key (e.g., `trailer_variant_0`, `subtitles_variant_0_en`)

**Query Parameters:**
- `download`: Set to `true` to force download (default: stream)

**Example:**
```bash
# Stream video
curl http://localhost:5007/jobs/a1b2c3d4/deliverables/trailer_variant_0

# Download video
curl "http://localhost:5007/jobs/a1b2c3d4/deliverables/trailer_variant_0?download=true" \
  -o trailer.mp4
```

#### Response

**200 OK:** Binary file stream with appropriate `Content-Type`

**404 Not Found:**
```json
{
  "error": "Deliverable not found"
}
```

---

### GET `/jobs/<job_id>/storyboard`

**Purpose:** Download storyboard JSON

#### Response

**200 OK:** JSON file with complete scene metadata and timeline

---

## Generation Pipeline

### Pipeline Orchestration Function

**Function:** `_run_pipeline()`  
**Lines:** 345-477  
**Purpose:** Coordinates all stages of trailer generation

#### Pipeline Stages

```python
def _run_pipeline(
    app: Flask,
    job_id: str,
    video_path: Path,
    profile: Dict[str, Any],
    target_language: str,
    subtitle_language: str,
    max_duration: int,
    output_format: str,
    include_captions: bool,
    include_storyboard: bool,
) -> Dict[str, Any]:
    # Stage 1: Probe video duration
    source_duration = _probe_media_duration(video_path)
    
    # Stage 2: Video analysis (AWS or mock)
    if PIPELINE_MODE == "aws" and boto3:
        analysis = _aws_rekognition_analysis(...)
    else:
        analysis = _mock_rekognition_analysis(...)
    
    # Stage 3: Scene personalization
    personalization = _mock_personalize_scenes(...)
    
    # Stage 4: Primary assembly
    assembly = _mock_assemble_trailer(...)
    
    # Stage 5: Variant assemblies
    assemblies = []
    for variant in personalization.get("variants", []):
        variant_assembly = _mock_assemble_trailer_variant(...)
        assemblies.append(variant_assembly)
    
    # Stage 6: Generate deliverables
    deliverables = _generate_deliverables_multivariant(...)
    
    return {
        "providers": {...},
        "analysis": analysis,
        "personalization": personalization,
        "assembly": assembly,
        "assemblies": assemblies,
        "deliverables": deliverables,
    }
```

---

## Scene Analysis Logic

### Mock Scene Detection

**Function:** `_mock_rekognition_analysis()`  
**Lines:** 730-866  
**Purpose:** Generate realistic scene data without AWS

#### Algorithm

```python
def _mock_rekognition_analysis(
    rng: random.Random,
    video_path: Path,
    profile: Dict[str, Any],
    source_duration: Optional[float] = None,
) -> Dict[str, Any]:
    # 1. Determine base duration
    if source_duration and source_duration > 1:
        base_duration = float(source_duration)
    else:
        base_duration = float(rng.randint(90, 150))
    
    # 2. Extract profile preferences
    dominant_emotions = profile["preferences"]["dominantEmotions"]
    tags_pool = profile["preferences"].get("foregroundTags", []) + [
        "Landscape", "Dialogue", "Crowd", "Vehicle", "Logo"
    ]
    
    # 3. Calculate target scene count
    min_scene_len = 6.0  # seconds
    max_scene_len = 18.0  # seconds
    target_scene_count = max(10, min(30, int(math.ceil(base_duration / 12.0))))
    
    # 4. Generate scenes to cover full duration
    cursor = 0.0
    scenes = []
    scene_index = 0
    
    while cursor < (base_duration - min_scene_len):
        scene_length = rng.uniform(min_scene_len, max_scene_len)
        start = cursor
        end = min(base_duration, start + scene_length)
        
        # Assign emotions and labels
        scene_emotions = rng.sample(dominant_emotions + ["Neutral", "Joy", "Fear"], k=2)
        labels = rng.sample(tags_pool, k=min(3, len(tags_pool)))
        
        # Create character data
        characters = [
            {
                "name": rng.choice(["Lead", "Supporting", "Cameo"]),
                "confidence": round(rng.uniform(72, 98), 2),
                "emotion": scene_emotions[0],
            }
            for _ in range(rng.randint(1, 3))
        ]
        
        scenes.append({
            "sceneId": f"scene_{scene_index + 1}",
            "start": round(start, 2),
            "end": round(end, 2),
            "duration": round(end - start, 2),
            "emotions": scene_emotions,
            "labels": labels,
            "characters": characters,
            "keyVisual": f"frame_{scene_index + 1:02d}.jpg",
            "highlights": rng.sample(labels + scene_emotions, k=2)
        })
        
        cursor = end
        scene_index += 1
    
    # 5. Calculate coverage metrics
    coverage_seconds = scenes[-1]["end"] if scenes else 0.0
    coverage_ratio = round(coverage_seconds / base_duration, 3)
    
    return {
        "video": video_path.name,
        "totalDuration": round(base_duration, 2),
        "scenes": scenes,
        "dominantEmotions": dominant_emotions,
        "metrics": {
            "analysisMs": rng.randint(850, 1450),
            "detectedPeople": rng.randint(5, 14),
            "detectedLocations": rng.randint(2, 6),
            "detectedObjects": rng.randint(10, 22),
            "coverageSeconds": round(coverage_seconds, 2),
            "coverageRatio": coverage_ratio
        }
    }
```

### AWS Rekognition Analysis

**Function:** `_aws_rekognition_analysis()`  
**Lines:** 500-728  
**Purpose:** Real AI-powered video analysis

#### Process Flow

```
1. Extract Frames
   ├─ Calculate frame interval (source_duration / 30)
   ├─ FFmpeg: Extract frames as JPEGs
   └─ Store frames in temp directory

2. Analyze Each Frame
   ├─ detect_labels() → Objects, scenes, activities
   ├─ detect_faces() → Faces with emotions, age, gender
   └─ recognize_celebrities() → Celebrity identification

3. Segment Into Scenes
   ├─ Group frames by time ranges
   ├─ Calculate scene_duration = source_duration / 5
   └─ Create ~5 scenes covering full video

4. Build Scene Objects
   ├─ Aggregate labels for time range
   ├─ Aggregate emotions for time range
   ├─ Create character list with emotions
   └─ Calculate scene metadata

5. Calculate Metrics
   ├─ Count detected people
   ├─ Count unique locations
   ├─ Count unique objects
   └─ Calculate coverage statistics
```

---

## Personalization Algorithm

**Function:** `_mock_personalize_scenes()`  
**Lines:** 868-1150  
**Purpose:** Rank and select scenes based on viewer profile

### Scoring Algorithm

```python
def _mock_personalize_scenes(
    rng: random.Random,
    analysis: Dict[str, Any],
    profile: Dict[str, Any],
    max_duration: int,
) -> Dict[str, Any]:
    # 1. Extract profile preferences
    preferred_emotions = set(profile["preferences"]["dominantEmotions"])
    preferred_tags = set(profile["preferences"]["foregroundTags"])
    
    # 2. Score each scene
    for scene in analysis["scenes"]:
        base_score = rng.uniform(0.6, 0.98)
        weight = 1.0
        
        # Boost for matching emotions
        for emotion in scene["emotions"]:
            if emotion in preferred_emotions:
                weight += 0.15
        
        # Boost for matching tags
        for tag in scene["labels"]:
            if tag in preferred_tags:
                weight += 0.10
        
        weighted_score = min(1.0, round(base_score * weight, 3))
        
        ranked.append({
            "sceneId": scene["sceneId"],
            "score": weighted_score,
            "start": scene["start"],
            "end": scene["end"],
            "duration": scene["duration"],
            "normalizedStart": scene["start"] / total_duration
        })
    
    # 3. Sort by score (descending)
    ranked.sort(key=lambda item: item["score"], reverse=True)
    
    # 4. Distribute across regions (early, middle, late)
    regions = {
        "early": {"items": [], "quota": max_duration * 0.3},
        "middle": {"items": [], "quota": max_duration * 0.4},
        "late": {"items": [], "quota": max_duration * 0.3}
    }
    
    for item in ranked:
        if item["normalizedStart"] < 1/3:
            regions["early"]["items"].append(item)
        elif item["normalizedStart"] < 2/3:
            regions["middle"]["items"].append(item)
        else:
            regions["late"]["items"].append(item)
    
    # 5. Select scenes from each region
    selected = []
    cumulative = 0.0
    
    for region_name, region_data in regions.items():
        for scene in region_data["items"]:
            if cumulative >= max_duration:
                break
            if scene_fits_in_quota(scene, region_data["quota"]):
                selected.append(scene)
                cumulative += scene["duration"]
    
    # 6. Sort selected scenes chronologically
    selected.sort(key=lambda x: x["start"])
    
    return {
        "rankedScenes": ranked,
        "selectedScenes": selected,
        "variants": variants,  # Generated separately
        "targetDuration": max_duration,
        "estimatedDuration": round(cumulative, 2)
    }
```

### Composite Scoring Formula

```
weighted_score = base_score × weight

where:
  base_score = random(0.6, 0.98)
  weight = 1.0 + emotion_bonus + tag_bonus
  emotion_bonus = 0.15 per matching emotion
  tag_bonus = 0.10 per matching tag
  
max(weighted_score) = 1.0 (capped)
```

---

## Multi-Variant Generation

### Strategy: Minimize Content Overlap

**Purpose:** Generate 4 trailer variants with unique scene selections

### Variant Definitions

| Variant | Name | Distribution | Strategy |
|---------|------|--------------|----------|
| 1 | Opening Act | 60% early, 30% middle, 10% late | Emphasizes setup |
| 2 | Middle Climax | 20% early, 60% middle, 20% late | Showcases peak action |
| 3 | Grand Finale | 10% early, 30% middle, 60% late | Highlights climax |
| 4 | Balanced Mix | 33% early, 34% middle, 33% late | Equal representation |

### Selection Algorithm

```python
def select_variant_scenes(
    early_ratio: float,
    middle_ratio: float,
    late_ratio: float,
    variant_name: str,
    offset_multiplier: int = 0
) -> List[Dict[str, Any]]:
    """
    Select scenes with minimal overlap to other variants.
    Uses offset and interleaving (skip every other scene).
    """
    variant_scenes = []
    
    # Early region - use offset and skip pattern
    early_sorted = sorted(regions["early"]["items"], key=lambda x: x["score"], reverse=True)
    for i in range(offset_multiplier, len(early_sorted), 2):  # Skip every other
        if scene_fits_quota:
            if scene["sceneId"] not in used_across_variants:
                variant_scenes.append(scene)
                used_across_variants.add(scene["sceneId"])
    
    # Middle region - different offset
    middle_offset = (offset_multiplier + 1) % 2
    # ... similar logic
    
    # Late region - different offset
    late_offset = offset_multiplier % 2
    # ... similar logic
    
    variant_scenes.sort(key=lambda x: x["start"])
    return variant_scenes
```

### Overlap Minimization Techniques

1. **Offset Selection**: Each variant starts at different index
2. **Interleaving**: Skip every other scene (stride=2)
3. **Cross-Variant Tracking**: Track scenes used across all variants
4. **Fallback Strategy**: Use ranked list with offset if no unique scenes available

---

## Video Assembly Process

### Timeline Generation

**Function:** `_mock_assemble_trailer_variant()`  
**Lines:** 1152-1273  
**Purpose:** Create timeline from selected scenes with transitions

#### Handle Calculation (Padding)

```python
for index, scene in enumerate(selected_scenes):
    # Calculate padding before scene
    pad_before = 0.75  # Default 0.75 seconds
    if last_source_end > 0:
        gap_from_previous = max(0.0, scene["start"] - last_source_end)
        pad_before = min(pad_before, gap_from_previous)
    
    # Calculate padding after scene
    pad_after = 0.9  # Default 0.9 seconds
    if next_scene is not None:
        gap_to_next = next_scene["start"] - scene["end"]
        if gap_to_next > 0:
            pad_after = min(pad_after, gap_to_next * 0.45)
    
    # Apply source boundaries
    source_start = max(0.0, scene["start"] - pad_before)
    source_end = scene["end"] + pad_after
    
    # Ensure within source duration
    if source_duration is not None:
        source_start = min(source_start, max(0.0, source_duration - 1.5))
        source_end = min(source_end, source_duration)
    
    clip_duration = max(1.5, source_end - source_start)
```

#### Transition Selection

```python
transition = rng.choice(["cut", "fade", "dip"])
audio_cue = rng.choice(["rise", "drop", "sting", "motif"])
```

#### Timeline Entry Format

```json
{
  "sceneId": "scene_5",
  "in": 12.5,
  "out": 18.3,
  "sourceStart": 45.2,
  "sourceEnd": 51.0,
  "handles": {
    "padBefore": 0.75,
    "padAfter": 0.85
  },
  "transition": "fade",
  "audioCue": "rise"
}
```

---

## Deliverable Generation

**Function:** `_generate_deliverables_multivariant()`  
**Lines:** 1391-1527  
**Purpose:** Generate all output files for multiple variants

### Process Flow

```
1. Render Primary Trailer
   └─ _render_trailer_ffmpeg() for main variant

2. Render All Variant Trailers
   ├─ Loop through assemblies
   ├─ _render_trailer_ffmpeg() for each variant
   └─ Add to deliverables dict

3. Generate Subtitles (if enabled)
   ├─ Loop through variants
   ├─ _mock_vtt() for each language
   └─ Save as .vtt files

4. Generate Storyboard (if enabled)
   ├─ Collect all timeline data
   ├─ Serialize to JSON
   └─ Save to outputs/

5. Calculate Metadata
   ├─ File sizes (os.path.getsize)
   ├─ Durations (from assemblies)
   └─ MIME types

6. Build Deliverables Object
   {
     "trailer_variant_0": {...},
     "trailer_variant_1": {...},
     "subtitles_variant_0_en": {...},
     "storyboard": {...}
   }
```

### FFmpeg Video Rendering

**Function:** `_render_trailer_ffmpeg()`  
**Lines:** 1634-1770  
**Purpose:** Assemble video from timeline using FFmpeg

#### FFmpeg Command Structure

```bash
# 1. Extract scene segments
ffmpeg -ss {source_start} -i {input_video} -t {duration} -c copy segment_{i}.mp4

# 2. Create concat file
file 'segment_0.mp4'
file 'segment_1.mp4'
file 'segment_2.mp4'

# 3. Concatenate with re-encoding
ffmpeg -f concat -safe 0 -i concat_list.txt \
  -c:v libx264 -preset fast -crf 23 \
  -c:a aac -b:a 192k \
  -movflags +faststart \
  output_trailer.mp4
```

### Subtitle Generation (WebVTT)

**Function:** `_mock_vtt()`  
**Lines:** 1772-1782  
**Purpose:** Generate WebVTT subtitle file

#### WebVTT Format

```vtt
WEBVTT

00:00:00.000 --> 00:00:05.800
Scene: Action sequence begins

00:00:05.800 --> 00:00:12.500
Scene: Hero faces challenge

00:00:12.500 --> 00:00:18.300
Scene: Climactic moment
```

---

## Next Document

➡️ **Part 3: Frontend Architecture & Components**  
Covers React UI, state management, and user interaction flow.

---

*End of Part 2*
# Personalized Trailer System - Architecture & Logic Guide
## Part 3: Frontend Architecture & Components

**Document Version:** 1.0  
**Last Updated:** October 24, 2025  
**System:** MediaGenAI - AI-Powered Personalized Trailer Generation

---

## Table of Contents (Part 3)

1. [Frontend Architecture Overview](#frontend-architecture-overview)
2. [Component Structure](#component-structure)
3. [State Management](#state-management)
4. [User Interaction Flow](#user-interaction-flow)
5. [API Integration](#api-integration)
6. [Multi-Variant Display](#multi-variant-display)
7. [UI Components](#ui-components)

---

## Frontend Architecture Overview

### Technology Stack

| Category | Technology | Version | Purpose |
|----------|-----------|---------|---------|
| **Framework** | React | 18.2+ | Component architecture |
| **Styling** | styled-components | 6.1+ | CSS-in-JS styling |
| **HTTP Client** | axios | 1.6+ | API communication |
| **State** | React Hooks | Built-in | State management |
| **Routing** | React Router | 6.0+ | Navigation |

### Component Architecture

```
PersonalizedTrailer (Main Component - 1145 lines)
│
├── File Upload Section
│   ├── UploadCard (drag & drop)
│   ├── MetaRow (file info)
│   └── VideoPreview (preview player)
│
├── Profile Selection Section
│   ├── ProfilesGrid (4 profile cards)
│   └── ProfileCard (interactive button)
│
├── Settings Section
│   ├── OptionsPanel (configuration grid)
│   ├── Duration selector
│   ├── Language selectors
│   ├── Format selector
│   └── Checkbox controls
│
├── Action Section
│   ├── PrimaryButton (generate)
│   ├── SecondaryButton (reset)
│   └── StatusBanner (progress/errors)
│
└── Results Section
    ├── JobSection (job summary)
    ├── Multi-Variant Display (4 trailers)
    ├── Scene Intelligence (analysis data)
    ├── Personalization Ranking (scored scenes)
    ├── Assembly Plan (timeline)
    └── Deliverables List (downloads)
```

### Data Flow

```
┌────────────────────────────────────────────────────────────┐
│                     User Actions                            │
│  • Select video file (drag/drop or browse)                  │
│  • Choose viewer profile                                    │
│  • Configure settings (duration, language, format)          │
│  • Click "Generate trailer plan"                            │
└────────────────┬───────────────────────────────────────────┘
                 │
                 ▼
┌────────────────────────────────────────────────────────────┐
│                   React State Layer                         │
│  • selectedFile: File | null                                │
│  • selectedProfileId: string                                │
│  • duration: number (15-90)                                 │
│  • targetLanguage: string                                   │
│  • processing: boolean                                      │
│  • uploadProgress: number | null                            │
│  • job: JobObject | null                                    │
└────────────────┬───────────────────────────────────────────┘
                 │
                 ▼
┌────────────────────────────────────────────────────────────┐
│                   API Communication                         │
│  • POST /generate (with FormData)                           │
│  • Upload progress tracking                                 │
│  • Response parsing                                         │
└────────────────┬───────────────────────────────────────────┘
                 │
                 ▼
┌────────────────────────────────────────────────────────────┐
│                   Backend Processing                        │
│  (See Parts 1-2 for backend details)                        │
└────────────────┬───────────────────────────────────────────┘
                 │
                 ▼
┌────────────────────────────────────────────────────────────┐
│                   UI Updates                                │
│  • Display job summary                                      │
│  • Render 4 trailer variants with video players             │
│  • Show scene intelligence table                            │
│  • Display personalization metrics                          │
│  • Provide download links                                   │
└────────────────────────────────────────────────────────────┘
```

---

## Component Structure

### Main Component: PersonalizedTrailer

**File:** `frontend/src/PersonalizedTrailer.js` (1145 lines)

**Purpose:** Complete UI for personalized trailer generation

**Key Sections**:
- Lines 1-65: Imports, constants, utility functions
- Lines 67-427: Styled components (43 styled elements)
- Lines 461-1145: Main component logic and JSX

---

## State Management

### State Variables

```javascript
export default function PersonalizedTrailer() {
  // Profile Management
  const [profiles, setProfiles] = useState(DEFAULT_PROFILES);
  const [selectedProfileId, setSelectedProfileId] = useState(DEFAULT_PROFILES[0]?.id ?? null);
  
  // File Management
  const [selectedFile, setSelectedFile] = useState(null);
  const [previewUrl, setPreviewUrl] = useState('');
  
  // Configuration Options
  const [options, setOptions] = useState(DEFAULT_OPTIONS);
  const [duration, setDuration] = useState(60);
  const [targetLanguage, setTargetLanguage] = useState('en');
  const [subtitleLanguage, setSubtitleLanguage] = useState('en');
  const [outputFormat, setOutputFormat] = useState('mp4');
  const [includeCaptions, setIncludeCaptions] = useState(true);
  const [includeStoryboard, setIncludeStoryboard] = useState(true);
  
  // Processing State
  const [processing, setProcessing] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(null);
  const uploadProgressRef = useRef(0);
  const uploadProgressResetRef = useRef(null);
  
  // Status & Results
  const [status, setStatus] = useState('');
  const [error, setError] = useState('');
  const [job, setJob] = useState(null);
  
  // Configuration
  const API_BASE = useMemo(() => resolveTrailerApiBase(), []);
  const REQUEST_TIMEOUT = useMemo(() => {
    const envValue = Number(process.env.REACT_APP_TRAILER_TIMEOUT_MS);
    return Number.isFinite(envValue) && envValue > 0 ? envValue : DEFAULT_TIMEOUT_MS;
  }, []);
}
```

### State Dependencies

```javascript
// Computed values from job state
const activeProfile = profiles.find((profile) => profile.id === selectedProfileId) || null;
const personalization = job?.personalization;
const analysis = job?.analysis;
const providers = job?.providers;
const assembly = job?.assembly;
const deliverables = job?.deliverables;
```

---

## User Interaction Flow

### 1. Initial Load

```javascript
useEffect(() => {
  let cancelled = false;

  const fetchProfilesAndOptions = async () => {
    try {
      // Fetch profiles
      const endpoint = API_BASE ? `${API_BASE}/profiles` : '/profiles';
      const { data } = await axios.get(endpoint, { timeout: REQUEST_TIMEOUT });
      
      if (cancelled) return;
      
      if (Array.isArray(data?.profiles) && data.profiles.length > 0) {
        setProfiles(data.profiles);
        setSelectedProfileId(data.profiles[0].id);
      }
      
      // Update default options
      if (data?.defaults) {
        const defaults = {
          languages: data.defaults.languages || DEFAULT_OPTIONS.languages,
          subtitleLanguages: data.defaults.subtitleLanguages || DEFAULT_OPTIONS.subtitleLanguages,
          durations: data.defaults.durations || DEFAULT_OPTIONS.durations,
          outputFormats: data.defaults.outputFormats || DEFAULT_OPTIONS.outputFormats,
        };
        setOptions((prev) => ({ ...prev, ...defaults }));
        
        // Update state with first default values
        if (defaults.durations?.length > 0) {
          setDuration(defaults.durations[0]);
        }
        if (defaults.languages?.length > 0) {
          setTargetLanguage(defaults.languages[0]);
        }
      }
    } catch (err) {
      if (!cancelled) {
        setError('Unable to refresh profiles from backend. Using defaults.');
      }
    }
    
    // Fetch additional options
    try {
      const endpoint = API_BASE ? `${API_BASE}/options` : '/options';
      const { data } = await axios.get(endpoint, { timeout: REQUEST_TIMEOUT });
      if (cancelled) return;
      if (data) {
        setOptions((prev) => ({ ...prev, ...data }));
      }
    } catch (err) {
      // Ignore secondary errors
    }
  };

  fetchProfilesAndOptions();

  return () => {
    cancelled = true;
  };
}, [API_BASE, REQUEST_TIMEOUT]);
```

### 2. File Selection

```javascript
const handleFileSelection = useCallback((file) => {
  if (!file) return;
  
  // Validate file type
  if (!file.type.startsWith('video/')) {
    setError('Please choose a video file.');
    return;
  }
  
  // Clean up previous preview URL
  if (previewUrl) {
    URL.revokeObjectURL(previewUrl);
  }
  
  // Update state
  setSelectedFile(file);
  setPreviewUrl(URL.createObjectURL(file));
  setError('');
  setStatus('');
  setJob(null);
  setUploadProgress(null);
  
  // Reset progress tracking
  if (uploadProgressResetRef.current) {
    clearTimeout(uploadProgressResetRef.current);
    uploadProgressResetRef.current = null;
  }
  uploadProgressRef.current = 0;
}, [previewUrl]);

// Drag & drop handler
const onDrop = (event) => {
  event.preventDefault();
  const file = event.dataTransfer.files?.[0];
  handleFileSelection(file);
};

// File input handler
const onFileInputChange = (event) => {
  const file = event.target.files?.[0];
  handleFileSelection(file);
};
```

### 3. Profile Selection

```jsx
<ProfilesGrid>
  {profiles.map((profile) => (
    <ProfileCard
      key={profile.id}
      type="button"
      onClick={() => setSelectedProfileId(profile.id)}
      $active={profile.id === selectedProfileId}
    >
      <ProfileTitle>{profile.label}</ProfileTitle>
      <ProfileSummary>{profile.summary}</ProfileSummary>
    </ProfileCard>
  ))}
</ProfilesGrid>
```

### 4. Configuration

```jsx
<OptionsPanel>
  {/* Duration */}
  <OptionGroup>
    <span>Maximum runtime (seconds)</span>
    <SelectInput 
      value={duration} 
      onChange={(event) => setDuration(Number(event.target.value))}
    >
      {options.durations.map((value) => (
        <option key={value} value={value}>{value}</option>
      ))}
    </SelectInput>
  </OptionGroup>
  
  {/* Target Language */}
  <OptionGroup>
    <span>Target language</span>
    <SelectInput 
      value={targetLanguage} 
      onChange={(event) => setTargetLanguage(event.target.value)}
    >
      {options.languages.map((lang) => (
        <option key={lang} value={lang}>{lang.toUpperCase()}</option>
      ))}
    </SelectInput>
  </OptionGroup>
  
  {/* Subtitle Language */}
  <OptionGroup>
    <span>Subtitle language</span>
    <SelectInput 
      value={subtitleLanguage} 
      onChange={(event) => setSubtitleLanguage(event.target.value)}
    >
      {options.subtitleLanguages.map((lang) => (
        <option key={lang} value={lang}>{lang.toUpperCase()}</option>
      ))}
    </SelectInput>
    <CheckboxRow>
      <input
        type="checkbox"
        checked={includeCaptions}
        onChange={(event) => setIncludeCaptions(event.target.checked)}
      />
      Include captions file
    </CheckboxRow>
  </OptionGroup>
  
  {/* Output Format */}
  <OptionGroup>
    <span>Master output format</span>
    <SelectInput 
      value={outputFormat} 
      onChange={(event) => setOutputFormat(event.target.value)}
    >
      {options.outputFormats.map((fmt) => (
        <option key={fmt} value={fmt}>{fmt.toUpperCase()}</option>
      ))}
    </SelectInput>
    <CheckboxRow>
      <input
        type="checkbox"
        checked={includeStoryboard}
        onChange={(event) => setIncludeStoryboard(event.target.checked)}
      />
      Generate storyboard summary
    </CheckboxRow>
  </OptionGroup>
</OptionsPanel>
```

### 5. Submit Request

```javascript
const submitRequest = async () => {
  // Validation
  if (!selectedFile) {
    setError('Choose a video asset to personalize.');
    return;
  }
  if (!selectedProfileId) {
    setError('Select a viewer profile.');
    return;
  }

  // Initialize processing
  setProcessing(true);
  setError('');
  setStatus('Uploading to personalized trailer service...');
  setJob(null);
  setUploadProgress(1);
  uploadProgressRef.current = 1;

  // Build FormData
  const formData = new FormData();
  formData.append('video', selectedFile);
  formData.append('profile_id', selectedProfileId);
  formData.append('max_duration', String(duration));
  formData.append('target_language', targetLanguage);
  formData.append('subtitle_language', subtitleLanguage);
  formData.append('output_format', outputFormat);
  formData.append('include_captions', includeCaptions ? 'true' : 'false');
  formData.append('include_storyboard', includeStoryboard ? 'true' : 'false');

  try {
    const endpoint = API_BASE ? `${API_BASE}/generate` : '/generate';
    const { data } = await axios.post(endpoint, formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
      timeout: REQUEST_TIMEOUT,
      maxContentLength: Infinity,
      maxBodyLength: Infinity,
      
      // Track upload progress
      onUploadProgress: (event) => {
        if (!event.total || !Number.isFinite(event.total)) {
          uploadProgressRef.current = Math.max(uploadProgressRef.current || 0, 1);
          setUploadProgress((prev) => (prev == null || prev < 1 ? 1 : prev));
          return;
        }
        
        const rawPercent = Math.round((event.loaded / event.total) * 100);
        const bounded = Math.min(99, Math.max(1, rawPercent));
        
        if (bounded <= uploadProgressRef.current) {
          return;
        }
        
        uploadProgressRef.current = bounded;
        setUploadProgress(bounded);
      },
    });

    // Success
    uploadProgressRef.current = 100;
    setUploadProgress(100);
    setStatus('Personalized trailer plan generated.');
    setJob(data?.job ?? null);
    
  } catch (requestError) {
    const backendError = requestError.response?.data?.error || requestError.message;
    setError(`Failed to personalize trailer: ${backendError}`);
    setStatus('Personalized trailer request failed.');
    
  } finally {
    setProcessing(false);
    
    // Reset progress after delay
    uploadProgressResetRef.current = setTimeout(() => {
      setUploadProgress(null);
      uploadProgressResetRef.current = null;
    }, 400);
    
    uploadProgressRef.current = 0;
  }
};
```

---

## API Integration

### API Base URL Resolution

```javascript
const resolveTrailerApiBase = () => {
  // Check environment variable
  const envValue = process.env.REACT_APP_TRAILER_API_BASE;
  if (envValue) {
    return envValue.replace(/\/$/, '');  // Remove trailing slash
  }
  
  // Auto-detect from window.location
  if (typeof window !== 'undefined') {
    const { protocol, hostname } = window.location;
    const normalized = hostname === '0.0.0.0' ? '127.0.0.1' : hostname;
    const localHosts = new Set(['localhost', '127.0.0.1', '::1']);

    if (localHosts.has(normalized)) {
      return `${protocol}//${normalized}:5007`.replace(/\/$/, '');
    }

    return `${protocol}//${hostname}`.replace(/\/$/, '');
  }
  
  return '';
};
```

### Deliverable URL Builder

```javascript
const buildDeliverableUrl = useCallback((path, options = {}) => {
  if (!path) return null;
  
  const normalized = path.startsWith('/') ? path : `/${path}`;
  const base = API_BASE || '';
  let url = `${base}${normalized}`;
  
  // Add download query parameter
  if (options.download) {
    url += normalized.includes('?') ? '&download=true' : '?download=true';
  }
  
  return url;
}, [API_BASE]);
```

### File Size Formatter

```javascript
const formatFileSize = (bytes) => {
  if (!Number.isFinite(bytes) || bytes <= 0) {
    return null;
  }
  
  const units = ['B', 'KB', 'MB', 'GB'];
  let size = bytes;
  let unitIndex = 0;
  
  while (size >= 1024 && unitIndex < units.length - 1) {
    size /= 1024;
    unitIndex += 1;
  }
  
  const precision = unitIndex === 0 ? 0 : unitIndex === units.length - 1 ? 2 : 1;
  return `${size.toFixed(precision)} ${units[unitIndex]}`;
};
```

---

## Multi-Variant Display

### Variant Detection

```javascript
// Extract variant keys from deliverables
const variantKeys = deliverables 
  ? Object.keys(deliverables).filter(k => k.startsWith('variant_')) 
  : [];

console.log('🎬 Deliverables:', deliverables);
console.log('🎬 Variant keys found:', variantKeys);
console.log('🎬 Number of variants:', variantKeys.length);
```

### Variant Rendering

```jsx
{variantKeys.length > 0 ? (
  <JobSection>
    <SectionTitle>
      Rendered Trailer Variants ({variantKeys.length} versions)
    </SectionTitle>
    
    {Object.entries(deliverables)
      .filter(([key]) => key.startsWith('variant_'))
      .sort(([keyA], [keyB]) => keyA.localeCompare(keyB))
      .map(([key, variant]) => {
        const variantStreamUrl = buildDeliverableUrl(variant?.downloadUrl);
        const variantDownloadUrl = buildDeliverableUrl(
          variant?.downloadUrl, 
          { download: true }
        );
        const variantSizeLabel = formatFileSize(variant?.sizeBytes);
        
        return (
          <div key={key} style={{ marginBottom: '2rem' }}>
            {/* Variant Name */}
            <h4 style={{ 
              margin: '1rem 0 0.5rem 0',
              fontSize: '1.1rem',
              fontWeight: 600,
              color: '#1a1a1a'
            }}>
              {variant?.name || key}
            </h4>
            
            {/* Variant Description */}
            {variant?.description && (
              <p style={{ 
                margin: '0 0 0.5rem 0',
                fontSize: '0.9rem',
                color: '#666'
              }}>
                {variant.description}
              </p>
            )}
            
            {/* Distribution Info */}
            {variant?.distribution && (
              <p style={{ 
                margin: '0 0 0.8rem 0',
                fontSize: '0.85rem',
                color: '#888',
                fontStyle: 'italic'
              }}>
                Distribution: {
                  Object.entries(variant.distribution)
                    .map(([k, v]) => `${k}: ${v}`)
                    .join(', ')
                }
              </p>
            )}
            
            {/* Video Player */}
            {variantStreamUrl && (
              <>
                <RenderedVideo 
                  controls 
                  src={variantStreamUrl} 
                  preload="metadata" 
                />
                
                {/* Download Button */}
                <DownloadRow>
                  <DownloadButton
                    as="a"
                    href={variantDownloadUrl || variantStreamUrl}
                    download
                  >
                    Download {variant?.name || key}
                  </DownloadButton>
                  
                  {variantSizeLabel && (
                    <FileMeta>≈ {variantSizeLabel}</FileMeta>
                  )}
                </DownloadRow>
              </>
            )}
          </div>
        );
      })}
  </JobSection>
) : (
  // Fallback to master deliverable (backward compatible)
  masterStreamUrl && (
    <JobSection>
      <SectionTitle>Rendered trailer</SectionTitle>
      <RenderedVideo controls src={masterStreamUrl} preload="metadata" />
      <DownloadRow>
        <DownloadButton
          as="a"
          href={masterDownloadUrl || masterStreamUrl}
          download
        >
          Download trailer
        </DownloadButton>
        {masterSizeLabel && <FileMeta>≈ {masterSizeLabel}</FileMeta>}
      </DownloadRow>
    </JobSection>
  )
)}
```

### Variant Display Features

1. **Automatic Detection**: Finds all deliverables starting with `variant_`
2. **Sorted Display**: Alphabetically sorted by key
3. **Rich Metadata**:
   - Variant name (e.g., "Opening Act")
   - Description (e.g., "Emphasizes the beginning and setup")
   - Distribution percentages (e.g., "early: 60%, middle: 30%, late: 10%")
4. **Video Player**: Inline HTML5 video with controls
5. **Download Links**: Direct download with file size display
6. **Backward Compatibility**: Falls back to `master` deliverable if no variants

---

## UI Components

### Job Summary Section

```jsx
<JobSection>
  <SectionTitle>Job summary</SectionTitle>
  <MetricGrid>
    <MetricCard>
      <MetricLabel>Job ID</MetricLabel>
      <MetricValue>{job.jobId}</MetricValue>
    </MetricCard>
    <MetricCard>
      <MetricLabel>Profile</MetricLabel>
      <MetricValue>{activeProfile?.label}</MetricValue>
    </MetricCard>
    <MetricCard>
      <MetricLabel>Duration target</MetricLabel>
      <MetricValue>{job.input?.maxDurationSeconds}s</MetricValue>
    </MetricCard>
    <MetricCard>
      <MetricLabel>Pipeline mode</MetricLabel>
      <MetricValue>{job.mode}</MetricValue>
    </MetricCard>
  </MetricGrid>

  {/* Providers */}
  {providers && (
    <ProvidersRow>
      <SectionTitle>Providers</SectionTitle>
      <PillGroup>
        {Object.entries(providers).map(([key, details]) => (
          <ProviderPill key={key}>
            <span style={{ fontWeight: 700 }}>{key}</span>
            <span style={{ opacity: 0.7 }}>{details.mode}</span>
          </ProviderPill>
        ))}
      </PillGroup>
    </ProvidersRow>
  )}
</JobSection>
```

### Scene Intelligence Section

```jsx
<JobSection>
  <SectionTitle>Scene intelligence</SectionTitle>
  
  {/* Metrics */}
  <MetricGrid>
    <MetricCard>
      <MetricLabel>Total runtime analysed</MetricLabel>
      <MetricValue>{analysis.totalDuration}s</MetricValue>
    </MetricCard>
    <MetricCard>
      <MetricLabel>Detected people</MetricLabel>
      <MetricValue>{analysis.metrics?.detectedPeople}</MetricValue>
    </MetricCard>
    <MetricCard>
      <MetricLabel>Detected objects</MetricLabel>
      <MetricValue>{analysis.metrics?.detectedObjects}</MetricValue>
    </MetricCard>
    <MetricCard>
      <MetricLabel>Dominant emotions</MetricLabel>
      <MetricValue>{analysis.dominantEmotions?.join(', ')}</MetricValue>
    </MetricCard>
  </MetricGrid>

  {/* Scene Table */}
  {analysis.scenes?.length ? (
    <ScrollContainer>
      <Table>
        <TableHead>
          <tr>
            <TableHeaderCell>Scene</TableHeaderCell>
            <TableHeaderCell>Window (s)</TableHeaderCell>
            <TableHeaderCell>Emotions</TableHeaderCell>
            <TableHeaderCell>Labels</TableHeaderCell>
          </tr>
        </TableHead>
        <tbody>
          {analysis.scenes.map((scene) => (
            <tr key={scene.sceneId}>
              <TableBodyCell>{scene.sceneId}</TableBodyCell>
              <TableBodyCell>{scene.start}–{scene.end}</TableBodyCell>
              <TableBodyCell>{scene.emotions.join(', ')}</TableBodyCell>
              <TableBodyCell>{scene.labels.join(', ')}</TableBodyCell>
            </tr>
          ))}
        </tbody>
      </Table>
    </ScrollContainer>
  ) : (
    <EmptyState>No scenes detected.</EmptyState>
  )}
</JobSection>
```

### Personalization Ranking Section

```jsx
<JobSection>
  <SectionTitle>Personalization ranking</SectionTitle>
  
  <MetricGrid>
    <MetricCard>
      <MetricLabel>Selected scenes</MetricLabel>
      <MetricValue>{personalization.selectedScenes?.length ?? 0}</MetricValue>
    </MetricCard>
    <MetricCard>
      <MetricLabel>Estimated runtime</MetricLabel>
      <MetricValue>{personalization.estimatedDuration ?? 0}s</MetricValue>
    </MetricCard>
  </MetricGrid>
  
  {/* Top Ranked Scenes */}
  {personalization.rankedScenes?.length && (
    <>
      <SubsectionHeading>Top ranked scenes</SubsectionHeading>
      <SceneList>
        {personalization.rankedScenes.slice(0, 6).map((scene) => (
          <SceneItem key={scene.sceneId}>
            <strong>{scene.sceneId}</strong> — score {scene.score} ({scene.duration}s)
          </SceneItem>
        ))}
      </SceneList>
    </>
  )}
  
  {/* Selected Scenes */}
  {personalization.selectedScenes?.length && (
    <>
      <SubsectionHeading>Selected trailer sequence</SubsectionHeading>
      <SceneList>
        {personalization.selectedScenes.map((scene) => (
          <SceneItem key={scene.sceneId}>
            <strong>{scene.sceneId}</strong> — score {scene.score} ({scene.duration}s)
          </SceneItem>
        ))}
      </SceneList>
    </>
  )}
</JobSection>
```

### Assembly Plan Section

```jsx
<JobSection>
  <SectionTitle>Assembly plan</SectionTitle>
  
  <MetricGrid>
    <MetricCard>
      <MetricLabel>Estimated duration</MetricLabel>
      <MetricValue>{assembly.estimatedDuration}s</MetricValue>
    </MetricCard>
    <MetricCard>
      <MetricLabel>Renditions</MetricLabel>
      <MetricValue>{assembly.renditions?.length ?? 0}</MetricValue>
    </MetricCard>
  </MetricGrid>
  
  {assembly.timeline?.length ? (
    <SceneList>
      {assembly.timeline.map((clip) => (
        <SceneItem key={`${clip.sceneId}-${clip.in}`}>
          {clip.sceneId}: {clip.in}s → {clip.out}s 
          (transition: {clip.transition}, audio cue: {clip.audioCue})
        </SceneItem>
      ))}
    </SceneList>
  ) : (
    <EmptyState>No timeline entries generated.</EmptyState>
  )}
</JobSection>
```

---

## Key Frontend Features

### 1. Drag & Drop Upload

- Native HTML5 drag & drop
- File type validation
- Preview generation with `URL.createObjectURL()`
- Automatic cleanup with `URL.revokeObjectURL()`

### 2. Upload Progress Tracking

- Real-time progress bar (0-100%)
- `axios.onUploadProgress` callback
- Bounded updates (1-99% during upload, 100% on complete)
- Auto-reset after 400ms delay

### 3. Profile-Based UI

- 4 predefined viewer profiles
- Visual selection with active state
- Profile preferences displayed
- Easy switching between profiles

### 4. Multi-Variant Display

- Automatic detection of variant deliverables
- Side-by-side comparison with video players
- Rich metadata (name, description, distribution)
- Individual download links

### 5. Comprehensive Results

- Job summary with metadata
- Provider status indicators
- Scene intelligence table
- Personalization ranking
- Assembly timeline
- Deliverable downloads

### 6. Error Handling

- Validation before submission
- Network error catching
- User-friendly error messages
- Status banner for feedback

---

## Next Document

➡️ **Part 4: Deployment & Operations**  
Covers environment setup, service management, and troubleshooting.

---

*End of Part 3*
# Personalized Trailer System - Architecture & Logic Guide
## Part 4: Deployment & Operations

**Document Version:** 1.0  
**Last Updated:** October 24, 2025  
**System:** MediaGenAI - AI-Powered Personalized Trailer Generation

---

## Table of Contents (Part 4)

1. [Environment Setup](#environment-setup)
2. [Service Configuration](#service-configuration)
3. [Deployment Procedures](#deployment-procedures)
4. [Monitoring & Logging](#monitoring--logging)
5. [Troubleshooting](#troubleshooting)
6. [Performance Optimization](#performance-optimization)
7. [Security Best Practices](#security-best-practices)

---

## Environment Setup

### Prerequisites

#### System Requirements

| Component | Requirement | Purpose |
|-----------|------------|---------|
| **Operating System** | Linux, macOS, or Windows | Backend runtime |
| **Python** | 3.11 or higher | Backend application |
| **FFmpeg** | 6.0 or higher | Video processing |
| **FFprobe** | 6.0 or higher | Media inspection |
| **Node.js** | 18+ (for frontend dev) | Frontend build |
| **Disk Space** | 20GB+ free | Video processing temp files |
| **RAM** | 8GB+ recommended | Video processing |

#### Python Dependencies

```bash
# Core framework
Flask==3.0+
flask-cors==4.0+

# AWS SDK (optional, for production mode)
boto3==1.28+

# Utilities
python-dotenv==1.0+
```

Install via:
```bash
cd personalizedTrailer
pip install -r requirements.txt
```

#### FFmpeg Installation

**macOS (Homebrew):**
```bash
brew install ffmpeg
```

**Ubuntu/Debian:**
```bash
sudo apt update
sudo apt install ffmpeg
```

**Windows (Chocolatey):**
```bash
choco install ffmpeg
```

**Verify Installation:**
```bash
ffmpeg -version
ffprobe -version
```

---

## Service Configuration

### Environment Variables

Create `.env` file in `personalizedTrailer/` directory:

```bash
# ==========================================
# Personalized Trailer Service Configuration
# ==========================================

# ─────────────────────────────────────────
# Service Settings
# ─────────────────────────────────────────
FLASK_HOST=0.0.0.0
FLASK_PORT=5007
FLASK_DEBUG=False

# ─────────────────────────────────────────
# Pipeline Mode
# ─────────────────────────────────────────
# Options: "mock" (default, no AWS) or "aws" (production)
PIPELINE_MODE=mock

# ─────────────────────────────────────────
# CORS Configuration
# ─────────────────────────────────────────
# Comma-separated list of allowed origins
CORS_ORIGINS=http://localhost:3000,http://localhost:5000

# ─────────────────────────────────────────
# File Storage
# ─────────────────────────────────────────
# Base directory for uploads/outputs (relative to service root)
UPLOAD_DIR=uploads
OUTPUT_DIR=outputs

# Maximum upload file size (bytes) - 2GB default
MAX_UPLOAD_SIZE=2147483648

# ─────────────────────────────────────────
# Processing Limits
# ─────────────────────────────────────────
# Maximum video duration to process (seconds)
MAX_VIDEO_DURATION=7200

# Maximum trailer duration (seconds)
MAX_TRAILER_DURATION=90

# ─────────────────────────────────────────
# AWS Configuration (required for PIPELINE_MODE=aws)
# ─────────────────────────────────────────
AWS_REGION=us-east-1
AWS_ACCESS_KEY_ID=your_access_key_here
AWS_SECRET_ACCESS_KEY=your_secret_key_here

# S3 Bucket for video storage
AWS_S3_BUCKET=your-trailer-bucket

# AWS Services
AWS_REKOGNITION_ENABLED=true
AWS_PERSONALIZE_ENABLED=false
AWS_MEDIACONVERT_ENABLED=false

# ─────────────────────────────────────────
# FFmpeg Configuration
# ─────────────────────────────────────────
# Path to FFmpeg binary (auto-detected if not set)
FFMPEG_PATH=/usr/local/bin/ffmpeg
FFPROBE_PATH=/usr/local/bin/ffprobe

# FFmpeg encoding settings
FFMPEG_VIDEO_CODEC=libx264
FFMPEG_AUDIO_CODEC=aac
FFMPEG_PRESET=medium
FFMPEG_CRF=23

# ─────────────────────────────────────────
# Logging
# ─────────────────────────────────────────
LOG_LEVEL=INFO
LOG_FILE=personalized_trailer.log
```

### Configuration Loading

The service automatically loads configuration in this order:

1. **Default values** (hardcoded in service)
2. **Environment variables** (`.env` file)
3. **Runtime overrides** (command-line arguments)

### Profile Presets

Profiles are defined in `personalized_trailer_service.py`:

```python
DEFAULT_PROFILES = [
    {
        'id': 'action_enthusiast',
        'label': 'Action Enthusiast',
        'summary': 'Focuses on high-energy scenes with explosions, chases, and fight sequences.',
        'preferredEmotions': ['excited', 'intense', 'tense'],
        'preferredTags': ['action', 'explosion', 'chase', 'fight', 'combat', 'car', 'weapon'],
        'emotionWeight': 1.5,
        'tagWeight': 2.0,
    },
    {
        'id': 'family_viewer',
        'label': 'Family Viewer',
        'summary': 'Highlights heartwarming moments and family-friendly content.',
        'preferredEmotions': ['happy', 'calm', 'content'],
        'preferredTags': ['family', 'child', 'animal', 'nature', 'celebration', 'friendship'],
        'emotionWeight': 2.0,
        'tagWeight': 1.5,
    },
    {
        'id': 'thriller_buff',
        'label': 'Thriller Buff',
        'summary': 'Emphasizes suspenseful and mysterious scenes.',
        'preferredEmotions': ['tense', 'surprised', 'confused'],
        'preferredTags': ['dark', 'shadow', 'mystery', 'suspense', 'investigation', 'secret'],
        'emotionWeight': 2.5,
        'tagWeight': 1.0,
    },
    {
        'id': 'romance_devotee',
        'label': 'Romance Devotee',
        'summary': 'Showcases romantic interactions and emotional connections.',
        'preferredEmotions': ['happy', 'content', 'love'],
        'preferredTags': ['couple', 'kiss', 'romance', 'wedding', 'date', 'embrace', 'flower'],
        'emotionWeight': 2.0,
        'tagWeight': 2.0,
    },
]
```

**To add custom profiles:**
1. Add new profile object to `DEFAULT_PROFILES` list
2. Include unique `id`, descriptive `label`, and `summary`
3. Define `preferredEmotions` and `preferredTags` arrays
4. Set `emotionWeight` and `tagWeight` (default: 1.0)
5. Restart service

---

## Deployment Procedures

### Local Development

#### Start Backend Service

```bash
cd personalizedTrailer
python app.py
```

Expected output:
```
 * Serving Flask app 'personalized_trailer_service'
 * Debug mode: off
WARNING: This is a development server. Do not use it in a production deployment.
 * Running on http://0.0.0.0:5007
```

#### Start Frontend (Development)

```bash
cd frontend
npm install
npm start
```

Frontend will launch at `http://localhost:3000`

### Production Deployment

#### Using systemd (Linux)

Create service file `/etc/systemd/system/personalized-trailer.service`:

```ini
[Unit]
Description=Personalized Trailer Generation Service
After=network.target

[Service]
Type=simple
User=www-data
WorkingDirectory=/opt/mediaGenAI/personalizedTrailer
Environment="PATH=/opt/mediaGenAI/venv/bin"
ExecStart=/opt/mediaGenAI/venv/bin/python app.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

**Start service:**
```bash
sudo systemctl enable personalized-trailer
sudo systemctl start personalized-trailer
sudo systemctl status personalized-trailer
```

#### Using Gunicorn (WSGI Server)

```bash
pip install gunicorn

gunicorn \
  --bind 0.0.0.0:5007 \
  --workers 4 \
  --timeout 300 \
  --access-logfile - \
  --error-logfile - \
  "personalized_trailer_service:create_app()"
```

**systemd service with Gunicorn:**

```ini
[Unit]
Description=Personalized Trailer Service (Gunicorn)
After=network.target

[Service]
Type=notify
User=www-data
WorkingDirectory=/opt/mediaGenAI/personalizedTrailer
Environment="PATH=/opt/mediaGenAI/venv/bin"
ExecStart=/opt/mediaGenAI/venv/bin/gunicorn \
  --bind 0.0.0.0:5007 \
  --workers 4 \
  --timeout 300 \
  "personalized_trailer_service:create_app()"
ExecReload=/bin/kill -s HUP $MAINPID
KillMode=mixed
TimeoutStopSec=5
PrivateTmp=true

[Install]
WantedBy=multi-user.target
```

#### Reverse Proxy (Nginx)

```nginx
server {
    listen 80;
    server_name trailers.example.com;

    # Frontend static files
    location / {
        root /var/www/mediagenai/frontend/build;
        try_files $uri /index.html;
    }

    # Backend API proxy
    location /api/trailer/ {
        proxy_pass http://127.0.0.1:5007/;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_cache_bypass $http_upgrade;
        
        # Timeouts for large uploads
        proxy_connect_timeout 300s;
        proxy_send_timeout 300s;
        proxy_read_timeout 300s;
        
        # Large file uploads
        client_max_body_size 2G;
    }
}
```

#### Docker Deployment

**Dockerfile:**

```dockerfile
FROM python:3.11-slim

# Install FFmpeg
RUN apt-get update && apt-get install -y \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements and install
COPY personalizedTrailer/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY personalizedTrailer/ .

# Create directories
RUN mkdir -p uploads outputs

# Expose port
EXPOSE 5007

# Run service
CMD ["python", "app.py"]
```

**docker-compose.yml:**

```yaml
version: '3.8'

services:
  personalized-trailer:
    build: .
    ports:
      - "5007:5007"
    volumes:
      - ./uploads:/app/uploads
      - ./outputs:/app/outputs
    environment:
      - FLASK_HOST=0.0.0.0
      - FLASK_PORT=5007
      - PIPELINE_MODE=mock
      - CORS_ORIGINS=http://localhost:3000
    restart: unless-stopped
```

**Run with Docker Compose:**
```bash
docker-compose up -d
docker-compose logs -f personalized-trailer
```

---

## Monitoring & Logging

### Log Levels

```python
# In personalized_trailer_service.py
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    handlers=[
        logging.FileHandler('personalized_trailer.log'),
        logging.StreamHandler()
    ]
)
```

### Log Categories

| Level | Usage |
|-------|-------|
| **DEBUG** | Detailed processing steps, scene scoring |
| **INFO** | Request start/end, pipeline stages |
| **WARNING** | Fallback to mock mode, missing files |
| **ERROR** | Processing failures, API errors |

### Key Log Messages

```
INFO: Received /generate request for profile: action_enthusiast
INFO: Starting pipeline for job: job_abc123
INFO: [Stage 1/7] Upload complete: video.mp4 (1.2GB)
INFO: [Stage 2/7] Analysis: Detected 42 scenes
INFO: [Stage 3/7] Personalization: Selected 8 scenes
INFO: [Stage 4/7] Assembly: Generated 4 variants
INFO: [Stage 5/7] Rendering: Encoding variant_opening_act
INFO: [Stage 6/7] Deliverables: Created 4 video files
INFO: [Stage 7/7] Completion: Job successful (total: 45.2s)
```

### Health Check Endpoint

```bash
curl http://localhost:5007/health
```

Response:
```json
{
  "status": "ok",
  "version": "1.0.0",
  "mode": "mock",
  "uptime": 3600
}
```

### Metrics Collection

Monitor these key metrics:

1. **Request Volume**: Requests per hour
2. **Processing Time**: Average job duration (21-95s mock, 50-210s AWS)
3. **Success Rate**: Successful jobs / total jobs
4. **Queue Depth**: Pending jobs (if using queue)
5. **Disk Usage**: Upload/output directory size

---

## Troubleshooting

### Common Issues

#### 1. FFmpeg Not Found

**Symptom:**
```
ERROR: FFmpeg not found in PATH
```

**Solution:**
```bash
# Verify installation
which ffmpeg

# Set explicit path in .env
FFMPEG_PATH=/usr/local/bin/ffmpeg
FFPROBE_PATH=/usr/local/bin/ffprobe
```

#### 2. Upload Fails with 413 Error

**Symptom:**
```
413 Request Entity Too Large
```

**Solution:**

Update Nginx config:
```nginx
client_max_body_size 2G;
```

Update Flask config:
```python
app.config['MAX_CONTENT_LENGTH'] = 2 * 1024 * 1024 * 1024  # 2GB
```

#### 3. CORS Errors

**Symptom:**
```
Access to fetch at 'http://localhost:5007/generate' from origin 'http://localhost:3000' 
has been blocked by CORS policy
```

**Solution:**

Update `.env`:
```bash
CORS_ORIGINS=http://localhost:3000,http://localhost:5000
```

Or set wildcard (development only):
```python
CORS(app, origins="*")
```

#### 4. Video Processing Timeout

**Symptom:**
```
ERROR: FFmpeg process exceeded timeout
```

**Solution:**

1. Reduce input video size/duration
2. Increase timeout in Gunicorn:
```bash
gunicorn --timeout 600
```
3. Optimize FFmpeg settings:
```bash
FFMPEG_PRESET=ultrafast  # Faster encoding
FFMPEG_CRF=28  # Lower quality, faster
```

#### 5. AWS Credentials Error (Production Mode)

**Symptom:**
```
ERROR: Unable to locate credentials
```

**Solution:**

Set AWS credentials:
```bash
# Via environment variables
export AWS_ACCESS_KEY_ID=your_key
export AWS_SECRET_ACCESS_KEY=your_secret
export AWS_REGION=us-east-1

# Or via AWS CLI
aws configure
```

#### 6. Disk Space Exhausted

**Symptom:**
```
ERROR: No space left on device
```

**Solution:**

1. Clean old uploads:
```bash
find uploads/ -type f -mtime +7 -delete
```

2. Clean outputs:
```bash
find outputs/ -type f -mtime +7 -delete
```

3. Add cron job for automatic cleanup:
```bash
# crontab -e
0 2 * * * find /opt/mediaGenAI/personalizedTrailer/uploads -type f -mtime +7 -delete
0 2 * * * find /opt/mediaGenAI/personalizedTrailer/outputs -type f -mtime +7 -delete
```

---

## Performance Optimization

### Processing Time Optimization

#### 1. FFmpeg Preset Tuning

```bash
# Faster encoding (lower quality)
FFMPEG_PRESET=ultrafast  # ~2x faster
FFMPEG_CRF=28  # Reduce quality

# Balanced (default)
FFMPEG_PRESET=medium
FFMPEG_CRF=23

# Slower encoding (higher quality)
FFMPEG_PRESET=slow
FFMPEG_CRF=18
```

#### 2. Scene Detection Optimization

Reduce frame extraction rate:

```python
# In _aws_rekognition_analysis()
frame_interval = 2.0  # Extract every 2 seconds (default: 1.0)
```

#### 3. Parallel Processing

Use multi-threading for variant rendering:

```python
from concurrent.futures import ThreadPoolExecutor

with ThreadPoolExecutor(max_workers=4) as executor:
    futures = [
        executor.submit(_render_variant, variant)
        for variant in variants
    ]
    results = [f.result() for f in futures]
```

### Memory Optimization

#### 1. Stream Processing

Process large videos in chunks:

```python
# Use subprocess.Popen with PIPE for streaming
proc = subprocess.Popen(
    ffmpeg_cmd,
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE,
    bufsize=1024*1024  # 1MB buffer
)
```

#### 2. Cleanup Temp Files

```python
import tempfile
import shutil

# Use context manager for automatic cleanup
with tempfile.TemporaryDirectory() as tmpdir:
    # Process files in tmpdir
    pass  # Automatically deleted
```

### Network Optimization

#### 1. CDN for Deliverables

Serve video files via CDN:

```python
# S3 + CloudFront
deliverable_url = f"https://cdn.example.com/{job_id}/{filename}"
```

#### 2. Resume Uploads

Support multipart uploads:

```python
# Use tus protocol or chunked uploads
# https://tus.io/
```

---

## Security Best Practices

### 1. Input Validation

```python
def validate_upload(file):
    # File type whitelist
    ALLOWED_EXTENSIONS = {'mp4', 'mov', 'mkv', 'avi', 'webm'}
    ext = file.filename.split('.')[-1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise ValueError('Invalid file type')
    
    # File size limit
    MAX_SIZE = 2 * 1024 * 1024 * 1024  # 2GB
    file.seek(0, os.SEEK_END)
    size = file.tell()
    file.seek(0)
    if size > MAX_SIZE:
        raise ValueError('File too large')
    
    # Magic number validation
    magic = file.read(12)
    file.seek(0)
    if not magic.startswith(b'\x00\x00\x00'):  # MP4/MOV signature
        raise ValueError('Invalid video file')
```

### 2. Path Sanitization

```python
import os
from werkzeug.utils import secure_filename

def safe_path(filename):
    # Remove path traversal attempts
    name = secure_filename(filename)
    
    # Generate unique filename
    unique_name = f"{uuid.uuid4()}_{name}"
    
    # Ensure within allowed directory
    full_path = os.path.abspath(os.path.join(UPLOAD_DIR, unique_name))
    if not full_path.startswith(os.path.abspath(UPLOAD_DIR)):
        raise ValueError('Path traversal detected')
    
    return full_path
```

### 3. Rate Limiting

```python
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

limiter = Limiter(
    app,
    key_func=get_remote_address,
    default_limits=["100 per hour"]
)

@app.route('/generate', methods=['POST'])
@limiter.limit("10 per hour")
def generate():
    # ... processing ...
```

### 4. Authentication (Production)

```python
from functools import wraps
from flask import request, abort

def require_api_key(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        api_key = request.headers.get('X-API-Key')
        if not api_key or api_key not in VALID_API_KEYS:
            abort(401)
        return f(*args, **kwargs)
    return decorated

@app.route('/generate', methods=['POST'])
@require_api_key
def generate():
    # ... processing ...
```

### 5. AWS IAM Policy (Production)

Minimum required permissions:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "s3:PutObject",
        "s3:GetObject",
        "s3:DeleteObject"
      ],
      "Resource": "arn:aws:s3:::your-trailer-bucket/*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "rekognition:DetectLabels",
        "rekognition:DetectFaces"
      ],
      "Resource": "*"
    }
  ]
}
```

---

## Backup & Recovery

### Database Backup (if using DB)

```bash
# Backup job metadata
pg_dump mediagenai > backup_$(date +%Y%m%d).sql
```

### File Backup

```bash
# Backup uploads and outputs
tar -czf backup_$(date +%Y%m%d).tar.gz uploads/ outputs/

# Sync to S3
aws s3 sync uploads/ s3://backup-bucket/uploads/
aws s3 sync outputs/ s3://backup-bucket/outputs/
```

### Disaster Recovery

1. **Data Loss**: Restore from S3 backup
2. **Service Failure**: Restart from systemd
3. **Corruption**: Rebuild outputs from uploaded source videos

---

## Appendix: Quick Reference

### Service Endpoints

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/health` | GET | Health check |
| `/profiles` | GET | List viewer profiles |
| `/options` | GET | Get configuration options |
| `/generate` | POST | Generate personalized trailer |
| `/job/<job_id>` | GET | Get job status |
| `/download/<job_id>/<file>` | GET | Download deliverable |
| `/clear` | POST | Clear temp files |

### Default Ports

| Service | Port |
|---------|------|
| Personalized Trailer API | 5007 |
| Frontend (dev) | 3000 |

### File Locations

| Type | Path |
|------|------|
| Uploads | `personalizedTrailer/uploads/` |
| Outputs | `personalizedTrailer/outputs/` |
| Logs | `personalizedTrailer/personalized_trailer.log` |
| Config | `personalizedTrailer/.env` |

### Command Reference

```bash
# Start service
python app.py

# Start with Gunicorn
gunicorn -w 4 -b 0.0.0.0:5007 "personalized_trailer_service:create_app()"

# Check logs
tail -f personalized_trailer.log

# Test health endpoint
curl http://localhost:5007/health

# Generate trailer (example)
curl -X POST http://localhost:5007/generate \
  -F "video=@input.mp4" \
  -F "profile_id=action_enthusiast" \
  -F "max_duration=60"
```

---

## Documentation Complete

This concludes the 4-part Personalized Trailer System Architecture & Logic Guide:

- **Part 1:** System Overview & Architecture
- **Part 2:** API Endpoints & Backend Processing
- **Part 3:** Frontend Architecture & Components
- **Part 4:** Deployment & Operations *(this document)*

For questions or support, contact the MediaGenAI development team.

---

*End of Part 4 — Documentation Series Complete*