# AWS Transcribe Integration Setup

## Overview
The AI Subtitle Generation service now supports real subtitle generation using AWS Transcribe service instead of mock data.

## Setup Instructions

### 1. Install Required Packages
```bash
# Activate virtual environment
source .venv/bin/activate

# Install required packages
pip install boto3 moviepy pydub
```

### 2. Set Up AWS Account & Credentials
1. Go to [AWS Console](https://aws.amazon.com/console/)
2. Sign up or log in to your AWS account
3. Create an IAM user with the following permissions:
   - `AmazonTranscribeFullAccess`
   - `AmazonS3FullAccess` (for temporary audio file storage)
4. Generate Access Key and Secret Key for the IAM user
5. Create an S3 bucket for temporary file storage

### 3. Configure Environment Variables
Create a `.env` file in the `aiSubtitle` directory:

```bash
# Copy the example file
cp .env.example .env

# Edit the .env file
nano .env
```

Add your AWS credentials:
```env
AWS_ACCESS_KEY_ID=AKIAIOSFODNN7EXAMPLE
AWS_SECRET_ACCESS_KEY=wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY
AWS_REGION=us-east-1
AWS_S3_BUCKET=your-transcribe-bucket-name
```

### 4. Create S3 Bucket
```bash
# Using AWS CLI (optional)
aws s3 mb s3://your-transcribe-bucket-name --region us-east-1
```

### 5. Restart the Backend Service
```bash
# Stop current services
./stop-backend.sh

# Start services with new configuration
./start-backend.sh
```

## API Endpoints

### Check API Status
```bash
curl http://localhost:5001/api-status
```

Response:
```json
{
  "aws_transcribe_available": true,
  "aws_s3_available": true,
  "aws_credentials_configured": true,
  "aws_s3_bucket_configured": true,
  "subtitle_mode": "aws_transcribe",
  "aws_region": "us-east-1",
  "timestamp": "2025-10-08T23:30:00"
}
```

## How It Works

1. **Video Upload**: Upload video file via `/upload` endpoint
2. **Audio Extraction**: Extract MP3 audio from video using FFmpeg
3. **S3 Upload**: Temporarily upload audio to S3 bucket
4. **AWS Transcribe**: Start transcription job and wait for completion
5. **SRT Conversion**: Convert AWS Transcribe JSON output to SRT format
6. **Cleanup**: Remove temporary files from S3
7. **Download**: Download generated subtitle file

## Transcription Process

### AWS Transcribe Features Used:
- **Language**: English (en-US) - can be configured
- **Format**: MP3 audio input
- **Output**: JSON with word-level timestamps
- **Speaker Labels**: Disabled (can be enabled for multi-speaker content)

### SRT Generation:
- Groups words into 12-word segments for readability
- Preserves precise timing from AWS Transcribe
- Formats timestamps in standard SRT format (HH:MM:SS,mmm)

## Fallback Behavior

- If AWS credentials are not configured, the service falls back to mock subtitles
- If AWS Transcribe job fails, it automatically uses mock subtitles as backup
- The system gracefully handles network issues and AWS service limits

## Supported Audio Formats

AWS Transcribe supports:
- MP3, MP4, WAV, FLAC, AMR, 3GA, M4A, OGG, WebM

Our service extracts audio as MP3 for optimal compatibility.

## Cost Considerations

- AWS Transcribe pricing: $0.024 per minute of audio (first 60 minutes free per month)
- For a 10-minute video: ~$0.24
- S3 storage costs are minimal for temporary files
- Consider implementing usage limits for production use

## AWS Service Limits

- Maximum audio file size: 2 GB
- Maximum audio duration: 4 hours
- Supported sample rates: 8000 Hz to 48000 Hz

## Troubleshooting

### Check API Status
```bash
curl http://localhost:5001/api-status
```

### Common Issues
1. **Invalid AWS Credentials**: Check `.env` file configuration
2. **S3 Bucket Access**: Verify bucket exists and permissions are correct
3. **Network Issues**: Verify internet connection to AWS services
4. **File Size Limits**: AWS Transcribe has file size limitations
5. **Service Limits**: AWS may throttle requests

### Logs
Check the backend logs for detailed error messages:
```bash
tail -f ai-subtitle.log
```

### AWS CLI Setup (Optional)
```bash
# Install AWS CLI
pip install awscli

# Configure AWS CLI
aws configure
```

## Security Notes

- Store AWS credentials securely in `.env` file
- Use IAM roles with minimal required permissions
- Consider using AWS IAM roles instead of access keys in production
- Regularly rotate access keys
- Monitor AWS CloudTrail for access logs