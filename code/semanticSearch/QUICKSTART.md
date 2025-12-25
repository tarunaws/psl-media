# Semantic Video Search - Quick Start Guide

## 🎯 What is Semantic Video Search?

Search your video library using natural language! Instead of searching by filename or manual tags, you can search by:
- **Visual content**: "sunset on the beach", "people dancing"
- **Dialogue**: "thank you speech", "emotional moment"
- **Emotions**: "happy celebration", "sad farewell"
- **Activities**: "outdoor sports", "cooking demonstration"
- **Text on screen**: "news headlines", "title cards"

## 🚀 How It Works

1. **Upload a video** → System extracts frames every 10 seconds
2. **AWS Rekognition analyzes** → Detects objects, scenes, faces, emotions, text
3. **AWS Transcribe converts** → Audio to text transcript
4. **AWS Bedrock creates** → Semantic embedding (vector representation)
5. **Search with natural language** → Find videos by meaning, not just keywords

## 📋 Prerequisites

### AWS Services Required
- ✅ Amazon Rekognition (for visual analysis)
- ✅ Amazon Transcribe (for speech-to-text)
- ✅ Amazon Bedrock (for embeddings) - **Titan Embeddings model**
- ✅ Amazon S3 (for temporary storage)

### Enable Bedrock Model Access
1. Go to AWS Console → Amazon Bedrock
2. Click "Model access" in left sidebar
3. Find "Titan Embeddings G1 - Text"
4. Click "Request access" (usually instant approval)

### AWS Credentials
Ensure your AWS credentials are configured:
```bash
aws configure
# Enter your AWS Access Key ID
# Enter your AWS Secret Access Key
# Default region: us-east-1
```

### Dependencies
```bash
cd semanticSearch
pip install -r requirements.txt
```

## 🎬 Usage

### Start the Service

```bash
# From project root
./start-backend.sh

# Or start semantic search only
cd semanticSearch
python app.py
```

Service runs on **http://localhost:5008**

### Access the UI

Open your browser:
```
http://localhost:3000/semantic-search
```

### API Examples

#### 1. Upload a Video
```bash
curl -X POST http://localhost:5008/upload-video \
  -F "video=@/path/to/video.mp4" \
  -F "title=Beach Vacation 2024" \
  -F "description=Family trip to Hawaii"
```

Response:
```json
{
  "id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "title": "Beach Vacation 2024",
  "message": "Video uploaded and indexed successfully",
  "labels_count": 45,
  "transcript_length": 1234,
  "frame_count": 18
}
```

#### 2. Search Videos
```bash
curl -X POST http://localhost:5008/search \
  -H "Content-Type: application/json" \
  -d '{
    "query": "happy moments at the beach",
    "top_k": 5
  }'
```

Response:
```json
{
  "query": "happy moments at the beach",
  "results": [
    {
      "id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
      "title": "Beach Vacation 2024",
      "similarity_score": 0.8542,
      "labels": ["Beach", "Ocean", "Person", "Happy", "Outdoor"],
      "emotions": ["HAPPY", "CALM"],
      "transcript_snippet": "Look at those beautiful waves..."
    }
  ],
  "total_videos": 10
}
```

#### 3. List All Videos
```bash
curl http://localhost:5008/videos
```

#### 4. Get Video Details
```bash
curl http://localhost:5008/video/{video_id}
```

## 🔍 Search Examples

### Scene-Based
- "sunset on the beach"
- "indoor office meeting"
- "rainy street scenes"
- "mountain landscape"

### Dialogue-Based
- "thank you speech"
- "wedding vows"
- "tutorial explanation"
- "news report"

### Emotion-Based
- "happy celebration"
- "sad goodbye"
- "excited reaction"
- "calm meditation"

### Activity-Based
- "people dancing"
- "cooking demonstration"
- "sports competition"
- "walking in park"

### Text-Based
- "news headlines"
- "title cards"
- "street signs"
- "product labels"

## 🏗️ Architecture

```
┌─────────────┐
│ Upload Video│
└──────┬──────┘
       │
       ▼
┌─────────────────────┐
│ Extract Frames      │
│ (every 10 seconds)  │
└──────┬──────────────┘
       │
       ▼
┌─────────────────────┐
│ AWS Rekognition     │
│ - Detect Labels     │
│ - Detect Text       │
│ - Detect Faces      │
│ - Detect Emotions   │
└──────┬──────────────┘
       │
       ├────────────────┐
       │                │
       ▼                ▼
┌─────────────┐  ┌─────────────┐
│ Extract     │  │ Aggregate   │
│ Audio       │  │ Visual      │
└──────┬──────┘  │ Metadata    │
       │         └──────┬──────┘
       ▼                │
┌─────────────┐         │
│ AWS         │         │
│ Transcribe  │         │
└──────┬──────┘         │
       │                │
       └────────┬───────┘
                │
                ▼
       ┌────────────────┐
       │ Combine All    │
       │ Metadata       │
       └────────┬───────┘
                │
                ▼
       ┌────────────────┐
       │ AWS Bedrock    │
       │ Titan Embed    │
       └────────┬───────┘
                │
                ▼
       ┌────────────────┐
       │ Store in Index │
       │ (Vector + Meta)│
       └────────────────┘
```

## 💰 Cost Estimation

Per video processing (10-minute video):

| Service | Usage | Cost |
|---------|-------|------|
| Rekognition (Labels) | 30 frames | $0.03 |
| Rekognition (Text) | 30 frames | $0.03 |
| Rekognition (Faces) | 30 frames | $0.03 |
| Transcribe | 10 minutes | $0.24 |
| Bedrock Titan | 1 embedding | $0.001 |
| S3 | Temporary storage | ~$0.00 |
| **Total** | | **~$0.33** |

*Note: Costs are approximate and vary by region*

## ⚡ Performance

### Processing Time
- **1-2 minute video**: 2-3 minutes
- **5-10 minute video**: 5-8 minutes
- **20+ minute video**: 10-15 minutes

Bottleneck: AWS Transcribe (real-time or slower)

### Optimizations
- Limits to 30 frames per video
- Extracts frames every 10 seconds
- Uses multipart upload for large files
- Cleans up temporary files automatically

## 🎨 UI Features

- **Drag & Drop Upload**: Easy video upload interface
- **Real-time Progress**: See upload and processing status
- **Search Suggestions**: Example queries to get started
- **Similarity Scores**: See how well each video matches your query
- **Visual Previews**: Thumbnail from middle of video
- **Detailed View**: Click any video to see full analysis

## 🔧 Configuration

### Environment Variables
```bash
# AWS Configuration
AWS_REGION=us-east-1

# S3 Bucket for temporary transcription files
SEMANTIC_SEARCH_BUCKET=mediagenai-semantic-search

# FFmpeg Path (auto-detected if not set)
FFMPEG_PATH=/opt/homebrew/bin/ffmpeg
```

### Customization

**Frame Interval** (default: 10 seconds):
```python
# In app.py, _extract_video_frames function
frames = _extract_video_frames(video_path, frames_dir, interval=10)
```

**Max Frames** (default: 30):
```python
# In app.py, upload_video function
for frame in frames[:30]:  # Limit to 30 frames
```

**Search Results** (default: 5):
```python
# In frontend, search request
{
  "query": "...",
  "top_k": 5  // Change this
}
```

## 🚨 Troubleshooting

### "Bedrock model not accessible"
**Solution**: Enable Titan Embeddings in AWS Bedrock console
1. Go to AWS Bedrock
2. Click "Model access"
3. Enable "Titan Embeddings G1 - Text"

### "S3 bucket access denied"
**Solution**: Ensure IAM permissions
```json
{
  "Effect": "Allow",
  "Action": [
    "s3:CreateBucket",
    "s3:PutObject",
    "s3:GetObject",
    "s3:DeleteObject"
  ],
  "Resource": "arn:aws:s3:::mediagenai-semantic-search/*"
}
```

### "FFmpeg not found"
**Solution**: Install FFmpeg
```bash
# macOS
brew install ffmpeg

# Ubuntu
sudo apt-get install ffmpeg
```

### "Transcription timeout"
**Solution**: Increase timeout for longer videos
```python
# In app.py, _extract_audio_and_transcribe function
max_wait = 300  # Increase this (in seconds)
```

### "No results found"
**Possible causes**:
1. Video not fully indexed yet (check logs)
2. Query too specific or vague
3. Try different search terms

## 📊 Monitoring

### Check Service Status
```bash
curl http://localhost:5008/health
```

### View Logs
```bash
tail -f semantic-search.log
```

### Check Indexed Videos
```bash
curl http://localhost:5008/videos | jq
```

## 🔮 Future Enhancements

1. **Video Segmentation**: Search within specific timestamps
2. **OpenSearch Integration**: Replace in-memory index for production
3. **Async Processing**: Queue-based processing for multiple videos
4. **Multi-modal Search**: Upload image to find similar scenes
5. **Advanced Filters**: Duration, date, specific labels
6. **Video Clips**: Return specific clips instead of full videos
7. **Batch Upload**: Process multiple videos at once
8. **Real-time Indexing**: Stream processing for live videos

## 📝 Notes

- **In-Memory Index**: Videos are lost on server restart. For production, use OpenSearch or DynamoDB.
- **Video Storage**: Currently only metadata is stored, not the actual video files.
- **Processing Time**: Transcription takes time proportional to video length.
- **API Limits**: Be aware of AWS service limits (Rekognition: 5 TPS, Transcribe: 100 concurrent jobs).

## 🎓 Learn More

- [AWS Rekognition Documentation](https://docs.aws.amazon.com/rekognition/)
- [AWS Transcribe Documentation](https://docs.aws.amazon.com/transcribe/)
- [AWS Bedrock Documentation](https://docs.aws.amazon.com/bedrock/)
- [Semantic Search Concepts](https://en.wikipedia.org/wiki/Semantic_search)

## 🆘 Support

For issues or questions:
1. Check logs: `tail -f semantic-search.log`
2. Verify AWS credentials: `aws sts get-caller-identity`
3. Test Bedrock access: Check model access in console
4. Review README.md for detailed API documentation

---

**Ready to start?** Upload your first video at http://localhost:3000/semantic-search 🎬
