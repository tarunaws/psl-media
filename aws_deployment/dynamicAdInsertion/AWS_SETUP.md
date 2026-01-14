# AWS MediaTailor Setup Guide

Complete guide to integrate your local Ad Decision Server with AWS Elemental MediaTailor for production-ready Dynamic Ad Insertion.

## Prerequisites

- AWS Account with appropriate permissions
- AWS CLI configured (`aws configure`)
- S3 bucket for video storage
- Local Ad Decision Server running on port 5010
- ngrok installed (`brew install ngrok` on macOS)

## Architecture

```
┌─────────────────┐
│  Video Player   │
│   (Frontend)    │
└────────┬────────┘
         │
         ▼
┌─────────────────────┐
│ AWS MediaTailor     │
│ (Ad Stitching)      │
└──────┬──────┬───────┘
       │      │
       │      └──────────────┐
       │                     │
       ▼                     ▼
┌──────────────┐      ┌──────────────────┐
│  S3 Content  │      │ Local ADS (ngrok)│
│  (Main Video)│      │  Port 5010       │
└──────────────┘      └──────────────────┘
       │                     │
       │                     ▼
       └──────────────┐  ┌──────────────┐
                      │  │  S3 Ads      │
                      ▼  │  (Creatives) │
               ┌────────────────────┐   │
               │   Player receives  │◄──┘
               │   stitched stream  │
               └────────────────────┘
```

## Step 1: Prepare Video Content

### 1.1 Create S3 Bucket

```bash
# Set your bucket name
BUCKET_NAME="mediagenai-ad-insertion"
AWS_REGION="us-east-1"

# Create bucket
aws s3api create-bucket \
    --bucket $BUCKET_NAME \
    --region $AWS_REGION

# Enable public access for video delivery
aws s3api put-bucket-cors \
    --bucket $BUCKET_NAME \
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
      "ExposeHeaders": []
    }
  ]
}
```

### 1.2 Prepare Main Content with Ad Markers

Your main video needs SCTE-35 ad markers. You can:

**Option A: Use existing content with markers**
```bash
# Upload pre-marked content
aws s3 cp your-video-with-scte35.mp4 \
    s3://$BUCKET_NAME/content/main-video.mp4
```

**Option B: Add markers using ffmpeg**
```bash
# Install ffmpeg if needed
brew install ffmpeg

# Add SCTE-35 markers at specific times (e.g., 30s, 60s)
ffmpeg -i input.mp4 \
    -f hls \
    -hls_time 6 \
    -hls_list_size 0 \
    -hls_flags program_date_time \
    -master_pl_name master.m3u8 \
    output/playlist.m3u8

# Upload to S3
aws s3 sync output/ s3://$BUCKET_NAME/content/main-video/
```

### 1.3 Prepare Ad Creatives

```bash
# Upload ad videos
aws s3 cp tech_gadget_ad.mp4 s3://$BUCKET_NAME/ads/tech_gadget_ad.mp4
aws s3 cp sports_drink_ad.mp4 s3://$BUCKET_NAME/ads/sports_drink_ad.mp4
aws s3 cp streaming_service_ad.mp4 s3://$BUCKET_NAME/ads/streaming_service_ad.mp4
aws s3 cp family_vacation_ad.mp4 s3://$BUCKET_NAME/ads/family_vacation_ad.mp4
aws s3 cp default_ad.mp4 s3://$BUCKET_NAME/ads/default_ad.mp4
```

### 1.4 Convert to HLS Format (Required for MediaTailor)

```bash
# Convert each ad to HLS
for ad in tech_gadget_ad sports_drink_ad streaming_service_ad family_vacation_ad default_ad
do
    ffmpeg -i $ad.mp4 \
        -f hls \
        -hls_time 6 \
        -hls_list_size 0 \
        -hls_segment_filename "s3://$BUCKET_NAME/ads/$ad/segment_%03d.ts" \
        "s3://$BUCKET_NAME/ads/$ad/playlist.m3u8"
done
```

## Step 2: Expose Local ADS via ngrok

### 2.1 Install ngrok

```bash
# macOS
brew install ngrok

# Linux
curl -s https://ngrok-agent.s3.amazonaws.com/ngrok.asc | \
    sudo tee /etc/apt/trusted.gpg.d/ngrok.asc >/dev/null
echo "deb https://ngrok-agent.s3.amazonaws.com buster main" | \
    sudo tee /etc/apt/sources.list.d/ngrok.list
sudo apt update && sudo apt install ngrok
```

### 2.2 Setup ngrok Account

```bash
# Sign up at https://dashboard.ngrok.com/signup
# Get your auth token from https://dashboard.ngrok.com/get-started/your-authtoken

# Configure ngrok
ngrok config add-authtoken YOUR_AUTH_TOKEN
```

### 2.3 Start ngrok Tunnel

```bash
# Start tunnel for local ADS on port 5010
ngrok http 5010
```

You'll see output like:
```
Forwarding  https://abc123.ngrok.io -> http://localhost:5010
```

**Save this URL!** You'll need it for MediaTailor configuration.

### 2.4 Test ngrok Endpoint

```bash
# Replace with your ngrok URL
NGROK_URL="https://abc123.ngrok.io"

# Test health endpoint
curl $NGROK_URL/health

# Test ad request
curl "$NGROK_URL/ads?profile_id=tech_enthusiast"
```

## Step 3: Configure AWS MediaTailor

### 3.1 Create MediaTailor Configuration

```bash
# Set your ngrok URL
ADS_URL="https://abc123.ngrok.io"

# Create MediaTailor configuration
aws mediatailor put-playback-configuration \
    --name "mediagenai-dai-demo" \
    --video-content-source-url "https://$BUCKET_NAME.s3.$AWS_REGION.amazonaws.com/content/main-video/" \
    --ad-decision-server-url "$ADS_URL/ads" \
    --region $AWS_REGION
```

### 3.2 Get MediaTailor Playback Endpoints

```bash
# Get configuration details
aws mediatailor get-playback-configuration \
    --name "mediagenai-dai-demo" \
    --region $AWS_REGION

# Save the HlsConfiguration.ManifestEndpointPrefix
```

Output will include:
```json
{
    "HlsConfiguration": {
        "ManifestEndpointPrefix": "https://abc123.mediatailor.us-east-1.amazonaws.com/v1/master/...",
    }
}
```

### 3.3 Configure Ad Tracking

```bash
# Update configuration with ad tracking
aws mediatailor put-playback-configuration \
    --name "mediagenai-dai-demo" \
    --video-content-source-url "https://$BUCKET_NAME.s3.$AWS_REGION.amazonaws.com/content/main-video/" \
    --ad-decision-server-url "$ADS_URL/ads" \
    --cdn-configuration '{"AdSegmentUrlPrefix":"https://'$BUCKET_NAME'.s3.'$AWS_REGION'.amazonaws.com/ads/"}' \
    --region $AWS_REGION
```

## Step 4: Update Frontend to Use MediaTailor

### 4.1 Get MediaTailor Session URL

The MediaTailor playback URL will be in this format:
```
https://<origin-id>.mediatailor.<region>.amazonaws.com/v1/session/<hashed-id>/master.m3u8
```

### 4.2 Update DynamicAdInsertion.js

Add MediaTailor streaming option:

```javascript
const [streamSource, setStreamSource] = useState('local'); // 'local' or 'mediatailor'
const MEDIATAILOR_URL = 'https://your-mediatailor-endpoint.amazonaws.com/v1/session/...';

// In the video player section:
{streamSource === 'mediatailor' ? (
  <VideoContainer>
    <VideoPlayer 
      ref={videoRef}
      controls
      autoPlay
    >
      <source src={MEDIATAILOR_URL} type="application/x-mpegURL" />
    </VideoPlayer>
  </VideoContainer>
) : (
  // Existing local ad player
)}
```

## Step 5: Test End-to-End

### 5.1 Start All Services

```bash
# Terminal 1: Start local ADS
./start-all.sh

# Terminal 2: Start ngrok
ngrok http 5010

# Terminal 3: Test MediaTailor
curl "https://your-mediatailor-endpoint.amazonaws.com/v1/session/.../master.m3u8"
```

### 5.2 Play Video

1. Open frontend: `http://localhost:3000/dynamic-ad-insertion`
2. Select a user profile
3. Click "Request Personalized Ad"
4. Video player will fetch from MediaTailor with ads stitched in

### 5.3 Monitor Logs

```bash
# Watch ADS logs
tail -f dynamic-ad-insertion.log

# Watch MediaTailor requests in ngrok
# ngrok web interface: http://localhost:4040
```

## Configuration Files

### mediatailor-config.json

Save this for easy updates:
```json
{
  "Name": "mediagenai-dai-demo",
  "VideoContentSourceUrl": "https://mediagenai-ad-insertion.s3.us-east-1.amazonaws.com/content/main-video/",
  "AdDecisionServerUrl": "https://abc123.ngrok.io/ads",
  "CdnConfiguration": {
    "AdSegmentUrlPrefix": "https://mediagenai-ad-insertion.s3.us-east-1.amazonaws.com/ads/"
  }
}
```

Update configuration:
```bash
aws mediatailor put-playback-configuration --cli-input-json file://mediatailor-config.json
```

## Troubleshooting

### MediaTailor can't reach ADS

**Problem:** MediaTailor gets timeout calling ADS
**Solution:** 
- Ensure ngrok is running: `curl https://abc123.ngrok.io/health`
- Check ngrok web interface: `http://localhost:4040`
- Verify ADS is running: `curl http://localhost:5010/health`

### Ads not appearing in stream

**Problem:** Stream plays but no ads
**Solution:**
- Verify main content has SCTE-35 markers
- Check ad creative format (must be HLS)
- Test ADS directly: `curl "https://abc123.ngrok.io/ads?profile_id=tech_enthusiast"`
- Check MediaTailor logs in AWS Console

### CORS errors in browser

**Problem:** Video won't play due to CORS
**Solution:**
- Update S3 bucket CORS configuration
- Enable CORS in MediaTailor configuration
- Add CORS headers in local ADS (already done in app.py)

### ngrok tunnel expired

**Problem:** Free ngrok tunnels expire after 2 hours
**Solution:**
- Restart ngrok tunnel
- Update MediaTailor configuration with new URL
- Consider ngrok paid plan for persistent URLs

## Cost Optimization

### MediaTailor Pricing (us-east-1)
- **Session Initialization:** $0.005 per session
- **Manifest Requests:** $0.005 per 1000 requests
- **Output:** $0.0045 per GB

### Estimated Demo Costs
- 100 test sessions/day: ~$0.50/day
- S3 storage (10GB): ~$0.23/month
- Data transfer: ~$0.90/month (first GB free)

**Total: ~$15-20/month for demo**

## Production Considerations

1. **Persistent ngrok URL**: Use paid ngrok plan or deploy ADS to AWS Lambda
2. **High Availability**: Run multiple ADS instances behind load balancer
3. **Caching**: Add caching layer for ad inventory
4. **Analytics**: Integrate with AWS CloudWatch for detailed metrics
5. **Security**: Add authentication to ADS endpoints
6. **Monitoring**: Set up alerts for ADS downtime

## Cleanup

```bash
# Delete MediaTailor configuration
aws mediatailor delete-playback-configuration \
    --name "mediagenai-dai-demo" \
    --region $AWS_REGION

# Delete S3 content
aws s3 rm s3://$BUCKET_NAME --recursive

# Delete bucket
aws s3api delete-bucket --bucket $BUCKET_NAME

# Stop ngrok
# Press Ctrl+C in ngrok terminal
```

## Next Steps

1. ✅ Test with sample videos
2. ✅ Verify ad insertion works
3. Configure multiple ad pods
4. Add frequency capping
5. Implement competitive separation
6. Set up A/B testing
7. Add real-time reporting
