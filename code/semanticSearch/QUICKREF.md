# 🔍 Semantic Video Search - Quick Reference

## 🚀 Quick Start

### Start Service
```bash
./start-backend.sh
```

### Access UI
```
http://localhost:3000/semantic-search
```

### Service URL
```
http://localhost:5008
```

## 📋 Prerequisites Checklist

- [ ] AWS credentials configured (`aws configure`)
- [ ] Bedrock Titan Embeddings model enabled (AWS Console → Bedrock → Model Access)
- [ ] FFmpeg installed (`brew install ffmpeg` on macOS)
- [ ] Dependencies installed (`cd semanticSearch && pip install -r requirements.txt`)

## 🎯 Common Use Cases

### Upload a Video
**UI**: Drag & drop at http://localhost:3000/semantic-search

**CLI**:
```bash
curl -X POST http://localhost:5008/upload-video \
  -F "video=@/path/to/video.mp4" \
  -F "title=My Video" \
  -F "description=Optional description"
```

### Search Videos
**UI**: Use search box on page

**CLI**:
```bash
curl -X POST http://localhost:5008/search \
  -H "Content-Type: application/json" \
  -d '{"query": "happy beach scenes", "top_k": 5}'
```

### List All Videos
```bash
curl http://localhost:5008/videos | jq
```

### Get Video Details
```bash
curl http://localhost:5008/video/{video_id} | jq
```

## 🔍 Search Examples

| Use Case | Example Query |
|----------|---------------|
| Scene-based | "sunset on the beach" |
| Dialogue-based | "thank you speech" |
| Emotion-based | "happy celebration" |
| Activity-based | "people dancing" |
| Text-based | "news headlines" |

## ⏱️ Processing Time

| Video Length | Processing Time |
|--------------|-----------------|
| 1-2 minutes | 2-3 minutes |
| 5-10 minutes | 5-8 minutes |
| 20+ minutes | 10-15 minutes |

## 💰 Cost

~$0.33 per 10-minute video:
- Rekognition: $0.09
- Transcribe: $0.24
- Bedrock: $0.001

## 🔧 Troubleshooting

### Service not running?
```bash
# Check status
curl http://localhost:5008/health

# View logs
tail -f semantic-search.log

# Restart service
./stop-backend.sh && ./start-backend.sh
```

### "Bedrock model not accessible"?
1. Go to AWS Bedrock console
2. Click "Model access"
3. Enable "Titan Embeddings G1 - Text"

### FFmpeg not found?
```bash
# macOS
brew install ffmpeg

# Ubuntu
sudo apt-get install ffmpeg
```

### No search results?
- Check if videos are uploaded: `curl http://localhost:5008/videos`
- View logs: `tail -f semantic-search.log`
- Try different search terms

## 📊 Monitoring

### Health Check
```bash
curl http://localhost:5008/health
```

### View Logs
```bash
tail -f semantic-search.log
```

### Test Everything
```bash
cd semanticSearch
./test.sh
```

## 📚 Documentation

- **API Docs**: `semanticSearch/README.md`
- **User Guide**: `semanticSearch/QUICKSTART.md`
- **Feature Docs**: `SEMANTIC_SEARCH_FEATURE.md`
- **Implementation**: `IMPLEMENTATION_SUMMARY.md`

## 🎓 How It Works

```
Video → Extract Frames → Rekognition Analysis → Audio Transcription
         ↓                    ↓                        ↓
    10s interval    Labels, Text, Faces, Emotions  Speech-to-Text
                              ↓
                    Combine All Metadata
                              ↓
                    Bedrock Titan Embeddings
                              ↓
                    Semantic Search Index
                              ↓
         Query → Similarity Ranking → Results
```

## ⚙️ Configuration

**Frame interval** (default: 10s):
```python
# app.py, line ~90
frames = _extract_video_frames(video_path, frames_dir, interval=10)
```

**Max frames** (default: 30):
```python
# app.py, line ~235
for frame in frames[:30]:
```

**Search results** (default: 10):
```javascript
// SemanticSearch.js
top_k: 10
```

## 🎯 Next Steps

1. Enable Bedrock model access
2. Upload a test video
3. Try searching with natural language
4. Explore different search queries
5. Check detailed video analysis

## 🔗 Quick Links

- UI: http://localhost:3000/semantic-search
- API: http://localhost:5008
- Logs: `tail -f semantic-search.log`
- Test: `cd semanticSearch && ./test.sh`

---

**Ready to search your videos? Start at http://localhost:3000/semantic-search** 🎬
