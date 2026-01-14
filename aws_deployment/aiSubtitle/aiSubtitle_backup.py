#!/usr/bin/env python3
"""
AI Subtitle Generation Service
A Flask-based backend service for generating subtitles from video files using AWS Transcribe.
"""

from flask import Flask, request, jsonify, send_file, render_template, Response
from flask_cors import CORS
import os
import tempfile
import subprocess
from datetime import datetime
import uuid
from pathlib import Path
import json
import time
import threading
from werkzeug.utils import secure_filename
from shared.env_loader import load_environment

# Load environment variables
load_environment()

# AWS imports (will be imported only if AWS credentials are available)
try:
    import boto3
    from botocore.exceptions import ClientError, NoCredentialsError
    
    # Initialize AWS clients if credentials are available
    aws_access_key = os.getenv('AWS_ACCESS_KEY_ID')
    aws_secret_key = os.getenv('AWS_SECRET_ACCESS_KEY')
    aws_region = os.getenv('AWS_REGION')
    aws_s3_bucket = os.getenv('AWS_S3_BUCKET')
    
    if aws_access_key and aws_secret_key and aws_s3_bucket:
        if not aws_region:
            raise RuntimeError("Set AWS_REGION before starting aiSubtitle service with AWS credentials")
        transcribe_client = boto3.client(
            'transcribe',
            aws_access_key_id=aws_access_key,
            aws_secret_access_key=aws_secret_key,
            region_name=aws_region
        )
        s3_client = boto3.client(
            's3',
            aws_access_key_id=aws_access_key,
            aws_secret_access_key=aws_secret_key,
            region_name=aws_region
        )
    else:
        transcribe_client = None
        s3_client = None
except ImportError:
    transcribe_client = None
    s3_client = None

app = Flask(__name__)

# Configure Flask for larger file uploads and longer timeouts
app.config['MAX_CONTENT_LENGTH'] = 5 * 1024 * 1024 * 1024  # 5GB
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 300  # 5 minutes for file serving
# Increase timeout for large file processing
app.config['PERMANENT_SESSION_LIFETIME'] = 30 * 60  # 30 minutes

CORS(app, 
     origins=['http://localhost:3000'],  # Allow frontend origin
     methods=['GET', 'POST', 'OPTIONS'],  # Allow necessary HTTP methods
     allow_headers=['Content-Type', 'Range'],  # Allow Range header for audio streaming
     expose_headers=['Accept-Ranges', 'Content-Range', 'Content-Length'],  # Expose headers for streaming
     max_age=600  # CORS preflight cache for 10 minutes
)

# Configuration
UPLOAD_FOLDER = 'uploads'
OUTPUT_FOLDER = 'outputs'
AUDIO_FOLDER = 'audio'
MAX_FILE_SIZE = 5 * 1024 * 1024 * 1024  # 5GB
ALLOWED_EXTENSIONS = {'mp4', 'avi', 'mov', 'mkv', 'webm', 'flv'}

# Create necessary directories
for folder in [UPLOAD_FOLDER, OUTPUT_FOLDER, AUDIO_FOLDER]:
    os.makedirs(folder, exist_ok=True)

# Progress tracking system
progress_data = {}
progress_lock = threading.Lock()

def update_progress(file_id, progress, message):
    """Update progress for a specific file_id."""
    with progress_lock:
        progress_data[file_id] = {
            'progress': progress,
            'message': message,
            'timestamp': time.time()
        }

def get_progress(file_id):
    """Get progress for a specific file_id."""
    with progress_lock:
        return progress_data.get(file_id, {'progress': 0, 'message': 'Starting...', 'timestamp': time.time()})

def allowed_file(filename):
    """Check if the uploaded file has an allowed extension."""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def extract_audio_from_video(video_path, audio_path):
    """Extract audio from video file using ffmpeg and convert to MP3."""
    try:
        cmd = [
            'ffmpeg', '-i', video_path,
            '-acodec', 'mp3',           # Use MP3 codec
            '-ab', '128k',              # 128k bitrate for good quality/size balance
            '-ac', '2',                 # Stereo audio
            '-ar', '44100',             # 44.1kHz sample rate
            '-vn',                      # No video output
            audio_path, '-y'            # Output file and overwrite if exists
        ]
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        print(f"Audio extraction successful for {video_path}")
        return True
    except subprocess.CalledProcessError as e:
        print(f"Error extracting audio: {e}")
        print(f"FFmpeg stderr: {e.stderr}")
        return False
    except FileNotFoundError:
        print("ffmpeg not found. Please install ffmpeg.")
        return False

def upload_to_s3_with_progress(file_path, bucket_name, object_name, file_id=None):
    """Upload a file to an S3 bucket with progress tracking and multipart upload for large files."""
    try:
        file_size = os.path.getsize(file_path)
        
        # Use multipart upload for files larger than 100MB
        if file_size > 100 * 1024 * 1024:  # 100MB threshold
            return _multipart_upload_to_s3(file_path, bucket_name, object_name, file_id, file_size)
        else:
            return _single_upload_to_s3(file_path, bucket_name, object_name, file_id, file_size)
            
    except Exception as e:
        if file_id:
            update_progress(file_id, -1, f"S3 upload failed: {str(e)}")
        print(f"Error uploading to S3: {e}")
        return None

def _single_upload_to_s3(file_path, bucket_name, object_name, file_id, file_size):
    """Single-part upload for smaller files."""
    def progress_callback(bytes_transferred):
        if file_id:
            progress = int((bytes_transferred / file_size) * 100)
            update_progress(file_id, progress, f"Uploading to S3... {progress}%")
    
    s3_client.upload_file(
        file_path, 
        bucket_name, 
        object_name,
        Callback=progress_callback
    )
    
    if file_id:
        update_progress(file_id, 100, "Upload to S3 completed")
    
    return f"s3://{bucket_name}/{object_name}"

def _multipart_upload_to_s3(file_path, bucket_name, object_name, file_id, file_size):
    """Multipart upload for large files with progress tracking."""
    # Initialize multipart upload
    response = s3_client.create_multipart_upload(
        Bucket=bucket_name,
        Key=object_name
    )
    upload_id = response['UploadId']
    
    try:
        parts = []
        part_size = 100 * 1024 * 1024  # 100MB parts
        part_number = 1
        bytes_uploaded = 0
        
        if file_id:
            update_progress(file_id, 0, "Starting multipart upload to S3...")
        
        with open(file_path, 'rb') as file:
            while True:
                # Read part
                part_data = file.read(part_size)
                if not part_data:
                    break
                
                if file_id:
                    progress = int((bytes_uploaded / file_size) * 100)
                    update_progress(file_id, progress, f"Uploading part {part_number} to S3... {progress}%")
                
                # Upload part
                part_response = s3_client.upload_part(
                    Bucket=bucket_name,
                    Key=object_name,
                    PartNumber=part_number,
                    UploadId=upload_id,
                    Body=part_data
                )
                
                parts.append({
                    'ETag': part_response['ETag'],
                    'PartNumber': part_number
                })
                
                bytes_uploaded += len(part_data)
                part_number += 1
        
        # Complete multipart upload
        s3_client.complete_multipart_upload(
            Bucket=bucket_name,
            Key=object_name,
            UploadId=upload_id,
            MultipartUpload={'Parts': parts}
        )
        
        if file_id:
            update_progress(file_id, 100, "Multipart upload to S3 completed")
        
        print(f"Multipart upload completed: {len(parts)} parts uploaded")
        return f"s3://{bucket_name}/{object_name}"
        
    except Exception as e:
        # Abort multipart upload on error
        s3_client.abort_multipart_upload(
            Bucket=bucket_name,
            Key=object_name,
            UploadId=upload_id
        )
        raise e

def upload_to_s3(file_path, bucket_name, object_name):
    """Upload a file to an S3 bucket for AWS Transcribe processing (legacy function)."""
    return upload_to_s3_with_progress(file_path, bucket_name, object_name)

def convert_transcribe_to_srt(transcription_json):
    """Convert AWS Transcribe JSON output to SRT format."""
    try:
        if isinstance(transcription_json, str):
            transcription_data = json.loads(transcription_json)
        else:
            transcription_data = transcription_json
            
        print(f"Transcription data keys: {transcription_data.keys()}")
        print(f"Results keys: {transcription_data.get('results', {}).keys()}")
        
        items = transcription_data['results']['items']
        print(f"Total items: {len(items)}")
        
        # Show a sample of items to understand the structure
        print(f"Sample items:")
        for i, item in enumerate(items[:5]):
            print(f"  Item {i}: {item}")
        
        words = []
        
        # Extract words with timestamps
        for i, item in enumerate(items):
            item_type = item.get('type')
            has_start_time = 'start_time' in item
            alternatives = item.get('alternatives', [])
            content = alternatives[0].get('content', 'N/A') if alternatives else 'N/A'
            print(f"Item {i}: type={item_type}, has_start_time={has_start_time}, content='{content}'")
            
            if item['type'] == 'pronunciation' and 'start_time' in item:
                words.append({
                    'word': item['alternatives'][0]['content'],
                    'start_time': float(item['start_time']),
                    'end_time': float(item['end_time'])
                })
        
        print(f"Words extracted: {len(words)}")
        if len(words) == 0:
            print("No words with timestamps found!")
            # Let's check if there are any full transcripts we can use
            if 'transcripts' in transcription_data['results']:
                print(f"Available transcripts: {len(transcription_data['results']['transcripts'])}")
                for i, transcript in enumerate(transcription_data['results']['transcripts']):
                    print(f"  Transcript {i}: {transcript}")
            return None
        
        # Group words into subtitle segments (10-15 words per segment)
        srt_content = ""
        segment_num = 1
        words_per_segment = 12
        
        for i in range(0, len(words), words_per_segment):
            segment_words = words[i:i + words_per_segment]
            if not segment_words:
                continue
                
            start_time = segment_words[0]['start_time']
            end_time = segment_words[-1]['end_time']
            
            # Format timestamp for SRT (HH:MM:SS,mmm)
            def format_srt_time(seconds):
                hours = int(seconds // 3600)
                minutes = int((seconds % 3600) // 60)
                secs = int(seconds % 60)
                millisecs = int((seconds % 1) * 1000)
                return f"{hours:02d}:{minutes:02d}:{secs:02d},{millisecs:03d}"
            
            start_formatted = format_srt_time(start_time)
            end_formatted = format_srt_time(end_time)
            
            text = ' '.join([word['word'] for word in segment_words])
            
            srt_content += f"{segment_num}\n"
            srt_content += f"{start_formatted} --> {end_formatted}\n"
            srt_content += f"{text}\n\n"
            
            segment_num += 1
        
        return srt_content.strip()
        
    except Exception as e:
        print(f"Error converting to SRT: {e}")
        import traceback
        traceback.print_exc()
        return None

def generate_subtitles_with_aws_transcribe(audio_path, file_id=None):
    """
    Generate subtitles using AWS Transcribe service.
    Returns SRT formatted subtitle content.
    Requires valid AWS credentials and configuration.
    """
    # Validate AWS configuration
    aws_access_key = os.getenv('AWS_ACCESS_KEY_ID')
    aws_secret_key = os.getenv('AWS_SECRET_ACCESS_KEY')
    aws_s3_bucket = os.getenv('AWS_S3_BUCKET')
    
    print(f"AWS credentials check:")
    print(f"  AWS_ACCESS_KEY_ID: {aws_access_key[:10] if aws_access_key else None}...")
    print(f"  AWS_SECRET_ACCESS_KEY: {'***' if aws_secret_key else None}")
    print(f"  AWS_S3_BUCKET: {aws_s3_bucket}")
    print(f"  transcribe_client: {transcribe_client is not None}")
    print(f"  s3_client: {s3_client is not None}")
    
    # Ensure AWS is properly configured
    if not transcribe_client or not s3_client or not aws_s3_bucket:
        error_msg = "AWS Transcribe is not configured. Please set AWS credentials and S3 bucket."
        print(f"ERROR: {error_msg}")
        if file_id:
            update_progress(file_id, -1, error_msg)
        raise ValueError(error_msg)
    
    try:
        print(f"Transcribing audio file with AWS Transcribe: {audio_path}")
        
        if file_id:
            update_progress(file_id, 20, "Starting AWS Transcribe job...")
        
        # Generate unique job name
        job_name = f"transcription-{uuid.uuid4().hex[:8]}-{int(time.time())}"
        
        # Upload audio file to S3
        audio_filename = os.path.basename(audio_path)
        s3_object_name = f"audio/{job_name}/{audio_filename}"
        
        print(f"Uploading audio to S3: {s3_object_name}")
        if file_id:
            update_progress(file_id, 30, "Uploading audio to S3 for transcription...")
            
        s3_uri = upload_to_s3(audio_path, os.getenv('AWS_S3_BUCKET'), s3_object_name)
        
        if not s3_uri:
            raise Exception("Failed to upload audio to S3")
        
        # Start transcription job
        print(f"Starting transcription job: {job_name}")
        if file_id:
            update_progress(file_id, 40, "Starting AWS Transcribe analysis...")
            
        transcribe_client.start_transcription_job(
            TranscriptionJobName=job_name,
            Media={'MediaFileUri': s3_uri},
            MediaFormat='mp3',
            LanguageCode='en-US',
            OutputBucketName=os.getenv('AWS_S3_BUCKET'),
            OutputKey=f"transcriptions/{job_name}.json"
        )
        
        # Wait for transcription to complete
        print("Waiting for transcription to complete...")
        if file_id:
            update_progress(file_id, 50, "AWS Transcribe processing audio...")
            
        max_wait_time = 300  # 5 minutes maximum wait
        wait_time = 0
        
        while wait_time < max_wait_time:
            response = transcribe_client.get_transcription_job(TranscriptionJobName=job_name)
            status = response['TranscriptionJob']['TranscriptionJobStatus']
            
            # Update progress based on wait time
            if file_id:
                progress = min(50 + (wait_time / max_wait_time) * 30, 80)
                update_progress(file_id, int(progress), f"Transcription in progress... ({wait_time}s)")
            
            if status == 'COMPLETED':
                if file_id:
                    update_progress(file_id, 85, "Downloading transcription results...")
                    
                transcript_uri = response['TranscriptionJob']['Transcript']['TranscriptFileUri']
                print(f"Transcription completed. Result URI: {transcript_uri}")
                
                # Extract S3 key from the URI 
                # URI format: https://s3.region.amazonaws.com/bucket/key
                # We need to extract only the key part (after the bucket)
                import urllib.parse
                parsed_uri = urllib.parse.urlparse(transcript_uri)
                # For S3 URIs, the path includes the bucket and key: /bucket/key
                # We need to remove the bucket part and keep only the key
                path_parts = parsed_uri.path.strip('/').split('/', 1)
                if len(path_parts) > 1:
                    # Remove bucket name from path
                    transcript_key = path_parts[1]  # This should be the key after bucket name
                else:
                    # This shouldn't happen, but fallback
                    transcript_key = parsed_uri.path.lstrip('/')
                
                print(f"Full transcript URI: {transcript_uri}")
                print(f"Parsed path: {parsed_uri.path}")
                print(f"Path parts: {path_parts}")
                print(f"Final transcript key: {transcript_key}")
                print(f"Bucket: {os.getenv('AWS_S3_BUCKET')}")
                
                transcript_file = f"/tmp/{job_name}_transcript.json"
                
                s3_client.download_file(os.getenv('AWS_S3_BUCKET'), transcript_key, transcript_file)
                print(f"Downloaded transcript to: {transcript_file}")
                
                if file_id:
                    update_progress(file_id, 90, "Converting to SRT format...")
                
                # Read and convert to SRT
                with open(transcript_file, 'r') as f:
                    transcript_data = json.load(f)
                
                srt_content = convert_transcribe_to_srt(transcript_data)
                
                # Cleanup temporary files
                try:
                    os.remove(transcript_file)
                    s3_client.delete_object(Bucket=os.getenv('AWS_S3_BUCKET'), Key=s3_object_name)
                    s3_client.delete_object(Bucket=os.getenv('AWS_S3_BUCKET'), Key=transcript_key)
                except:
                    pass  # Ignore cleanup errors
                
                if srt_content:
                    return srt_content
                else:
                    raise Exception("Failed to convert transcription to SRT format")
                    
            elif status == 'FAILED':
                failure_reason = response['TranscriptionJob'].get('FailureReason', 'Unknown error')
                raise Exception(f"Transcription failed: {failure_reason}")
            
            time.sleep(10)  # Wait 10 seconds before checking again
            wait_time += 10
        
        raise Exception("Transcription timed out")
        
    except Exception as e:
        print(f"Error in AWS Transcribe: {e}")
        print(f"Error type: {type(e).__name__}")
        import traceback
        print("Full traceback:")
        traceback.print_exc()
        if file_id:
            update_progress(file_id, -1, f"AWS Transcribe failed: {str(e)}")
        raise e  # Re-raise the error instead of falling back

def format_timestamp(seconds):
    """Convert seconds to SRT timestamp format (HH:MM:SS,mmm)."""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    millisecs = int((seconds % 1) * 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{millisecs:03d}"

@app.route('/', methods=['GET'])
def index():
    """Serve the main HTML page."""
    return render_template('index.html')

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint."""
    return jsonify({
        'status': 'healthy',
        'service': 'AI Subtitle Generation',
        'port': 5001,
        'timestamp': datetime.now().isoformat()
    })

@app.route('/progress/<file_id>', methods=['GET'])
def get_progress_endpoint(file_id):
    """Get progress for a specific file upload/processing."""
    progress_info = get_progress(file_id)
    return jsonify(progress_info)

@app.route('/api-status', methods=['GET'])
def api_status():
    """Check AWS Transcribe availability - AWS is required for operation."""
    aws_configured = (transcribe_client is not None and 
                     s3_client is not None and 
                     bool(os.getenv('AWS_S3_BUCKET')))
    
    return jsonify({
        'aws_transcribe_available': transcribe_client is not None,
        'aws_s3_available': s3_client is not None,
        'aws_credentials_configured': bool(os.getenv('AWS_ACCESS_KEY_ID') and os.getenv('AWS_SECRET_ACCESS_KEY')),
        'aws_s3_bucket_configured': bool(os.getenv('AWS_S3_BUCKET')),
        'service_operational': aws_configured,
        'subtitle_mode': 'aws_transcribe_only',
    'aws_region': os.getenv('AWS_REGION'),
        'timestamp': datetime.now().isoformat(),
        'message': 'AWS configuration required for operation' if not aws_configured else 'Service ready'
    })

def _save_large_file_streaming(file_stream, output_path, file_id, total_size):
    """Save large file using streaming to avoid memory issues."""
    chunk_size = 8 * 1024 * 1024  # 8MB chunks
    bytes_written = 0
    
    with open(output_path, 'wb') as output_file:
        while True:
            chunk = file_stream.read(chunk_size)
            if not chunk:
                break
            
            output_file.write(chunk)
            bytes_written += len(chunk)
            
            # Update progress for file saving
            progress = int((bytes_written / total_size) * 20)  # 0-20% for file saving
            update_progress(file_id, progress, f"Saving file... {progress}%")
    
    update_progress(file_id, 20, "Large file saved successfully")

@app.route('/upload', methods=['POST'])
def upload_video():
    """Upload video file and automatically extract audio. Requires AWS configuration."""
    try:
        # Check AWS configuration first
        if not transcribe_client or not s3_client or not os.getenv('AWS_S3_BUCKET'):
            return jsonify({
                'error': 'AWS Transcribe is not configured. Please set AWS credentials and S3 bucket.',
                'aws_configured': False
            }), 503
        
        # Check if file is present
        if 'video' not in request.files:
            return jsonify({'error': 'No video file provided'}), 400
        
        file = request.files['video']
        
        # Check if file is selected
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400
        
        # Check file extension
        if not allowed_file(file.filename):
            return jsonify({'error': 'Invalid file type. Allowed: ' + ', '.join(ALLOWED_EXTENSIONS)}), 400
        
        # Check file size
        file.seek(0, os.SEEK_END)
        file_size = file.tell()
        file.seek(0)
        
        if file_size > MAX_FILE_SIZE:
            # Convert to GB for display
            max_size_gb = MAX_FILE_SIZE / (1024 * 1024 * 1024)
            return jsonify({'error': f'File too large. Maximum size: {max_size_gb:.0f}GB'}), 400
        
        # Generate unique filename
        file_id = str(uuid.uuid4())
        file_extension = file.filename.rsplit('.', 1)[1].lower()
        video_filename = f"{file_id}.{file_extension}"
        video_path = os.path.join(UPLOAD_FOLDER, video_filename)
        
        # Initialize progress
        update_progress(file_id, 0, f"Starting upload of {file_size / (1024*1024*1024):.2f}GB file...")
        
        # Save uploaded file with streaming for large files
        if file_size > 100 * 1024 * 1024:  # Stream files larger than 100MB
            _save_large_file_streaming(file, video_path, file_id, file_size)
        else:
            file.save(video_path)
        
        update_progress(file_id, 20, "Video saved locally...")
        
        # Start background processing
        def process_in_background():
            try:
                # Automatically extract audio
                audio_filename = f"{file_id}.mp3"
                audio_path = os.path.join(AUDIO_FOLDER, audio_filename)
                
                update_progress(file_id, 30, "Extracting audio from video...")
                
                if not extract_audio_from_video(video_path, audio_path):
                    update_progress(file_id, -1, "Failed to extract audio from video")
                    return
                
                update_progress(file_id, 50, "Audio extraction completed")
                
                # Upload to S3
                try:
                    # Upload both video and audio files
                    if s3_client and os.getenv('AWS_S3_BUCKET'):
                        update_progress(file_id, 60, "Preparing S3 upload...")
                        
                        # Upload video
                        s3_video_key = f"videos/{file_id}/{video_filename}"
                        s3_audio_key = f"audio/{file_id}/{audio_filename}"
                        
                        # Upload video file
                        upload_to_s3_with_progress(video_path, os.getenv('AWS_S3_BUCKET'), s3_video_key, file_id)
                        
                        # Upload audio file
                        upload_to_s3_with_progress(audio_path, os.getenv('AWS_S3_BUCKET'), s3_audio_key, file_id)
                        
                        print(f"Files uploaded to S3: {s3_video_key}, {s3_audio_key}")
                        
                except Exception as e:
                    update_progress(file_id, -1, f"S3 upload failed: {str(e)}")
                    print(f"S3 upload failed: {e}")
                    return
                
                update_progress(file_id, 100, "Upload and processing completed")
                
            except Exception as e:
                update_progress(file_id, -1, f"Processing failed: {str(e)}")
                print(f"Background processing failed: {e}")
        
        # Start background thread
        import threading
        thread = threading.Thread(target=process_in_background)
        thread.daemon = True
        thread.start()
        
        # Return response with file info
        return jsonify({
            'file_id': file_id,
            'filename': file.filename,
            'size': file_size,
            'message': 'Upload started successfully'
        }), 200
        
    except Exception as e:
        return jsonify({'error': f'Upload failed: {str(e)}'}), 500

def _save_large_file_streaming(file_stream, output_path, file_id, total_size):
    """Save large file using streaming to avoid memory issues."""
    chunk_size = 8 * 1024 * 1024  # 8MB chunks
    bytes_written = 0
    
    with open(output_path, 'wb') as output_file:
        while True:
            chunk = file_stream.read(chunk_size)
            if not chunk:
                break
            
            output_file.write(chunk)
            bytes_written += len(chunk)
            
            # Update progress for file saving
            progress = int((bytes_written / total_size) * 20)  # 0-20% for file saving
            update_progress(file_id, progress, f"Saving file... {progress}%")
    
    update_progress(file_id, 20, "Large file saved successfully")

@app.route('/download-audio/<file_id>', methods=['GET'])
def download_audio(file_id):
    """Serve extracted audio file for playback or download."""
    try:
        audio_path = os.path.join(AUDIO_FOLDER, f"{file_id}.mp3")
        
        if not os.path.exists(audio_path):
            return jsonify({'error': 'Audio file not found'}), 404
        
        # Check if client wants to download or stream
        # If 'download' parameter is present, serve as attachment
        download_requested = request.args.get('download') is not None
        
        return send_file(
            audio_path,
            as_attachment=download_requested,
            download_name=f"audio_{file_id}.mp3" if download_requested else None,
            mimetype='audio/mpeg',
            conditional=True  # Enable range requests for audio streaming
        )
        
    except Exception as e:
        return jsonify({'error': f'Download failed: {str(e)}'}), 500

@app.route('/stream-audio/<file_id>', methods=['GET'])
def stream_audio(file_id):
    """Stream audio file for web playback with proper headers."""
    try:
        audio_path = os.path.join(AUDIO_FOLDER, f"{file_id}.mp3")
        
        if not os.path.exists(audio_path):
            return jsonify({'error': 'Audio file not found'}), 404
        
        # Serve audio file with streaming-friendly headers
        response = send_file(
            audio_path,
            mimetype='audio/mpeg',
            as_attachment=False,
            conditional=True  # Enable range requests for streaming
        )
        
        # Add headers for better browser compatibility
        response.headers['Accept-Ranges'] = 'bytes'
        response.headers['Cache-Control'] = 'public, max-age=3600'
        response.headers['Content-Disposition'] = 'inline'
        
        return response
        
    except Exception as e:
        return jsonify({'error': f'Streaming failed: {str(e)}'}), 500

@app.route('/generate-subtitles', methods=['POST'])
def generate_subtitles():
    """Generate subtitles from uploaded video using AWS Transcribe."""
    try:
        # Check AWS configuration first
        if not transcribe_client or not s3_client or not os.getenv('AWS_S3_BUCKET'):
            return jsonify({
                'error': 'AWS Transcribe is not configured. Please set AWS credentials and S3 bucket.',
                'aws_configured': False
            }), 503
        
        data = request.get_json()
        file_id = data.get('file_id')
        
        if not file_id:
            return jsonify({'error': 'File ID is required'}), 400
        
        # Initialize progress for subtitle generation
        update_progress(file_id, 0, "Starting subtitle generation...")
        
        # Find audio file (should already exist from upload)
        audio_path = os.path.join(AUDIO_FOLDER, f"{file_id}.mp3")
        
        if not os.path.exists(audio_path):
            return jsonify({'error': 'Audio file not found. Please upload video first.'}), 404
        
        # Start background subtitle generation
        def generate_in_background():
            try:
                update_progress(file_id, 10, "Preparing AWS Transcribe request...")
                
                # Generate subtitles using AWS Transcribe
                subtitles_content = generate_subtitles_with_aws_transcribe(audio_path, file_id)
                
                if subtitles_content:
                    update_progress(file_id, 90, "Saving subtitle file...")
                    
                    # Save subtitles to file
                    subtitles_filename = f"{file_id}.srt"
                    subtitles_path = os.path.join(OUTPUT_FOLDER, subtitles_filename)
                    
                    with open(subtitles_path, 'w', encoding='utf-8') as f:
                        f.write(subtitles_content)
                    
                    update_progress(file_id, 100, "Subtitles generated successfully!")
                else:
                    update_progress(file_id, -1, "Failed to generate subtitles")
                    
            except Exception as e:
                update_progress(file_id, -1, f"Subtitle generation failed: {str(e)}")
        
        # Start background thread
        thread = threading.Thread(target=generate_in_background)
        thread.start()
        
        return jsonify({
            'message': 'Subtitle generation started',
            'file_id': file_id,
            'progress_url': f'/progress/{file_id}'
        }), 200
        
    except Exception as e:
        return jsonify({'error': f'Subtitle generation failed: {str(e)}'}), 500

@app.route('/subtitles/<file_id>', methods=['GET'])
def get_subtitles(file_id):
    """Get generated subtitles for a file."""
    try:
        subtitles_path = os.path.join(OUTPUT_FOLDER, f"{file_id}.srt")
        
        if not os.path.exists(subtitles_path):
            return jsonify({'error': 'Subtitle file not found'}), 404
        
        # Read subtitle content
        with open(subtitles_path, 'r', encoding='utf-8') as f:
            subtitles_content = f.read()
        
        return jsonify({
            'file_id': file_id,
            'subtitles': subtitles_content,
            'download_url': f'/download/{file_id}'
        }), 200
        
    except Exception as e:
        return jsonify({'error': f'Failed to get subtitles: {str(e)}'}), 500

@app.route('/download/<file_id>', methods=['GET'])
def download_subtitles(file_id):
    """Download generated subtitle file."""
    try:
        subtitles_path = os.path.join(OUTPUT_FOLDER, f"{file_id}.srt")
        
        if not os.path.exists(subtitles_path):
            return jsonify({'error': 'Subtitle file not found'}), 404
        
        return send_file(
            subtitles_path,
            as_attachment=True,
            download_name=f"subtitles_{file_id}.srt",
            mimetype='text/plain'
        )
        
    except Exception as e:
        return jsonify({'error': f'Download failed: {str(e)}'}), 500

@app.route('/status/<file_id>', methods=['GET'])
def get_processing_status(file_id):
    """Get processing status for a file."""
    try:
        video_files = [f for f in os.listdir(UPLOAD_FOLDER) if f.startswith(file_id)]
        subtitles_path = os.path.join(OUTPUT_FOLDER, f"{file_id}.srt")
        
        if not video_files:
            return jsonify({'status': 'not_found'}), 404
        
        if os.path.exists(subtitles_path):
            return jsonify({'status': 'completed'}), 200
        else:
            return jsonify({'status': 'processing'}), 200
            
    except Exception as e:
        return jsonify({'error': f'Status check failed: {str(e)}'}), 500

@app.route('/cleanup/<file_id>', methods=['DELETE'])
def cleanup_files(file_id):
    """Clean up uploaded and generated files."""
    try:
        # Remove video file
        video_files = [f for f in os.listdir(UPLOAD_FOLDER) if f.startswith(file_id)]
        for video_file in video_files:
            video_path = os.path.join(UPLOAD_FOLDER, video_file)
            if os.path.exists(video_path):
                os.remove(video_path)
        
        # Remove subtitle file
        subtitles_path = os.path.join(OUTPUT_FOLDER, f"{file_id}.srt")
        if os.path.exists(subtitles_path):
            os.remove(subtitles_path)
        
        return jsonify({'message': 'Files cleaned up successfully'}), 200
        
    except Exception as e:
        return jsonify({'error': f'Cleanup failed: {str(e)}'}), 500

@app.errorhandler(413)
def too_large(e):
    """Handle file too large error."""
    return jsonify({'error': 'File too large'}), 413

@app.errorhandler(404)
def not_found(e):
    """Handle not found errors."""
    return jsonify({'error': 'Resource not found'}), 404

@app.errorhandler(500)
def internal_error(e):
    """Handle internal server errors."""
    return jsonify({'error': 'Internal server error'}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5001))
    debug = os.environ.get('DEBUG', 'True').lower() == 'true'
    
    print(f"Starting AI Subtitle Generation Service on port {port}")
    print(f"Upload folder: {os.path.abspath(UPLOAD_FOLDER)}")
    print(f"Output folder: {os.path.abspath(OUTPUT_FOLDER)}")
    print(f"Max file size: {MAX_FILE_SIZE / (1024*1024*1024):.1f}GB")
    
    # Configure Werkzeug for large file uploads
    from werkzeug.serving import WSGIRequestHandler
    
    # Increase request timeout for large file uploads
    WSGIRequestHandler.timeout = 30 * 60  # 30 minutes
    
    app.run(
        host='0.0.0.0',
        port=port,
        debug=debug,
        threaded=True,  # Enable threading for better concurrent handling
        request_handler=WSGIRequestHandler
    )