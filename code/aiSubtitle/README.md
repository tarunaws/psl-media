# AI Subtitle Service

A Flask-based backend service for generating subtitles from video files using AWS Transcribe.

## 📁 Folder Structure

```
aiSubtitle/
├── .env                    # AWS credentials configuration
├── .env.example           # Example environment configuration
├── aiSubtitle.py          # Main Flask application
├── requirements.txt       # Python dependencies
├── AWS_TRANSCRIBE_SETUP.md # Setup documentation
├── audio/                 # Extracted audio files (MP3)
├── outputs/               # Generated subtitle files (SRT)
├── templates/             # HTML templates
│   └── index.html        # Basic web interface
└── uploads/               # Uploaded video files
```

## 🚀 Quick Start

1. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Configure AWS (optional):**
   ```bash
   cp .env.example .env
   # Edit .env with your AWS credentials
   ```

3. **Run the service:**
   ```bash
   python aiSubtitle.py
   ```

4. **Access the API:**
   - Service: http://localhost:5001
   - Health: http://localhost:5001/health
   - Status: http://localhost:5001/api-status

## 📋 API Endpoints

- `POST /upload` - Upload video file
- `POST /extract-audio` - Extract audio from video
- `POST /generate-subtitles` - Generate subtitles with AWS Transcribe
- `GET /download/{file_id}` - Download SRT file
- `GET /stream-audio/{file_id}` - Stream audio file
- `GET /api-status` - Check AWS configuration status

## 🔧 Features

- **Video Upload**: Support for MP4, AVI, MOV formats
- **Audio Extraction**: High-quality MP3 extraction using FFmpeg
- **AWS Transcribe**: Real-time speech-to-text conversion
- **SRT Generation**: Professional subtitle file format
- **Enhanced Mock Mode**: Realistic subtitles when AWS is not configured
- **Error Handling**: Graceful fallback mechanisms
- **CORS Support**: Ready for frontend integration

## 📖 Documentation

See `AWS_TRANSCRIBE_SETUP.md` for detailed setup instructions and AWS configuration.

## 🧹 Clean Structure

This folder has been cleaned of all irrelevant files. Only essential AI subtitle functionality remains:
- Removed Bedrock/Titan related files
- Removed Lambda configuration files
- Removed test scripts and old documentation
- Kept only working files and current test data