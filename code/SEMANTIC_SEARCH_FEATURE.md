# Semantic Video Search - Complete Feature Documentation

## 🎯 Overview

**Semantic Video Search** is a new feature in MediaGenAI that enables natural language search across your video library. Unlike traditional filename or tag-based search, this uses AI to understand the **actual content** of your videos - what's shown, what's said, and what emotions are expressed.

## ✨ Key Capabilities

### 1. Multi-Modal Video Analysis
- **Visual Recognition**: Objects, scenes, activities (e.g., "beach", "sunset", "dancing")
- **Speech-to-Text**: Full transcription of spoken dialogue
- **Text Detection**: On-screen text like titles, captions, signs
- **Emotion Analysis**: Facial expressions and emotions detected
- **Semantic Understanding**: Converts all metadata into searchable embeddings

### 2. Natural Language Search
Search using plain English queries:
- "happy moments at the beach"
- "someone giving a speech"
- "outdoor activities with children"
- "sunset scenes with ocean"
- "emotional farewell"

### 3. Intelligent Ranking
Results are ranked by **semantic similarity** (0-100% match score), not just keyword matching.

## 🏗️ Technical Architecture

### AWS Services Integration

```
┌─────────────────────────────────────────────────────┐
│                  Video Upload                        │
└─────────────────┬───────────────────────────────────┘
                  │
                  ▼
    ┌─────────────────────────┐
    │   Frame Extraction      │
    │   (FFmpeg - 10s interval)│
    └─────────┬───────────────┘
              │
              ▼
    ┌─────────────────────────┐
    │  Amazon Rekognition     │
    │  • DetectLabels         │──► Objects, Scenes, Activities
    │  • DetectText           │──► On-screen text
    │  • DetectFaces          │──► Emotions, Demographics
    └─────────┬───────────────┘
              │
              ├─────────────────────┐
              │                     │
              ▼                     ▼
    ┌──────────────────┐   ┌───────────────┐
    │ Audio Extraction │   │   Aggregate   │
    │    (FFmpeg)      │   │ Visual Data   │
    └────────┬─────────┘   └───────┬───────┘
             │                     │
             ▼                     │
    ┌──────────────────┐          │
    │ AWS Transcribe   │          │
    │ Speech-to-Text   │          │
    └────────┬─────────┘          │
             │                     │
             └──────────┬──────────┘
                        │
                        ▼
              ┌──────────────────┐
              │ Metadata Fusion  │
              │ (Combine All)    │
              └────────┬─────────┘
                       │
                       ▼
              ┌──────────────────┐
              │ Amazon Bedrock   │
              │ Titan Embeddings │
              │ (1536-dim vector)│
              └────────┬─────────┘
                       │
                       ▼
              ┌──────────────────┐
              │  In-Memory Index │
              │ (Production: Use │
              │   OpenSearch)    │
              └──────────────────┘

Query Flow:
Query → Bedrock Embedding → Cosine Similarity → Ranked Results
```

### Technology Stack

**Backend (Flask)**:
- Python 3.11
- Flask 3.0.0
- Boto3 (AWS SDK)
- FFmpeg (media processing)

**AWS Services**:
- Amazon Rekognition (visual analysis)
- Amazon Transcribe (audio-to-text)
- Amazon Bedrock (embeddings with Titan)
- Amazon S3 (temporary storage)

**Frontend (React)**:
- React 18
- Axios (API calls)
- Styled Components (UI)

## 📁 Project Structure

```
semanticSearch/
├── app.py                 # Main Flask service
├── requirements.txt       # Python dependencies
├── README.md             # Detailed API documentation
├── QUICKSTART.md         # User guide
└── __pycache__/          # Python cache

Integration Files:
├── frontend/src/SemanticSearch.js    # React UI component
├── start-backend.sh                  # Updated with service 5008
└── stop-backend.sh                   # Updated with service 5008
```

## 🔌 API Endpoints

### Health Check
```
GET /health
Response: {"status": "ok", "service": "semantic-search", "region": "us-east-1"}
```

### Upload Video
```
POST /upload-video
Content-Type: multipart/form-data

Form Fields:
- video: File (required)
- title: String (optional)
- description: String (optional)

Response:
{
  "id": "uuid",
  "title": "Video Title",
  "message": "Video uploaded and indexed successfully",
  "labels_count": 45,
  "transcript_length": 1234,
  "frame_count": 18
}
```

### Search Videos
```
POST /search
Content-Type: application/json

{
  "query": "happy beach scenes",
  "top_k": 5
}

Response:
{
  "query": "happy beach scenes",
  "results": [
    {
      "id": "uuid",
      "title": "Beach Vacation",
      "description": "Family trip",
      "transcript_snippet": "Look at those waves...",
      "labels": ["Beach", "Ocean", "Happy"],
      "emotions": ["HAPPY", "CALM"],
      "thumbnail": "base64_encoded_jpg",
      "similarity_score": 0.8542,
      "uploaded_at": "2025-10-23T10:30:00"
    }
  ],
  "total_videos": 10
}
```

### List All Videos
```
GET /videos

Response:
{
  "videos": [
    {
      "id": "uuid",
      "title": "Video Title",
      "description": "Description",
      "labels_count": 45,
      "has_transcript": true,
      "uploaded_at": "2025-10-23T10:30:00",
      "thumbnail": "base64_encoded_jpg"
    }
  ],
  "total": 10
}
```

### Get Video Details
```
GET /video/<video_id>

Response:
{
  "id": "uuid",
  "title": "Video Title",
  "description": "Description",
  "transcript": "Full transcript text...",
  "labels": ["Label1", "Label2", ...],
  "text_detected": ["Text1", "Text2"],
  "emotions": ["HAPPY", "CALM"],
  "thumbnail": "base64_encoded_jpg",
  "uploaded_at": "2025-10-23T10:30:00"
}
```

## 🚀 Setup & Installation

### 1. Prerequisites

**AWS Account Configuration**:
```bash
aws configure
# AWS Access Key ID: [your-key]
# AWS Secret Access Key: [your-secret]
# Default region: us-east-1
```

**Enable Bedrock Model Access**:
1. AWS Console → Amazon Bedrock
2. Click "Model access"
3. Find "Titan Embeddings G1 - Text"
4. Click "Request access" (instant approval)

**Install Dependencies**:
```bash
cd semanticSearch
pip install -r requirements.txt
```

### 2. Start Service

**Using Startup Scripts** (recommended):
```bash
# From project root
./start-backend.sh
```

**Manual Start**:
```bash
cd semanticSearch
python app.py
```

Service runs on **http://localhost:5008**

### 3. Access UI

Open browser:
```
http://localhost:3000/semantic-search
```

## 💡 Usage Examples

### Example 1: Upload Family Video
```bash
curl -X POST http://localhost:5008/upload-video \
  -F "video=@vacation.mp4" \
  -F "title=Summer Vacation 2024" \
  -F "description=Family trip to the beach"
```

**Processing** (5-minute video):
- ⏱️ Takes ~5-8 minutes
- 🖼️ Extracts 30 frames
- 🔍 Analyzes with Rekognition (90 API calls)
- 🎤 Transcribes audio
- 🧠 Generates embedding
- ✅ Ready to search!

### Example 2: Search for Happy Moments
```bash
curl -X POST http://localhost:5008/search \
  -H "Content-Type: application/json" \
  -d '{
    "query": "happy family moments at the beach",
    "top_k": 3
  }'
```

**Returns**:
- Videos ranked by similarity (85%, 72%, 68%)
- Thumbnails for visual preview
- Transcript snippets showing context
- Detected labels and emotions

### Example 3: Find Specific Dialogue
```bash
curl -X POST http://localhost:5008/search \
  -H "Content-Type: application/json" \
  -d '{"query": "thank you speech", "top_k": 5}'
```

Finds videos where someone says "thank you" or gives a speech.

## 🎨 Frontend Features

### Upload Interface
- **Drag & Drop**: Easy file upload
- **Progress Bar**: Real-time upload status
- **Metadata Input**: Optional title and description
- **Status Messages**: Success/error feedback

### Search Interface
- **Natural Language Input**: Plain English queries
- **Example Suggestions**: Click to try searches
- **Real-time Results**: Instant search
- **Similarity Scores**: See match percentage

### Results Display
- **Grid Layout**: Visual card display
- **Thumbnails**: Middle frame preview
- **Match Score**: Highlighted similarity percentage
- **Labels**: Top detected objects/scenes
- **Transcript Snippet**: Relevant dialogue preview

### Video Details Modal
- **Full Thumbnail**: High-quality preview
- **Complete Transcript**: Full audio text
- **All Labels**: Every detected element
- **Emotions**: Detected facial expressions
- **On-screen Text**: OCR results

## ⚙️ Configuration

### Environment Variables
```bash
# .env file or export
AWS_REGION=us-east-1
SEMANTIC_SEARCH_BUCKET=mediagenai-semantic-search
FFMPEG_PATH=/opt/homebrew/bin/ffmpeg  # Optional, auto-detected
```

### Customization Options

**Frame Extraction Interval**:
```python
# app.py, line ~90
frames = _extract_video_frames(video_path, frames_dir, interval=10)
# Change interval=10 to extract more/fewer frames
```

**Maximum Frames per Video**:
```python
# app.py, line ~235
for frame in frames[:30]:  # Process first 30 frames
# Increase to 50 for more detail (higher cost)
```

**Search Result Count**:
```python
# Frontend: SemanticSearch.js
const response = await axios.post(`${BACKEND_URL}/search`, {
  query: searchQuery,
  top_k: 10  // Default 10, change as needed
});
```

**Transcription Timeout**:
```python
# app.py, line ~145
max_wait = 300  # 5 minutes
# Increase for longer videos
```

## 💰 Cost Analysis

### Per Video (10-minute video)

| Service | Usage | Cost per Call | Calls | Total |
|---------|-------|---------------|-------|-------|
| Rekognition - Labels | 30 frames | $0.001 | 30 | $0.03 |
| Rekognition - Text | 30 frames | $0.001 | 30 | $0.03 |
| Rekognition - Faces | 30 frames | $0.001 | 30 | $0.03 |
| Transcribe | 10 minutes | $0.024/min | 10 | $0.24 |
| Bedrock Titan | 1 embedding | $0.0001/1K tokens | ~2K | $0.001 |
| S3 Storage | Temporary | ~$0 | - | $0.00 |
| **Total** | | | | **$0.33** |

### Cost Optimization Tips
1. **Reduce Frames**: Extract every 15s instead of 10s
2. **Skip Analysis**: Only run Rekognition APIs you need
3. **Batch Processing**: Upload multiple videos at once
4. **Smart Caching**: Store embeddings to avoid regeneration

## 📊 Performance Metrics

### Processing Time
| Video Length | Estimated Time | Bottleneck |
|--------------|----------------|------------|
| 1-2 minutes | 2-3 minutes | Transcription |
| 5-10 minutes | 5-8 minutes | Transcription |
| 20-30 minutes | 10-15 minutes | Transcription |

### Accuracy
- **Visual Labels**: 90%+ accuracy (Rekognition)
- **Transcription**: 85-95% accuracy (varies by audio quality)
- **Emotion Detection**: 80-85% accuracy
- **Text Detection**: 95%+ accuracy (clear text)

### Limitations
- **In-Memory Index**: Lost on restart (use OpenSearch for production)
- **No Video Storage**: Only metadata stored
- **Synchronous Processing**: Blocks during upload
- **API Rate Limits**: Rekognition 5 TPS, Transcribe 100 concurrent jobs

## 🔮 Production Recommendations

### 1. Replace In-Memory Index with OpenSearch
```python
from opensearchpy import OpenSearch

client = OpenSearch([{"host": "your-domain.us-east-1.es.amazonaws.com", "port": 443}])

# Index video
client.index(
    index="videos",
    body={
        "title": title,
        "embedding": embedding,
        "metadata": metadata
    }
)

# k-NN Search
results = client.search(
    index="videos",
    body={"query": {"knn": {"embedding": {"vector": query_vector, "k": 5}}}}
)
```

### 2. Async Processing with SQS + Lambda
```
Upload → S3 → EventBridge → Lambda → Process → DynamoDB
                                 ↓
                          Update Status
```

### 3. Persistent Storage
- **Videos**: Amazon S3 with lifecycle policies
- **Metadata**: DynamoDB with GSI on upload date
- **Embeddings**: OpenSearch with k-NN plugin
- **Thumbnails**: S3 + CloudFront CDN

### 4. Monitoring & Logging
- **CloudWatch Logs**: Centralized logging
- **CloudWatch Metrics**: API latency, errors
- **X-Ray**: Distributed tracing
- **Cost Explorer**: Track AWS spending

## 🐛 Troubleshooting

### Issue: "Bedrock model not accessible"
**Cause**: Titan Embeddings model not enabled  
**Solution**:
1. AWS Console → Bedrock
2. Model access → Enable "Titan Embeddings G1 - Text"

### Issue: "S3 bucket access denied"
**Cause**: Missing IAM permissions  
**Solution**: Add S3 permissions to IAM role/user:
```json
{
  "Effect": "Allow",
  "Action": ["s3:CreateBucket", "s3:PutObject", "s3:GetObject", "s3:DeleteObject"],
  "Resource": "arn:aws:s3:::mediagenai-semantic-search/*"
}
```

### Issue: "FFmpeg not found"
**Cause**: FFmpeg not installed  
**Solution**:
```bash
# macOS
brew install ffmpeg

# Ubuntu
sudo apt-get install ffmpeg
```

### Issue: "Transcription timeout"
**Cause**: Long video exceeds 5-minute timeout  
**Solution**: Increase `max_wait` in `_extract_audio_and_transcribe()`

### Issue: "No search results"
**Causes**:
1. Video not fully indexed (check logs)
2. Query too specific/vague
3. No videos uploaded yet

**Solution**:
```bash
# Check service logs
tail -f semantic-search.log

# Verify videos indexed
curl http://localhost:5008/videos
```

## 📈 Monitoring & Debugging

### Check Service Health
```bash
curl http://localhost:5008/health
```

### View Logs
```bash
# Real-time logs
tail -f semantic-search.log

# Search for errors
grep ERROR semantic-search.log
```

### Test Endpoints
```bash
# List videos
curl http://localhost:5008/videos | jq

# Search test
curl -X POST http://localhost:5008/search \
  -H "Content-Type: application/json" \
  -d '{"query": "test", "top_k": 1}' | jq
```

### AWS Service Status
```bash
# Verify AWS credentials
aws sts get-caller-identity

# Test Bedrock access
aws bedrock list-foundation-models --region us-east-1

# Check Rekognition
aws rekognition detect-labels --image '{"S3Object":{"Bucket":"my-bucket","Name":"image.jpg"}}' --region us-east-1
```

## 🎓 Advanced Use Cases

### 1. Content Discovery
"Find all videos with beach scenes for summer promo"

### 2. Compliance Monitoring
"Find videos mentioning specific product names"

### 3. Sentiment Analysis
"Find negative customer feedback videos"

### 4. Scene Selection
"Find sunset scenes for B-roll footage"

### 5. Speaker Identification
"Find videos where CEO appears"

## 🔐 Security Best Practices

1. **AWS Credentials**: Use IAM roles, not hardcoded keys
2. **S3 Buckets**: Enable encryption at rest
3. **API Access**: Add authentication (JWT, API keys)
4. **Input Validation**: Sanitize file uploads
5. **Rate Limiting**: Prevent API abuse

## 📝 Future Roadmap

- [ ] OpenSearch integration for scalability
- [ ] Async processing with SQS
- [ ] Video clip extraction (timestamp-based)
- [ ] Multi-modal search (upload image to find similar scenes)
- [ ] Advanced filters (duration, date, custom labels)
- [ ] Batch upload interface
- [ ] Real-time video streaming support
- [ ] Multi-language support
- [ ] Custom model fine-tuning
- [ ] Analytics dashboard

## 🆘 Support

**Documentation**:
- [README.md](README.md) - Detailed API docs
- [QUICKSTART.md](QUICKSTART.md) - User guide

**Logs**:
```bash
tail -f semantic-search.log
```

**AWS Resources**:
- [Rekognition Docs](https://docs.aws.amazon.com/rekognition/)
- [Transcribe Docs](https://docs.aws.amazon.com/transcribe/)
- [Bedrock Docs](https://docs.aws.amazon.com/bedrock/)

---

**Built with ❤️ for MediaGenAI Platform**
