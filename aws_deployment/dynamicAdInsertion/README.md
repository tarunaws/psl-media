# Dynamic Ad Insertion (DAI) Service

Server-side ad stitching with personalized targeting for streaming content.

## Overview

This service simulates Dynamic Ad Insertion using a local Ad Decision Server (ADS) that provides personalized ad selection based on user profiles. It demonstrates how streaming platforms can deliver targeted advertising while maintaining a seamless viewing experience.

## Features

- **Ad Decision Server (ADS)**: Flask-based service that selects ads based on user profiles
- **User Profile Management**: 4 distinct viewer personas with different demographics and interests
- **Ad Inventory**: 5 different ad categories with targeting rules
- **Real-time Analytics**: Track ad requests, sessions, and targeting performance
- **Request Logging**: Complete audit trail of ad decisions and targeting reasons

## Architecture

```
Frontend (React) → Ad Decision Server (Flask) → Ad Selection Logic
                                                      ↓
                                              Ad Inventory Database
```

## User Profiles

1. **Tech Enthusiast** - Urban, 25-34, interests in Technology, Gaming, Innovation
2. **Sports Fan** - All locations, 18-45, interests in Sports, Fitness, Athletics
3. **Movie Lover** - All locations, 22-55, interests in Movies, Entertainment, Streaming
4. **Family Viewer** - Suburban, 30-50, interests in Family, Education, Kids Content

## Ad Inventory

- **Tech Gadget Ad** - Latest Smartphone Launch (Technology category)
- **Sports Drink Ad** - Energy Sports Drink (Sports & Fitness category)
- **Streaming Service Ad** - Premium Streaming Service (Entertainment category)
- **Family Vacation Ad** - Family Vacation Package (Travel & Family category)
- **Default Ad** - General Brand Advertisement (fallback)

## API Endpoints

### Health Check
```
GET /health
```
Returns service status and configuration.

### Get Ad
```
GET /ads?profile_id=<profile_id>&session_id=<session_id>
```
Returns personalized ad based on user profile.

**Response:**
```json
{
  "ad_id": "tech_gadget_ad",
  "ad_name": "Latest Smartphone Launch",
  "duration": 30,
  "category": "Technology",
  "video_url": "https://...",
  "hls_url": "https://...",
  "thumbnail": "https://...",
  "targeting_reason": "Matched interests: Technology, Gaming, Innovation",
  "session_id": "..."
}
```

### Get Profiles
```
GET /profiles
```
Returns all available user profiles.

### Get Profile Details
```
GET /profiles/<profile_id>
```
Returns specific profile information.

### Get Ad Inventory
```
GET /ads/inventory
```
Returns all available ads.

### Get Logs
```
GET /logs?limit=50
```
Returns recent ad request logs.

### Clear Logs
```
POST /logs/clear
```
Clears all ad request logs.

### Get Statistics
```
GET /stats
```
Returns ad serving statistics including:
- Total requests
- Unique sessions
- Ads by category
- Ads by profile

## Running the Service

### Start Service
```bash
# Using start script
./start-all.sh

# Or manually
cd /Users/tarun_bhardwaj/mydrive/Projects/mediaGenAI
.venv/bin/python dynamicAdInsertion/app.py
```

The service will start on **port 5010**.

### Access the UI
Navigate to: `http://localhost:3000/dynamic-ad-insertion`

## Usage

1. **Select a User Profile**: Choose from Tech Enthusiast, Sports Fan, Movie Lover, or Family Viewer
2. **Request Ad**: Click "Request Personalized Ad" to simulate an ad request
3. **View Results**: See the targeted ad with explanation of why it was selected
4. **Monitor Analytics**: Track ad requests, sessions, and performance in real-time
5. **Review Logs**: See detailed logs of all ad decisions

## Targeting Logic

The Ad Decision Server uses a scoring algorithm:
- **+10 points** for each matching interest between user profile and ad
- **+5 points** for demographic match
- Minimum score of 5 required for targeted ad
- Falls back to default ad if no good match

## AWS Integration (Optional)

For full production deployment with AWS Elemental MediaTailor:

1. **Upload Content to S3**:
   - Main content with SCTE-35 ad markers
   - Ad creative files

2. **Transcode with MediaConvert**:
   - Convert content to HLS format
   - Prepare ad creatives

3. **Configure MediaTailor**:
   - Point to this Ad Decision Server (via ngrok)
   - Set up CloudFront distribution

4. **Expose Local ADS**:
```bash
ngrok http 5010
```
Then configure MediaTailor ADS URL to the ngrok endpoint.

## Environment Variables

- `AWS_REGION`: AWS region (default: us-east-1)
- `DAI_S3_BUCKET`: S3 bucket for ad storage (default: mediagenai-ad-insertion)

## Logs

Service logs are written to: `dynamic-ad-insertion.log`

## Development

The service uses:
- **Flask**: Web framework
- **Flask-CORS**: Cross-origin resource sharing
- **In-memory storage**: For user profiles, ad inventory, and request logs

## Future Enhancements

- [ ] Integration with AWS Elemental MediaTailor
- [ ] Real video ad stitching with HLS streams
- [ ] Advanced targeting algorithms (ML-based)
- [ ] A/B testing capabilities
- [ ] Real-time bidding simulation
- [ ] Frequency capping
- [ ] Sequential ad delivery
- [ ] Geographic targeting

## Troubleshooting

**Service won't start:**
- Check if port 5010 is available: `lsof -i:5010`
- Verify virtual environment: `which python` should point to `.venv/bin/python`

**No ads returned:**
- Check service logs: `tail -f dynamic-ad-insertion.log`
- Verify profile exists: `curl http://localhost:5010/profiles`

**Frontend can't connect:**
- Ensure CORS is enabled (check Flask-CORS installation)
- Verify backend is running: `curl http://localhost:5010/health`
