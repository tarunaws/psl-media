# Content Moderation Service - Part 1 of 4
## Executive Summary, Architecture Overview & AWS Integration

**Document Version:** 1.0  
**Last Updated:** October 22, 2025  
**Service Port:** 5006  
**Part:** 1/4 - Foundation & AWS Integration

---

## Table of Contents - Part 1

1. [Executive Summary](#1-executive-summary)
2. [Service Overview](#2-service-overview)
3. [Architecture Overview](#3-architecture-overview)
4. [AWS Integration Deep Dive](#4-aws-integration-deep-dive)
5. [Configuration Management](#5-configuration-management)

---

## 1. Executive Summary

### 1.1 Purpose

The **Content Moderation Service** is a critical safety and compliance component of the MediaGenAI platform that automatically detects and flags potentially inappropriate, harmful, or sensitive content in video files. This service empowers content creators, moderators, and compliance teams to:

- **Automate Content Review:** Replace manual frame-by-frame review with AI-powered detection
- **Ensure Platform Safety:** Identify policy violations before content goes live
- **Support Compliance:** Meet regulatory requirements for content platforms
- **Accelerate Moderation Workflows:** Reduce review time from hours to minutes
- **Provide Audit Trails:** Generate timestamped reports for compliance documentation

### 1.2 Business Value

**For Content Platforms:**
- Reduce moderation costs by 70-85% through automation
- Scale content review to match platform growth
- Maintain brand safety and advertiser confidence
- Meet regulatory compliance (COPPA, GDPR, local laws)

**For Content Creators:**
- Pre-upload validation to avoid rejection
- Self-service content analysis before submission
- Understand platform policy boundaries
- Faster approval cycles

**For Compliance Teams:**
- Comprehensive audit logs with exact timestamps
- Category-based filtering for focused review
- Confidence-based prioritization
- JSON export for compliance systems

### 1.3 Key Capabilities

| Feature | Description | Business Impact |
|---------|-------------|-----------------|
| **11 Moderation Categories** | Explicit Nudity, Suggestive, Violence, Visually Disturbing, Rude Gestures, Tobacco, Drugs, Alcohol, Hate Symbols, Weapons, Gambling | Comprehensive policy enforcement |
| **Configurable Confidence** | Adjustable 0-100% threshold | Balance precision vs. recall |
| **Timestamp Precision** | Millisecond-level detection (HH:MM:SS.mmm) | Surgical content editing |
| **Real-time Processing** | Up to 5-minute analysis timeout | Fast feedback for creators |
| **2GB File Support** | MP4, MOV, MKV, M4V, AVI, WEBM formats | Production-grade videos |
| **Category Filtering** | Select specific violation types | Focused compliance review |
| **JSON Reports** | Persistent storage with job IDs | Integration with workflows |
| **Drag-and-Drop Upload** | Intuitive browser-based interface | No technical expertise required |

### 1.4 Technical Highlights

- **AWS Rekognition Video:** Industry-leading computer vision ML models
- **Synchronous Polling Architecture:** Real-time progress updates
- **S3 Integration:** Scalable video storage and access
- **Flask Backend:** Lightweight, production-ready API
- **React Frontend:** Modern, responsive user experience
- **CORS-Enabled:** Cross-origin integration support

### 1.5 Integration Points

```
┌─────────────────────────────────────────────────────────────┐
│                    MediaGenAI Platform                      │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  Frontend (React) ──────► Content Moderation Service       │
│                                   │                         │
│                                   ▼                         │
│                          AWS S3 (Video Storage)             │
│                                   │                         │
│                                   ▼                         │
│                     AWS Rekognition (AI Analysis)           │
│                                   │                         │
│                                   ▼                         │
│                          Moderation Reports (JSON)          │
│                                   │                         │
│                                   ▼                         │
│              Compliance Systems / Content Workflow          │
└─────────────────────────────────────────────────────────────┘
```

### 1.6 Use Cases

**1. Pre-Publication Review**
- Creators upload videos before publishing
- Service flags potential policy violations
- Creators edit content or appeal decisions
- Reduces platform liability and takedown requests

**2. Batch Compliance Audits**
- Compliance team reviews existing content library
- Filter by specific categories (e.g., only Alcohol/Tobacco)
- Generate reports for regulatory submissions
- Identify content requiring age restrictions

**3. User-Generated Content (UGC) Platforms**
- Automated screening of all uploads
- High-confidence violations auto-rejected
- Medium-confidence flagged for human review
- Low-confidence approved automatically

**4. Advertiser Brand Safety**
- Analyze content before ad placement
- Ensure ads don't appear near inappropriate content
- Category-based ad exclusions (e.g., no ads on Alcohol content)
- Protect advertiser brand reputation

**5. Age Restriction Classification**
- Detect mature content automatically
- Apply age gates based on violation types
- Comply with child safety regulations
- Generate parental guidance labels

---

## 2. Service Overview

### 2.1 Service Identity

```yaml
Service Name: Content Moderation Service
Service ID: contentModeration
Port: 5006
Protocol: HTTP REST
Technology Stack:
  Backend: Python 3.11+, Flask 3.0.0
  Frontend: React 18.x
  Cloud: AWS (Rekognition, S3)
  Storage: Local JSON files
```

### 2.2 Repository Structure

```
contentModeration/
├── app.py                          # Service launcher (11 lines)
├── content_moderation_service.py   # Main Flask application (457 lines)
├── requirements.txt                # Python dependencies
├── README.md                       # Quick start guide
├── __pycache__/                    # Python bytecode cache
├── uploads/                        # Temporary video storage (auto-cleaned)
└── reports/                        # Persistent JSON moderation reports
    ├── <job_id_1>.json
    ├── <job_id_2>.json
    └── ...

frontend/src/
└── ContentModeration.js            # React UI component (644 lines)
```

### 2.3 Workflow Overview

```
┌──────────────────────────────────────────────────────────────────┐
│                    CONTENT MODERATION WORKFLOW                    │
└──────────────────────────────────────────────────────────────────┘

 1. USER UPLOAD
    │
    ├─► User selects video file (MP4/MOV/etc., max 2GB)
    ├─► Configures moderation categories (11 options)
    ├─► Sets confidence threshold (0-100%, default 75%)
    └─► Clicks "Analyse video"
    │
    ▼
 2. FRONTEND VALIDATION
    │
    ├─► Validate file size (<2GB)
    ├─► Validate file type (allowed extensions)
    ├─► Generate video preview
    └─► Display upload progress
    │
    ▼
 3. BACKEND PROCESSING
    │
    ├─► Receive multipart/form-data POST
    ├─► Secure filename sanitization
    ├─► Save to uploads/ directory
    └─► Validate file integrity
    │
    ▼
 4. AWS S3 UPLOAD
    │
    ├─► Generate unique S3 key (prefix + timestamp + filename)
    ├─► Upload video to S3 bucket
    ├─► Verify upload success
    └─► Store S3 object metadata
    │
    ▼
 5. AWS REKOGNITION JOB START
    │
    ├─► Call StartContentModeration API
    ├─► Provide S3 bucket/key reference
    ├─► Apply min confidence threshold
    └─► Receive JobId from AWS
    │
    ▼
 6. SYNCHRONOUS POLLING
    │
    ├─► Poll GetContentModeration every 2 seconds
    ├─► Check job status: IN_PROGRESS → SUCCEEDED/FAILED
    ├─► Handle pagination (NextToken for large results)
    ├─► Maximum 5-minute timeout (150 polls)
    └─► Aggregate all moderation labels
    │
    ▼
 7. RESULTS PROCESSING
    │
    ├─► Filter by selected categories
    ├─► Apply confidence threshold
    ├─► Format timestamps (ms → HH:MM:SS.mmm)
    ├─► Aggregate category counts
    └─► Generate summary statistics
    │
    ▼
 8. REPORT GENERATION
    │
    ├─► Structure JSON report with:
    │   - Job metadata (ID, duration, S3 key)
    │   - Moderation events (timestamp, category, label, confidence)
    │   - Summary (total findings, category breakdown)
    │   - Request parameters (categories, min confidence)
    ├─► Save to reports/<job_id>.json
    └─► Return report to frontend
    │
    ▼
 9. FRONTEND DISPLAY
    │
    ├─► Summary Card:
    │   - Job ID, analysis time, total findings
    │   - Category breakdown counts
    │   - S3 object key reference
    │   - Download JSON link
    │
    └─► Timeline Table:
        - Sortable by timecode
        - Category/label/confidence columns
        - Filterable results
        - Empty state handling
    │
    ▼
10. EXPORT & INTEGRATION
    │
    ├─► Download JSON report via /result/<job_id>
    ├─► Import into compliance systems
    ├─► Integrate with video editing tools
    └─► Archive for audit trails
```

### 2.4 Data Flow Diagram

```
┌─────────────┐
│   Browser   │
│  (React UI) │
└──────┬──────┘
       │ 1. POST /moderate
       │    - video file (multipart)
       │    - categories (comma-separated)
       │    - min_confidence (0-100)
       │
       ▼
┌─────────────────────────────────────┐
│  Content Moderation Service (Flask) │
│  Port 5006                          │
├─────────────────────────────────────┤
│  2. Save to uploads/                │
│  3. Upload to S3                    │
│  4. Start Rekognition job           │
│  5. Poll for results (2s interval)  │
│  6. Filter & format results         │
│  7. Save to reports/<job_id>.json   │
│  8. Return JSON response            │
└──────┬──────────────────────────────┘
       │
       ├─► AWS S3
       │   └─► s3://<bucket>/<prefix>/<timestamp>_<filename>
       │
       ├─► AWS Rekognition
       │   ├─► StartContentModeration(S3Object, MinConfidence)
       │   │   Returns: JobId
       │   │
       │   └─► GetContentModeration(JobId, NextToken)
       │       Returns: JobStatus, ModerationLabels[], NextToken
       │
       └─► Local Filesystem
           └─► reports/<job_id>.json
               {
                 "jobId": "abc123...",
                 "video": { "objectKey": "...", "bucket": "..." },
                 "events": [
                   {
                     "timestamp": { "milliseconds": 1234, "seconds": 1.234, "timecode": "00:00:01.234" },
                     "category": "Explicit Nudity",
                     "label": "Graphic Male Nudity",
                     "confidence": 98.5
                   },
                   ...
                 ],
                 "summary": {
                   "totalFindings": 42,
                   "categories": { "Explicit Nudity": 12, "Violence": 30 }
                 },
                 "requestMeta": {
                   "selectedCategories": ["Explicit Nudity", "Violence"],
                   "minConfidence": 75
                 },
                 "metadata": {
                   "analysisDurationSeconds": 18
                 }
               }
```

### 2.5 API Endpoints

```python
# 1. Health Check
GET /health
Response: {
  "status": "healthy",
  "rekognition": true,
  "s3": true,
  "bucket": "<CONTENT_MODERATION_BUCKET>"
}

# 2. Available Moderation Categories
GET /moderation-options
Response: {
  "categories": [
    {"key": "Explicit Nudity", "label": "Explicit Nudity"},
    {"key": "Suggestive", "label": "Suggestive"},
    {"key": "Violence", "label": "Violence"},
    {"key": "Visually Disturbing", "label": "Visually Disturbing"},
    {"key": "Rude Gestures", "label": "Rude Gestures"},
    {"key": "Drugs", "label": "Drugs"},
    {"key": "Tobacco", "label": "Tobacco"},
    {"key": "Alcohol", "label": "Alcohol"},
    {"key": "Gambling", "label": "Gambling"},
    {"key": "Hate Symbols", "label": "Hate Symbols"},
    {"key": "Weapons", "label": "Weapons"}
  ]
}

# 3. Moderate Video
POST /moderate
Content-Type: multipart/form-data
Body:
  - video: <file> (required)
  - categories: "Explicit Nudity,Violence" (optional, comma-separated)
  - min_confidence: 80 (optional, 0-100)

Response: {
  "jobId": "abc123def456...",
  "video": {
    "objectKey": "moderation/20251022_143022_sample.mp4",
    "bucket": "my-content-bucket"
  },
  "events": [
    {
      "timestamp": {
        "milliseconds": 5234,
        "seconds": 5.234,
        "timecode": "00:00:05.234"
      },
      "category": "Violence",
      "label": "Graphic Violence",
      "confidence": 95.3
    },
    ...
  ],
  "summary": {
    "totalFindings": 18,
    "categories": {
      "Violence": 12,
      "Weapons": 6
    }
  },
  "requestMeta": {
    "selectedCategories": ["Explicit Nudity", "Violence"],
    "minConfidence": 80
  },
  "metadata": {
    "analysisDurationSeconds": 23
  }
}

# 4. Retrieve Saved Report
GET /result/<job_id>
Response: <same structure as POST /moderate response>
```

---

## 3. Architecture Overview

### 3.1 System Architecture

```
┌───────────────────────────────────────────────────────────────────────┐
│                         PRESENTATION LAYER                            │
├───────────────────────────────────────────────────────────────────────┤
│                                                                       │
│  ┌─────────────────────────────────────────────────────────────┐    │
│  │              React Frontend (ContentModeration.js)          │    │
│  ├─────────────────────────────────────────────────────────────┤    │
│  │  • Styled Components (30+ UI elements)                      │    │
│  │  • State Management (useState hooks)                        │    │
│  │  • File Upload (drag-and-drop + file picker)                │    │
│  │  • Category Selection (checkbox grid)                       │    │
│  │  • Confidence Slider (0-100%)                               │    │
│  │  • Upload Progress Tracking (axios onUploadProgress)        │    │
│  │  • Results Display (Summary Card + Timeline Table)          │    │
│  │  • JSON Export Download                                     │    │
│  └─────────────────────────────────────────────────────────────┘    │
│                                 │                                     │
│                                 │ HTTP POST /moderate                 │
│                                 │ (multipart/form-data)               │
└─────────────────────────────────┼─────────────────────────────────────┘
                                  │
                                  ▼
┌───────────────────────────────────────────────────────────────────────┐
│                         APPLICATION LAYER                             │
├───────────────────────────────────────────────────────────────────────┤
│                                                                       │
│  ┌─────────────────────────────────────────────────────────────┐    │
│  │       Flask Backend (content_moderation_service.py)         │    │
│  ├─────────────────────────────────────────────────────────────┤    │
│  │                                                             │    │
│  │  REQUEST HANDLING                                           │    │
│  │  ├─► CORS middleware (configurable origins)                │    │
│  │  ├─► Multipart file parsing (werkzeug)                     │    │
│  │  ├─► File validation (size, extension)                     │    │
│  │  └─► Secure filename sanitization                          │    │
│  │                                                             │    │
│  │  FILE MANAGEMENT                                            │    │
│  │  ├─► Save to uploads/ (temporary storage)                  │    │
│  │  ├─► Generate unique S3 key (timestamp prefix)             │    │
│  │  └─► Upload to S3 bucket                                   │    │
│  │                                                             │    │
│  │  AWS ORCHESTRATION                                          │    │
│  │  ├─► StartContentModeration (initiate job)                 │    │
│  │  ├─► Synchronous polling loop (2s interval)                │    │
│  │  ├─► GetContentModeration (fetch results)                  │    │
│  │  ├─► Pagination handling (NextToken)                       │    │
│  │  └─► Timeout management (5-minute max)                     │    │
│  │                                                             │    │
│  │  RESULTS PROCESSING                                         │    │
│  │  ├─► Category filtering (selected categories only)         │    │
│  │  ├─► Confidence threshold application                      │    │
│  │  ├─► Timestamp formatting (ms → HH:MM:SS.mmm)              │    │
│  │  ├─► Event aggregation (category counts)                   │    │
│  │  └─► Summary statistics generation                         │    │
│  │                                                             │    │
│  │  PERSISTENCE                                                │    │
│  │  ├─► Save report to reports/<job_id>.json                  │    │
│  │  └─► Return JSON response to frontend                      │    │
│  │                                                             │    │
│  └─────────────────────────────────────────────────────────────┘    │
│                                 │                                     │
│                     ┌───────────┼───────────┐                         │
│                     │           │           │                         │
└─────────────────────┼───────────┼───────────┼─────────────────────────┘
                      │           │           │
                      ▼           ▼           ▼
┌───────────────────────────────────────────────────────────────────────┐
│                         INTEGRATION LAYER                             │
├───────────────────────────────────────────────────────────────────────┤
│                                                                       │
│  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐   │
│  │    AWS S3        │  │ AWS Rekognition  │  │ Local Filesystem │   │
│  ├──────────────────┤  ├──────────────────┤  ├──────────────────┤   │
│  │ • Video storage  │  │ • StartContent   │  │ • uploads/       │   │
│  │ • Bucket config  │  │   Moderation     │  │ • reports/       │   │
│  │ • Object keys    │  │ • GetContent     │  │ • JSON files     │   │
│  │ • Access control │  │   Moderation     │  │                  │   │
│  │                  │  │ • ML models      │  │                  │   │
│  │                  │  │ • Job status     │  │                  │   │
│  └──────────────────┘  └──────────────────┘  └──────────────────┘   │
│                                                                       │
└───────────────────────────────────────────────────────────────────────┘
```

### 3.2 Synchronous Polling Architecture

**Unlike Scene Summarization (async with SNS callbacks), Content Moderation uses synchronous polling:**

```python
# SYNCHRONOUS POLLING WORKFLOW

def _poll_moderation_results(job_id, min_confidence, selected_categories):
    """
    Poll AWS Rekognition GetContentModeration API until job completes.
    
    Key Characteristics:
    - Blocks HTTP request until job finishes
    - 2-second polling interval
    - 5-minute maximum timeout (150 polls)
    - Handles pagination with NextToken
    - Returns complete results in single response
    """
    
    start_time = time.time()
    all_labels = []
    
    while True:
        elapsed = time.time() - start_time
        
        # TIMEOUT CHECK
        if elapsed > MAX_WAIT_SECONDS:  # 300 seconds = 5 minutes
            raise TimeoutError(f"Moderation job {job_id} exceeded {MAX_WAIT_SECONDS}s timeout")
        
        # POLL AWS API
        response = rekognition_client.get_content_moderation(JobId=job_id)
        status = response.get('JobStatus')
        
        # CHECK STATUS
        if status == 'SUCCEEDED':
            # Collect results from this page
            labels = response.get('ModerationLabels', [])
            all_labels.extend(labels)
            
            # PAGINATION: Check for more results
            next_token = response.get('NextToken')
            if next_token:
                # More results available, fetch next page
                response = rekognition_client.get_content_moderation(
                    JobId=job_id,
                    NextToken=next_token
                )
                all_labels.extend(response.get('ModerationLabels', []))
            
            # Job complete, return all results
            return {
                'status': 'SUCCEEDED',
                'labels': all_labels,
                'duration': elapsed
            }
        
        elif status == 'FAILED':
            # Job failed, return error
            return {
                'status': 'FAILED',
                'error': response.get('StatusMessage', 'Unknown error')
            }
        
        elif status == 'IN_PROGRESS':
            # Still processing, wait and poll again
            time.sleep(POLL_INTERVAL_SECONDS)  # 2 seconds
            continue
        
        else:
            # Unknown status
            raise ValueError(f"Unexpected job status: {status}")
```

**Comparison with Scene Summarization (Async):**

| Aspect | Content Moderation (Sync) | Scene Summarization (Async) |
|--------|---------------------------|----------------------------|
| **Request Model** | Client waits for complete response | Client receives job ID immediately |
| **Polling** | Backend polls AWS in loop | Frontend polls backend endpoint |
| **Timeout** | 5-minute hard limit | No strict timeout (client decides) |
| **Use Case** | Short videos (<5 min analysis) | Long videos (hours of processing) |
| **User Experience** | Loading spinner, no refresh | Background processing, notifications |
| **Complexity** | Simpler (single request) | More complex (job tracking) |
| **Scalability** | Limited (ties up backend thread) | Better (non-blocking) |
| **Error Handling** | Immediate feedback | Delayed error discovery |

**Why Synchronous for Content Moderation?**

1. **Fast Processing:** AWS Rekognition typically completes in <30 seconds for short videos
2. **User Context:** Moderation is part of upload workflow (user waits anyway)
3. **Immediate Feedback:** Creators need instant validation before proceeding
4. **Simpler UX:** No need to explain "job submitted, check back later"
5. **Lower Complexity:** No job queue, no notification system required

### 3.3 Component Interaction Sequence

```
┌────────┐        ┌─────────┐         ┌───────────┐      ┌─────┐      ┌────────────┐
│ User   │        │ React   │         │   Flask   │      │ S3  │      │ Rekognition│
│ Browser│        │Frontend │         │  Backend  │      │     │      │            │
└────┬───┘        └────┬────┘         └─────┬─────┘      └──┬──┘      └──────┬─────┘
     │                 │                    │               │                 │
     │ 1. Select video │                    │               │                 │
     │────────────────>│                    │               │                 │
     │                 │                    │               │                 │
     │ 2. Configure    │                    │               │                 │
     │    categories   │                    │               │                 │
     │────────────────>│                    │               │                 │
     │                 │                    │               │                 │
     │ 3. Set min      │                    │               │                 │
     │    confidence   │                    │               │                 │
     │────────────────>│                    │               │                 │
     │                 │                    │               │                 │
     │ 4. Click        │                    │               │                 │
     │   "Analyse"     │                    │               │                 │
     │────────────────>│                    │               │                 │
     │                 │                    │               │                 │
     │                 │ 5. POST /moderate  │               │                 │
     │                 │    (multipart)     │               │                 │
     │                 │───────────────────>│               │                 │
     │                 │                    │               │                 │
     │                 │                    │ 6. Save file  │                 │
     │                 │                    │   to uploads/ │                 │
     │                 │                    │──────┐        │                 │
     │                 │                    │      │        │                 │
     │                 │                    │<─────┘        │                 │
     │                 │                    │               │                 │
     │                 │                    │ 7. PUT video  │                 │
     │                 │                    │─────────────> │                 │
     │                 │                    │               │                 │
     │                 │                    │ 8. S3 URL     │                 │
     │                 │                    │ <──────────── │                 │
     │                 │                    │               │                 │
     │                 │                    │ 9. StartContentModeration       │
     │                 │                    │────────────────────────────────>│
     │                 │                    │               │                 │
     │                 │                    │ 10. JobId     │                 │
     │                 │                    │ <────────────────────────────── │
     │                 │                    │               │                 │
     │                 │                    │ ╔═══════════════════════════╗  │
     │                 │                    │ ║ POLLING LOOP (2s interval)║  │
     │                 │                    │ ╚═══════════════════════════╝  │
     │                 │                    │               │                 │
     │                 │                    │ 11. GetContentModeration        │
     │                 │                    │────────────────────────────────>│
     │                 │                    │               │                 │
     │                 │                    │ 12. IN_PROGRESS                 │
     │                 │                    │ <────────────────────────────── │
     │                 │                    │               │                 │
     │                 │                    │ [wait 2 seconds]                │
     │                 │                    │               │                 │
     │                 │                    │ 13. GetContentModeration        │
     │                 │                    │────────────────────────────────>│
     │                 │                    │               │                 │
     │                 │                    │ 14. SUCCEEDED + Labels          │
     │                 │                    │ <────────────────────────────── │
     │                 │                    │               │                 │
     │                 │                    │ 15. Filter & │                 │
     │                 │                    │     format   │                 │
     │                 │                    │──────┐       │                 │
     │                 │                    │      │       │                 │
     │                 │                    │<─────┘       │                 │
     │                 │                    │               │                 │
     │                 │                    │ 16. Save to  │                 │
     │                 │                    │   reports/   │                 │
     │                 │                    │──────┐       │                 │
     │                 │                    │      │       │                 │
     │                 │                    │<─────┘       │                 │
     │                 │                    │               │                 │
     │                 │ 17. JSON response  │               │                 │
     │                 │ <───────────────── │               │                 │
     │                 │                    │               │                 │
     │                 │ 18. Render results │               │                 │
     │                 │──────┐             │               │                 │
     │                 │      │             │               │                 │
     │                 │<─────┘             │               │                 │
     │                 │                    │               │                 │
     │ 19. Display     │                    │               │                 │
     │     timeline    │                    │               │                 │
     │ <───────────────│                    │               │                 │
     │                 │                    │               │                 │
     │ 20. Download    │                    │               │                 │
     │     JSON        │                    │               │                 │
     │────────────────>│                    │               │                 │
     │                 │                    │               │                 │
     │                 │ 21. GET /result/   │               │                 │
     │                 │     <job_id>       │               │                 │
     │                 │───────────────────>│               │                 │
     │                 │                    │               │                 │
     │                 │                    │ 22. Read JSON │                 │
     │                 │                    │     from disk │                 │
     │                 │                    │──────┐        │                 │
     │                 │                    │      │        │                 │
     │                 │                    │<─────┘        │                 │
     │                 │                    │               │                 │
     │                 │ 23. JSON file      │               │                 │
     │                 │ <───────────────── │               │                 │
     │                 │                    │               │                 │
     │ 24. Download    │                    │               │                 │
     │ <───────────────│                    │               │                 │
     │                 │                    │               │                 │
```

---

## 4. AWS Integration Deep Dive

### 4.1 AWS Rekognition Video API

**Service:** Amazon Rekognition Video  
**API Version:** 2016-06-27  
**Region:** Configurable (default: us-east-1)

**Key APIs Used:**

#### 4.1.1 StartContentModeration

```python
response = rekognition_client.start_content_moderation(
    Video={
        'S3Object': {
            'Bucket': 'my-content-bucket',
            'Name': 'moderation/20251022_143022_sample.mp4'
        }
    },
    MinConfidence=75.0,
    NotificationChannel={  # OPTIONAL (not used in sync mode)
        'SNSTopicArn': 'arn:aws:sns:us-east-1:123456789:moderation-notifications',
        'RoleArn': 'arn:aws:iam::123456789:role/RekognitionSNSRole'
    },
    JobTag='content-moderation-service'  # Optional identifier
)

# Response:
{
    'JobId': 'abc123def456ghi789...',
    'ResponseMetadata': {
        'RequestId': '...',
        'HTTPStatusCode': 200
    }
}
```

**Parameters:**
- `Video.S3Object.Bucket` (required): S3 bucket containing video
- `Video.S3Object.Name` (required): S3 object key
- `Video.S3Object.Version` (optional): S3 object version
- `MinConfidence` (optional): 0-100, default 50 (our service defaults to 75)
- `NotificationChannel` (optional): SNS topic for async notifications (unused in sync mode)
- `JobTag` (optional): Custom identifier for tracking

**Response:**
- `JobId`: Unique identifier for polling results

**Cost:** ~$0.10 per minute of video analyzed

#### 4.1.2 GetContentModeration

```python
response = rekognition_client.get_content_moderation(
    JobId='abc123def456ghi789...',
    MaxResults=1000,  # Max labels per page (default 1000)
    NextToken='...',  # For pagination (if previous response had NextToken)
    SortBy='TIMESTAMP'  # or 'NAME' (our service uses TIMESTAMP)
)

# Response:
{
    'JobStatus': 'SUCCEEDED',  # IN_PROGRESS, SUCCEEDED, FAILED
    'StatusMessage': '',       # Error message if FAILED
    'VideoMetadata': {
        'Codec': 'h264',
        'DurationMillis': 12345,
        'Format': 'QuickTime / MOV',
        'FrameRate': 29.97,
        'FrameHeight': 1080,
        'FrameWidth': 1920
    },
    'ModerationLabels': [
        {
            'Timestamp': 1234,  # Milliseconds from start
            'ModerationLabel': {
                'Confidence': 98.5,
                'Name': 'Graphic Violence',
                'ParentName': 'Violence'
            }
        },
        {
            'Timestamp': 5678,
            'ModerationLabel': {
                'Confidence': 95.3,
                'Name': 'Weapons',
                'ParentName': 'Violence'
            }
        },
        # ... up to MaxResults labels
    ],
    'NextToken': '...',  # Present if more results available
    'ModerationModelVersion': '6.0',  # Rekognition model version
    'ResponseMetadata': {
        'RequestId': '...',
        'HTTPStatusCode': 200
    }
}
```

**Parameters:**
- `JobId` (required): From StartContentModeration response
- `MaxResults` (optional): 1-1000 labels per page (default 1000)
- `NextToken` (optional): Pagination token from previous response
- `SortBy` (optional): TIMESTAMP (default) or NAME

**Response Fields:**
- `JobStatus`: IN_PROGRESS → SUCCEEDED/FAILED
- `ModerationLabels[]`: Array of detected violations
  - `Timestamp`: Milliseconds from video start
  - `ModerationLabel.Name`: Specific label (e.g., "Graphic Violence")
  - `ModerationLabel.ParentName`: Category (e.g., "Violence")
  - `ModerationLabel.Confidence`: 0-100 confidence score
- `NextToken`: Present if results exceed MaxResults (pagination required)
- `VideoMetadata`: Video file properties

**Pagination Example:**

```python
def fetch_all_labels(job_id):
    """Fetch all moderation labels across multiple pages."""
    all_labels = []
    next_token = None
    
    while True:
        params = {'JobId': job_id, 'MaxResults': 1000}
        if next_token:
            params['NextToken'] = next_token
        
        response = rekognition_client.get_content_moderation(**params)
        
        all_labels.extend(response.get('ModerationLabels', []))
        
        next_token = response.get('NextToken')
        if not next_token:
            break  # No more pages
    
    return all_labels
```

### 4.2 Moderation Categories & Labels

**AWS Rekognition detects 11 parent categories with 60+ specific labels:**

#### 4.2.1 Explicit Nudity
- Graphic Male Nudity
- Graphic Female Nudity
- Sexual Activity
- Illustrated Explicit Nudity
- Adult Toys

**Use Cases:** Adult content filtering, age restriction enforcement

#### 4.2.2 Suggestive
- Female Swimwear Or Underwear
- Male Swimwear Or Underwear
- Partial Nudity
- Barechested Male
- Revealing Clothes
- Sexual Situations

**Use Cases:** Brand-safe advertising, workplace compliance

#### 4.2.3 Violence
- Graphic Violence Or Gore
- Physical Violence
- Weapon Violence
- Weapons
- Self Injury

**Use Cases:** Child safety, sensitive content warnings

#### 4.2.4 Visually Disturbing
- Emaciated Bodies
- Corpses
- Hanging
- Air Crash
- Explosions And Blasts

**Use Cases:** Trauma-sensitive filtering, news content labeling

#### 4.2.5 Rude Gestures
- Middle Finger

**Use Cases:** Professional content standards, broadcast compliance

#### 4.2.6 Drugs
- Drug Products
- Drug Use
- Pills
- Drug Paraphernalia

**Use Cases:** Legal compliance (drug advertising laws), youth protection

#### 4.2.7 Tobacco
- Tobacco Products
- Smoking

**Use Cases:** Advertising restrictions, health regulations

#### 4.2.8 Alcohol
- Drinking
- Alcoholic Beverages

**Use Cases:** Age-restricted content, advertiser guidelines

#### 4.2.9 Gambling
- Gambling

**Use Cases:** Regulatory compliance, platform policies

#### 4.2.10 Hate Symbols
- Nazi Party
- White Supremacy
- Extremist

**Use Cases:** Hate speech enforcement, legal compliance

#### 4.2.11 Weapons
- Firearms (specific to Violence category)

**Note:** Weapons can appear under Violence category or standalone

**Category Hierarchy:**

```
ParentName (Category)
  └── Name (Specific Label)
      └── Confidence (0-100%)

Example:
Violence (ParentName)
  ├── Graphic Violence Or Gore (Name: 98.5% confidence)
  ├── Physical Violence (Name: 92.3% confidence)
  └── Weapons (Name: 87.6% confidence)
```

### 4.3 AWS S3 Integration

**Bucket Configuration:**

```python
# Environment Variables
CONTENT_MODERATION_BUCKET = os.getenv('CONTENT_MODERATION_BUCKET')
CONTENT_MODERATION_PREFIX = os.getenv('CONTENT_MODERATION_PREFIX', 'moderation/')

# S3 Key Generation
def _build_s3_key(filename):
    """
    Generate unique S3 object key with timestamp prefix.
    
    Example:
    filename: "user_video.mp4"
    prefix: "moderation/"
    output: "moderation/20251022_143022_user_video.mp4"
    """
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    safe_filename = secure_filename(filename)  # Remove path traversal attacks
    return f"{CONTENT_MODERATION_PREFIX}{timestamp}_{safe_filename}"
```

**Upload Process:**

```python
def _upload_to_s3(local_file_path, s3_key):
    """
    Upload video file to S3 bucket.
    
    Args:
        local_file_path: Path to file in uploads/ directory
        s3_key: Generated S3 object key
    
    Returns:
        dict: {'bucket': '...', 'key': '...', 'url': '...'}
    
    Raises:
        ClientError: If upload fails (permissions, quota, etc.)
    """
    try:
        s3_client.upload_file(
            Filename=local_file_path,
            Bucket=CONTENT_MODERATION_BUCKET,
            Key=s3_key,
            ExtraArgs={
                'ContentType': 'video/mp4',  # Adjust based on file type
                'ServerSideEncryption': 'AES256'  # Optional encryption
            }
        )
        
        return {
            'bucket': CONTENT_MODERATION_BUCKET,
            'key': s3_key,
            'url': f"s3://{CONTENT_MODERATION_BUCKET}/{s3_key}"
        }
    except ClientError as e:
        raise Exception(f"S3 upload failed: {str(e)}")
```

**IAM Permissions Required:**

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "s3:PutObject",
        "s3:PutObjectAcl",
        "s3:GetObject",
        "s3:GetObjectVersion"
      ],
      "Resource": "arn:aws:s3:::my-content-bucket/moderation/*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "s3:ListBucket"
      ],
      "Resource": "arn:aws:s3:::my-content-bucket"
    }
  ]
}
```

**Cost Considerations:**
- S3 Storage: ~$0.023/GB/month (Standard tier)
- S3 PUT Requests: $0.005 per 1,000 requests
- S3 GET Requests: $0.0004 per 1,000 requests
- Data Transfer Out: $0.09/GB (if downloading results)

**Best Practices:**
1. **Lifecycle Policies:** Auto-delete videos after 30 days to save costs
2. **Server-Side Encryption:** Protect sensitive content at rest
3. **Bucket Versioning:** Enable for audit trails (optional)
4. **Access Logging:** Track who accesses moderation videos
5. **Cross-Region Replication:** For disaster recovery (optional)

### 4.4 AWS Credentials Management

**Configuration Methods:**

1. **Environment Variables (Recommended for Development):**
```bash
export AWS_ACCESS_KEY_ID="AKIAIOSFODNN7EXAMPLE"
export AWS_SECRET_ACCESS_KEY="wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY"
export AWS_REGION="us-east-1"
```

2. **AWS CLI Configuration (~/.aws/credentials):**
```ini
[default]
aws_access_key_id = AKIAIOSFODNN7EXAMPLE
aws_secret_access_key = wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY
region = us-east-1
```

3. **IAM Role (Recommended for Production - EC2/ECS):**
```python
# No credentials needed - boto3 auto-discovers from instance metadata
rekognition_client = boto3.client('rekognition')  # Uses instance role
```

4. **.env File (Development):**
```bash
# .env file (git-ignored)
AWS_ACCESS_KEY_ID=AKIAIOSFODNN7EXAMPLE
AWS_SECRET_ACCESS_KEY=wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY
AWS_REGION=us-east-1
CONTENT_MODERATION_BUCKET=my-content-bucket
```

**Security Best Practices:**

```python
# NEVER hardcode credentials
# ❌ BAD:
rekognition_client = boto3.client(
    'rekognition',
    aws_access_key_id='AKIAIOSFODNN7EXAMPLE',  # NEVER DO THIS
    aws_secret_access_key='wJalrXUtnFEMI/K7MDENG...'
)

# ✅ GOOD:
rekognition_client = boto3.client('rekognition')  # Auto-discover from environment
```

**IAM Policy for Service Account:**

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "RekognitionContentModeration",
      "Effect": "Allow",
      "Action": [
        "rekognition:StartContentModeration",
        "rekognition:GetContentModeration"
      ],
      "Resource": "*"
    },
    {
      "Sid": "S3VideoAccess",
      "Effect": "Allow",
      "Action": [
        "s3:PutObject",
        "s3:GetObject"
      ],
      "Resource": "arn:aws:s3:::my-content-bucket/moderation/*"
    }
  ]
}
```

**Credential Rotation:**
- Rotate access keys every 90 days
- Use AWS Secrets Manager for production
- Monitor with AWS CloudTrail

---

## 5. Configuration Management

### 5.1 Environment Variables

```python
# REQUIRED
CONTENT_MODERATION_BUCKET = os.getenv('CONTENT_MODERATION_BUCKET')
# S3 bucket name for video storage
# Example: "my-content-bucket"
# Must exist and be accessible with AWS credentials

# REQUIRED (AWS Credentials - use ONE method)
AWS_ACCESS_KEY_ID = os.getenv('AWS_ACCESS_KEY_ID')
AWS_SECRET_ACCESS_KEY = os.getenv('AWS_SECRET_ACCESS_KEY')
# OR use ~/.aws/credentials
# OR use IAM instance role (production)

# OPTIONAL
AWS_REGION = os.getenv('AWS_REGION', 'us-east-1')
# AWS region for Rekognition and S3
# Default: us-east-1
# Options: us-east-1, us-west-2, eu-west-1, etc.

CONTENT_MODERATION_PREFIX = os.getenv('CONTENT_MODERATION_PREFIX', 'moderation/')
# S3 key prefix (folder) for uploaded videos
# Default: "moderation/"
# Example: "content/videos/moderation/"

CONTENT_MODERATION_MIN_CONFIDENCE = float(os.getenv('CONTENT_MODERATION_MIN_CONFIDENCE', '75'))
# Default confidence threshold (0-100)
# Default: 75
# Users can override per-request

CONTENT_MODERATION_POLL_INTERVAL = int(os.getenv('CONTENT_MODERATION_POLL_INTERVAL', '2'))
# Seconds between GetContentModeration polls
# Default: 2
# Lower = faster results, higher AWS API costs

CONTENT_MODERATION_MAX_WAIT_SECONDS = int(os.getenv('CONTENT_MODERATION_MAX_WAIT_SECONDS', '300'))
# Maximum polling duration before timeout
# Default: 300 (5 minutes)
# Increase for longer videos

CONTENT_MODERATION_ALLOWED_ORIGINS = os.getenv('CONTENT_MODERATION_ALLOWED_ORIGINS', '*')
# CORS allowed origins (comma-separated)
# Default: * (allow all - development only)
# Production: "https://mediagenai.com,https://app.mediagenai.com"

CONTENT_MODERATION_API_PORT = int(os.getenv('CONTENT_MODERATION_API_PORT', '5006'))
# Flask server port
# Default: 5006
# Change if port conflict exists

# OPTIONAL (Async Notifications - not used in sync mode)
CONTENT_MODERATION_SNS_TOPIC_ARN = os.getenv('CONTENT_MODERATION_SNS_TOPIC_ARN', '')
CONTENT_MODERATION_SNS_ROLE_ARN = os.getenv('CONTENT_MODERATION_SNS_ROLE_ARN', '')
# Leave empty for synchronous polling
# Provide both for async notifications (advanced use case)
```

### 5.2 Flask Application Configuration

```python
# FILE UPLOAD SETTINGS
app.config['MAX_CONTENT_LENGTH'] = 2 * 1024 * 1024 * 1024  # 2GB max upload
app.config['UPLOAD_FOLDER'] = BASE_DIR / 'uploads'
app.config['ALLOWED_EXTENSIONS'] = {'mp4', 'mov', 'mkv', 'm4v', 'avi', 'webm'}

# DIRECTORY CREATION
BASE_DIR = Path(__file__).parent
(BASE_DIR / 'uploads').mkdir(exist_ok=True)   # Temporary video storage
(BASE_DIR / 'reports').mkdir(exist_ok=True)   # JSON report persistence

# CORS CONFIGURATION
allowed_origins = os.getenv('CONTENT_MODERATION_ALLOWED_ORIGINS', '*')
CORS(app, resources={
    r"/*": {
        "origins": allowed_origins.split(',') if allowed_origins != '*' else '*',
        "methods": ["GET", "POST", "OPTIONS"],
        "allow_headers": ["Content-Type"]
    }
})

# AWS CLIENT INITIALIZATION
rekognition_client = boto3.client('rekognition', region_name=AWS_REGION)
s3_client = boto3.client('s3', region_name=AWS_REGION)
```

### 5.3 Frontend Configuration

```javascript
// API Base URL Resolution
function resolveModerationApiBase() {
  // Development: localhost
  if (window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1') {
    return 'http://localhost:5006';
  }
  
  // Production: same-origin or environment variable
  const prodBase = process.env.REACT_APP_MODERATION_API_BASE;
  if (prodBase) {
    return prodBase;
  }
  
  // Fallback: assume backend on same domain, different port
  return `${window.location.protocol}//${window.location.hostname}:5006`;
}

const API_BASE = resolveModerationApiBase();

// Default Values
const DEFAULT_MIN_CONFIDENCE = 75;  // Match backend default
const DEFAULT_TIMEOUT_MS = 300000;  // 5 minutes (match backend MAX_WAIT_SECONDS)
const DEFAULT_CATEGORIES = [        // All 11 categories selected by default
  'Explicit Nudity',
  'Suggestive',
  'Violence',
  'Visually Disturbing',
  'Rude Gestures',
  'Drugs',
  'Tobacco',
  'Alcohol',
  'Gambling',
  'Hate Symbols',
  'Weapons'
];

// Axios Configuration
axios.defaults.timeout = DEFAULT_TIMEOUT_MS;
axios.defaults.headers.post['Content-Type'] = 'multipart/form-data';
```

### 5.4 Production Configuration Checklist

**Security:**
- [ ] Replace `ALLOWED_ORIGINS=*` with specific domains
- [ ] Use IAM roles instead of access keys (EC2/ECS)
- [ ] Enable S3 server-side encryption
- [ ] Implement S3 bucket policies restricting public access
- [ ] Enable AWS CloudTrail for audit logging
- [ ] Rotate AWS access keys every 90 days

**Performance:**
- [ ] Adjust `POLL_INTERVAL` based on video length (2s for <1min, 5s for >5min)
- [ ] Increase `MAX_WAIT_SECONDS` for longer videos (600s for 10-minute videos)
- [ ] Configure S3 lifecycle policies (delete after 30 days)
- [ ] Use CloudFront CDN for S3 video delivery (optional)

**Reliability:**
- [ ] Implement retry logic for transient AWS API errors
- [ ] Add dead letter queue for failed jobs (if using async)
- [ ] Set up CloudWatch alarms for API errors
- [ ] Configure auto-scaling for backend servers
- [ ] Implement rate limiting (prevent abuse)

**Cost Optimization:**
- [ ] Use S3 Intelligent-Tiering for infrequent access
- [ ] Delete temporary uploads after processing
- [ ] Archive old reports to S3 Glacier
- [ ] Monitor Rekognition usage with AWS Cost Explorer
- [ ] Set budget alerts for AWS services

**Compliance:**
- [ ] Enable S3 access logging
- [ ] Implement data retention policies
- [ ] Configure S3 object locking (immutable reports)
- [ ] Document data processing agreements (GDPR)
- [ ] Implement user consent mechanisms

---

## End of Part 1

**This concludes Part 1 of the Content Moderation Service reference documentation.**

### What's Covered in Part 1:
✅ Executive Summary & Business Value  
✅ Service Overview & Workflow  
✅ Architecture Overview (Synchronous Polling)  
✅ AWS Integration (Rekognition + S3)  
✅ Configuration Management  

### Coming in Part 2:
📄 Backend Deep Dive (Flask Routes & Helper Functions)  
📄 Results Processing & Filtering Logic  
📄 Report Storage & Retrieval  
📄 Frontend Architecture (Upload Component)  

### Coming in Part 3:
📄 Frontend Results Display & User Experience  
📄 Error Handling & Status Management  
📄 API Reference & Request/Response Examples  

### Coming in Part 4:
📄 Deployment Guide  
📄 Troubleshooting & Common Issues  
📄 Performance Optimization  
📄 Production Checklist  

---

**Document Navigation:**
- **Current:** Part 1 - Foundation & AWS Integration
- **Next:** [Part 2 - Backend Implementation](CONTENT_MODERATION_PART2.md)
- **Index:** [Documentation Index](DOCUMENTATION_INDEX.md)

**Last Updated:** October 22, 2025  
**Maintainer:** MediaGenAI Platform Team  
**Service Version:** 1.0

# Content Moderation Service - Part 2 of 4
## Backend Implementation, Results Processing & Report Storage

**Document Version:** 1.0  
**Last Updated:** October 22, 2025  
**Service Port:** 5006  
**Part:** 2/4 - Backend Deep Dive

---

## Table of Contents - Part 2

6. [Backend Deep Dive](#6-backend-deep-dive)
7. [Helper Functions](#7-helper-functions)
8. [Results Processing & Filtering](#8-results-processing--filtering)
9. [Report Storage & Retrieval](#9-report-storage--retrieval)

---

## 6. Backend Deep Dive

### 6.1 Flask Application Structure

**File:** `contentModeration/content_moderation_service.py` (457 lines)

```python
"""
Content Moderation Service - Backend Implementation

This Flask service provides video content moderation using AWS Rekognition.
It uploads videos to S3, initiates moderation jobs, polls for results,
and returns timestamped moderation labels filtered by category and confidence.

Key Features:
- Synchronous polling architecture (2-second intervals)
- 11 moderation categories (Explicit Nudity, Violence, Drugs, etc.)
- Configurable confidence threshold (0-100%)
- Category-based filtering
- JSON report persistence
- 2GB maximum file upload
- 5-minute analysis timeout
"""

from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
import boto3
from botocore.exceptions import ClientError
import os
import time
from pathlib import Path
from datetime import datetime
from werkzeug.utils import secure_filename
import json
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Flask app initialization
app = Flask(__name__)

# Configuration constants
MAX_CONTENT_LENGTH = 2 * 1024 * 1024 * 1024  # 2GB
DEFAULT_MIN_CONFIDENCE = float(os.getenv('CONTENT_MODERATION_MIN_CONFIDENCE', '75'))
POLL_INTERVAL_SECONDS = int(os.getenv('CONTENT_MODERATION_POLL_INTERVAL', '2'))
MAX_WAIT_SECONDS = int(os.getenv('CONTENT_MODERATION_MAX_WAIT_SECONDS', '300'))
AWS_REGION = os.getenv('AWS_REGION', 'us-east-1')
ALLOWED_EXTENSIONS = {'mp4', 'mov', 'mkv', 'm4v', 'avi', 'webm'}

# AWS configuration
CONTENT_MODERATION_BUCKET = os.getenv('CONTENT_MODERATION_BUCKET')
CONTENT_MODERATION_PREFIX = os.getenv('CONTENT_MODERATION_PREFIX', 'moderation/')
CONTENT_MODERATION_SNS_TOPIC_ARN = os.getenv('CONTENT_MODERATION_SNS_TOPIC_ARN', '')
CONTENT_MODERATION_SNS_ROLE_ARN = os.getenv('CONTENT_MODERATION_SNS_ROLE_ARN', '')

# Directory setup
BASE_DIR = Path(__file__).parent
UPLOAD_DIR = BASE_DIR / 'uploads'
REPORTS_DIR = BASE_DIR / 'reports'
UPLOAD_DIR.mkdir(exist_ok=True)
REPORTS_DIR.mkdir(exist_ok=True)

# Flask configuration
app.config['MAX_CONTENT_LENGTH'] = MAX_CONTENT_LENGTH
app.config['UPLOAD_FOLDER'] = str(UPLOAD_DIR)

# CORS setup
allowed_origins = os.getenv('CONTENT_MODERATION_ALLOWED_ORIGINS', '*')
CORS(app, resources={
    r"/*": {
        "origins": allowed_origins.split(',') if allowed_origins != '*' else '*',
        "methods": ["GET", "POST", "OPTIONS"],
        "allow_headers": ["Content-Type"]
    }
})

# AWS clients
rekognition_client = boto3.client('rekognition', region_name=AWS_REGION)
s3_client = boto3.client('s3', region_name=AWS_REGION)

# Moderation category options (11 categories)
MODERATION_CATEGORY_OPTIONS = [
    {"key": "Explicit Nudity", "label": "Explicit Nudity"},
    {"key": "Suggestive", "label": "Suggestive"},
    {"key": "Violence", "label": "Violence"},
    {"key": "Visually Disturbing", "label": "Visually Disturbing"},
    {"key": "Rude Gestures", "label": "Rude Gestures"},
    {"key": "Drugs", "label": "Drugs"},
    {"key": "Tobacco", "label": "Tobacco"},
    {"key": "Alcohol", "label": "Alcohol"},
    {"key": "Gambling", "label": "Gambling"},
    {"key": "Hate Symbols", "label": "Hate Symbols"},
    {"key": "Weapons", "label": "Weapons"}
]
```

### 6.2 Service Readiness Check

```python
def _service_ready():
    """
    Verify that AWS clients are properly configured.
    
    Checks:
    - Rekognition client initialized
    - S3 client initialized
    - S3 bucket configured (environment variable set)
    
    Returns:
        bool: True if service is ready, False otherwise
    
    Usage:
        Called by /health endpoint to verify downstream dependencies
    """
    if not rekognition_client:
        return False
    if not s3_client:
        return False
    if not CONTENT_MODERATION_BUCKET:
        return False
    return True
```

### 6.3 File Validation

```python
def allowed_file(filename):
    """
    Validate file extension against allowed video formats.
    
    Args:
        filename (str): Original filename from upload
    
    Returns:
        bool: True if extension is allowed, False otherwise
    
    Allowed Extensions:
        - mp4: H.264/H.265 video (most common)
        - mov: QuickTime format (Apple devices)
        - mkv: Matroska container (open source)
        - m4v: MPEG-4 video (iTunes)
        - avi: Audio Video Interleave (legacy)
        - webm: WebM format (web optimized)
    
    Security Notes:
        - Case-insensitive comparison (.MP4 == .mp4)
        - Requires filename to have extension (dot present)
        - Does not validate MIME type (backend responsibility)
    
    Examples:
        >>> allowed_file('video.mp4')
        True
        >>> allowed_file('video.MP4')
        True
        >>> allowed_file('video.txt')
        False
        >>> allowed_file('video')
        False
    """
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS
```

### 6.4 Flask Route Implementations

#### 6.4.1 Health Check Endpoint

```python
@app.route('/health', methods=['GET'])
def health():
    """
    Service health check endpoint.
    
    Returns:
        JSON: {
            "status": "healthy" | "unhealthy",
            "rekognition": bool,
            "s3": bool,
            "bucket": str | null
        }
    
    HTTP Status Codes:
        200: Service healthy (all checks passed)
        503: Service unhealthy (missing configuration)
    
    Example Request:
        GET http://localhost:5006/health
    
    Example Response (Healthy):
        {
            "status": "healthy",
            "rekognition": true,
            "s3": true,
            "bucket": "my-content-bucket"
        }
    
    Example Response (Unhealthy):
        {
            "status": "unhealthy",
            "rekognition": true,
            "s3": true,
            "bucket": null
        }
    
    Use Cases:
        - Load balancer health checks
        - Kubernetes readiness probes
        - Monitoring system validation
        - Pre-deployment smoke tests
    """
    if not _service_ready():
        return jsonify({
            "status": "unhealthy",
            "rekognition": rekognition_client is not None,
            "s3": s3_client is not None,
            "bucket": CONTENT_MODERATION_BUCKET
        }), 503
    
    return jsonify({
        "status": "healthy",
        "rekognition": True,
        "s3": True,
        "bucket": CONTENT_MODERATION_BUCKET
    }), 200
```

#### 6.4.2 Moderation Options Endpoint

```python
@app.route('/moderation-options', methods=['GET'])
def moderation_options():
    """
    Return available moderation categories.
    
    Returns:
        JSON: {
            "categories": [
                {"key": str, "label": str},
                ...
            ]
        }
    
    HTTP Status Codes:
        200: Success
    
    Example Request:
        GET http://localhost:5006/moderation-options
    
    Example Response:
        {
            "categories": [
                {"key": "Explicit Nudity", "label": "Explicit Nudity"},
                {"key": "Suggestive", "label": "Suggestive"},
                {"key": "Violence", "label": "Violence"},
                {"key": "Visually Disturbing", "label": "Visually Disturbing"},
                {"key": "Rude Gestures", "label": "Rude Gestures"},
                {"key": "Drugs", "label": "Drugs"},
                {"key": "Tobacco", "label": "Tobacco"},
                {"key": "Alcohol", "label": "Alcohol"},
                {"key": "Gambling", "label": "Gambling"},
                {"key": "Hate Symbols", "label": "Hate Symbols"},
                {"key": "Weapons", "label": "Weapons"}
            ]
        }
    
    Use Cases:
        - Frontend initialization (populate checkboxes)
        - API documentation generation
        - Client SDK configuration
        - Dynamic form generation
    
    Frontend Integration:
        const response = await fetch(`${API_BASE}/moderation-options`);
        const { categories } = await response.json();
        setAvailableCategories(categories);
    """
    return jsonify({"categories": MODERATION_CATEGORY_OPTIONS}), 200
```

#### 6.4.3 Moderate Video Endpoint (Main Processing)

```python
@app.route('/moderate', methods=['POST'])
def moderate():
    """
    Main video moderation endpoint.
    
    Request:
        Content-Type: multipart/form-data
        Body:
            - video (file, required): Video file (max 2GB)
            - categories (string, optional): Comma-separated category list
              Example: "Explicit Nudity,Violence,Drugs"
              Default: All categories
            - min_confidence (number, optional): Confidence threshold (0-100)
              Default: 75
    
    Response:
        JSON: {
            "jobId": str,
            "video": {
                "objectKey": str,
                "bucket": str
            },
            "events": [
                {
                    "timestamp": {
                        "milliseconds": int,
                        "seconds": float,
                        "timecode": str  # HH:MM:SS.mmm
                    },
                    "category": str,
                    "label": str,
                    "confidence": float
                },
                ...
            ],
            "summary": {
                "totalFindings": int,
                "categories": {
                    "Violence": int,
                    "Explicit Nudity": int,
                    ...
                }
            },
            "requestMeta": {
                "selectedCategories": [str, ...],
                "minConfidence": float
            },
            "metadata": {
                "analysisDurationSeconds": float
            }
        }
    
    HTTP Status Codes:
        200: Success (moderation completed)
        400: Bad request (missing file, invalid file type, validation error)
        413: Payload too large (file exceeds 2GB)
        500: Internal server error (AWS API failure, timeout)
        503: Service unavailable (AWS clients not configured)
    
    Error Response:
        {
            "error": "Error message description"
        }
    
    Processing Flow:
        1. Validate service readiness
        2. Extract and validate form data
        3. Save file to uploads/ directory
        4. Upload to S3
        5. Start Rekognition moderation job
        6. Poll for results (synchronous, max 5 minutes)
        7. Filter results by category and confidence
        8. Format timestamps
        9. Generate summary statistics
        10. Save report to reports/ directory
        11. Return JSON response
    
    Example cURL Request:
        curl -X POST http://localhost:5006/moderate \
          -F "video=@sample.mp4" \
          -F "categories=Explicit Nudity,Violence" \
          -F "min_confidence=80"
    
    Example Axios Request:
        const formData = new FormData();
        formData.append('video', fileObject);
        formData.append('categories', 'Explicit Nudity,Violence');
        formData.append('min_confidence', '80');
        
        const response = await axios.post(
          `${API_BASE}/moderate`,
          formData,
          {
            headers: { 'Content-Type': 'multipart/form-data' },
            onUploadProgress: (e) => {
              const percent = Math.round((e.loaded * 100) / e.total);
              setUploadProgress(percent);
            }
          }
        );
    """
    
    # STEP 1: Service readiness check
    if not _service_ready():
        return jsonify({"error": "Service not configured. Check AWS credentials and S3 bucket."}), 503
    
    # STEP 2: Extract video file from form data
    if 'video' not in request.files:
        return jsonify({"error": "No video file provided"}), 400
    
    video_file = request.files['video']
    
    if video_file.filename == '':
        return jsonify({"error": "Empty filename"}), 400
    
    if not allowed_file(video_file.filename):
        return jsonify({
            "error": f"Invalid file type. Allowed: {', '.join(ALLOWED_EXTENSIONS)}"
        }), 400
    
    # STEP 3: Extract optional parameters
    categories_param = request.form.get('categories', '')  # Comma-separated string
    min_confidence_param = request.form.get('min_confidence', DEFAULT_MIN_CONFIDENCE)
    
    try:
        min_confidence = float(min_confidence_param)
        if not 0 <= min_confidence <= 100:
            return jsonify({"error": "min_confidence must be between 0 and 100"}), 400
    except (ValueError, TypeError):
        return jsonify({"error": "min_confidence must be a valid number"}), 400
    
    # STEP 4: Parse selected categories
    selected_categories = _normalise_selected_categories(categories_param)
    
    # STEP 5: Save file to uploads/ directory
    safe_filename = secure_filename(video_file.filename)
    timestamp_prefix = datetime.now().strftime('%Y%m%d_%H%M%S')
    local_filename = f"{timestamp_prefix}_{safe_filename}"
    local_filepath = UPLOAD_DIR / local_filename
    
    try:
        video_file.save(str(local_filepath))
    except Exception as e:
        return jsonify({"error": f"Failed to save file: {str(e)}"}), 500
    
    # STEP 6: Upload to S3
    s3_key = _build_s3_key(safe_filename)
    
    try:
        s3_upload_result = _upload_to_s3(str(local_filepath), s3_key)
    except Exception as e:
        # Clean up local file on S3 failure
        if local_filepath.exists():
            local_filepath.unlink()
        return jsonify({"error": f"S3 upload failed: {str(e)}"}), 500
    
    # STEP 7: Start Rekognition moderation job
    try:
        job_id = _start_content_moderation_job(
            bucket=CONTENT_MODERATION_BUCKET,
            key=s3_key,
            min_confidence=min_confidence
        )
    except Exception as e:
        # Clean up local file and S3 object on Rekognition failure
        if local_filepath.exists():
            local_filepath.unlink()
        try:
            s3_client.delete_object(Bucket=CONTENT_MODERATION_BUCKET, Key=s3_key)
        except:
            pass
        return jsonify({"error": f"Failed to start moderation job: {str(e)}"}), 500
    
    # STEP 8: Poll for results (synchronous, blocks until complete or timeout)
    analysis_start = time.time()
    
    try:
        poll_result = _poll_moderation_results(
            job_id=job_id,
            min_confidence=min_confidence,
            selected_categories=selected_categories
        )
    except Exception as e:
        # Clean up local file on polling failure
        if local_filepath.exists():
            local_filepath.unlink()
        return jsonify({"error": f"Moderation polling failed: {str(e)}"}), 500
    finally:
        # Always clean up local file after processing
        if local_filepath.exists():
            local_filepath.unlink()
    
    analysis_duration = time.time() - analysis_start
    
    # STEP 9: Check polling result status
    if poll_result['status'] != 'SUCCEEDED':
        return jsonify({
            "error": f"Moderation job failed: {poll_result.get('error', 'Unknown error')}"
        }), 500
    
    # STEP 10: Process and format results
    raw_labels = poll_result['labels']
    
    # Filter by selected categories
    filtered_events = []
    for label in raw_labels:
        timestamp_ms = label.get('Timestamp', 0)
        mod_label = label.get('ModerationLabel', {})
        confidence = mod_label.get('Confidence', 0)
        label_name = mod_label.get('Name', '')
        parent_name = mod_label.get('ParentName', '')
        
        # Apply category filter
        if selected_categories and not _category_matches(parent_name, selected_categories):
            continue
        
        # Apply confidence threshold
        if confidence < min_confidence:
            continue
        
        # Format event
        event = {
            "timestamp": _format_timestamp(timestamp_ms),
            "category": parent_name,
            "label": label_name,
            "confidence": round(confidence, 2)
        }
        filtered_events.append(event)
    
    # STEP 11: Generate summary statistics
    summary = _summarise_events(filtered_events)
    
    # STEP 12: Build final report
    report = {
        "jobId": job_id,
        "video": {
            "objectKey": s3_key,
            "bucket": CONTENT_MODERATION_BUCKET
        },
        "events": filtered_events,
        "summary": summary,
        "requestMeta": {
            "selectedCategories": selected_categories if selected_categories else None,
            "minConfidence": min_confidence
        },
        "metadata": {
            "analysisDurationSeconds": round(analysis_duration, 2)
        }
    }
    
    # STEP 13: Save report to disk
    try:
        _store_report(job_id, report)
    except Exception as e:
        # Non-fatal error, log but continue
        print(f"Warning: Failed to store report: {str(e)}")
    
    # STEP 14: Return response
    return jsonify(report), 200
```

#### 6.4.4 Result Retrieval Endpoint

```python
@app.route('/result/<job_id>', methods=['GET'])
def get_result(job_id):
    """
    Retrieve saved moderation report by job ID.
    
    Args:
        job_id (str): Rekognition job ID (from /moderate response)
    
    Returns:
        JSON: Saved report (same structure as /moderate response)
        or
        File: JSON file download (Content-Disposition: attachment)
    
    HTTP Status Codes:
        200: Success (report found)
        404: Not found (job ID doesn't exist)
        500: Internal server error (file read failure)
    
    Example Request:
        GET http://localhost:5006/result/abc123def456ghi789
    
    Example Response:
        {
            "jobId": "abc123def456ghi789",
            "video": { "objectKey": "...", "bucket": "..." },
            "events": [...],
            "summary": {...},
            "requestMeta": {...},
            "metadata": {...}
        }
    
    Use Cases:
        - Download report for archival
        - Retrieve results after browser refresh
        - Integration with compliance systems
        - Audit trail generation
    
    File Storage:
        Location: reports/<job_id>.json
        Format: JSON
        Retention: Indefinite (manual cleanup required)
    
    Frontend Integration:
        // Direct download link
        <a href={`${API_BASE}/result/${jobId}`} download>
          Download JSON Report
        </a>
        
        // Fetch and process
        const response = await fetch(`${API_BASE}/result/${jobId}`);
        const report = await response.json();
    """
    report_path = REPORTS_DIR / f"{job_id}.json"
    
    if not report_path.exists():
        return jsonify({"error": f"Report not found for job ID: {job_id}"}), 404
    
    try:
        with open(report_path, 'r') as f:
            report = json.load(f)
        return jsonify(report), 200
    except Exception as e:
        return jsonify({"error": f"Failed to read report: {str(e)}"}), 500
```

### 6.5 Flask Server Startup

```python
if __name__ == '__main__':
    """
    Development server startup.
    
    Configuration:
        - Host: 0.0.0.0 (listen on all interfaces)
        - Port: 5006 (configurable via CONTENT_MODERATION_API_PORT)
        - Debug: False (disable in production)
        - Threaded: True (handle concurrent requests)
    
    Production Deployment:
        DO NOT use Flask development server in production.
        Use WSGI server instead:
        
        # Gunicorn (recommended)
        gunicorn -w 4 -b 0.0.0.0:5006 content_moderation_service:app
        
        # uWSGI
        uwsgi --http 0.0.0.0:5006 --wsgi-file content_moderation_service.py --callable app
    
    Environment Variables:
        CONTENT_MODERATION_API_PORT: Override default port (5006)
    """
    port = int(os.getenv('CONTENT_MODERATION_API_PORT', '5006'))
    print(f"Content Moderation Service starting on port {port}...")
    print(f"S3 Bucket: {CONTENT_MODERATION_BUCKET}")
    print(f"AWS Region: {AWS_REGION}")
    print(f"Min Confidence: {DEFAULT_MIN_CONFIDENCE}%")
    print(f"Poll Interval: {POLL_INTERVAL_SECONDS}s")
    print(f"Max Wait: {MAX_WAIT_SECONDS}s")
    
    app.run(
        host='0.0.0.0',
        port=port,
        debug=False,
        threaded=True
    )
```

---

## 7. Helper Functions

### 7.1 S3 Key Generation

```python
def _build_s3_key(filename):
    """
    Generate unique S3 object key with timestamp prefix.
    
    Args:
        filename (str): Sanitized filename (from secure_filename)
    
    Returns:
        str: S3 object key
    
    Format:
        <prefix><timestamp>_<filename>
    
    Examples:
        Input:  "user_video.mp4"
        Prefix: "moderation/"
        Output: "moderation/20251022_143022_user_video.mp4"
        
        Input:  "vacation.mov"
        Prefix: "content/uploads/"
        Output: "content/uploads/20251022_143022_vacation.mov"
    
    Benefits:
        - Uniqueness: Timestamp prevents collisions
        - Organization: Prefix for folder-like structure
        - Sortability: Chronological ordering in S3 console
        - Traceability: Timestamp in key aids debugging
    
    S3 Key Best Practices:
        - Avoid leading slashes (use "folder/" not "/folder/")
        - Use lowercase for consistency
        - Limit to 1024 characters
        - Avoid special characters (!, *, ', (, ), etc.)
    """
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    return f"{CONTENT_MODERATION_PREFIX}{timestamp}_{filename}"
```

### 7.2 S3 Upload Function

```python
def _upload_to_s3(local_file_path, s3_key):
    """
    Upload video file to S3 bucket.
    
    Args:
        local_file_path (str): Absolute path to local file
        s3_key (str): S3 object key (from _build_s3_key)
    
    Returns:
        dict: {
            'bucket': str,
            'key': str,
            'url': str  # s3://bucket/key format
        }
    
    Raises:
        ClientError: If S3 upload fails
            - NoSuchBucket: Bucket doesn't exist
            - AccessDenied: Insufficient IAM permissions
            - RequestTimeout: Network issue
            - SlowDown: S3 rate limiting
    
    Upload Configuration:
        - ContentType: Inferred from file extension (video/mp4, video/quicktime, etc.)
        - ServerSideEncryption: AES256 (enabled by default)
        - StorageClass: STANDARD (can change to INTELLIGENT_TIERING for cost savings)
        - ACL: Private (not publicly accessible)
    
    Performance Optimization:
        For files >100MB, consider multipart upload:
        
        from boto3.s3.transfer import TransferConfig
        
        config = TransferConfig(
            multipart_threshold=100 * 1024 * 1024,  # 100MB
            max_concurrency=10,
            multipart_chunksize=10 * 1024 * 1024,   # 10MB chunks
            use_threads=True
        )
        
        s3_client.upload_file(
            local_file_path,
            CONTENT_MODERATION_BUCKET,
            s3_key,
            Config=config
        )
    
    Example:
        >>> _upload_to_s3('/tmp/video.mp4', 'moderation/20251022_143022_video.mp4')
        {
            'bucket': 'my-content-bucket',
            'key': 'moderation/20251022_143022_video.mp4',
            'url': 's3://my-content-bucket/moderation/20251022_143022_video.mp4'
        }
    """
    try:
        # Infer content type from file extension
        content_type = 'video/mp4'  # Default
        if s3_key.endswith('.mov'):
            content_type = 'video/quicktime'
        elif s3_key.endswith('.mkv'):
            content_type = 'video/x-matroska'
        elif s3_key.endswith('.avi'):
            content_type = 'video/x-msvideo'
        elif s3_key.endswith('.webm'):
            content_type = 'video/webm'
        
        # Upload file to S3
        s3_client.upload_file(
            Filename=local_file_path,
            Bucket=CONTENT_MODERATION_BUCKET,
            Key=s3_key,
            ExtraArgs={
                'ContentType': content_type,
                'ServerSideEncryption': 'AES256'
            }
        )
        
        return {
            'bucket': CONTENT_MODERATION_BUCKET,
            'key': s3_key,
            'url': f"s3://{CONTENT_MODERATION_BUCKET}/{s3_key}"
        }
    
    except ClientError as e:
        error_code = e.response['Error']['Code']
        error_message = e.response['Error']['Message']
        raise Exception(f"S3 upload error ({error_code}): {error_message}")
```

### 7.3 Start Moderation Job

```python
def _start_content_moderation_job(bucket, key, min_confidence):
    """
    Initiate AWS Rekognition content moderation job.
    
    Args:
        bucket (str): S3 bucket name
        key (str): S3 object key
        min_confidence (float): Confidence threshold (0-100)
    
    Returns:
        str: Rekognition job ID
    
    Raises:
        ClientError: If Rekognition API fails
            - InvalidS3ObjectException: S3 object not found or inaccessible
            - InvalidParameterException: Invalid parameters
            - AccessDeniedException: Insufficient IAM permissions
            - LimitExceededException: Concurrent job limit reached
            - ThrottlingException: API rate limit exceeded
    
    API Details:
        Endpoint: rekognition.StartContentModeration
        Request Rate: Up to 10 concurrent jobs per account
        Video Limits:
            - Max file size: 10GB
            - Max duration: 2 hours
            - Supported codecs: H.264, H.265, VP8, VP9
            - Supported containers: MP4, MOV, MKV, WEBM, AVI
    
    Job Processing Time:
        - Typical: 30-60 seconds for 1-minute video
        - Formula: ~0.5-1x realtime (1min video = 30-60s processing)
        - Factors: Resolution, codec, scene complexity
    
    Optional Parameters (Not Used in Sync Mode):
        NotificationChannel: SNS topic for async completion notifications
            Requires:
                - SNS topic ARN
                - IAM role ARN (allows Rekognition to publish to SNS)
            Example:
                NotificationChannel={
                    'SNSTopicArn': 'arn:aws:sns:us-east-1:123456:moderation',
                    'RoleArn': 'arn:aws:iam::123456:role/RekognitionSNSRole'
                }
    
    Example:
        >>> _start_content_moderation_job(
        ...     bucket='my-bucket',
        ...     key='moderation/20251022_143022_video.mp4',
        ...     min_confidence=75.0
        ... )
        'abc123def456ghi789jkl012mno345pqr678stu901vwx234yz567'
    """
    try:
        params = {
            'Video': {
                'S3Object': {
                    'Bucket': bucket,
                    'Name': key
                }
            },
            'MinConfidence': float(min_confidence)
        }
        
        # Optional: Add SNS notification channel for async mode
        if CONTENT_MODERATION_SNS_TOPIC_ARN and CONTENT_MODERATION_SNS_ROLE_ARN:
            params['NotificationChannel'] = {
                'SNSTopicArn': CONTENT_MODERATION_SNS_TOPIC_ARN,
                'RoleArn': CONTENT_MODERATION_SNS_ROLE_ARN
            }
        
        response = rekognition_client.start_content_moderation(**params)
        job_id = response['JobId']
        
        print(f"Started moderation job: {job_id}")
        return job_id
    
    except ClientError as e:
        error_code = e.response['Error']['Code']
        error_message = e.response['Error']['Message']
        raise Exception(f"Rekognition error ({error_code}): {error_message}")
```

### 7.4 Timestamp Formatting

```python
def _format_timestamp(milliseconds):
    """
    Convert milliseconds to human-readable timecode.
    
    Args:
        milliseconds (int): Timestamp from Rekognition (milliseconds from video start)
    
    Returns:
        dict: {
            'milliseconds': int,
            'seconds': float,
            'timecode': str  # HH:MM:SS.mmm format
        }
    
    Examples:
        >>> _format_timestamp(0)
        {'milliseconds': 0, 'seconds': 0.0, 'timecode': '00:00:00.000'}
        
        >>> _format_timestamp(1234)
        {'milliseconds': 1234, 'seconds': 1.234, 'timecode': '00:00:01.234'}
        
        >>> _format_timestamp(125678)
        {'milliseconds': 125678, 'seconds': 125.678, 'timecode': '00:02:05.678'}
        
        >>> _format_timestamp(3661000)
        {'milliseconds': 3661000, 'seconds': 3661.0, 'timecode': '01:01:01.000'}
    
    Use Cases:
        - Video player seek (event.timestamp.seconds)
        - User display (event.timestamp.timecode)
        - Report export (all three formats)
        - API integration (flexible format support)
    
    Timecode Format:
        HH:MM:SS.mmm
        - HH: Hours (00-99, zero-padded)
        - MM: Minutes (00-59, zero-padded)
        - SS: Seconds (00-59, zero-padded)
        - mmm: Milliseconds (000-999, zero-padded)
    
    Video Editor Compatibility:
        - Premiere Pro: HH:MM:SS:FF (frames, not milliseconds)
        - Final Cut Pro: HH:MM:SS:FF
        - DaVinci Resolve: HH:MM:SS:FF
        - Avid: HH:MM:SS:FF
        
        To convert for video editors at 24fps:
        frames = int((milliseconds / 1000) * 24)
        timecode = f"{hours:02d}:{minutes:02d}:{seconds:02d}:{frames:02d}"
    """
    seconds_total = milliseconds / 1000.0
    hours = int(seconds_total // 3600)
    minutes = int((seconds_total % 3600) // 60)
    seconds = int(seconds_total % 60)
    millis = int(milliseconds % 1000)
    
    timecode = f"{hours:02d}:{minutes:02d}:{seconds:02d}.{millis:03d}"
    
    return {
        'milliseconds': milliseconds,
        'seconds': round(seconds_total, 3),
        'timecode': timecode
    }
```

### 7.5 Category Normalization

```python
def _normalise_selected_categories(categories_param):
    """
    Parse and validate comma-separated category string.
    
    Args:
        categories_param (str): Comma-separated categories from request
            Examples:
                - "Explicit Nudity,Violence"
                - "Drugs, Alcohol, Tobacco"  (spaces trimmed)
                - ""  (empty = all categories)
                - None  (all categories)
    
    Returns:
        list: Validated category names (empty list = all categories)
            Examples:
                - ["Explicit Nudity", "Violence"]
                - []  (all categories)
    
    Validation:
        - Trims whitespace from each category
        - Ignores empty strings
        - Case-sensitive matching (must match MODERATION_CATEGORY_OPTIONS exactly)
        - Invalid categories are silently filtered (not rejected)
    
    Examples:
        >>> _normalise_selected_categories("Explicit Nudity,Violence")
        ["Explicit Nudity", "Violence"]
        
        >>> _normalise_selected_categories("Drugs, Alcohol")
        ["Drugs", "Alcohol"]
        
        >>> _normalise_selected_categories("")
        []
        
        >>> _normalise_selected_categories("Invalid Category,Violence")
        ["Violence"]  # Invalid category filtered out
    
    Frontend Usage:
        const categories = selectedCategories.join(',');  // "Violence,Drugs"
        formData.append('categories', categories);
    
    Backend Processing:
        selected_categories = _normalise_selected_categories(request.form.get('categories', ''))
        if not selected_categories:
            # Empty list = include all categories
            filter_all = False
        else:
            # Non-empty list = filter by these categories only
            filter_all = True
    """
    if not categories_param:
        return []  # Empty = all categories
    
    # Split by comma and trim whitespace
    raw_categories = [cat.strip() for cat in categories_param.split(',')]
    
    # Validate against known categories
    valid_category_keys = {opt['key'] for opt in MODERATION_CATEGORY_OPTIONS}
    
    # Filter to only valid categories
    validated = [cat for cat in raw_categories if cat in valid_category_keys]
    
    return validated
```

---

## 8. Results Processing & Filtering

### 8.1 Polling Loop Implementation

```python
def _poll_moderation_results(job_id, min_confidence, selected_categories):
    """
    Synchronously poll Rekognition GetContentModeration API until job completes.
    
    Args:
        job_id (str): Rekognition job ID (from StartContentModeration)
        min_confidence (float): Confidence threshold (0-100) - applied client-side
        selected_categories (list): Category filter (empty = all categories)
    
    Returns:
        dict: {
            'status': 'SUCCEEDED' | 'FAILED',
            'labels': [...]  # Raw ModerationLabels from AWS
            'error': str  # Only present if status == 'FAILED'
        }
    
    Raises:
        TimeoutError: If polling exceeds MAX_WAIT_SECONDS (5 minutes)
        ClientError: If AWS API call fails
    
    Polling Strategy:
        - Interval: 2 seconds (POLL_INTERVAL_SECONDS)
        - Timeout: 300 seconds / 5 minutes (MAX_WAIT_SECONDS)
        - Max iterations: 150 polls (300s ÷ 2s)
        - Pagination: Automatically handles NextToken for large result sets
    
    Job Status Flow:
        IN_PROGRESS → IN_PROGRESS → ... → SUCCEEDED
                                      └──► FAILED
    
    Pagination:
        AWS returns up to 1000 labels per GetContentModeration call.
        If more results exist, response includes NextToken.
        This function automatically fetches all pages.
    
    Performance Tuning:
        Short videos (<30s): Keep 2s interval
        Medium videos (30s-2min): Consider 3-5s interval
        Long videos (>2min): Consider 5-10s interval
        
        Trade-off:
            Shorter interval = faster user feedback, higher AWS API costs
            Longer interval = lower costs, slower feedback
    
    Cost Considerations:
        GetContentModeration API: $0.10 per 1000 requests
        Example: 150 polls = $0.015 per video
        
        Optimization: Increase POLL_INTERVAL_SECONDS for cost savings
    
    Example Usage:
        result = _poll_moderation_results(
            job_id='abc123...',
            min_confidence=75.0,
            selected_categories=['Violence', 'Explicit Nudity']
        )
        
        if result['status'] == 'SUCCEEDED':
            for label in result['labels']:
                print(f"{label['Timestamp']}ms: {label['ModerationLabel']['Name']}")
        else:
            print(f"Job failed: {result['error']}")
    """
    start_time = time.time()
    all_labels = []
    
    print(f"Polling job {job_id}...")
    
    while True:
        elapsed = time.time() - start_time
        
        # TIMEOUT CHECK
        if elapsed > MAX_WAIT_SECONDS:
            raise TimeoutError(
                f"Moderation job {job_id} exceeded {MAX_WAIT_SECONDS}s timeout. "
                f"Consider increasing CONTENT_MODERATION_MAX_WAIT_SECONDS."
            )
        
        try:
            # POLL AWS API
            response = rekognition_client.get_content_moderation(
                JobId=job_id,
                MaxResults=1000,  # Max labels per page
                SortBy='TIMESTAMP'  # Chronological order
            )
            
            status = response.get('JobStatus')
            print(f"Job status: {status} (elapsed: {elapsed:.1f}s)")
            
            # CHECK STATUS
            if status == 'SUCCEEDED':
                # COLLECT RESULTS
                labels = response.get('ModerationLabels', [])
                all_labels.extend(labels)
                
                # PAGINATION: Fetch remaining pages
                next_token = response.get('NextToken')
                while next_token:
                    print(f"Fetching next page (token: {next_token[:20]}...)")
                    page_response = rekognition_client.get_content_moderation(
                        JobId=job_id,
                        NextToken=next_token,
                        MaxResults=1000,
                        SortBy='TIMESTAMP'
                    )
                    page_labels = page_response.get('ModerationLabels', [])
                    all_labels.extend(page_labels)
                    next_token = page_response.get('NextToken')
                
                print(f"Job succeeded. Total labels: {len(all_labels)}")
                return {
                    'status': 'SUCCEEDED',
                    'labels': all_labels
                }
            
            elif status == 'FAILED':
                # JOB FAILED
                error_message = response.get('StatusMessage', 'Unknown error')
                print(f"Job failed: {error_message}")
                return {
                    'status': 'FAILED',
                    'error': error_message
                }
            
            elif status == 'IN_PROGRESS':
                # STILL PROCESSING: Wait and poll again
                time.sleep(POLL_INTERVAL_SECONDS)
                continue
            
            else:
                # UNKNOWN STATUS
                raise ValueError(f"Unexpected job status: {status}")
        
        except ClientError as e:
            # AWS API ERROR
            error_code = e.response['Error']['Code']
            error_message = e.response['Error']['Message']
            raise Exception(f"GetContentModeration error ({error_code}): {error_message}")
```

### 8.2 Category Matching

```python
def _category_matches(parent_name, selected_categories):
    """
    Check if moderation label's category matches user-selected filters.
    
    Args:
        parent_name (str): Category from AWS (ModerationLabel.ParentName)
            Examples: "Violence", "Explicit Nudity", "Drugs"
        selected_categories (list): User-selected categories
            Examples: ["Violence", "Drugs"]
            Empty list = match all categories
    
    Returns:
        bool: True if label should be included, False if filtered out
    
    Logic:
        - Empty selected_categories: Return True (include all)
        - Non-empty selected_categories: Return True only if parent_name in list
    
    Case Sensitivity:
        - Exact match required (case-sensitive)
        - "Violence" != "violence"
        - AWS always returns title case ("Explicit Nudity", not "explicit nudity")
    
    Examples:
        >>> _category_matches("Violence", ["Violence", "Drugs"])
        True
        
        >>> _category_matches("Alcohol", ["Violence", "Drugs"])
        False
        
        >>> _category_matches("Violence", [])
        True  # Empty list = include all
        
        >>> _category_matches("Explicit Nudity", ["Explicit Nudity"])
        True
    
    Usage in Filtering:
        for label in raw_labels:
            parent_name = label['ModerationLabel']['ParentName']
            if not _category_matches(parent_name, selected_categories):
                continue  # Skip this label
            # Process label...
    
    Performance:
        O(1) if selected_categories is empty
        O(n) if selected_categories has n items (list membership test)
        For better performance with many categories, convert to set:
            selected_categories_set = set(selected_categories)
            return parent_name in selected_categories_set
    """
    if not selected_categories:
        return True  # No filter = include all
    
    return parent_name in selected_categories
```

### 8.3 Event Summarization

```python
def _summarise_events(events):
    """
    Generate summary statistics from moderation events.
    
    Args:
        events (list): Formatted moderation events
            [
                {
                    "timestamp": {...},
                    "category": "Violence",
                    "label": "Graphic Violence",
                    "confidence": 95.3
                },
                ...
            ]
    
    Returns:
        dict: {
            'totalFindings': int,  # Total number of events
            'categories': {        # Count per category
                'Violence': int,
                'Explicit Nudity': int,
                ...
            }
        }
    
    Examples:
        >>> events = [
        ...     {"category": "Violence", "label": "Graphic Violence", "confidence": 95},
        ...     {"category": "Violence", "label": "Weapons", "confidence": 87},
        ...     {"category": "Drugs", "label": "Drug Use", "confidence": 92}
        ... ]
        >>> _summarise_events(events)
        {
            'totalFindings': 3,
            'categories': {
                'Violence': 2,
                'Drugs': 1
            }
        }
        
        >>> _summarise_events([])
        {
            'totalFindings': 0,
            'categories': {}
        }
    
    Use Cases:
        - Dashboard widgets: "18 violations found in 3 categories"
        - Category prioritization: "12 Violence, 5 Drugs, 1 Alcohol"
        - Report summaries: "Total findings: 18"
        - Compliance reporting: Category-level counts
    
    Frontend Display:
        <Card>
          <h3>Summary</h3>
          <p>Total findings: {summary.totalFindings}</p>
          <ul>
            {Object.entries(summary.categories).map(([category, count]) => (
              <li key={category}>{category}: {count}</li>
            ))}
          </ul>
        </Card>
    
    Performance:
        Time Complexity: O(n) where n = len(events)
        Space Complexity: O(k) where k = number of unique categories (max 11)
    """
    if not events:
        return {
            'totalFindings': 0,
            'categories': {}
        }
    
    category_counts = {}
    
    for event in events:
        category = event.get('category', '')
        if category:
            category_counts[category] = category_counts.get(category, 0) + 1
    
    return {
        'totalFindings': len(events),
        'categories': category_counts
    }
```

---

## 9. Report Storage & Retrieval

### 9.1 Report Storage Function

```python
def _store_report(job_id, report):
    """
    Save moderation report to local JSON file.
    
    Args:
        job_id (str): Rekognition job ID (used as filename)
        report (dict): Complete moderation report
            {
                "jobId": str,
                "video": {...},
                "events": [...],
                "summary": {...},
                "requestMeta": {...},
                "metadata": {...}
            }
    
    Returns:
        Path: File path where report was saved
    
    Raises:
        OSError: If file write fails (permissions, disk full, etc.)
        JSONEncodeError: If report cannot be serialized to JSON
    
    File Location:
        reports/<job_id>.json
        
        Example:
            job_id = "abc123def456..."
            path = reports/abc123def456.json
    
    File Format:
        JSON with 2-space indentation (pretty-printed)
        Ensures readability for manual inspection
    
    File Permissions:
        Default: 0o644 (rw-r--r--)
        Owner: Read/write
        Group: Read
        Others: Read
    
    Retention Policy:
        Files persist indefinitely (no automatic cleanup)
        
        Recommended cleanup strategies:
        
        1. Age-based deletion (cron job):
           find reports/ -name "*.json" -mtime +30 -delete
           
        2. Size-based rotation:
           if [ $(du -sm reports | cut -f1) -gt 1000 ]; then
             rm reports/$(ls -t reports | tail -1)
           fi
        
        3. Python cleanup script:
           def cleanup_old_reports(days=30):
               cutoff = time.time() - (days * 86400)
               for report_file in REPORTS_DIR.glob('*.json'):
                   if report_file.stat().st_mtime < cutoff:
                       report_file.unlink()
    
    Example Usage:
        report = {
            "jobId": "abc123",
            "events": [...],
            "summary": {...}
        }
        
        path = _store_report("abc123", report)
        print(f"Report saved to {path}")
        # Output: Report saved to reports/abc123.json
    
    Integration with Archive Systems:
        # Upload to S3 for long-term storage
        def archive_report(job_id, report):
            local_path = _store_report(job_id, report)
            s3_key = f"reports/{job_id}.json"
            s3_client.upload_file(
                str(local_path),
                'archive-bucket',
                s3_key
            )
            local_path.unlink()  # Delete local copy
    """
    report_path = REPORTS_DIR / f"{job_id}.json"
    
    try:
        with open(report_path, 'w') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        
        print(f"Report saved: {report_path}")
        return report_path
    
    except OSError as e:
        raise Exception(f"Failed to save report: {str(e)}")
    except json.JSONEncodeError as e:
        raise Exception(f"Failed to serialize report to JSON: {str(e)}")
```

### 9.2 Report Structure

```json
{
  "jobId": "abc123def456ghi789jkl012mno345pqr678stu901vwx234yz567",
  "video": {
    "objectKey": "moderation/20251022_143022_sample.mp4",
    "bucket": "my-content-bucket"
  },
  "events": [
    {
      "timestamp": {
        "milliseconds": 5234,
        "seconds": 5.234,
        "timecode": "00:00:05.234"
      },
      "category": "Violence",
      "label": "Graphic Violence",
      "confidence": 95.3
    },
    {
      "timestamp": {
        "milliseconds": 8901,
        "seconds": 8.901,
        "timecode": "00:00:08.901"
      },
      "category": "Violence",
      "label": "Weapons",
      "confidence": 87.6
    },
    {
      "timestamp": {
        "milliseconds": 12345,
        "seconds": 12.345,
        "timecode": "00:00:12.345"
      },
      "category": "Drugs",
      "label": "Drug Use",
      "confidence": 92.1
    }
  ],
  "summary": {
    "totalFindings": 3,
    "categories": {
      "Violence": 2,
      "Drugs": 1
    }
  },
  "requestMeta": {
    "selectedCategories": ["Violence", "Drugs"],
    "minConfidence": 75
  },
  "metadata": {
    "analysisDurationSeconds": 18.23
  }
}
```

### 9.3 Report File Management

**Directory Structure:**

```
contentModeration/
└── reports/
    ├── abc123def456ghi789.json              # Report 1
    ├── jkl012mno345pqr678.json              # Report 2
    ├── stu901vwx234yz567ab.json             # Report 3
    └── ...
```

**File Naming Convention:**

```python
# Job ID is used as filename
job_id = "abc123def456ghi789jkl012mno345pqr678stu901vwx234yz567"
filename = f"{job_id}.json"
# Result: abc123def456ghi789jkl012mno345pqr678stu901vwx234yz567.json
```

**Storage Considerations:**

| Aspect | Details |
|--------|---------|
| **File Size** | Typical: 5-50 KB per report |
| **Growth Rate** | ~10-100 reports/day (depends on usage) |
| **Disk Usage** | 1 GB = ~20,000-200,000 reports |
| **Retrieval Speed** | O(1) - direct file access by job ID |
| **Backup Strategy** | Daily sync to S3 or backup server |
| **Retention** | Recommend 30-90 days local, indefinite S3 archive |

**Cleanup Script Example:**

```python
#!/usr/bin/env python3
"""
Cleanup old moderation reports.

Usage:
    python cleanup_reports.py --days 30
"""

import argparse
from pathlib import Path
import time

def cleanup_reports(reports_dir, days=30):
    """Delete reports older than specified days."""
    cutoff_time = time.time() - (days * 86400)
    deleted_count = 0
    
    for report_file in Path(reports_dir).glob('*.json'):
        if report_file.stat().st_mtime < cutoff_time:
            report_file.unlink()
            deleted_count += 1
            print(f"Deleted: {report_file.name}")
    
    print(f"Cleanup complete. Deleted {deleted_count} reports.")

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--days', type=int, default=30,
                        help='Delete reports older than N days')
    args = parser.parse_args()
    
    cleanup_reports('reports', args.days)
```

**Cron Job for Automated Cleanup:**

```bash
# Add to crontab: crontab -e
# Run cleanup daily at 2 AM
0 2 * * * cd /path/to/contentModeration && python3 cleanup_reports.py --days 30
```

---

## End of Part 2

**This concludes Part 2 of the Content Moderation Service reference documentation.**

### What's Covered in Part 2:
✅ Backend Deep Dive (Flask Routes)  
✅ Helper Functions (S3, Rekognition, Timestamp)  
✅ Results Processing & Filtering Logic  
✅ Report Storage & Retrieval  
✅ Synchronous Polling Implementation  

### Coming in Part 3:
📄 Frontend Architecture (React Component Structure)  
📄 Upload Component (Drag-and-Drop)  
📄 Category Selection & Confidence Control  
📄 Results Display (Timeline Table)  
📄 Error Handling & Status Management  

### Coming in Part 4:
📄 API Reference (Complete Examples)  
📄 Deployment Guide (Production Setup)  
📄 Troubleshooting & Common Issues  
📄 Performance Optimization  
📄 Security Best Practices  
📄 Production Checklist  

---

**Document Navigation:**
- **Previous:** [Part 1 - Foundation & AWS Integration](CONTENT_MODERATION_PART1.md)
- **Current:** Part 2 - Backend Implementation
- **Next:** [Part 3 - Frontend Architecture](CONTENT_MODERATION_PART3.md)
- **Index:** [Documentation Index](DOCUMENTATION_INDEX.md)

**Last Updated:** October 22, 2025  
**Maintainer:** MediaGenAI Platform Team  
**Service Version:** 1.0

# Content Moderation Service - Part 3 of 4
## Frontend Architecture, User Interface & Results Display

**Document Version:** 1.0  
**Last Updated:** October 22, 2025  
**Service Port:** 5006  
**Part:** 3/4 - Frontend Implementation

---

## Table of Contents - Part 3

10. [Frontend Architecture](#10-frontend-architecture)
11. [Upload Component](#11-upload-component)
12. [Category Selection & Confidence Control](#12-category-selection--confidence-control)
13. [Results Display](#13-results-display)
14. [Error Handling & Status Management](#14-error-handling--status-management)

---

## 10. Frontend Architecture

### 10.1 Component Overview

**File:** `frontend/src/ContentModeration.js` (644 lines)

```javascript
/**
 * Content Moderation Component
 * 
 * A comprehensive React component for uploading videos and analyzing them
 * for potentially inappropriate content using AWS Rekognition.
 * 
 * Key Features:
 * - Drag-and-drop video upload
 * - File type and size validation
 * - Video preview generation
 * - 11 moderation category checkboxes
 * - Adjustable confidence threshold slider
 * - Real-time upload progress tracking
 * - Synchronous analysis with loading states
 * - Results display with timeline table
 * - Summary statistics cards
 * - JSON report download
 * 
 * State Management:
 * - selectedFile: Video file object
 * - previewUrl: Blob URL for video preview
 * - selectedCategories: Array of enabled categories
 * - minConfidence: Confidence threshold (0-100)
 * - processing: Boolean for loading state
 * - status: Status message string
 * - error: Error message string
 * - result: API response object
 * - uploadProgress: Upload percentage (0-100)
 * 
 * API Integration:
 * - POST /moderate: Upload and analyze video
 * - GET /result/<job_id>: Download report
 * 
 * Dependencies:
 * - React 18.x
 * - styled-components (UI styling)
 * - axios (HTTP client)
 */

import React, { useState } from 'react';
import styled from 'styled-components';
import axios from 'axios';
```

### 10.2 Configuration & Constants

```javascript
// API BASE URL RESOLUTION
function resolveModerationApiBase() {
  /**
   * Dynamically resolve API base URL based on environment.
   * 
   * Logic:
   * 1. Development (localhost): Use http://localhost:5006
   * 2. Production with env var: Use REACT_APP_MODERATION_API_BASE
   * 3. Fallback: Same hostname, port 5006
   * 
   * Environment Variables:
   * - REACT_APP_MODERATION_API_BASE: Override for production
   *   Example: "https://api.mediagenai.com/moderation"
   * 
   * Examples:
   * - localhost:3000 → http://localhost:5006
   * - mediagenai.com → https://mediagenai.com:5006
   * - Custom: https://api.mediagenai.com/moderation
   */
  
  // Development environment
  if (window.location.hostname === 'localhost' || 
      window.location.hostname === '127.0.0.1') {
    return 'http://localhost:5006';
  }
  
  // Production with environment variable
  const prodBase = process.env.REACT_APP_MODERATION_API_BASE;
  if (prodBase) {
    return prodBase;
  }
  
  // Fallback: same domain, different port
  return `${window.location.protocol}//${window.location.hostname}:5006`;
}

const API_BASE = resolveModerationApiBase();

// MODERATION CATEGORY OPTIONS (must match backend)
const CATEGORY_OPTIONS = [
  { key: 'Explicit Nudity', label: 'Explicit Nudity' },
  { key: 'Suggestive', label: 'Suggestive' },
  { key: 'Violence', label: 'Violence' },
  { key: 'Visually Disturbing', label: 'Visually Disturbing' },
  { key: 'Rude Gestures', label: 'Rude Gestures' },
  { key: 'Drugs', label: 'Drugs' },
  { key: 'Tobacco', label: 'Tobacco' },
  { key: 'Alcohol', label: 'Alcohol' },
  { key: 'Gambling', label: 'Gambling' },
  { key: 'Hate Symbols', label: 'Hate Symbols' },
  { key: 'Weapons', label: 'Weapons' }
];

// TIMEOUT CONFIGURATION
const DEFAULT_TIMEOUT_MS = 300000;  // 5 minutes (matches backend MAX_WAIT_SECONDS)

// AXIOS DEFAULT CONFIGURATION
axios.defaults.timeout = DEFAULT_TIMEOUT_MS;
```

### 10.3 State Management

```javascript
export default function ContentModeration() {
  // FILE UPLOAD STATE
  const [selectedFile, setSelectedFile] = useState(null);
  /**
   * Type: File object or null
   * Description: Selected video file from file input or drag-and-drop
   * Properties:
   *   - name: Filename (e.g., "video.mp4")
   *   - size: File size in bytes
   *   - type: MIME type (e.g., "video/mp4")
   *   - lastModified: Timestamp
   */
  
  const [previewUrl, setPreviewUrl] = useState(null);
  /**
   * Type: String (Blob URL) or null
   * Description: Object URL for video preview
   * Example: "blob:http://localhost:3000/abc-123-def-456"
   * Cleanup: Must call URL.revokeObjectURL() to prevent memory leaks
   */
  
  // MODERATION CONFIGURATION STATE
  const [selectedCategories, setSelectedCategories] = useState(
    CATEGORY_OPTIONS.map(opt => opt.key)
  );
  /**
   * Type: Array of strings
   * Description: Enabled moderation categories
   * Default: All 11 categories selected
   * Example: ["Explicit Nudity", "Violence", "Drugs"]
   */
  
  const [minConfidence, setMinConfidence] = useState(75);
  /**
   * Type: Number (0-100)
   * Description: Confidence threshold percentage
   * Default: 75 (matches backend DEFAULT_MIN_CONFIDENCE)
   * User Control: Range slider
   */
  
  // PROCESSING STATE
  const [processing, setProcessing] = useState(false);
  /**
   * Type: Boolean
   * Description: True during video upload and analysis
   * Use: Disable buttons, show loading spinner
   */
  
  const [status, setStatus] = useState('');
  /**
   * Type: String
   * Description: Status message for user feedback
   * Examples:
   *   - "Uploading video..."
   *   - "Analysing video..."
   *   - "Analysis complete"
   */
  
  const [error, setError] = useState('');
  /**
   * Type: String
   * Description: Error message (if any)
   * Display: Red banner when non-empty
   */
  
  const [uploadProgress, setUploadProgress] = useState(null);
  /**
   * Type: Number (0-100) or null
   * Description: Upload progress percentage
   * Display: Progress bar or percentage text
   */
  
  // RESULTS STATE
  const [result, setResult] = useState(null);
  /**
   * Type: Object or null
   * Description: API response from /moderate endpoint
   * Structure:
   *   {
   *     jobId: string,
   *     video: { objectKey: string, bucket: string },
   *     events: [{ timestamp, category, label, confidence }, ...],
   *     summary: { totalFindings: number, categories: {...} },
   *     requestMeta: { selectedCategories: [...], minConfidence: number },
   *     metadata: { analysisDurationSeconds: number }
   *   }
   */
  
  // DERIVED STATE (computed from result)
  const moderationEvents = result?.events || [];
  const summary = result?.summary;
  const requestMeta = result?.requestMeta;
  const metadata = result?.metadata;
  
  // ... (rest of component implementation)
}
```

### 10.4 Styled Components (UI Elements)

```javascript
// LAYOUT COMPONENTS

const Page = styled.div`
  max-width: 1200px;
  margin: 0 auto;
  padding: 2rem 1rem;
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Roboto', 'Oxygen',
    'Ubuntu', 'Cantarell', 'Fira Sans', 'Droid Sans', 'Helvetica Neue', sans-serif;
  color: #333;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  min-height: 100vh;
`;

const PageTitle = styled.h1`
  font-size: 2.5rem;
  font-weight: 700;
  text-align: center;
  margin-bottom: 0.5rem;
  color: #fff;
  text-shadow: 0 2px 4px rgba(0,0,0,0.2);
`;

const PageSubtitle = styled.p`
  font-size: 1.1rem;
  text-align: center;
  margin-bottom: 2rem;
  color: rgba(255, 255, 255, 0.9);
`;

// UPLOAD CARD

const UploadCard = styled.div`
  background: #fff;
  border-radius: 12px;
  box-shadow: 0 10px 40px rgba(0, 0, 0, 0.1);
  padding: 2rem;
  margin-bottom: 2rem;
`;

const DropZone = styled.div`
  border: 3px dashed ${props => props.$isDragOver ? '#667eea' : '#ccc'};
  border-radius: 12px;
  padding: 3rem 2rem;
  text-align: center;
  background: ${props => props.$isDragOver ? 'rgba(102, 126, 234, 0.05)' : '#f9fafb'};
  cursor: pointer;
  transition: all 0.3s ease;
  
  &:hover {
    border-color: #667eea;
    background: rgba(102, 126, 234, 0.05);
  }
`;

const FileInput = styled.input`
  display: none;
`;

const UploadIcon = styled.div`
  font-size: 3rem;
  margin-bottom: 1rem;
  color: #667eea;
`;

const UploadText = styled.div`
  font-size: 1.2rem;
  font-weight: 600;
  color: #333;
  margin-bottom: 0.5rem;
`;

const UploadHint = styled.div`
  font-size: 0.9rem;
  color: #666;
`;

// VIDEO PREVIEW

const PreviewWrap = styled.div`
  margin-top: 1.5rem;
  text-align: center;
`;

const PreviewVideo = styled.video`
  max-width: 100%;
  max-height: 300px;
  border-radius: 8px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
  margin-bottom: 0.5rem;
`;

// CONFIGURATION CONTROLS

const ConfidenceRow = styled.div`
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-top: 1.5rem;
  padding: 1rem;
  background: #f9fafb;
  border-radius: 8px;
  
  span {
    font-size: 0.95rem;
    color: #333;
  }
`;

const Slider = styled.input`
  flex: 1;
  margin-left: 1.5rem;
  height: 6px;
  border-radius: 3px;
  outline: none;
  background: linear-gradient(
    to right,
    #667eea 0%,
    #667eea ${props => props.value}%,
    #ddd ${props => props.value}%,
    #ddd 100%
  );
  
  &::-webkit-slider-thumb {
    appearance: none;
    width: 18px;
    height: 18px;
    border-radius: 50%;
    background: #667eea;
    cursor: pointer;
    box-shadow: 0 2px 4px rgba(0, 0, 0, 0.2);
  }
  
  &::-moz-range-thumb {
    width: 18px;
    height: 18px;
    border-radius: 50%;
    background: #667eea;
    cursor: pointer;
    border: none;
    box-shadow: 0 2px 4px rgba(0, 0, 0, 0.2);
  }
`;

// CATEGORY CHECKBOXES

const OptionsGrid = styled.div`
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
  gap: 1rem;
  margin-top: 1.5rem;
`;

const OptionCard = styled.label`
  display: flex;
  align-items: center;
  padding: 1rem;
  background: #f9fafb;
  border: 2px solid ${props => props.$checked ? '#667eea' : '#e5e7eb'};
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.2s ease;
  
  &:hover {
    border-color: #667eea;
    background: rgba(102, 126, 234, 0.05);
  }
  
  div {
    flex: 1;
    margin-left: 0.75rem;
    
    > div:first-child {
      font-weight: 600;
      color: #333;
      margin-bottom: 0.25rem;
    }
  }
`;

const OptionCheckbox = styled.input`
  width: 20px;
  height: 20px;
  cursor: pointer;
  accent-color: #667eea;
`;

const Badge = styled.span`
  display: inline-block;
  padding: 0.25rem 0.75rem;
  background: ${props => props.$checked ? '#667eea' : '#e5e7eb'};
  color: ${props => props.$checked ? '#fff' : '#666'};
  border-radius: 12px;
  font-size: 0.75rem;
  font-weight: 600;
  text-transform: uppercase;
`;

// ACTION BUTTONS

const ActionsRow = styled.div`
  display: flex;
  gap: 1rem;
  margin-top: 1.5rem;
`;

const PrimaryButton = styled.button`
  flex: 1;
  padding: 1rem 2rem;
  font-size: 1.1rem;
  font-weight: 600;
  color: #fff;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  border: none;
  border-radius: 8px;
  cursor: ${props => props.disabled ? 'not-allowed' : 'pointer'};
  opacity: ${props => props.disabled ? 0.6 : 1};
  transition: all 0.3s ease;
  box-shadow: 0 4px 12px rgba(102, 126, 234, 0.3);
  
  &:hover:not(:disabled) {
    transform: translateY(-2px);
    box-shadow: 0 6px 16px rgba(102, 126, 234, 0.4);
  }
  
  &:active:not(:disabled) {
    transform: translateY(0);
  }
`;

const SecondaryButton = styled.button`
  flex: 1;
  padding: 1rem 2rem;
  font-size: 1.1rem;
  font-weight: 600;
  color: #667eea;
  background: #fff;
  border: 2px solid #667eea;
  border-radius: 8px;
  cursor: ${props => props.disabled ? 'not-allowed' : 'pointer'};
  opacity: ${props => props.disabled ? 0.6 : 1};
  transition: all 0.3s ease;
  
  &:hover:not(:disabled) {
    background: rgba(102, 126, 234, 0.1);
  }
`;

// STATUS BANNERS

const StatusBanner = styled.div`
  margin-top: 1rem;
  padding: 1rem;
  border-radius: 8px;
  text-align: center;
  font-weight: 600;
  background: ${props => props.$error ? '#fee2e2' : '#dbeafe'};
  color: ${props => props.$error ? '#991b1b' : '#1e40af'};
  border: 2px solid ${props => props.$error ? '#fca5a5' : '#93c5fd'};
`;

// RESULTS DISPLAY

const ResultsGrid = styled.div`
  display: grid;
  grid-template-columns: 1fr;
  gap: 2rem;
  margin-top: 2rem;
  
  @media (min-width: 768px) {
    grid-template-columns: 1fr 2fr;
  }
`;

const Card = styled.div`
  background: #fff;
  border-radius: 12px;
  box-shadow: 0 10px 40px rgba(0, 0, 0, 0.1);
  padding: 2rem;
`;

const CardTitle = styled.h2`
  font-size: 1.5rem;
  font-weight: 700;
  color: #333;
  margin-bottom: 1rem;
  border-bottom: 3px solid #667eea;
  padding-bottom: 0.5rem;
`;

const SummaryList = styled.ul`
  list-style: none;
  padding: 0;
  margin: 0;
`;

const SummaryItem = styled.li`
  padding: 0.75rem 0;
  border-bottom: 1px solid #e5e7eb;
  font-size: 0.95rem;
  color: #555;
  
  &:last-child {
    border-bottom: none;
  }
  
  strong {
    color: #333;
    margin-right: 0.5rem;
  }
`;

const DownloadLink = styled.a`
  color: #667eea;
  text-decoration: none;
  font-weight: 600;
  
  &:hover {
    text-decoration: underline;
  }
`;

// EVENTS TABLE

const EventsTable = styled.table`
  width: 100%;
  border-collapse: collapse;
  
  thead {
    background: #f9fafb;
  }
`;

const EventsHeadCell = styled.th`
  padding: 0.75rem;
  text-align: left;
  font-weight: 600;
  color: #333;
  border-bottom: 2px solid #e5e7eb;
`;

const EventsCell = styled.td`
  padding: 0.75rem;
  border-bottom: 1px solid #e5e7eb;
  font-size: 0.9rem;
  color: #555;
`;

const EmptyState = styled.div`
  text-align: center;
  padding: 3rem 2rem;
  color: #666;
  font-size: 1.1rem;
  background: #f9fafb;
  border-radius: 8px;
  margin-top: 2rem;
`;
```

---

## 11. Upload Component

### 11.1 File Selection Handler

```javascript
function handleFileSelection(file) {
  /**
   * Process selected file and generate preview.
   * 
   * Steps:
   * 1. Revoke previous preview URL (prevent memory leaks)
   * 2. Validate file type
   * 3. Validate file size (<2GB)
   * 4. Generate Blob URL for preview
   * 5. Update state
   * 6. Clear previous results and errors
   * 
   * Args:
   *   file (File): File object from input or drag-and-drop
   * 
   * Validation:
   *   - Type: video/* MIME types only
   *   - Size: Maximum 2GB (2,147,483,648 bytes)
   * 
   * Error Handling:
   *   - Invalid type: Show error message
   *   - Too large: Show error message with size limit
   *   - Clear file selection on validation failure
   */
  
  // Clean up previous preview URL
  if (previewUrl) {
    URL.revokeObjectURL(previewUrl);
  }
  
  // Validate file type
  if (!file.type.startsWith('video/')) {
    setError('Please select a video file (MP4, MOV, MKV, AVI, WEBM).');
    setSelectedFile(null);
    setPreviewUrl(null);
    return;
  }
  
  // Validate file size (2GB max)
  const maxSize = 2 * 1024 * 1024 * 1024;  // 2GB in bytes
  if (file.size > maxSize) {
    setError(`File too large. Maximum size is 2GB. Your file is ${(file.size / (1024 * 1024 * 1024)).toFixed(2)}GB.`);
    setSelectedFile(null);
    setPreviewUrl(null);
    return;
  }
  
  // Generate preview URL
  const videoUrl = URL.createObjectURL(file);
  
  // Update state
  setSelectedFile(file);
  setPreviewUrl(videoUrl);
  setError('');
  setResult(null);  // Clear previous results
  setStatus('');
}
```

### 11.2 File Input Handler

```javascript
function onFileInputChange(event) {
  /**
   * Handle file selection from file input.
   * 
   * Triggered by:
   *   - Clicking "Choose file" button
   *   - Clicking drop zone (triggers hidden file input)
   * 
   * Event Structure:
   *   event.target.files: FileList (array-like)
   *   event.target.files[0]: First selected file
   * 
   * Behavior:
   *   - Only process first file (ignore multiple selections)
   *   - Delegate to handleFileSelection for validation
   */
  
  const file = event.target.files && event.target.files[0];
  if (file) {
    handleFileSelection(file);
  }
}
```

### 11.3 Drag-and-Drop Handler

```javascript
function onDrop(event) {
  /**
   * Handle file drop from drag-and-drop.
   * 
   * Steps:
   * 1. Prevent default browser behavior (opening file in new tab)
   * 2. Stop event propagation
   * 3. Extract file from dataTransfer
   * 4. Validate and process file
   * 5. Reset drag-over state
   * 
   * Event Structure:
   *   event.dataTransfer.files: FileList
   *   event.dataTransfer.items: DataTransferItemList
   * 
   * Behavior:
   *   - Only process first dropped file
   *   - Ignore non-file drops (text, URLs, etc.)
   */
  
  event.preventDefault();
  event.stopPropagation();
  
  const file = event.dataTransfer.files && event.dataTransfer.files[0];
  if (file) {
    handleFileSelection(file);
  }
}

function onDragOver(event) {
  /**
   * Handle drag-over event (required for drop to work).
   * 
   * Purpose:
   *   - Prevent default browser behavior
   *   - Enable drop zone visual feedback
   * 
   * Without this handler, onDrop will not fire.
   */
  
  event.preventDefault();
  event.stopPropagation();
}

function onDragEnter(event) {
  /**
   * Handle drag-enter event (visual feedback).
   * 
   * Purpose:
   *   - Update drop zone styling
   *   - Show "drop here" indicator
   * 
   * State Update:
   *   - Set isDragOver to true (changes border color)
   */
  
  event.preventDefault();
  setIsDragOver(true);
}

function onDragLeave(event) {
  /**
   * Handle drag-leave event (reset visual feedback).
   * 
   * Purpose:
   *   - Reset drop zone styling
   *   - Remove "drop here" indicator
   * 
   * State Update:
   *   - Set isDragOver to false (restores default border)
   */
  
  event.preventDefault();
  setIsDragOver(false);
}
```

### 11.4 Upload JSX

```javascript
// FILE UPLOAD DROP ZONE

<UploadCard>
  <DropZone
    $isDragOver={isDragOver}
    onClick={() => fileInputRef.current && fileInputRef.current.click()}
    onDrop={onDrop}
    onDragOver={onDragOver}
    onDragEnter={onDragEnter}
    onDragLeave={onDragLeave}
  >
    <UploadIcon>🎬</UploadIcon>
    <UploadText>
      Drag & drop video here, or click to choose
    </UploadText>
    <UploadHint>
      Supported formats: MP4, MOV, MKV, AVI, WEBM (Max 2GB)
    </UploadHint>
    
    <FileInput
      ref={fileInputRef}
      type="file"
      accept="video/*"
      onChange={onFileInputChange}
    />
  </DropZone>
  
  {/* FILE INFO (shown after selection) */}
  {selectedFile && (
    <ConfidenceRow>
      <span><strong>Selected:</strong> {selectedFile.name}</span>
      <span><strong>Size:</strong> {(selectedFile.size / (1024 * 1024)).toFixed(1)} MB</span>
      <span><strong>Type:</strong> {selectedFile.type || 'Unknown'}</span>
    </ConfidenceRow>
  )}
  
  {/* VIDEO PREVIEW (shown after selection) */}
  {previewUrl && (
    <PreviewWrap>
      <PreviewVideo src={previewUrl} controls preload="metadata" />
      <span>Preview generated from the uploaded asset.</span>
    </PreviewWrap>
  )}
</UploadCard>
```

---

## 12. Category Selection & Confidence Control

### 12.1 Category Toggle Handler

```javascript
function toggleCategory(categoryKey) {
  /**
   * Toggle category selection (checkbox handler).
   * 
   * Logic:
   *   - If category is selected: Remove from array
   *   - If category is not selected: Add to array
   * 
   * Args:
   *   categoryKey (string): Category identifier
   *     Example: "Explicit Nudity", "Violence"
   * 
   * State Update:
   *   - Updates selectedCategories array
   *   - Preserves other selected categories
   * 
   * Examples:
   *   Before: ["Violence", "Drugs", "Alcohol"]
   *   Toggle "Violence": ["Drugs", "Alcohol"]
   *   Toggle "Tobacco": ["Drugs", "Alcohol", "Tobacco"]
   */
  
  setSelectedCategories(prev => {
    if (prev.includes(categoryKey)) {
      // Remove category
      return prev.filter(key => key !== categoryKey);
    } else {
      // Add category
      return [...prev, categoryKey];
    }
  });
}
```

### 12.2 Clear Selection Handler

```javascript
function clearSelection() {
  /**
   * Reset all form state (clear selection button).
   * 
   * Actions:
   *   1. Revoke preview URL (free memory)
   *   2. Clear selected file
   *   3. Clear preview URL
   *   4. Reset categories to all selected
   *   5. Reset confidence to default (75)
   *   6. Clear results
   *   7. Clear errors and status
   * 
   * Triggered by:
   *   - "Clear selection" button
   *   - Starting new analysis
   * 
   * Use Cases:
   *   - Upload different video
   *   - Reset configuration
   *   - Clear previous results
   */
  
  // Clean up preview URL
  if (previewUrl) {
    URL.revokeObjectURL(previewUrl);
  }
  
  // Reset all state
  setSelectedFile(null);
  setPreviewUrl(null);
  setSelectedCategories(CATEGORY_OPTIONS.map(opt => opt.key));  // All selected
  setMinConfidence(75);  // Default confidence
  setResult(null);
  setError('');
  setStatus('');
  setUploadProgress(null);
}
```

### 12.3 Configuration JSX

```javascript
// CONFIDENCE SLIDER

<ConfidenceRow>
  <span><strong>Confidence threshold:</strong> {minConfidence}%</span>
  <Slider
    type="range"
    min="0"
    max="100"
    step="1"
    value={minConfidence}
    onChange={(event) => setMinConfidence(Number(event.target.value))}
  />
</ConfidenceRow>

// CATEGORY CHECKBOXES GRID

<OptionsGrid>
  {CATEGORY_OPTIONS.map((option) => {
    const checked = selectedCategories.includes(option.key);
    return (
      <OptionCard key={option.key} $checked={checked}>
        <OptionCheckbox
          type="checkbox"
          checked={checked}
          onChange={() => toggleCategory(option.key)}
        />
        <div>
          <div>{option.label}</div>
          <Badge $checked={checked}>
            {checked ? 'Included' : 'Excluded'}
          </Badge>
        </div>
      </OptionCard>
    );
  })}
</OptionsGrid>

// ACTION BUTTONS

<ActionsRow>
  <PrimaryButton 
    type="button" 
    onClick={analyseVideo} 
    disabled={processing || !selectedFile}
  >
    {processing ? 'Analysing…' : 'Analyse video'}
  </PrimaryButton>
  
  <SecondaryButton 
    type="button" 
    onClick={clearSelection} 
    disabled={processing || !selectedFile}
  >
    Clear selection
  </SecondaryButton>
</ActionsRow>
```

---

## 13. Results Display

### 13.1 Analysis Function

```javascript
async function analyseVideo() {
  /**
   * Upload video and analyze for moderation labels.
   * 
   * Process:
   * 1. Validate file selection
   * 2. Prepare FormData with file and parameters
   * 3. Upload to backend with progress tracking
   * 4. Wait for synchronous analysis (up to 5 minutes)
   * 5. Display results
   * 
   * State Updates:
   *   - processing: true → false
   *   - status: "Uploading..." → "Analysing..." → "Complete"
   *   - uploadProgress: 0% → 100%
   *   - result: null → API response
   *   - error: null → error message (on failure)
   * 
   * Error Handling:
   *   - Network errors
   *   - Timeout errors (5 minutes)
   *   - Server errors (500, 503)
   *   - Validation errors (400)
   * 
   * API Request:
   *   Method: POST
   *   Endpoint: /moderate
   *   Content-Type: multipart/form-data
   *   Body:
   *     - video: File
   *     - categories: "Violence,Drugs" (comma-separated)
   *     - min_confidence: 75 (number)
   * 
   * API Response:
   *   {
   *     jobId: string,
   *     video: { objectKey, bucket },
   *     events: [...],
   *     summary: { totalFindings, categories },
   *     requestMeta: { selectedCategories, minConfidence },
   *     metadata: { analysisDurationSeconds }
   *   }
   */
  
  if (!selectedFile) {
    setError('Please select a video file first.');
    return;
  }
  
  // Reset state
  setProcessing(true);
  setError('');
  setResult(null);
  setUploadProgress(0);
  setStatus('Uploading video...');
  
  try {
    // Prepare form data
    const formData = new FormData();
    formData.append('video', selectedFile);
    
    // Add categories (only if not all selected)
    if (selectedCategories.length > 0 && 
        selectedCategories.length < CATEGORY_OPTIONS.length) {
      formData.append('categories', selectedCategories.join(','));
    }
    
    // Add confidence threshold
    formData.append('min_confidence', minConfidence.toString());
    
    // Upload and analyze
    const response = await axios.post(
      `${API_BASE}/moderate`,
      formData,
      {
        headers: {
          'Content-Type': 'multipart/form-data'
        },
        onUploadProgress: (progressEvent) => {
          // Update upload progress
          const percentCompleted = Math.round(
            (progressEvent.loaded * 100) / progressEvent.total
          );
          setUploadProgress(percentCompleted);
          
          if (percentCompleted === 100) {
            setStatus('Analysing video...');
          }
        },
        timeout: DEFAULT_TIMEOUT_MS  // 5 minutes
      }
    );
    
    // Success
    setResult(response.data);
    setStatus('Analysis complete');
    setUploadProgress(null);
    
  } catch (err) {
    // Error handling
    console.error('Analysis error:', err);
    
    if (err.code === 'ECONNABORTED') {
      setError('Request timed out. Video may be too long or analysis took longer than 5 minutes.');
    } else if (err.response) {
      // Server responded with error
      const errorMessage = err.response.data?.error || 'Analysis failed';
      setError(`Error: ${errorMessage}`);
    } else if (err.request) {
      // No response from server
      setError('No response from server. Please check your connection and try again.');
    } else {
      // Other errors
      setError(`Error: ${err.message}`);
    }
    
    setUploadProgress(null);
    
  } finally {
    setProcessing(false);
  }
}
```

### 13.2 Results Summary Display

```javascript
// SUMMARY CARD (Job metadata and category counts)

<Card>
  <CardTitle>Summary</CardTitle>
  
  <SummaryList>
    {/* Job ID */}
    <SummaryItem>
      <strong>Job ID:</strong> {result.jobId}
    </SummaryItem>
    
    {/* Selected Categories */}
    <SummaryItem>
      <strong>Categories:</strong> {
        Array.isArray(requestMeta?.selectedCategories)
          ? requestMeta.selectedCategories.join(', ')
          : 'All recognised categories'
      }
    </SummaryItem>
    
    {/* Confidence Threshold */}
    <SummaryItem>
      <strong>Minimum confidence:</strong> {
        typeof requestMeta?.minConfidence === 'number'
          ? `${requestMeta.minConfidence}%`
          : 'Default'
      }
    </SummaryItem>
    
    {/* Total Findings */}
    <SummaryItem>
      <strong>Total findings:</strong> {summary?.totalFindings || 0}
    </SummaryItem>
    
    {/* Analysis Duration */}
    {typeof metadata?.analysisDurationSeconds === 'number' && (
      <SummaryItem>
        <strong>Analysis time:</strong> {metadata.analysisDurationSeconds}s
      </SummaryItem>
    )}
    
    {/* S3 Object Key */}
    {result.video?.objectKey && (
      <SummaryItem>
        <strong>S3 object key:</strong> {result.video.objectKey}
      </SummaryItem>
    )}
  </SummaryList>
  
  {/* Category Breakdown */}
  {summary?.categories && Object.keys(summary.categories).length > 0 && (
    <>
      <Badge>Categories</Badge>
      <SummaryList>
        {Object.entries(summary.categories).map(([category, count]) => (
          <SummaryItem key={category}>
            {category}: {count}
          </SummaryItem>
        ))}
      </SummaryList>
    </>
  )}
  
  {/* Download Report Link */}
  {result.jobId && (
    <SummaryItem>
      <strong>Download report:</strong>{' '}
      <DownloadLink
        href={`${API_BASE}/result/${result.jobId}`}
        target="_blank"
        rel="noopener noreferrer"
      >
        JSON export
      </DownloadLink>
    </SummaryItem>
  )}
</Card>
```

### 13.3 Events Timeline Table

```javascript
// TIMELINE TABLE (Moderation events with timestamps)

<Card>
  <CardTitle>Moderation Timeline</CardTitle>
  
  {moderationEvents.length === 0 ? (
    // EMPTY STATE (no events)
    <EmptyState>
      No moderation events matched the current filters.
    </EmptyState>
  ) : (
    // EVENTS TABLE
    <EventsTable>
      <thead>
        <tr>
          <EventsHeadCell>Timecode</EventsHeadCell>
          <EventsHeadCell>Category</EventsHeadCell>
          <EventsHeadCell>Label</EventsHeadCell>
          <EventsHeadCell>Confidence</EventsHeadCell>
        </tr>
      </thead>
      <tbody>
        {moderationEvents.map((event, index) => (
          <tr key={`${event.timestamp?.milliseconds}-${event.label}-${index}`}>
            <EventsCell>
              {event.timestamp?.timecode || '00:00:00.000'}
            </EventsCell>
            <EventsCell>
              {event.category || '—'}
            </EventsCell>
            <EventsCell>
              {event.label || '—'}
            </EventsCell>
            <EventsCell>
              {event.confidence ? `${event.confidence}%` : '—'}
            </EventsCell>
          </tr>
        ))}
      </tbody>
    </EventsTable>
  )}
</Card>
```

---

## 14. Error Handling & Status Management

### 14.1 Status Banners

```javascript
// SUCCESS STATUS (blue banner)
{status && !error && (
  <StatusBanner>
    {status}
  </StatusBanner>
)}

// ERROR STATUS (red banner)
{error && (
  <StatusBanner $error>
    {error}
  </StatusBanner>
)}

// UPLOAD PROGRESS (blue banner with percentage)
{processing && uploadProgress !== null && (
  <StatusBanner>
    Upload progress: {uploadProgress}%
  </StatusBanner>
)}
```

### 14.2 Error Scenarios

```javascript
// ERROR HANDLING PATTERNS

// 1. VALIDATION ERRORS (Client-Side)
if (!file.type.startsWith('video/')) {
  setError('Please select a video file (MP4, MOV, MKV, AVI, WEBM).');
  return;
}

if (file.size > 2 * 1024 * 1024 * 1024) {
  setError(`File too large. Maximum size is 2GB. Your file is ${(file.size / (1024 * 1024 * 1024)).toFixed(2)}GB.`);
  return;
}

// 2. NETWORK ERRORS
catch (err) {
  if (err.code === 'ECONNABORTED') {
    // Timeout (5 minutes exceeded)
    setError('Request timed out. Video may be too long or analysis took longer than 5 minutes.');
  } else if (err.request && !err.response) {
    // No response from server
    setError('No response from server. Please check your connection and try again.');
  } else {
    // Other network errors
    setError(`Network error: ${err.message}`);
  }
}

// 3. SERVER ERRORS (HTTP Status Codes)
if (err.response) {
  const status = err.response.status;
  const errorMessage = err.response.data?.error || 'Unknown error';
  
  switch (status) {
    case 400:
      setError(`Invalid request: ${errorMessage}`);
      break;
    case 413:
      setError('File too large. Maximum size is 2GB.');
      break;
    case 500:
      setError(`Server error: ${errorMessage}`);
      break;
    case 503:
      setError('Service unavailable. Please try again later.');
      break;
    default:
      setError(`Error (${status}): ${errorMessage}`);
  }
}

// 4. AWS ERRORS (from backend)
// Example server responses:
// - "S3 upload failed: AccessDenied"
// - "Failed to start moderation job: InvalidS3ObjectException"
// - "Moderation job failed: Unknown error"
```

### 14.3 Empty States

```javascript
// NO FILE SELECTED (initial state)
{!result && !processing && !error && !selectedFile && (
  <EmptyState>
    Choose a clip, keep the relevant categories enabled, 
    and we'll produce a reviewer-ready moderation timeline in one click.
  </EmptyState>
)}

// NO EVENTS FOUND (analysis complete, no violations)
{moderationEvents.length === 0 && (
  <EmptyState>
    No moderation events matched the current filters.
  </EmptyState>
)}
```

### 14.4 Loading States

```javascript
// BUTTON LOADING STATE
<PrimaryButton 
  disabled={processing || !selectedFile}
>
  {processing ? 'Analysing…' : 'Analyse video'}
</PrimaryButton>

// UPLOAD PROGRESS INDICATOR
{processing && uploadProgress !== null && (
  <StatusBanner>
    Upload progress: {uploadProgress}%
  </StatusBanner>
)}

// ANALYSIS PROGRESS INDICATOR
{processing && uploadProgress === 100 && (
  <StatusBanner>
    Analysing video... This may take up to 5 minutes.
  </StatusBanner>
)}
```

---

## End of Part 3

**This concludes Part 3 of the Content Moderation Service reference documentation.**

### What's Covered in Part 3:
✅ Frontend Architecture (React Component)  
✅ Upload Component (Drag-and-Drop + File Input)  
✅ Category Selection (11 Checkboxes)  
✅ Confidence Control (Range Slider)  
✅ Results Display (Summary Card + Timeline Table)  
✅ Error Handling & Status Management  
✅ Styled Components (30+ UI Elements)  

### Coming in Part 4:
📄 API Reference (Complete Request/Response Examples)  
📄 Deployment Guide (Production Setup)  
📄 Troubleshooting & Common Issues  
📄 Performance Optimization  
📄 Security Best Practices  
📄 Production Checklist  
📄 Monitoring & Logging  

---

**Document Navigation:**
- **Previous:** [Part 2 - Backend Implementation](CONTENT_MODERATION_PART2.md)
- **Current:** Part 3 - Frontend Architecture
- **Next:** [Part 4 - Deployment & Production](CONTENT_MODERATION_PART4.md)
- **Index:** [Documentation Index](DOCUMENTATION_INDEX.md)

**Last Updated:** October 22, 2025  
**Maintainer:** MediaGenAI Platform Team  
**Service Version:** 1.0

# Content Moderation Service - Part 4 of 4
## Deployment, Troubleshooting & Production Best Practices

**Document Version:** 1.0  
**Last Updated:** October 22, 2025  
**Service Port:** 5006  
**Part:** 4/4 - Deployment & Operations

---

## Table of Contents - Part 4

15. [Deployment Guide](#15-deployment-guide)
16. [Troubleshooting & Common Issues](#16-troubleshooting--common-issues)
17. [Performance Optimization](#17-performance-optimization)
18. [Security Best Practices](#18-security-best-practices)
19. [Monitoring & Logging](#19-monitoring--logging)
20. [Production Checklist](#20-production-checklist)

---

## 15. Deployment Guide

### 15.1 Local Development Setup

```bash
# STEP 1: Clone Repository
git clone https://github.com/your-org/mediaGenAI.git
cd mediaGenAI

# STEP 2: Install Python Dependencies
python3 -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
pip install -r requirements.txt
pip install -r contentModeration/requirements.txt

# STEP 3: Configure Environment Variables
cd contentModeration
cp .env.example .env
nano .env

# Required environment variables:
AWS_ACCESS_KEY_ID=your_access_key_id
AWS_SECRET_ACCESS_KEY=your_secret_access_key
AWS_REGION=us-east-1
CONTENT_MODERATION_BUCKET=your-s3-bucket-name

# Optional environment variables:
CONTENT_MODERATION_PREFIX=moderation/
CONTENT_MODERATION_MIN_CONFIDENCE=75
CONTENT_MODERATION_POLL_INTERVAL=2
CONTENT_MODERATION_MAX_WAIT_SECONDS=300
CONTENT_MODERATION_ALLOWED_ORIGINS=http://localhost:3000
CONTENT_MODERATION_API_PORT=5006

# STEP 4: Create S3 Bucket (if not exists)
aws s3 mb s3://your-s3-bucket-name --region us-east-1
aws s3api put-bucket-versioning \
  --bucket your-s3-bucket-name \
  --versioning-configuration Status=Enabled

# STEP 5: Start Backend Server
python content_moderation_service.py

# Server will start on http://localhost:5006

# STEP 6: Install Frontend Dependencies
cd ../frontend
npm install

# STEP 7: Configure Frontend Environment
echo "REACT_APP_MODERATION_API_BASE=http://localhost:5006" > .env

# STEP 8: Start Frontend Development Server
npm start

# Frontend will start on http://localhost:3000
```

### 15.2 Production Deployment (AWS EC2)

```bash
# PRODUCTION DEPLOYMENT ON AWS EC2

# ========================================
# STEP 1: Launch EC2 Instance
# ========================================

# Recommended Specs:
# - Instance Type: t3.medium (2 vCPU, 4 GB RAM)
# - OS: Amazon Linux 2 or Ubuntu 22.04 LTS
# - Storage: 50 GB gp3 SSD
# - Security Group: Allow inbound TCP 5006 (or use ALB)

# ========================================
# STEP 2: Install Dependencies
# ========================================

# SSH into EC2 instance
ssh -i your-key.pem ec2-user@your-instance-ip

# Update system packages
sudo yum update -y  # Amazon Linux
# OR
sudo apt update && sudo apt upgrade -y  # Ubuntu

# Install Python 3.11+
sudo yum install python3.11 python3.11-pip -y  # Amazon Linux
# OR
sudo apt install python3.11 python3.11-venv python3-pip -y  # Ubuntu

# Install Git
sudo yum install git -y  # Amazon Linux
# OR
sudo apt install git -y  # Ubuntu

# ========================================
# STEP 3: Clone and Setup Application
# ========================================

# Clone repository
cd /opt
sudo git clone https://github.com/your-org/mediaGenAI.git
sudo chown -R ec2-user:ec2-user mediaGenAI
cd mediaGenAI

# Create virtual environment
python3.11 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install --upgrade pip
pip install -r requirements.txt
pip install -r contentModeration/requirements.txt

# Install production WSGI server
pip install gunicorn

# ========================================
# STEP 4: Configure IAM Role (Recommended)
# ========================================

# Attach IAM role to EC2 instance instead of using access keys
# IAM Role Policy:
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "rekognition:StartContentModeration",
        "rekognition:GetContentModeration"
      ],
      "Resource": "*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "s3:PutObject",
        "s3:GetObject"
      ],
      "Resource": "arn:aws:s3:::your-bucket-name/moderation/*"
    }
  ]
}

# ========================================
# STEP 5: Configure Environment Variables
# ========================================

# Create .env file (no AWS keys needed if using IAM role)
cd /opt/mediaGenAI/contentModeration
cat > .env << EOF
AWS_REGION=us-east-1
CONTENT_MODERATION_BUCKET=your-production-bucket
CONTENT_MODERATION_PREFIX=moderation/
CONTENT_MODERATION_MIN_CONFIDENCE=75
CONTENT_MODERATION_POLL_INTERVAL=2
CONTENT_MODERATION_MAX_WAIT_SECONDS=300
CONTENT_MODERATION_ALLOWED_ORIGINS=https://mediagenai.com,https://app.mediagenai.com
CONTENT_MODERATION_API_PORT=5006
EOF

# ========================================
# STEP 6: Create Systemd Service
# ========================================

sudo tee /etc/systemd/system/content-moderation.service > /dev/null << EOF
[Unit]
Description=Content Moderation Service
After=network.target

[Service]
Type=simple
User=ec2-user
Group=ec2-user
WorkingDirectory=/opt/mediaGenAI/contentModeration
Environment="PATH=/opt/mediaGenAI/.venv/bin"
ExecStart=/opt/mediaGenAI/.venv/bin/gunicorn \
    --workers 4 \
    --bind 0.0.0.0:5006 \
    --timeout 360 \
    --access-logfile /var/log/content-moderation-access.log \
    --error-logfile /var/log/content-moderation-error.log \
    content_moderation_service:app
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

# Create log files
sudo touch /var/log/content-moderation-access.log
sudo touch /var/log/content-moderation-error.log
sudo chown ec2-user:ec2-user /var/log/content-moderation-*.log

# Enable and start service
sudo systemctl daemon-reload
sudo systemctl enable content-moderation
sudo systemctl start content-moderation

# Check service status
sudo systemctl status content-moderation

# View logs
sudo journalctl -u content-moderation -f

# ========================================
# STEP 7: Configure Nginx Reverse Proxy (Optional)
# ========================================

# Install Nginx
sudo yum install nginx -y  # Amazon Linux
# OR
sudo apt install nginx -y  # Ubuntu

# Configure Nginx
sudo tee /etc/nginx/conf.d/content-moderation.conf > /dev/null << EOF
upstream content_moderation {
    server 127.0.0.1:5006;
}

server {
    listen 80;
    server_name moderation.mediagenai.com;

    # Increase client body size for video uploads
    client_max_body_size 2G;

    # Increase timeouts for long-running analysis
    proxy_connect_timeout 360s;
    proxy_send_timeout 360s;
    proxy_read_timeout 360s;
    send_timeout 360s;

    location / {
        proxy_pass http://content_moderation;
        proxy_http_version 1.1;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_cache_bypass \$http_upgrade;
    }
}
EOF

# Test Nginx configuration
sudo nginx -t

# Enable and start Nginx
sudo systemctl enable nginx
sudo systemctl start nginx

# ========================================
# STEP 8: Configure SSL with Let's Encrypt (Optional)
# ========================================

# Install Certbot
sudo yum install certbot python3-certbot-nginx -y  # Amazon Linux
# OR
sudo apt install certbot python3-certbot-nginx -y  # Ubuntu

# Obtain SSL certificate
sudo certbot --nginx -d moderation.mediagenai.com

# Auto-renewal cron job (already added by Certbot)
sudo certbot renew --dry-run

# ========================================
# STEP 9: Configure CloudWatch Monitoring (Optional)
# ========================================

# Install CloudWatch agent
wget https://s3.amazonaws.com/amazoncloudwatch-agent/amazon_linux/amd64/latest/amazon-cloudwatch-agent.rpm
sudo rpm -U ./amazon-cloudwatch-agent.rpm

# Configure CloudWatch agent
sudo tee /opt/aws/amazon-cloudwatch-agent/etc/config.json > /dev/null << EOF
{
  "logs": {
    "logs_collected": {
      "files": {
        "collect_list": [
          {
            "file_path": "/var/log/content-moderation-access.log",
            "log_group_name": "/mediagenai/content-moderation/access",
            "log_stream_name": "{instance_id}"
          },
          {
            "file_path": "/var/log/content-moderation-error.log",
            "log_group_name": "/mediagenai/content-moderation/error",
            "log_stream_name": "{instance_id}"
          }
        ]
      }
    }
  },
  "metrics": {
    "namespace": "MediaGenAI/ContentModeration",
    "metrics_collected": {
      "cpu": {
        "measurement": [{"name": "cpu_usage_idle", "rename": "CPU_IDLE", "unit": "Percent"}]
      },
      "mem": {
        "measurement": [{"name": "mem_used_percent", "rename": "MEM_USED", "unit": "Percent"}]
      }
    }
  }
}
EOF

# Start CloudWatch agent
sudo /opt/aws/amazon-cloudwatch-agent/bin/amazon-cloudwatch-agent-ctl \
  -a fetch-config \
  -m ec2 \
  -s \
  -c file:/opt/aws/amazon-cloudwatch-agent/etc/config.json

# ========================================
# STEP 10: Verify Deployment
# ========================================

# Test health endpoint
curl http://localhost:5006/health

# Expected response:
# {"status":"healthy","rekognition":true,"s3":true,"bucket":"your-bucket"}

# Test from external IP
curl http://your-instance-ip:5006/health
```

### 15.3 Docker Deployment

```dockerfile
# Dockerfile for Content Moderation Service

FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements files
COPY requirements.txt /app/
COPY contentModeration/requirements.txt /app/contentModeration/

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt
RUN pip install --no-cache-dir -r contentModeration/requirements.txt
RUN pip install --no-cache-dir gunicorn

# Copy application code
COPY contentModeration/ /app/contentModeration/

# Create necessary directories
RUN mkdir -p /app/contentModeration/uploads /app/contentModeration/reports

# Expose port
EXPOSE 5006

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV AWS_REGION=us-east-1

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
  CMD python -c "import requests; requests.get('http://localhost:5006/health')"

# Run with Gunicorn
CMD ["gunicorn", \
     "--chdir", "/app/contentModeration", \
     "--workers", "4", \
     "--bind", "0.0.0.0:5006", \
     "--timeout", "360", \
     "--access-logfile", "-", \
     "--error-logfile", "-", \
     "content_moderation_service:app"]
```

```yaml
# docker-compose.yml

version: '3.8'

services:
  content-moderation:
    build:
      context: .
      dockerfile: Dockerfile
    container_name: content-moderation-service
    ports:
      - "5006:5006"
    environment:
      - AWS_ACCESS_KEY_ID=${AWS_ACCESS_KEY_ID}
      - AWS_SECRET_ACCESS_KEY=${AWS_SECRET_ACCESS_KEY}
      - AWS_REGION=us-east-1
      - CONTENT_MODERATION_BUCKET=${CONTENT_MODERATION_BUCKET}
      - CONTENT_MODERATION_PREFIX=moderation/
      - CONTENT_MODERATION_MIN_CONFIDENCE=75
      - CONTENT_MODERATION_POLL_INTERVAL=2
      - CONTENT_MODERATION_MAX_WAIT_SECONDS=300
      - CONTENT_MODERATION_ALLOWED_ORIGINS=*
    volumes:
      - ./contentModeration/uploads:/app/contentModeration/uploads
      - ./contentModeration/reports:/app/contentModeration/reports
    restart: unless-stopped
    logging:
      driver: "json-file"
      options:
        max-size: "10m"
        max-file: "3"
```

```bash
# Build and run with Docker Compose
docker-compose up -d

# View logs
docker-compose logs -f content-moderation

# Stop service
docker-compose down
```

### 15.4 Kubernetes Deployment

```yaml
# kubernetes/content-moderation-deployment.yaml

apiVersion: v1
kind: ConfigMap
metadata:
  name: content-moderation-config
data:
  AWS_REGION: "us-east-1"
  CONTENT_MODERATION_PREFIX: "moderation/"
  CONTENT_MODERATION_MIN_CONFIDENCE: "75"
  CONTENT_MODERATION_POLL_INTERVAL: "2"
  CONTENT_MODERATION_MAX_WAIT_SECONDS: "300"
  CONTENT_MODERATION_ALLOWED_ORIGINS: "https://mediagenai.com"
  CONTENT_MODERATION_API_PORT: "5006"

---
apiVersion: v1
kind: Secret
metadata:
  name: content-moderation-secrets
type: Opaque
stringData:
  AWS_ACCESS_KEY_ID: "your-access-key-id"
  AWS_SECRET_ACCESS_KEY: "your-secret-access-key"
  CONTENT_MODERATION_BUCKET: "your-s3-bucket"

---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: content-moderation
  labels:
    app: content-moderation
spec:
  replicas: 3
  selector:
    matchLabels:
      app: content-moderation
  template:
    metadata:
      labels:
        app: content-moderation
    spec:
      containers:
      - name: content-moderation
        image: your-registry/content-moderation:latest
        ports:
        - containerPort: 5006
        envFrom:
        - configMapRef:
            name: content-moderation-config
        - secretRef:
            name: content-moderation-secrets
        resources:
          requests:
            memory: "512Mi"
            cpu: "250m"
          limits:
            memory: "2Gi"
            cpu: "1000m"
        livenessProbe:
          httpGet:
            path: /health
            port: 5006
          initialDelaySeconds: 10
          periodSeconds: 30
        readinessProbe:
          httpGet:
            path: /health
            port: 5006
          initialDelaySeconds: 5
          periodSeconds: 10
        volumeMounts:
        - name: uploads
          mountPath: /app/contentModeration/uploads
        - name: reports
          mountPath: /app/contentModeration/reports
      volumes:
      - name: uploads
        emptyDir: {}
      - name: reports
        persistentVolumeClaim:
          claimName: content-moderation-reports-pvc

---
apiVersion: v1
kind: Service
metadata:
  name: content-moderation-service
spec:
  selector:
    app: content-moderation
  ports:
  - protocol: TCP
    port: 80
    targetPort: 5006
  type: LoadBalancer

---
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: content-moderation-reports-pvc
spec:
  accessModes:
  - ReadWriteMany
  resources:
    requests:
      storage: 10Gi
  storageClassName: efs-storage
```

```bash
# Deploy to Kubernetes
kubectl apply -f kubernetes/content-moderation-deployment.yaml

# Check deployment status
kubectl get deployments
kubectl get pods
kubectl get services

# View logs
kubectl logs -f deployment/content-moderation

# Scale deployment
kubectl scale deployment/content-moderation --replicas=5
```

---

## 16. Troubleshooting & Common Issues

### 16.1 Service Fails to Start

**Problem:** `content_moderation_service.py` crashes on startup

**Symptoms:**
```
Traceback (most recent call last):
  File "content_moderation_service.py", line XX
ImportError: No module named 'boto3'
```

**Solutions:**

```bash
# 1. Verify virtual environment is activated
source .venv/bin/activate  # You should see (.venv) in prompt

# 2. Reinstall dependencies
pip install -r contentModeration/requirements.txt

# 3. Check Python version (requires 3.11+)
python --version  # Should show Python 3.11.x or higher

# 4. Verify all required packages
pip list | grep boto3
pip list | grep flask
pip list | grep flask-cors

# 5. Check for import errors
python -c "import boto3; print('boto3 OK')"
python -c "import flask; print('flask OK')"
python -c "from werkzeug.utils import secure_filename; print('werkzeug OK')"
```

### 16.2 AWS Credentials Not Found

**Problem:** Service returns "Service not configured" error

**Symptoms:**
```json
{
  "error": "Service not configured. Check AWS credentials and S3 bucket."
}
```

**Solutions:**

```bash
# 1. Verify environment variables
printenv | grep AWS
# Should show:
# AWS_ACCESS_KEY_ID=AKIAIOSFODNN7EXAMPLE
# AWS_SECRET_ACCESS_KEY=wJalrXUtnFEMI/K7MDENG...
# AWS_REGION=us-east-1

# 2. Check .env file
cat contentModeration/.env

# 3. Test AWS credentials manually
aws sts get-caller-identity
# Should show your AWS account details

# 4. Test S3 access
aws s3 ls s3://your-bucket-name/

# 5. Test Rekognition permissions
aws rekognition list-collections --region us-east-1

# 6. If using IAM role (EC2), verify role attachment
aws sts get-caller-identity
# Should show role ARN, not user ARN
```

### 16.3 S3 Upload Fails

**Problem:** Videos fail to upload to S3

**Symptoms:**
```json
{
  "error": "S3 upload failed: AccessDenied"
}
```

**Solutions:**

```bash
# 1. Verify S3 bucket exists
aws s3 ls s3://your-bucket-name/

# 2. Check bucket permissions (IAM policy)
aws s3api get-bucket-policy --bucket your-bucket-name

# Required IAM permissions:
{
  "Effect": "Allow",
  "Action": [
    "s3:PutObject",
    "s3:GetObject"
  ],
  "Resource": "arn:aws:s3:::your-bucket-name/moderation/*"
}

# 3. Test upload manually
echo "test" > test.txt
aws s3 cp test.txt s3://your-bucket-name/moderation/test.txt

# 4. Check bucket region (must match AWS_REGION)
aws s3api get-bucket-location --bucket your-bucket-name

# 5. Verify bucket is not public (security best practice)
aws s3api get-public-access-block --bucket your-bucket-name
```

### 16.4 Rekognition Job Fails

**Problem:** Moderation job fails with error

**Symptoms:**
```json
{
  "error": "Moderation job failed: Unknown error"
}
```

**Solutions:**

```bash
# 1. Check Rekognition permissions
aws rekognition describe-collection --collection-id test 2>&1 | grep -i denied

# Required IAM permissions:
{
  "Effect": "Allow",
  "Action": [
    "rekognition:StartContentModeration",
    "rekognition:GetContentModeration"
  ],
  "Resource": "*"
}

# 2. Verify video format is supported
file your-video.mp4
# Should show: video/mp4, H.264 codec

# 3. Check video file integrity
ffprobe your-video.mp4

# 4. Test with small sample video
curl -X POST http://localhost:5006/moderate \
  -F "video=@sample-10sec.mp4" \
  -F "min_confidence=75"

# 5. Check Rekognition service limits
aws rekognition describe-stream-processor --name test 2>&1
# Error: LimitExceededException means you hit concurrent job limit (10)
```

### 16.5 Request Timeout (5 Minutes)

**Problem:** Analysis exceeds 5-minute timeout

**Symptoms:**
```json
{
  "error": "Request timed out. Video may be too long or analysis took longer than 5 minutes."
}
```

**Solutions:**

```bash
# 1. Increase timeout in backend (.env file)
CONTENT_MODERATION_MAX_WAIT_SECONDS=600  # 10 minutes

# 2. Increase timeout in frontend (ContentModeration.js)
const DEFAULT_TIMEOUT_MS = 600000;  // 10 minutes

# 3. Increase Gunicorn timeout (production)
gunicorn --timeout 600 content_moderation_service:app

# 4. Increase Nginx timeout (if using reverse proxy)
proxy_read_timeout 600s;

# 5. Optimize video before upload
ffmpeg -i input.mp4 -vcodec h264 -acodec aac -b:v 2M output.mp4

# 6. Split long videos into segments
ffmpeg -i long-video.mp4 -c copy -segment_time 300 -f segment segment_%03d.mp4
```

### 16.6 CORS Errors

**Problem:** Frontend cannot access backend API

**Symptoms:**
```
Access to XMLHttpRequest at 'http://localhost:5006/moderate' from origin 'http://localhost:3000' 
has been blocked by CORS policy: No 'Access-Control-Allow-Origin' header is present.
```

**Solutions:**

```bash
# 1. Configure ALLOWED_ORIGINS in .env
CONTENT_MODERATION_ALLOWED_ORIGINS=http://localhost:3000,http://localhost:3001

# 2. For development, use wildcard (NOT for production)
CONTENT_MODERATION_ALLOWED_ORIGINS=*

# 3. For production, specify exact origins
CONTENT_MODERATION_ALLOWED_ORIGINS=https://mediagenai.com,https://app.mediagenai.com

# 4. Verify CORS configuration in backend
curl -H "Origin: http://localhost:3000" \
     -H "Access-Control-Request-Method: POST" \
     -H "Access-Control-Request-Headers: Content-Type" \
     -X OPTIONS \
     http://localhost:5006/moderate

# Expected headers in response:
# Access-Control-Allow-Origin: http://localhost:3000
# Access-Control-Allow-Methods: GET, POST, OPTIONS
# Access-Control-Allow-Headers: Content-Type

# 5. Test with curl (bypass browser CORS)
curl -X POST http://localhost:5006/moderate -F "video=@test.mp4"
```

### 16.7 File Size Limit Exceeded

**Problem:** Large videos rejected by server

**Symptoms:**
```
413 Payload Too Large
```

**Solutions:**

```bash
# 1. Verify backend file size limit (default 2GB)
# In content_moderation_service.py:
app.config['MAX_CONTENT_LENGTH'] = 2 * 1024 * 1024 * 1024  # 2GB

# 2. Increase Nginx upload limit (if using reverse proxy)
client_max_body_size 2G;

# 3. Compress video before upload
ffmpeg -i input.mp4 -vcodec h264 -crf 28 -preset fast output.mp4

# 4. Check file size in frontend
if (file.size > 2 * 1024 * 1024 * 1024) {
  alert('File too large. Maximum 2GB.');
  return;
}

# 5. For videos >2GB, split into chunks
ffmpeg -i large-video.mp4 -c copy -segment_time 600 -f segment chunk_%03d.mp4
```

### 16.8 Memory Errors

**Problem:** Server crashes with out-of-memory error

**Symptoms:**
```
MemoryError: Unable to allocate array
Killed
```

**Solutions:**

```bash
# 1. Check system memory
free -h

# 2. Reduce Gunicorn workers (each uses ~500MB-1GB)
gunicorn --workers 2 content_moderation_service:app

# 3. Increase EC2 instance memory (upgrade to t3.large or t3.xlarge)

# 4. Enable swap space (temporary fix)
sudo dd if=/dev/zero of=/swapfile bs=1G count=4
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile

# 5. Monitor memory usage
top  # Press Shift+M to sort by memory

# 6. Configure memory limits in Docker
docker run -m 2g content-moderation:latest

# 7. Clean up old uploads and reports
find contentModeration/uploads -mtime +1 -delete
find contentModeration/reports -mtime +30 -delete
```

---

## 17. Performance Optimization

### 17.1 Backend Optimizations

```python
# OPTIMIZATION 1: Asynchronous S3 Upload (for large files)

import aioboto3
import asyncio

async def _upload_to_s3_async(local_file_path, s3_key):
    """Async S3 upload for better concurrency."""
    session = aioboto3.Session()
    async with session.client('s3', region_name=AWS_REGION) as s3:
        await s3.upload_file(
            local_file_path,
            CONTENT_MODERATION_BUCKET,
            s3_key
        )

# OPTIMIZATION 2: Connection Pooling

import boto3
from botocore.config import Config

config = Config(
    max_pool_connections=50,  # Increase connection pool
    retries={'max_attempts': 3}
)

rekognition_client = boto3.client('rekognition', config=config)
s3_client = boto3.client('s3', config=config)

# OPTIMIZATION 3: Reduce Polling Interval for Short Videos

def _adaptive_poll_interval(video_duration_seconds):
    """Adjust polling interval based on video length."""
    if video_duration_seconds < 30:
        return 1  # 1-second polling for short videos
    elif video_duration_seconds < 120:
        return 2  # 2-second polling for medium videos
    else:
        return 5  # 5-second polling for long videos

# OPTIMIZATION 4: Cache Rekognition Results

from functools import lru_cache

@lru_cache(maxsize=100)
def _get_cached_moderation_result(job_id):
    """Cache Rekognition results to avoid redundant API calls."""
    report_path = REPORTS_DIR / f"{job_id}.json"
    if report_path.exists():
        with open(report_path, 'r') as f:
            return json.load(f)
    return None

# OPTIMIZATION 5: Batch Processing (Multiple Videos)

@app.route('/moderate-batch', methods=['POST'])
def moderate_batch():
    """Process multiple videos in parallel."""
    files = request.files.getlist('videos')
    results = []
    
    with ThreadPoolExecutor(max_workers=5) as executor:
        futures = [executor.submit(process_video, f) for f in files]
        for future in as_completed(futures):
            results.append(future.result())
    
    return jsonify(results)
```

### 17.2 Frontend Optimizations

```javascript
// OPTIMIZATION 1: Video Compression Before Upload

async function compressVideo(file) {
  /**
   * Compress video using Web Codecs API (experimental).
   * Reduces upload time and backend processing time.
   */
  
  // Note: Requires browser support for Web Codecs API
  const reader = new FileReader();
  reader.readAsArrayBuffer(file);
  
  return new Promise((resolve) => {
    reader.onload = async (event) => {
      const buffer = event.target.result;
      // Compression logic here (simplified)
      resolve(new Blob([buffer], { type: 'video/mp4' }));
    };
  });
}

// OPTIMIZATION 2: Lazy Load Results Table

function VirtualizedEventTable({ events }) {
  /**
   * Render only visible rows (virtualization).
   * Improves performance for videos with 1000+ events.
   */
  
  const [visibleRange, setVisibleRange] = useState({ start: 0, end: 50 });
  
  return (
    <EventsTable>
      <tbody>
        {events.slice(visibleRange.start, visibleRange.end).map(event => (
          <EventRow key={event.id} event={event} />
        ))}
      </tbody>
    </EventsTable>
  );
}

// OPTIMIZATION 3: Debounce Category Selection

import { debounce } from 'lodash';

const debouncedToggle = debounce((categoryKey) => {
  toggleCategory(categoryKey);
}, 300);  // Wait 300ms before updating

// OPTIMIZATION 4: Memoize Expensive Computations

import { useMemo } from 'react';

const sortedEvents = useMemo(() => {
  return moderationEvents.sort((a, b) => 
    a.timestamp.milliseconds - b.timestamp.milliseconds
  );
}, [moderationEvents]);

// OPTIMIZATION 5: Progressive Image Loading

const PreviewVideo = React.lazy(() => import('./PreviewVideo'));

function VideoPreviewWrapper() {
  return (
    <Suspense fallback={<LoadingSpinner />}>
      <PreviewVideo src={previewUrl} />
    </Suspense>
  );
}
```

### 17.3 AWS Optimizations

```bash
# OPTIMIZATION 1: Use S3 Transfer Acceleration

# Enable Transfer Acceleration on bucket
aws s3api put-bucket-accelerate-configuration \
  --bucket your-bucket-name \
  --accelerate-configuration Status=Enabled

# Update S3 endpoint in backend
s3_client = boto3.client(
    's3',
    region_name=AWS_REGION,
    config=Config(s3={'use_accelerate_endpoint': True})
)

# OPTIMIZATION 2: Use CloudFront for S3 Downloads

# Create CloudFront distribution
aws cloudfront create-distribution \
  --origin-domain-name your-bucket-name.s3.amazonaws.com \
  --default-cache-behavior '{
    "TargetOriginId": "S3-your-bucket-name",
    "ViewerProtocolPolicy": "redirect-to-https"
  }'

# OPTIMIZATION 3: Enable S3 Intelligent-Tiering

aws s3api put-bucket-intelligent-tiering-configuration \
  --bucket your-bucket-name \
  --id default-tiering \
  --intelligent-tiering-configuration '{
    "Id": "default-tiering",
    "Status": "Enabled",
    "Tierings": [
      {"Days": 90, "AccessTier": "ARCHIVE_ACCESS"},
      {"Days": 180, "AccessTier": "DEEP_ARCHIVE_ACCESS"}
    ]
  }'

# OPTIMIZATION 4: Use Rekognition Custom Models (Advanced)

# Train custom moderation model for your specific use case
aws rekognition create-project \
  --project-name custom-content-moderation

# OPTIMIZATION 5: Enable CloudWatch Logs Insights

# Query slow requests
aws logs start-query \
  --log-group-name /mediagenai/content-moderation \
  --start-time $(date -d '1 hour ago' +%s) \
  --end-time $(date +%s) \
  --query-string 'fields @timestamp, @message | filter @message like /SLOW/ | sort @timestamp desc'
```

### 17.4 Database Optimizations (If Using RDS)

```sql
-- OPTIMIZATION 1: Index on job_id for fast report retrieval

CREATE INDEX idx_reports_job_id ON reports(job_id);
CREATE INDEX idx_reports_created_at ON reports(created_at);

-- OPTIMIZATION 2: Partition reports table by date

CREATE TABLE reports_2025_10 PARTITION OF reports
FOR VALUES FROM ('2025-10-01') TO ('2025-11-01');

-- OPTIMIZATION 3: Archive old reports to S3

-- Run monthly cron job to move old reports
SELECT * FROM reports WHERE created_at < NOW() - INTERVAL '90 days';
-- Export to S3, then DELETE FROM reports WHERE ...

-- OPTIMIZATION 4: Add read replicas for report retrieval

-- Use read replica for GET /result/<job_id> endpoint
# In Python:
reader_db = psycopg2.connect(host='reader-endpoint', ...)
writer_db = psycopg2.connect(host='writer-endpoint', ...)
```

---

## 18. Security Best Practices

### 18.1 Authentication & Authorization

```python
# IMPLEMENTATION 1: API Key Authentication

from functools import wraps
from flask import request, jsonify

API_KEYS = os.getenv('API_KEYS', '').split(',')

def require_api_key(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        api_key = request.headers.get('X-API-Key')
        if not api_key or api_key not in API_KEYS:
            return jsonify({"error": "Invalid or missing API key"}), 401
        return f(*args, **kwargs)
    return decorated_function

@app.route('/moderate', methods=['POST'])
@require_api_key
def moderate():
    # Protected endpoint
    pass

# IMPLEMENTATION 2: JWT Authentication

import jwt
from datetime import datetime, timedelta

SECRET_KEY = os.getenv('JWT_SECRET_KEY')

def generate_token(user_id):
    payload = {
        'user_id': user_id,
        'exp': datetime.utcnow() + timedelta(hours=1)
    }
    return jwt.encode(payload, SECRET_KEY, algorithm='HS256')

def require_jwt(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        token = request.headers.get('Authorization', '').replace('Bearer ', '')
        try:
            payload = jwt.decode(token, SECRET_KEY, algorithms=['HS256'])
            request.user_id = payload['user_id']
        except jwt.ExpiredSignatureError:
            return jsonify({"error": "Token expired"}), 401
        except jwt.InvalidTokenError:
            return jsonify({"error": "Invalid token"}), 401
        return f(*args, **kwargs)
    return decorated_function

# IMPLEMENTATION 3: Rate Limiting

from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

limiter = Limiter(
    app=app,
    key_func=get_remote_address,
    default_limits=["200 per day", "50 per hour"]
)

@app.route('/moderate', methods=['POST'])
@limiter.limit("10 per hour")  # Max 10 videos per hour per IP
def moderate():
    pass
```

### 18.2 Input Validation

```python
# VALIDATION 1: File Type Whitelist

ALLOWED_MIME_TYPES = {
    'video/mp4',
    'video/quicktime',
    'video/x-matroska',
    'video/x-msvideo',
    'video/webm'
}

def validate_file_type(file):
    """Validate file MIME type (more secure than extension check)."""
    import magic
    mime = magic.from_buffer(file.read(1024), mime=True)
    file.seek(0)  # Reset file pointer
    
    if mime not in ALLOWED_MIME_TYPES:
        raise ValueError(f"Invalid file type: {mime}")

# VALIDATION 2: Filename Sanitization

from werkzeug.utils import secure_filename
import re

def sanitize_filename(filename):
    """Remove dangerous characters from filename."""
    # Remove path traversal attempts
    filename = secure_filename(filename)
    
    # Remove non-alphanumeric characters (except dots, dashes, underscores)
    filename = re.sub(r'[^a-zA-Z0-9._-]', '_', filename)
    
    # Limit filename length
    if len(filename) > 255:
        name, ext = os.path.splitext(filename)
        filename = name[:250] + ext
    
    return filename

# VALIDATION 3: Content Security Policy (CSP)

@app.after_request
def set_security_headers(response):
    """Add security headers to all responses."""
    response.headers['Content-Security-Policy'] = (
        "default-src 'self'; "
        "script-src 'self' 'unsafe-inline'; "
        "style-src 'self' 'unsafe-inline';"
    )
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'DENY'
    response.headers['X-XSS-Protection'] = '1; mode=block'
    return response

# VALIDATION 4: SQL Injection Prevention (if using database)

# Use parameterized queries
cursor.execute(
    "SELECT * FROM reports WHERE job_id = %s",
    (job_id,)  # Parameter tuple
)

# NEVER do this:
# cursor.execute(f"SELECT * FROM reports WHERE job_id = '{job_id}'")
```

### 18.3 Data Encryption

```python
# ENCRYPTION 1: Encrypt S3 Objects at Rest

s3_client.upload_file(
    local_file_path,
    CONTENT_MODERATION_BUCKET,
    s3_key,
    ExtraArgs={
        'ServerSideEncryption': 'AES256',  # Or 'aws:kms' for KMS encryption
        'SSEKMSKeyId': 'arn:aws:kms:us-east-1:123456789:key/...'  # If using KMS
    }
)

# ENCRYPTION 2: Encrypt Reports at Rest

from cryptography.fernet import Fernet

# Generate encryption key (store in environment variable or AWS Secrets Manager)
ENCRYPTION_KEY = os.getenv('REPORT_ENCRYPTION_KEY')
cipher = Fernet(ENCRYPTION_KEY.encode())

def encrypt_report(report_data):
    """Encrypt report JSON before saving."""
    json_str = json.dumps(report_data)
    encrypted = cipher.encrypt(json_str.encode())
    return encrypted

def decrypt_report(encrypted_data):
    """Decrypt report JSON when retrieving."""
    decrypted = cipher.decrypt(encrypted_data)
    return json.loads(decrypted.decode())

# ENCRYPTION 3: HTTPS Enforcement

@app.before_request
def enforce_https():
    """Redirect HTTP to HTTPS in production."""
    if not request.is_secure and os.getenv('ENV') == 'production':
        url = request.url.replace('http://', 'https://', 1)
        return redirect(url, code=301)

# ENCRYPTION 4: Secure Cookie Settings (if using sessions)

app.config['SESSION_COOKIE_SECURE'] = True  # HTTPS only
app.config['SESSION_COOKIE_HTTPONLY'] = True  # No JavaScript access
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'  # CSRF protection
```

### 18.4 Secrets Management

```bash
# SECRETS MANAGEMENT 1: AWS Secrets Manager

# Store secrets in AWS Secrets Manager
aws secretsmanager create-secret \
  --name mediagenai/content-moderation/credentials \
  --secret-string '{
    "aws_access_key_id": "AKIAIOSFODNN7EXAMPLE",
    "aws_secret_access_key": "wJalrXUtnFEMI/K7MDENG...",
    "s3_bucket": "my-content-bucket",
    "api_keys": ["key1", "key2", "key3"]
  }'

# Retrieve secrets in Python
import boto3
import json

def get_secrets():
    client = boto3.client('secretsmanager', region_name='us-east-1')
    response = client.get_secret_value(SecretId='mediagenai/content-moderation/credentials')
    return json.loads(response['SecretString'])

secrets = get_secrets()
AWS_ACCESS_KEY_ID = secrets['aws_access_key_id']

# SECRETS MANAGEMENT 2: HashiCorp Vault

# Store secrets in Vault
vault kv put secret/mediagenai/content-moderation \
  aws_access_key_id=AKIAIOSFODNN7EXAMPLE \
  aws_secret_access_key=wJalrXUtnFEMI/K7MDENG...

# Retrieve secrets in Python
import hvac

client = hvac.Client(url='http://vault:8200', token=os.getenv('VAULT_TOKEN'))
secrets = client.secrets.kv.v2.read_secret_version(path='mediagenai/content-moderation')
AWS_ACCESS_KEY_ID = secrets['data']['data']['aws_access_key_id']

# SECRETS MANAGEMENT 3: Environment Variables (Development Only)

# Use .env file (git-ignored)
# NEVER commit secrets to Git
echo ".env" >> .gitignore

# .env file
AWS_ACCESS_KEY_ID=AKIAIOSFODNN7EXAMPLE
AWS_SECRET_ACCESS_KEY=wJalrXUtnFEMI/K7MDENG...

# Load with python-dotenv
from dotenv import load_dotenv
load_dotenv()
```

---

## 19. Monitoring & Logging

### 19.1 Application Logging

```python
# LOGGING CONFIGURATION

import logging
from logging.handlers import RotatingFileHandler

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    handlers=[
        RotatingFileHandler(
            'logs/content-moderation.log',
            maxBytes=10*1024*1024,  # 10MB
            backupCount=5
        ),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

# LOG USAGE IN ENDPOINTS

@app.route('/moderate', methods=['POST'])
def moderate():
    logger.info(f"Moderation request received from {request.remote_addr}")
    
    try:
        # Process video...
        logger.info(f"Started moderation job: {job_id}")
        logger.info(f"Analysis complete. Job ID: {job_id}, Findings: {len(events)}")
        return jsonify(result)
    
    except Exception as e:
        logger.error(f"Moderation failed: {str(e)}", exc_info=True)
        return jsonify({"error": str(e)}), 500

# STRUCTURED LOGGING (JSON format)

import json_log_formatter

formatter = json_log_formatter.JSONFormatter()
handler = logging.StreamHandler()
handler.setFormatter(formatter)
logger.addHandler(handler)

logger.info("Moderation job completed", extra={
    'job_id': job_id,
    'findings_count': len(events),
    'duration_seconds': duration,
    'categories': list(summary['categories'].keys())
})
```

### 19.2 CloudWatch Integration

```python
# CLOUDWATCH METRICS

import boto3

cloudwatch = boto3.client('cloudwatch', region_name='us-east-1')

def publish_metric(metric_name, value, unit='Count'):
    """Publish custom metric to CloudWatch."""
    cloudwatch.put_metric_data(
        Namespace='MediaGenAI/ContentModeration',
        MetricData=[
            {
                'MetricName': metric_name,
                'Value': value,
                'Unit': unit,
                'Timestamp': datetime.utcnow()
            }
        ]
    )

# USAGE IN APPLICATION

@app.route('/moderate', methods=['POST'])
def moderate():
    start_time = time.time()
    
    try:
        # Process video...
        duration = time.time() - start_time
        
        # Publish metrics
        publish_metric('ModerationRequests', 1)
        publish_metric('ModerationDuration', duration, 'Seconds')
        publish_metric('ModerationFindings', len(events))
        
        return jsonify(result)
    
    except Exception as e:
        publish_metric('ModerationErrors', 1)
        raise
```

### 19.3 Health Check Endpoint

```python
# COMPREHENSIVE HEALTH CHECK

@app.route('/health', methods=['GET'])
def health():
    """
    Comprehensive health check with dependency validation.
    """
    health_status = {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "service": "content-moderation",
        "version": "1.0.0",
        "checks": {}
    }
    
    # Check Rekognition
    try:
        rekognition_client.list_collections(MaxResults=1)
        health_status["checks"]["rekognition"] = "healthy"
    except Exception as e:
        health_status["checks"]["rekognition"] = f"unhealthy: {str(e)}"
        health_status["status"] = "degraded"
    
    # Check S3
    try:
        s3_client.head_bucket(Bucket=CONTENT_MODERATION_BUCKET)
        health_status["checks"]["s3"] = "healthy"
    except Exception as e:
        health_status["checks"]["s3"] = f"unhealthy: {str(e)}"
        health_status["status"] = "degraded"
    
    # Check disk space
    import shutil
    disk_usage = shutil.disk_usage('/').free / (1024**3)  # GB
    health_status["checks"]["disk_space_gb"] = round(disk_usage, 2)
    
    if disk_usage < 5:  # Less than 5GB free
        health_status["status"] = "degraded"
        health_status["checks"]["disk_space"] = "low"
    
    # Return appropriate HTTP status
    http_status = 200 if health_status["status"] == "healthy" else 503
    return jsonify(health_status), http_status
```

### 19.4 Performance Monitoring

```python
# REQUEST TIMING MIDDLEWARE

@app.before_request
def start_timer():
    """Start request timer."""
    request.start_time = time.time()

@app.after_request
def log_request(response):
    """Log request details and duration."""
    if hasattr(request, 'start_time'):
        duration = time.time() - request.start_time
        logger.info(
            f"{request.method} {request.path} "
            f"{response.status_code} {duration:.3f}s"
        )
    return response

# SLOW REQUEST DETECTION

SLOW_REQUEST_THRESHOLD = 30  # seconds

@app.after_request
def detect_slow_requests(response):
    """Alert on slow requests."""
    if hasattr(request, 'start_time'):
        duration = time.time() - request.start_time
        if duration > SLOW_REQUEST_THRESHOLD:
            logger.warning(
                f"SLOW REQUEST: {request.method} {request.path} "
                f"took {duration:.2f}s"
            )
    return response
```

---

## 20. Production Checklist

### 20.1 Pre-Deployment Checklist

```markdown
## Infrastructure

- [ ] EC2 instance provisioned (t3.medium or larger)
- [ ] Security group configured (port 5006 or ALB)
- [ ] IAM role attached with required permissions
- [ ] S3 bucket created and configured
- [ ] S3 lifecycle policy configured (auto-delete after 30 days)
- [ ] CloudWatch alarms configured
- [ ] CloudWatch log groups created
- [ ] Backup strategy implemented

## Application

- [ ] Environment variables configured (no hardcoded secrets)
- [ ] AWS credentials verified (IAM role preferred)
- [ ] CORS origins restricted to production domains
- [ ] File size limit configured (2GB)
- [ ] Timeout values tuned for workload
- [ ] Error handling implemented
- [ ] Logging configured (CloudWatch + local files)
- [ ] Health check endpoint tested

## Security

- [ ] HTTPS enabled (SSL certificate installed)
- [ ] API authentication implemented (API keys or JWT)
- [ ] Rate limiting configured
- [ ] Input validation implemented
- [ ] SQL injection prevention (parameterized queries)
- [ ] XSS protection enabled
- [ ] CSRF protection enabled
- [ ] Security headers configured (CSP, X-Frame-Options, etc.)
- [ ] Secrets stored in AWS Secrets Manager (not .env files)
- [ ] IAM least privilege principle applied

## Performance

- [ ] Gunicorn workers configured (4-8 workers)
- [ ] Database connection pooling enabled (if using RDS)
- [ ] S3 Transfer Acceleration enabled (optional)
- [ ] CloudFront distribution created (optional)
- [ ] Caching strategy implemented
- [ ] Static assets optimized

## Monitoring

- [ ] CloudWatch metrics enabled
- [ ] CloudWatch alarms configured:
  - [ ] High CPU usage (>80%)
  - [ ] High memory usage (>80%)
  - [ ] High error rate (>5%)
  - [ ] Slow requests (>30s)
- [ ] CloudWatch Logs Insights queries saved
- [ ] SNS notifications configured
- [ ] PagerDuty/Opsgenie integration (optional)

## Testing

- [ ] Health check endpoint returns 200
- [ ] Can upload and analyze sample video
- [ ] Error handling works correctly
- [ ] CORS configuration verified
- [ ] Load testing completed (100 concurrent users)
- [ ] Stress testing completed (1000 requests/hour)
- [ ] Failover testing completed

## Documentation

- [ ] API documentation published
- [ ] Runbook created (incident response)
- [ ] Architecture diagram updated
- [ ] Environment variables documented
- [ ] Deployment process documented

## Backup & Recovery

- [ ] S3 bucket versioning enabled
- [ ] Database backups automated (if using RDS)
- [ ] Disaster recovery plan documented
- [ ] Backup restoration tested

## Compliance

- [ ] Data retention policy configured
- [ ] GDPR compliance verified (if applicable)
- [ ] Audit logging enabled
- [ ] Data encryption at rest enabled
- [ ] Data encryption in transit enabled (HTTPS)
```

### 20.2 Post-Deployment Checklist

```markdown
## Immediate (Day 1)

- [ ] Monitor CloudWatch metrics for first 24 hours
- [ ] Check error logs for unexpected issues
- [ ] Verify all endpoints responding correctly
- [ ] Test from production frontend
- [ ] Smoke test with real user workflows

## Short-Term (Week 1)

- [ ] Review CloudWatch alarms (false positives?)
- [ ] Analyze performance metrics
- [ ] Check cost usage (AWS Cost Explorer)
- [ ] Gather user feedback
- [ ] Identify optimization opportunities

## Medium-Term (Month 1)

- [ ] Review and update documentation
- [ ] Optimize based on usage patterns
- [ ] Update monitoring thresholds
- [ ] Plan capacity scaling
- [ ] Conduct security audit

## Long-Term (Quarter 1)

- [ ] Review architecture for improvements
- [ ] Update dependencies (security patches)
- [ ] Implement new features based on feedback
- [ ] Optimize costs (Reserved Instances, Savings Plans)
- [ ] Disaster recovery drill
```

### 20.3 Incident Response Plan

```markdown
## Severity Levels

### P0 - Critical (Service Down)
- **Response Time:** Immediate
- **Impact:** All users unable to use service
- **Examples:** Backend crashed, AWS outage

### P1 - High (Degraded Performance)
- **Response Time:** <15 minutes
- **Impact:** Service slow, intermittent errors
- **Examples:** High latency, 50% error rate

### P2 - Medium (Limited Impact)
- **Response Time:** <1 hour
- **Impact:** Some users affected
- **Examples:** Specific feature broken

### P3 - Low (Minimal Impact)
- **Response Time:** <1 day
- **Impact:** Minor bug, cosmetic issue
- **Examples:** Typo in UI, incorrect tooltip

## Incident Response Steps

1. **Detect:** CloudWatch alarm, user report, health check failure
2. **Triage:** Determine severity, impact, root cause
3. **Communicate:** Notify stakeholders, update status page
4. **Mitigate:** Implement temporary fix, rollback if needed
5. **Resolve:** Deploy permanent fix
6. **Post-Mortem:** Document incident, improve processes

## Common Incidents & Solutions

### Service Unresponsive
- **Check:** `systemctl status content-moderation`
- **Restart:** `sudo systemctl restart content-moderation`
- **Logs:** `sudo journalctl -u content-moderation -n 100`

### High Error Rate
- **Check:** CloudWatch metrics, error logs
- **Investigate:** AWS service health dashboard
- **Rollback:** `git checkout <previous-commit> && sudo systemctl restart content-moderation`

### S3 Upload Failures
- **Check:** S3 bucket permissions, IAM role
- **Verify:** `aws s3 ls s3://your-bucket/`
- **Fix:** Update IAM policy, increase bucket quota

### Rekognition Quota Exceeded
- **Check:** `aws rekognition describe-stream-processor --name test`
- **Request:** Quota increase via AWS Support
- **Temporary:** Implement request queuing

## Rollback Procedure

```bash
# 1. Identify last known good version
git log --oneline -n 10

# 2. Checkout previous version
git checkout <commit-hash>

# 3. Restart service
sudo systemctl restart content-moderation

# 4. Verify health
curl http://localhost:5006/health

# 5. Monitor for 15 minutes
watch -n 5 'curl -s http://localhost:5006/health | jq .'
```
```

---

## Conclusion

**This concludes the Content Moderation Service reference documentation.**

### Complete Documentation Summary:

**Part 1 (Foundation & AWS Integration):**
- Executive Summary & Business Value
- Service Overview & Workflow
- Architecture Overview (Synchronous Polling)
- AWS Integration (Rekognition + S3)
- Configuration Management

**Part 2 (Backend Implementation):**
- Backend Deep Dive (Flask Routes)
- Helper Functions (S3, Rekognition, Timestamp)
- Results Processing & Filtering Logic
- Report Storage & Retrieval

**Part 3 (Frontend Architecture):**
- Frontend Architecture (React Component)
- Upload Component (Drag-and-Drop)
- Category Selection & Confidence Control
- Results Display (Timeline Table)
- Error Handling & Status Management

**Part 4 (Deployment & Operations):**
- Deployment Guide (Local, EC2, Docker, Kubernetes)
- Troubleshooting & Common Issues
- Performance Optimization
- Security Best Practices
- Monitoring & Logging
- Production Checklist

### Total Documentation:
- **4 Parts**
- **~200 Pages**
- **Comprehensive Coverage**

---

**Document Navigation:**
- **Previous:** [Part 3 - Frontend Architecture](CONTENT_MODERATION_PART3.md)
- **Current:** Part 4 - Deployment & Operations
- **Index:** [Documentation Index](DOCUMENTATION_INDEX.md)

**Last Updated:** October 22, 2025  
**Maintainer:** MediaGenAI Platform Team  
**Service Version:** 1.0

---

**For Support:**
- **Email:** support@mediagenai.com
- **Documentation:** https://docs.mediagenai.com/content-moderation
- **GitHub Issues:** https://github.com/your-org/mediaGenAI/issues
- **Slack:** #content-moderation channel

**AWS Resources:**
- **Rekognition Documentation:** https://docs.aws.amazon.com/rekognition/
- **S3 Documentation:** https://docs.aws.amazon.com/s3/
- **IAM Best Practices:** https://docs.aws.amazon.com/IAM/latest/UserGuide/best-practices.html