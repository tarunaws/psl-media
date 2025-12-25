# AI Subtitle/Dubbing System - Architecture & Logic Guide
## Part 4: Deployment & Operations

**Document Version:** 1.0  
**Last Updated:** October 24, 2025  
**System:** MediaGenAI - AI Subtitle Generation & Translation Service

---

## Table of Contents (Part 4)

1. [Environment Setup](#environment-setup)
2. [Deployment Configuration](#deployment-configuration)
3. [Service Management](#service-management)
4. [Monitoring & Logging](#monitoring--logging)
5. [Troubleshooting Guide](#troubleshooting-guide)
6. [Security & Best Practices](#security--best-practices)
7. [Performance Optimization](#performance-optimization)

---

## Environment Setup

### Prerequisites

**System Requirements:**

| Component | Requirement |
|-----------|------------|
| Operating System | macOS, Linux, Windows (WSL2) |
| Python | 3.11+ |
| Node.js | 18.0+ |
| FFmpeg | 6.0+ |
| Memory | 4GB+ RAM |
| Storage | 50GB+ available (for video processing) |

**AWS Services:**

| Service | Purpose | Configuration |
|---------|---------|--------------|
| AWS Transcribe | Speech-to-text | 40+ language support |
| AWS Translate | Text translation | 75+ language support |
| AWS S3 | Audio file storage | Single bucket |
| IAM | Access credentials | Programmatic access |

### Backend Installation

#### 1. Clone Repository

```bash
cd /path/to/project
git clone <repository-url>
cd mediaGenAI
```

#### 2. Create Virtual Environment

```bash
# Create virtual environment
python3 -m venv .venv

# Activate virtual environment
# macOS/Linux:
source .venv/bin/activate

# Windows:
.venv\Scripts\activate
```

#### 3. Install Python Dependencies

```bash
cd aiSubtitle
pip install -r requirements.txt
```

**requirements.txt:**
```
Flask==2.3.3
Flask-Cors==4.0.0
python-dotenv==1.0.1
Werkzeug==2.3.7
boto3>=1.28.0
```

#### 4. Install FFmpeg

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

#### 5. Configure AWS Credentials

**Create .env file:**
```bash
cd aiSubtitle
cp .env.example .env
nano .env
```

**.env Configuration:**
```bash
# AWS Configuration for Transcribe Service
AWS_ACCESS_KEY_ID=AKIAIOSFODNN7EXAMPLE
AWS_SECRET_ACCESS_KEY=wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY
AWS_REGION=us-east-1
AWS_S3_BUCKET=mediagenai-transcribe-bucket

# Optional: Override default port
# FLASK_PORT=5001

# Optional: Enable debug mode
# FLASK_DEBUG=True
```

**Create S3 Bucket:**
```bash
# Create bucket
aws s3 mb s3://mediagenai-transcribe-bucket --region us-east-1

# Configure CORS for public access
aws s3api put-bucket-cors \
  --bucket mediagenai-transcribe-bucket \
  --cors-configuration file://cors-config.json
```

**cors-config.json:**
```json
{
  "CORSRules": [
    {
      "AllowedHeaders": ["*"],
      "AllowedMethods": ["GET", "HEAD"],
      "AllowedOrigins": ["*"],
      "ExposeHeaders": ["ETag"],
      "MaxAgeSeconds": 3000
    }
  ]
}
```

#### 6. Configure IAM Permissions

**Required IAM Policy:**
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "TranscribeAccess",
      "Effect": "Allow",
      "Action": [
        "transcribe:StartTranscriptionJob",
        "transcribe:GetTranscriptionJob",
        "transcribe:ListTranscriptionJobs",
        "transcribe:DeleteTranscriptionJob"
      ],
      "Resource": "*"
    },
    {
      "Sid": "TranslateAccess",
      "Effect": "Allow",
      "Action": [
        "translate:TranslateText",
        "translate:ListLanguages"
      ],
      "Resource": "*"
    },
    {
      "Sid": "S3Access",
      "Effect": "Allow",
      "Action": [
        "s3:PutObject",
        "s3:GetObject",
        "s3:ListBucket",
        "s3:DeleteObject"
      ],
      "Resource": [
        "arn:aws:s3:::mediagenai-transcribe-bucket",
        "arn:aws:s3:::mediagenai-transcribe-bucket/*"
      ]
    }
  ]
}
```

### Frontend Installation

#### 1. Navigate to Frontend Directory

```bash
cd frontend
```

#### 2. Install Node Dependencies

```bash
npm install
```

**Key Dependencies:**
```json
{
  "react": "^18.2.0",
  "styled-components": "^6.1.0",
  "axios": "^1.6.0",
  "hls.js": "^1.5.0",
  "dashjs": "^4.7.0"
}
```

#### 3. Configure Frontend Environment

**Create .env file:**
```bash
cp .env.example .env
nano .env
```

**.env Configuration:**
```bash
# API Endpoints
REACT_APP_SUBTITLE_API_BASE=http://localhost:5001

# Production endpoint (if different)
# REACT_APP_SUBTITLE_API_BASE=https://api.example.com
```

#### 4. Build Frontend

**Development Mode:**
```bash
npm start
# Runs on http://localhost:3000
```

**Production Build:**
```bash
npm run build
# Creates optimized build in ./build directory
```

---

## Deployment Configuration

### Project Structure

```
mediaGenAI/
├── .venv/                          # Python virtual environment
├── aiSubtitle/
│   ├── .env                        # AWS credentials (DO NOT COMMIT)
│   ├── .env.example                # Template for credentials
│   ├── aiSubtitle.py               # Flask backend (1424 lines)
│   ├── requirements.txt            # Python dependencies
│   ├── audio/                      # Extracted audio files
│   ├── outputs/
│   │   ├── streams/                # HLS/DASH manifests
│   │   └── subtitles/              # SRT/VTT files
│   ├── templates/
│   │   └── index.html              # Basic UI
│   └── uploads/                    # Uploaded videos
├── frontend/
│   ├── .env                        # Frontend config (DO NOT COMMIT)
│   ├── .env.example                # Template
│   ├── package.json                # Node dependencies
│   ├── build/                      # Production build
│   └── src/
│       ├── AISubtitling.js         # Main component (1431 lines)
│       └── ...
├── start-backend.sh                # Start all backend services
├── stop-backend.sh                 # Stop all backend services
└── start-all.sh                    # Start backend + frontend
```

### Backend Service Configuration

**Service Details:**

| Service | Port | Directory | Main File | Purpose |
|---------|------|-----------|-----------|---------|
| AI Subtitle | 5001 | aiSubtitle | aiSubtitle.py | Subtitle generation |
| Image Creation | 5002 | imageCreation | app.py | AI image generation |
| Synthetic Voiceover | 5003 | syntheticVoiceover | app.py | Text-to-speech |
| Scene Summarization | 5004 | sceneSummarization | app.py | Video analysis |
| Movie Script | 5005 | movieScriptCreation | app.py | Script generation |
| Content Moderation | 5006 | contentModeration | app.py | Content filtering |
| Personalized Trailer | 5007 | personalizedTrailer | app.py | Trailer creation |
| Semantic Search | 5008 | semanticSearch | app.py | Content search |

---

## Service Management

### Starting Services

#### Start Backend Services

```bash
cd /path/to/mediaGenAI
./start-backend.sh
```

**Script Functionality:**
- Checks for virtual environment
- Exports required PATH variables
- Starts each service in background
- Creates PID files for management
- Redirects logs to service-specific files

**Manual Start (Individual Service):**
```bash
cd aiSubtitle
source ../.venv/bin/activate
python aiSubtitle.py
```

#### Start Frontend

```bash
cd frontend
npm start
# Development server on http://localhost:3000
```

#### Start All Services

```bash
./start-all.sh
```

### Stopping Services

#### Stop Backend Services

```bash
./stop-backend.sh
```

**Script Functionality:**
- Reads PID from .pid files
- Sends SIGTERM to gracefully shutdown
- Removes PID files
- Cleans up log files

**Manual Stop (Individual Service):**
```bash
# Find PID
lsof -ti:5001

# Kill process
kill -9 <PID>
```

#### Stop Frontend

```bash
# Press Ctrl+C in terminal running npm start
```

#### Stop All Services

```bash
./stop-all.sh
```

### Service Health Check

**Check Backend Health:**
```bash
curl http://localhost:5001/health
# Expected: {"status":"healthy"}
```

**Check All Services:**
```bash
for port in {5001..5008}; do
  echo -n "Port $port: "
  curl -s http://localhost:$port/health | grep -q "healthy" && echo "✓ OK" || echo "✗ DOWN"
done
```

**View Running Processes:**
```bash
ps aux | grep "python.*app.py"
```

---

## Monitoring & Logging

### Log Files

**Backend Logs:**
```bash
# AI Subtitle Service
tail -f ai-subtitle.log

# All services
tail -f *.log
```

**Log Rotation Configuration:**
```bash
# /etc/logrotate.d/mediagenai
/path/to/mediaGenAI/*.log {
    daily
    rotate 7
    compress
    delaycompress
    missingok
    notifempty
}
```

### Application Logging

**Backend Logging Configuration:**
```python
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('aiSubtitle.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)
```

**Key Log Events:**
- File upload (size, format)
- Audio extraction (success/failure)
- AWS Transcribe job (start, progress, completion)
- Subtitle generation (format, language)
- Translation requests (source/target languages)
- Error events (with stack traces)

### Performance Metrics

**Track Processing Times:**
```python
import time

def track_time(operation):
    def decorator(func):
        def wrapper(*args, **kwargs):
            start = time.time()
            result = func(*args, **kwargs)
            duration = time.time() - start
            logger.info(f"{operation} completed in {duration:.2f}s")
            return result
        return wrapper
    return decorator

@track_time("Audio extraction")
def extract_audio_from_video(video_path, audio_path):
    # ... extraction logic
    pass
```

**Metrics to Monitor:**
- Upload time (per GB)
- Audio extraction time (per minute of video)
- Transcription time (per minute of audio)
- Translation time (per subtitle)
- Total end-to-end processing time

---

## Troubleshooting Guide

### Common Issues

#### 1. Backend Not Starting

**Symptom:** Service fails to start or immediately exits

**Diagnosis:**
```bash
# Check Python version
python3 --version

# Check virtual environment
ls -la .venv/

# Check dependencies
source .venv/bin/activate
pip list

# Check port availability
lsof -ti:5001
```

**Solutions:**
```bash
# Reinstall dependencies
pip install --upgrade -r requirements.txt

# Clear port
lsof -ti:5001 | xargs kill -9

# Check logs
tail -50 ai-subtitle.log
```

#### 2. AWS Authentication Errors

**Symptom:** `UnauthorizedOperation` or `InvalidAccessKeyId`

**Diagnosis:**
```bash
# Check .env file
cat aiSubtitle/.env

# Verify AWS credentials
aws sts get-caller-identity

# Test S3 access
aws s3 ls s3://mediagenai-transcribe-bucket
```

**Solutions:**
```bash
# Update .env with valid credentials
nano aiSubtitle/.env

# Verify IAM permissions (see IAM policy above)

# Test Transcribe access
aws transcribe list-transcription-jobs --max-results 1
```

#### 3. FFmpeg Not Found

**Symptom:** `FFmpeg binary not found` error

**Diagnosis:**
```bash
# Check FFmpeg installation
which ffmpeg
ffmpeg -version

# Check PATH
echo $PATH
```

**Solutions:**
```bash
# Install FFmpeg (macOS)
brew install ffmpeg

# Install FFmpeg (Ubuntu)
sudo apt install ffmpeg

# Add to PATH (macOS)
export PATH="/usr/local/bin:$PATH"
```

#### 4. Transcription Timeout

**Symptom:** Transcription job never completes

**Diagnosis:**
```bash
# Check AWS Transcribe console
aws transcribe list-transcription-jobs --status IN_PROGRESS

# Check specific job
aws transcribe get-transcription-job \
  --transcription-job-name subtitle-job-<file_id>-<timestamp>
```

**Solutions:**
- Verify audio file uploaded to S3
- Check S3 bucket permissions
- Verify AWS Transcribe region matches bucket region
- Check for language detection errors in logs

#### 5. Frontend Cannot Connect to Backend

**Symptom:** Network error or CORS issues

**Diagnosis:**
```bash
# Check backend health
curl http://localhost:5001/health

# Check CORS headers
curl -I -X OPTIONS http://localhost:5001/upload
```

**Solutions:**
```bash
# Update .env with correct API base
echo "REACT_APP_SUBTITLE_API_BASE=http://localhost:5001" > frontend/.env

# Rebuild frontend
cd frontend
npm run build

# Verify CORS in backend (aiSubtitle.py)
# CORS(app, origins=["http://localhost:3000"])
```

#### 6. Video Player Not Loading

**Symptom:** Black screen or "Cannot play video" error

**Diagnosis:**
```bash
# Check HLS manifest exists
ls -la aiSubtitle/outputs/streams/<file_id>/

# Check manifest content
cat aiSubtitle/outputs/streams/<file_id>/playlist.m3u8

# Verify video segments
ls -la aiSubtitle/outputs/streams/<file_id>/*.ts
```

**Solutions:**
- Verify HLS generation completed (check progress)
- Test manifest URL directly in browser
- Check video codec compatibility
- Verify FFmpeg HLS segmentation parameters

#### 7. Subtitle Not Displaying

**Symptom:** Subtitles available but not showing on video

**Diagnosis:**
```javascript
// Open browser console
console.log(videoRef.current.textTracks);

// Check track mode
Array.from(video.textTracks).forEach(track => {
  console.log(track.label, track.mode);
});
```

**Solutions:**
- Verify `captionsEnabled` state is true
- Check subtitle format (VTT required for web)
- Verify CORS headers on subtitle files
- Check `crossOrigin="anonymous"` on video element

---

## Security & Best Practices

### Security Checklist

- [ ] **Never commit .env files to version control**
- [ ] **Use IAM roles with least privilege**
- [ ] **Enable AWS CloudTrail for audit logs**
- [ ] **Implement file size validation (max 5GB)**
- [ ] **Sanitize filenames with `secure_filename()`**
- [ ] **Validate file types before processing**
- [ ] **Use HTTPS in production**
- [ ] **Implement rate limiting on upload endpoint**
- [ ] **Clean up temporary files regularly**
- [ ] **Set S3 lifecycle policies for old audio files**

### File Upload Security

```python
from werkzeug.utils import secure_filename
import os

ALLOWED_EXTENSIONS = {'mp4', 'avi', 'mov', 'mkv', 'webm', 'flv'}
MAX_FILE_SIZE = 5 * 1024 * 1024 * 1024  # 5GB

def allowed_file(filename):
    """Validate file extension."""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return jsonify({'error': 'No file part'}), 400
    
    file = request.files['file']
    
    # Validate filename
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400
    
    if not allowed_file(file.filename):
        return jsonify({'error': 'Invalid file type'}), 400
    
    # Validate file size
    file.seek(0, os.SEEK_END)
    file_size = file.tell()
    file.seek(0)
    
    if file_size > MAX_FILE_SIZE:
        return jsonify({'error': 'File too large'}), 413
    
    # Secure filename
    filename = secure_filename(file.filename)
    file_id = str(uuid.uuid4())
    file_path = os.path.join(UPLOAD_FOLDER, f"{file_id}_{filename}")
    
    file.save(file_path)
    # ... continue processing
```

### AWS S3 Security

**Bucket Policy (Restrict to Application):**
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "AllowApplicationAccess",
      "Effect": "Allow",
      "Principal": {
        "AWS": "arn:aws:iam::ACCOUNT_ID:user/mediagenai-app"
      },
      "Action": [
        "s3:GetObject",
        "s3:PutObject",
        "s3:DeleteObject"
      ],
      "Resource": "arn:aws:s3:::mediagenai-transcribe-bucket/*"
    }
  ]
}
```

**Enable Server-Side Encryption:**
```bash
aws s3api put-bucket-encryption \
  --bucket mediagenai-transcribe-bucket \
  --server-side-encryption-configuration '{
    "Rules": [{
      "ApplyServerSideEncryptionByDefault": {
        "SSEAlgorithm": "AES256"
      }
    }]
  }'
```

---

## Performance Optimization

### Backend Optimization

#### 1. Parallel Processing

```python
import threading
from concurrent.futures import ThreadPoolExecutor

# Process multiple translations in parallel
def translate_subtitles_parallel(file_id, source_lang, target_langs):
    with ThreadPoolExecutor(max_workers=5) as executor:
        futures = [
            executor.submit(translate_subtitle, file_id, source_lang, target)
            for target in target_langs
        ]
        
        results = [future.result() for future in futures]
    
    return results
```

#### 2. Caching

```python
from functools import lru_cache

@lru_cache(maxsize=128)
def get_language_name(code):
    """Cache language lookups."""
    return LANGUAGE_MAP.get(code, code)
```

#### 3. File Cleanup

```python
import schedule
import time

def cleanup_old_files():
    """Delete files older than 7 days."""
    cutoff = time.time() - (7 * 24 * 60 * 60)
    
    for folder in [UPLOAD_FOLDER, AUDIO_FOLDER, SUBTITLE_FOLDER]:
        for filename in os.listdir(folder):
            filepath = os.path.join(folder, filename)
            if os.path.getmtime(filepath) < cutoff:
                os.remove(filepath)
                logger.info(f"Cleaned up: {filepath}")

# Schedule cleanup
schedule.every().day.at("02:00").do(cleanup_old_files)
```

#### 4. Optimize FFmpeg Settings

```python
# Faster audio extraction with lower quality (sufficient for transcription)
cmd = [
    FFMPEG_BINARY,
    '-y',
    '-i', video_path,
    '-vn',
    '-acodec', 'libmp3lame',
    '-ar', '16000',        # Lower sample rate (16kHz sufficient for speech)
    '-ac', '1',            # Mono (reduces size by 50%)
    '-b:a', '64k',         # Lower bitrate
    '-threads', '4',       # Multi-threading
    audio_path
]
```

### Frontend Optimization

#### 1. Code Splitting

```javascript
import React, { lazy, Suspense } from 'react';

const AISubtitling = lazy(() => import('./AISubtitling'));

function App() {
  return (
    <Suspense fallback={<div>Loading...</div>}>
      <AISubtitling />
    </Suspense>
  );
}
```

#### 2. Memo Components

```javascript
import React, { memo } from 'react';

const SubtitleTrack = memo(({ track, onSelect }) => {
  return (
    <option value={track.code}>{track.label}</option>
  );
});
```

#### 3. Debounce Progress Polling

```javascript
import { useCallback } from 'react';
import debounce from 'lodash.debounce';

const debouncedPoll = useCallback(
  debounce((fileId) => pollProgress(fileId), 2000),
  []
);
```

### Database Optimization (Future Enhancement)

Consider adding PostgreSQL for production:

```python
# Track processing jobs
CREATE TABLE subtitle_jobs (
    job_id UUID PRIMARY KEY,
    filename VARCHAR(255),
    file_size BIGINT,
    source_language VARCHAR(10),
    target_languages TEXT[],
    status VARCHAR(20),
    progress INTEGER,
    created_at TIMESTAMP,
    completed_at TIMESTAMP
);

# Index for job lookup
CREATE INDEX idx_job_status ON subtitle_jobs(status);
CREATE INDEX idx_created_at ON subtitle_jobs(created_at DESC);
```

---

## Deployment Checklist

### Pre-Deployment

- [ ] Test all endpoints with sample videos
- [ ] Verify AWS credentials and permissions
- [ ] Check FFmpeg installation
- [ ] Configure CORS for production domain
- [ ] Set up SSL certificates (Let's Encrypt)
- [ ] Configure firewall rules
- [ ] Set up log rotation
- [ ] Create backup strategy

### Production Deployment

- [ ] Update .env with production values
- [ ] Build frontend with production config
- [ ] Configure reverse proxy (nginx/Apache)
- [ ] Set up process manager (systemd/PM2)
- [ ] Configure monitoring (CloudWatch/DataDog)
- [ ] Set up alerting (PagerDuty/Slack)
- [ ] Document runbooks for common issues
- [ ] Train team on operations

### Post-Deployment

- [ ] Monitor logs for errors
- [ ] Verify health checks pass
- [ ] Test end-to-end workflow
- [ ] Monitor AWS costs
- [ ] Set up regular backups
- [ ] Schedule maintenance windows

---

## Summary

This AI Subtitle/Dubbing System provides:

✅ **Complete Architecture** (Parts 1-4)
- Backend: Flask + AWS Transcribe + AWS Translate + FFmpeg
- Frontend: React + HLS.js + DASH.js + styled-components
- 40+ transcription languages
- 75+ translation languages
- Adaptive streaming (HLS/DASH)
- Real-time progress tracking

✅ **Production-Ready Features**
- File size validation (5GB max)
- Multiple subtitle formats (SRT, VTT, TTML, DFXP)
- Drag & drop upload
- Multi-language batch translation
- Automatic language detection
- Video streaming with synchronized captions

✅ **Operational Excellence**
- Automated service management scripts
- Comprehensive logging
- Health check endpoints
- Error recovery mechanisms
- Security best practices
- Performance optimization guidelines

**Total Documentation:** 4 comprehensive parts covering architecture, API, frontend, and operations.

---

*End of Part 4 - Documentation Complete*
