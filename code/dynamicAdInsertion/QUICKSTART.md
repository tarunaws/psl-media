# Quick Start: Dynamic Ad Insertion with AWS MediaTailor

Step-by-step guide to get your Dynamic Ad Insertion demo running with AWS MediaTailor.

## 🚀 Quick Setup (5 minutes)

### Prerequisites

```bash
# Install required tools
brew install ngrok awscli jq  # macOS
# or
sudo apt install ngrok awscli jq  # Linux

# Configure AWS CLI
aws configure
# Enter your AWS Access Key ID, Secret Access Key, and region (us-east-1)
```

### Step 1: Start Local Services

```bash
# Start the Ad Decision Server
cd /Users/tarun_bhardwaj/mydrive/Projects/mediaGenAI
./start-all.sh

# Verify ADS is running
curl http://localhost:5010/health
```

### Step 2: Setup ngrok

```bash
# Get your auth token from https://dashboard.ngrok.com/get-started/your-authtoken
ngrok config add-authtoken YOUR_AUTH_TOKEN

# Start ngrok tunnel (in a separate terminal)
cd dynamicAdInsertion
./start-ngrok.sh
```

Copy the **https** URL shown (e.g., `https://abc123.ngrok.io`)

### Step 3: Configure MediaTailor

```bash
# Run the automated setup script
cd dynamicAdInsertion
./setup-mediatailor.sh

# When prompted, paste your ngrok URL
```

The script will:
- ✅ Create S3 bucket
- ✅ Configure CORS
- ✅ Set up MediaTailor
- ✅ Return playback endpoints

### Step 4: Upload Sample Content

```bash
# Set your bucket name
export BUCKET_NAME="mediagenai-ad-insertion"

# Upload a sample video (replace with your video file)
aws s3 cp sample-video.mp4 s3://$BUCKET_NAME/content/main-video/video.mp4

# Upload ad videos
aws s3 cp tech_ad.mp4 s3://$BUCKET_NAME/ads/tech_gadget_ad.mp4
aws s3 cp sports_ad.mp4 s3://$BUCKET_NAME/ads/sports_drink_ad.mp4
```

### Step 5: Test It!

```bash
# Open the UI
open http://localhost:3000/dynamic-ad-insertion

# Or test the API directly
curl "http://localhost:5010/ads?profile_id=tech_enthusiast"
```

## 📺 Testing the Complete Flow

### 1. Via Frontend UI

1. Open `http://localhost:3000/dynamic-ad-insertion`
2. Select a user profile (e.g., "Tech Enthusiast")
3. Click "Request Personalized Ad"
4. See the targeted ad and explanation

### 2. Via MediaTailor Stream

Use the HLS endpoint from setup (saved in `mediatailor-config.json`):

```bash
# Get your HLS endpoint
cat dynamicAdInsertion/mediatailor-config.json | jq -r '.hls_endpoint'

# Test with VLC or ffplay
ffplay "https://your-mediatailor-endpoint.../master.m3u8"
```

### 3. Monitor Requests

```bash
# Watch ADS logs
tail -f dynamic-ad-insertion.log

# View ngrok requests (in browser)
open http://localhost:4040
```

## 🎯 Understanding the Flow

```
1. User selects profile → Frontend
                            ↓
2. Request ad           → Local ADS (port 5010)
                            ↓
3. Select ad based      → Targeting algorithm
   on profile              ↓
4. Return ad metadata   → Frontend displays
```

**With MediaTailor:**
```
1. Player requests video  → MediaTailor
                              ↓
2. MediaTailor hits       → ngrok → Local ADS (port 5010)
   SCTE-35 marker            ↓
3. ADS selects ad based   → Returns ad URL
   on profile                ↓
4. MediaTailor stitches   → Player receives seamless stream
   ad into stream
```

## 🔧 Common Issues & Solutions

### ngrok tunnel not accessible

**Problem:** MediaTailor can't reach your ADS

**Solution:**
```bash
# Check ngrok is running
curl https://your-ngrok-url.ngrok.io/health

# Check local ADS
curl http://localhost:5010/health

# View ngrok logs
open http://localhost:4040
```

### No ads in MediaTailor stream

**Problem:** Video plays but ads don't appear

**Reasons:**
1. Main video doesn't have SCTE-35 markers
2. Ad URLs are incorrect in ADS response
3. Ads are not in HLS format

**Solution:**
```bash
# Check ad URLs in response
curl "https://your-ngrok-url.ngrok.io/ads?profile_id=tech_enthusiast"

# Verify ads exist in S3
aws s3 ls s3://mediagenai-ad-insertion/ads/

# Check MediaTailor logs in AWS Console
```

### S3 CORS errors

**Problem:** Browser can't load videos from S3

**Solution:**
```bash
# Re-apply CORS configuration
aws s3api put-bucket-cors \
    --bucket mediagenai-ad-insertion \
    --cors-configuration '{
      "CORSRules": [{
        "AllowedHeaders": ["*"],
        "AllowedMethods": ["GET", "HEAD"],
        "AllowedOrigins": ["*"]
      }]
    }'
```

## 📊 Monitoring & Debugging

### View MediaTailor Configuration

```bash
aws mediatailor get-playback-configuration \
    --name mediagenai-dai-demo \
    --region us-east-1
```

### Check Recent Ad Requests

```bash
# Via API
curl http://localhost:5010/logs?limit=10

# Via UI
open http://localhost:3000/dynamic-ad-insertion
# Check the "Ad Request Logs" section
```

### View Statistics

```bash
# Via API
curl http://localhost:5010/stats

# Response shows:
# - Total requests
# - Unique sessions
# - Ads by category
# - Ads by profile
```

## 🧪 Testing Different Scenarios

### Test Different User Profiles

```bash
# Tech Enthusiast (gets tech ads)
curl "http://localhost:5010/ads?profile_id=tech_enthusiast"

# Sports Fan (gets sports ads)
curl "http://localhost:5010/ads?profile_id=sports_fan"

# Movie Lover (gets streaming ads)
curl "http://localhost:5010/ads?profile_id=movie_lover"

# Family Viewer (gets family ads)
curl "http://localhost:5010/ads?profile_id=family_viewer"
```

### Test ngrok Endpoint

```bash
# Replace with your ngrok URL
NGROK_URL="https://abc123.ngrok.io"

curl "$NGROK_URL/health"
curl "$NGROK_URL/profiles"
curl "$NGROK_URL/ads?profile_id=tech_enthusiast"
```

## 🧹 Cleanup

When you're done testing:

```bash
# Stop ngrok (Ctrl+C in ngrok terminal)

# Remove MediaTailor configuration and S3 bucket
cd dynamicAdInsertion
./cleanup-mediatailor.sh

# Stop local services
cd ..
./stop-all.sh
```

## 📝 Next Steps

### Add Real Videos

1. **Prepare main content with SCTE-35 markers:**
```bash
ffmpeg -i input.mp4 \
    -f hls \
    -hls_time 6 \
    -hls_list_size 0 \
    output/playlist.m3u8
```

2. **Upload to S3:**
```bash
aws s3 sync output/ s3://mediagenai-ad-insertion/content/main-video/
```

### Convert Ads to HLS

```bash
# Convert each ad video
ffmpeg -i ad.mp4 \
    -f hls \
    -hls_time 6 \
    -hls_list_size 0 \
    ad-output/playlist.m3u8

# Upload to S3
aws s3 sync ad-output/ s3://mediagenai-ad-insertion/ads/tech_gadget_ad/
```

### Enhance Targeting

Edit `dynamicAdInsertion/app.py` to add:
- Geographic targeting
- Time-based targeting
- Frequency capping
- A/B testing logic

### Deploy to Production

Instead of ngrok, deploy ADS to:
- AWS Lambda + API Gateway
- EC2 instance with public IP
- ECS/Fargate container

## 📚 Resources

- [AWS MediaTailor Documentation](https://docs.aws.amazon.com/mediatailor/)
- [ngrok Documentation](https://ngrok.com/docs)
- [HLS Specification](https://tools.ietf.org/html/rfc8216)
- [SCTE-35 Standard](https://www.scte.org/standards/library/catalog/scte-35-digital-program-insertion-cueing-message/)

## 💡 Tips

1. **Keep ngrok running:** Free tier tunnels change URLs on restart
2. **Monitor costs:** Check AWS billing dashboard regularly
3. **Test thoroughly:** Verify ads appear correctly before production
4. **Use CloudWatch:** Set up alarms for MediaTailor errors
5. **Secure your ADS:** Add authentication before production deployment

## 🆘 Getting Help

If you encounter issues:

1. Check service logs: `tail -f dynamic-ad-insertion.log`
2. View ngrok requests: `http://localhost:4040`
3. Test endpoints individually
4. Check AWS CloudWatch logs for MediaTailor
5. Verify S3 permissions and CORS

---

**Ready to go!** Start with Step 1 and you'll have a working Dynamic Ad Insertion demo in 5 minutes.
