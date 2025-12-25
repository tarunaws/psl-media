# AI Subtitle/Dubbing System - Architecture & Logic Guide
## Part 2: API Endpoints & Backend Logic

**Document Version:** 1.0  
**Last Updated:** October 24, 2025  
**System:** MediaGenAI - AI Subtitle Generation & Translation Service

---

## Table of Contents (Part 2)

1. [API Endpoints Overview](#api-endpoints-overview)
2. [Upload & Processing API](#upload--processing-api)
3. [Progress Tracking API](#progress-tracking-api)
4. [Subtitle Management API](#subtitle-management-api)
5. [Streaming API](#streaming-api)
6. [Backend Processing Logic](#backend-processing-logic)

---

## API Endpoints Overview

### Base URL
```
http://localhost:5001
```

### API Endpoint Summary

| Endpoint | Method | Purpose | Auth |
|----------|--------|---------|------|
| `/` | GET | Serve frontend HTML | None |
| `/health` | GET | Health check | None |
| `/upload` | POST | Upload video file | None |
| `/progress/<file_id>` | GET | Get processing progress | None |
| `/list` | GET | List processed files | None |
| `/delete/<file_id>` | POST | Delete file and outputs | None |
| `/subtitle/<file_id>/<lang>` | GET | Get subtitle file | None |
| `/audio/<file_id>` | GET | Get audio file | None |
| `/stream/<file_id>/playlist.m3u8` | GET | Get HLS playlist | None |
| `/stream/<file_id>/<filename>` | GET | Get HLS segment | None |
| `/video/<file_id>` | GET | Get original video | None |
| `/translate` | POST | Translate subtitles | None |
| `/fetch-subtitle` | POST | Fetch subtitle from URL | None |

---

## Upload & Processing API

### POST `/upload`

**Purpose:** Upload video file and trigger subtitle generation pipeline

#### Request Format

**Content-Type:** `multipart/form-data`

**Form Fields:**
```javascript
{
  file: File,                    // Video file (required)
  generate_subtitles: boolean,   // Generate subtitles (default: true)
  generate_hls: boolean,         // Generate HLS stream (default: false)
  language: string               // Language code or 'auto' (default: 'auto')
}
```

**cURL Example:**
```bash
curl -X POST http://localhost:5001/upload \
  -F "file=@video.mp4" \
  -F "generate_subtitles=true" \
  -F "generate_hls=true" \
  -F "language=en-US"
```

#### Response Format

**Success (200):**
```json
{
  "success": true,
  "file_id": "a1b2c3d4-5678-90ab-cdef-1234567890ab",
  "filename": "video.mp4",
  "message": "File uploaded successfully. Processing started."
}
```

**Error (400):**
```json
{
  "error": "No file part in request"
}
```

**Error (413):**
```json
{
  "error": "File too large. Maximum size is 5GB"
}
```

#### Processing Logic Flow

```python
def upload_file():
    # 1. Validate request
    if 'file' not in request.files:
        return jsonify({'error': 'No file part'}), 400
    
    file = request.files['file']
    
    # 2. Validate filename
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400
    
    if not allowed_file(file.filename):
        return jsonify({'error': 'Invalid file type'}), 400
    
    # 3. Generate unique file ID
    file_id = str(uuid.uuid4())
    filename = secure_filename(file.filename)
    
    # 4. Save uploaded file
    file_path = os.path.join(UPLOAD_FOLDER, f"{file_id}_{filename}")
    file.save(file_path)
    
    # 5. Initialize progress tracking
    update_progress(file_id, 0, "File uploaded")
    
    # 6. Get processing options
    generate_subtitles = request.form.get('generate_subtitles', 'true') == 'true'
    generate_hls = request.form.get('generate_hls', 'false') == 'true'
    language = request.form.get('language', 'auto')
    
    # 7. Start async processing
    if generate_subtitles:
        thread = threading.Thread(
            target=process_video_for_subtitles,
            args=(file_id, file_path, language)
        )
        thread.start()
    
    if generate_hls:
        thread = threading.Thread(
            target=generate_hls_stream,
            args=(file_id, file_path)
        )
        thread.start()
    
    # 8. Return immediate response
    return jsonify({
        'success': True,
        'file_id': file_id,
        'filename': filename,
        'message': 'Processing started'
    })
```

---

## Progress Tracking API

### GET `/progress/<file_id>`

**Purpose:** Get real-time processing progress for a specific file

#### Request Format

**URL Parameters:**
- `file_id` (string): Unique file identifier

**Example:**
```bash
curl http://localhost:5001/progress/a1b2c3d4-5678-90ab-cdef-1234567890ab
```

#### Response Format

**Success (200):**
```json
{
  "progress": 75,
  "message": "Transcribing audio...",
  "status": "processing",
  "available_languages": ["en"],
  "hls_available": false,
  "error": null
}
```

**Progress States:**

| Progress % | Status | Description |
|-----------|--------|-------------|
| 0-10 | `uploading` | File upload in progress |
| 10-20 | `extracting` | Audio extraction |
| 20-30 | `uploading_s3` | Uploading to S3 |
| 30-70 | `transcribing` | AWS Transcribe processing |
| 70-80 | `generating` | Subtitle file generation |
| 80-90 | `streaming` | HLS stream generation |
| 90-100 | `translating` | Translation (if requested) |
| 100 | `completed` | Processing complete |
| -1 | `failed` | Error occurred |

#### Implementation

```python
@app.route('/progress/<file_id>')
def get_progress_endpoint(file_id):
    """Get progress for a specific file."""
    progress_info = get_progress(file_id)
    
    # Add available subtitle languages
    subtitle_folder = os.path.join(SUBTITLE_FOLDER, file_id)
    if os.path.exists(subtitle_folder):
        languages = [
            f.split('_')[1].replace('.srt', '')
            for f in os.listdir(subtitle_folder)
            if f.endswith('.srt')
        ]
        progress_info['available_languages'] = languages
    else:
        progress_info['available_languages'] = []
    
    # Check HLS availability
    hls_playlist = os.path.join(STREAMS_FOLDER, file_id, 'playlist.m3u8')
    progress_info['hls_available'] = os.path.exists(hls_playlist)
    
    return jsonify(progress_info)
```

---

## Subtitle Management API

### GET `/subtitle/<file_id>/<lang>`

**Purpose:** Download subtitle file for a specific language

#### Request Format

**URL Parameters:**
- `file_id` (string): Unique file identifier
- `lang` (string): Language code (e.g., 'en', 'es', 'fr')

**Example:**
```bash
curl http://localhost:5001/subtitle/a1b2c3d4.../en \
  -o subtitles.srt
```

#### Response Format

**Success (200):**
```
Content-Type: text/plain; charset=utf-8
Content-Disposition: attachment; filename=subtitles_en.srt

1
00:00:00,000 --> 00:00:03,500
Welcome to our presentation

2
00:00:03,500 --> 00:00:07,000
Today we will discuss AI technology
```

**Error (404):**
```json
{
  "error": "Subtitle file not found"
}
```

### POST `/translate`

**Purpose:** Translate existing subtitles to a new language

#### Request Format

**Content-Type:** `application/json`

```json
{
  "file_id": "a1b2c3d4-5678-90ab-cdef-1234567890ab",
  "source_language": "en",
  "target_language": "es"
}
```

#### Response Format

**Success (200):**
```json
{
  "success": true,
  "message": "Translation completed",
  "target_language": "es",
  "subtitle_url": "/subtitle/a1b2c3d4.../es"
}
```

#### Translation Logic

```python
def translate_subtitle(file_id, source_lang, target_lang):
    """Translate subtitle from source to target language."""
    
    # 1. Read source subtitle file
    source_file = os.path.join(
        SUBTITLE_FOLDER, file_id, f'subtitle_{source_lang}.srt'
    )
    
    with open(source_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 2. Parse SRT format
    subtitles = parse_srt(content)
    
    # 3. Translate each segment
    translated_subtitles = []
    for subtitle in subtitles:
        response = translate_client.translate_text(
            Text=subtitle['text'],
            SourceLanguageCode=source_lang,
            TargetLanguageCode=target_lang
        )
        
        translated_subtitles.append({
            'index': subtitle['index'],
            'start': subtitle['start'],
            'end': subtitle['end'],
            'text': response['TranslatedText']
        })
    
    # 4. Generate new SRT file
    output_file = os.path.join(
        SUBTITLE_FOLDER, file_id, f'subtitle_{target_lang}.srt'
    )
    
    write_srt(output_file, translated_subtitles)
    
    return output_file
```

---

## Streaming API

### GET `/stream/<file_id>/playlist.m3u8`

**Purpose:** Get HLS playlist for adaptive streaming

#### Response Format

```m3u8
#EXTM3U
#EXT-X-VERSION:3
#EXT-X-TARGETDURATION:10
#EXT-X-MEDIA-SEQUENCE:0
#EXT-X-PLAYLIST-TYPE:VOD

#EXTINF:10.0,
segment000.ts
#EXTINF:10.0,
segment001.ts
#EXTINF:10.0,
segment002.ts
#EXT-X-ENDLIST
```

### GET `/stream/<file_id>/<segment>`

**Purpose:** Get specific video segment

**Response:** Binary video data (MPEG-TS format)

---

## Backend Processing Logic

### Audio Extraction Function

```python
def extract_audio_from_video(video_path, audio_path):
    """Extract audio from video file using ffmpeg."""
    
    cmd = [
        FFMPEG_BINARY,
        '-y',                           # Overwrite output
        '-i', video_path,               # Input video
        '-vn',                          # No video
        '-acodec', 'libmp3lame',        # MP3 codec
        '-ar', '44100',                 # Sample rate: 44.1kHz
        '-ac', '2',                     # Audio channels: stereo
        '-b:a', '128k',                 # Bitrate: 128 kbps
        audio_path                       # Output audio
    ]
    
    result = subprocess.run(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )
    
    return result.returncode == 0
```

### AWS Transcribe Processing

```python
def process_video_for_subtitles(file_id, video_path, language_code):
    """Main subtitle generation pipeline."""
    
    try:
        # Step 1: Extract Audio (10-20%)
        update_progress(file_id, 10, "Extracting audio...")
        audio_path = os.path.join(AUDIO_FOLDER, f'audio_{file_id}.mp3')
        
        if not extract_audio_from_video(video_path, audio_path):
            raise Exception("Audio extraction failed")
        
        update_progress(file_id, 20, "Audio extracted")
        
        # Step 2: Upload to S3 (20-30%)
        update_progress(file_id, 25, "Uploading to S3...")
        s3_key = f'audio/audio_{file_id}.mp3'
        
        s3_client.upload_file(
            audio_path,
            aws_s3_bucket,
            s3_key,
            ExtraArgs={'ACL': 'public-read'}
        )
        
        s3_uri = f's3://{aws_s3_bucket}/{s3_key}'
        update_progress(file_id, 30, "Uploaded to S3")
        
        # Step 3: Start Transcription (30-70%)
        update_progress(file_id, 35, "Starting transcription...")
        
        job_name = f'subtitle-job-{file_id}-{int(time.time())}'
        
        transcribe_params = {
            'TranscriptionJobName': job_name,
            'Media': {'MediaFileUri': s3_uri},
            'MediaFormat': 'mp3',
            'OutputBucketName': aws_s3_bucket
        }
        
        # Add language if specified
        if language_code != 'auto':
            transcribe_params['LanguageCode'] = language_code
        else:
            transcribe_params['IdentifyLanguage'] = True
        
        transcribe_client.start_transcription_job(**transcribe_params)
        
        # Step 4: Poll for completion
        while True:
            status = transcribe_client.get_transcription_job(
                TranscriptionJobName=job_name
            )
            
            job_status = status['TranscriptionJob']['TranscriptionJobStatus']
            
            if job_status == 'COMPLETED':
                transcript_uri = status['TranscriptionJob']['Transcript']['TranscriptFileUri']
                break
            elif job_status == 'FAILED':
                raise Exception("Transcription failed")
            
            time.sleep(5)
            update_progress(file_id, 50, "Transcribing...")
        
        update_progress(file_id, 70, "Transcription complete")
        
        # Step 5: Generate Subtitle (70-80%)
        update_progress(file_id, 75, "Generating subtitle...")
        
        # Download transcription JSON
        response = requests.get(transcript_uri)
        transcript_data = response.json()
        
        # Convert to SRT
        detected_lang = transcript_data.get('results', {}).get('language_code', 'en')
        subtitle_content = convert_transcript_to_srt(transcript_data)
        
        # Save SRT file
        subtitle_dir = os.path.join(SUBTITLE_FOLDER, file_id)
        os.makedirs(subtitle_dir, exist_ok=True)
        
        subtitle_path = os.path.join(
            subtitle_dir,
            f'subtitle_{detected_lang}.srt'
        )
        
        with open(subtitle_path, 'w', encoding='utf-8') as f:
            f.write(subtitle_content)
        
        update_progress(file_id, 100, "Complete", status='completed')
        
    except Exception as e:
        update_progress(file_id, -1, f"Error: {str(e)}", status='failed')
```

### Subtitle Format Conversion

```python
def convert_transcript_to_srt(transcript_data):
    """Convert AWS Transcribe JSON to SRT format."""
    
    items = transcript_data['results']['items']
    subtitles = []
    current_segment = {
        'start': None,
        'end': None,
        'text': []
    }
    
    for item in items:
        if item['type'] == 'pronunciation':
            start_time = float(item['start_time'])
            end_time = float(item['end_time'])
            word = item['alternatives'][0]['content']
            
            if current_segment['start'] is None:
                current_segment['start'] = start_time
            
            current_segment['end'] = end_time
            current_segment['text'].append(word)
            
            # Create segment every 10 words or 5 seconds
            if (len(current_segment['text']) >= 10 or 
                end_time - current_segment['start'] >= 5.0):
                
                subtitles.append({
                    'start': current_segment['start'],
                    'end': current_segment['end'],
                    'text': ' '.join(current_segment['text'])
                })
                
                current_segment = {
                    'start': None,
                    'end': None,
                    'text': []
                }
        
        elif item['type'] == 'punctuation' and current_segment['text']:
            current_segment['text'][-1] += item['alternatives'][0]['content']
    
    # Add remaining segment
    if current_segment['text']:
        subtitles.append({
            'start': current_segment['start'],
            'end': current_segment['end'],
            'text': ' '.join(current_segment['text'])
        })
    
    # Generate SRT format
    srt_content = []
    for i, subtitle in enumerate(subtitles, 1):
        start_time = format_timestamp(subtitle['start'])
        end_time = format_timestamp(subtitle['end'])
        
        srt_content.append(f"{i}")
        srt_content.append(f"{start_time} --> {end_time}")
        srt_content.append(subtitle['text'])
        srt_content.append("")  # Blank line
    
    return '\n'.join(srt_content)


def format_timestamp(seconds):
    """Convert seconds to SRT timestamp format."""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    millis = int((seconds % 1) * 1000)
    
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"
```

---

## Next Document

➡️ **Part 3: Frontend Architecture & Components**  
Covers React components, state management, and UI implementation.

---

*End of Part 2*
