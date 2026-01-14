# Dynamic Ad Insertion (DAI) Service - ENHANCED

**🎯 10 User Profiles | 10+ GenAI Advertisements | Intelligent Targeting**

Real-time personalized ad decision server with Amazon Nova Reel generated advertisements. This service demonstrates server-side ad insertion with advanced user profile targeting.

## 🌟 What's New

- ✅ **10 Diverse User Profiles** (expanded from 4)
- ✅ **10-Second GenAI Ads** powered by Amazon Nova Reel
- ✅ **Enhanced Targeting Algorithm** with interest matching
- ✅ **Ready for Ad Generation** - Scripts and guides included
- ✅ **Complete Frontend Integration** with profile selector

## 📊 User Profiles

| Profile | Demographics | Key Interests | Target Ads |
|---------|-------------|---------------|------------|
| **Tech Enthusiast** | Urban, 25-34 | Technology, Gaming, AI | Tech Gadgets |
| **Sports Fan** | All, 18-45 | Sports, Fitness, Athletics | Sports Drinks |
| **Movie Lover** | All, 22-55 | Movies, Entertainment | Streaming Services |
| **Family Viewer** | Suburban, 30-50 | Family, Education, Kids | Family Vacations |
| **Fitness Enthusiast** | Urban, 22-40 | Fitness, Health, Wellness | Fitness Equipment |
| **Gamer** | All, 16-35 | Gaming, Esports, VR | Gaming Consoles |
| **Foodie** | Urban, 25-45 | Cooking, Food, Restaurants | Gourmet Food |
| **Traveler** | All, 25-55 | Travel, Adventure, Culture | Travel Booking |
| **Eco-Conscious** | Urban, 25-45 | Sustainability, Environment | Eco Products |
| **Luxury Shopper** | Urban, 30-60 | Luxury, Fashion, Premium | Luxury Watches |

## 📺 Advertisement Inventory

All ads are **10 seconds** duration, ready for Amazon Nova Reel generation:

1. **Tech Gadget Ad** - Latest Smartphone Launch → Tech Enthusiast
2. **Sports Drink Ad** - Energy Sports Drink → Sports Fan
3. **Streaming Service Ad** - Premium Streaming → Movie Lover
4. **Family Vacation Ad** - Resort Package → Family Viewer
5. **Fitness Equipment Ad** - Premium Gym Gear → Fitness Enthusiast
6. **Gaming Console Ad** - Next-Gen Console → Gamer
7. **Gourmet Food Ad** - Food Delivery → Foodie
8. **Travel Booking Ad** - Adventure Trips → Traveler
9. **Eco Products Ad** - Sustainable Products → Eco-Conscious
10. **Luxury Watch Ad** - Premium Timepieces → Luxury Shopper

## 🚀 Quick Start

### 1. Start the Service

```bash
cd /Users/tarun_bhardwaj/mydrive/Projects/mediaGenAI
source .venv/bin/activate
python dynamicAdInsertion/app.py > dynamic-ad-insertion.log 2>&1 &
```

Service runs on **http://localhost:5010**

### 2. Verify Service

```bash
curl http://localhost:5010/health
```

Expected response:
```json
{
  "status": "ok",
  "service": "dynamic-ad-insertion",
  "region": "us-east-1",
  "s3_bucket": "mediagenai-ad-insertion"
}
```

### 3. Test Ad Request

```bash
curl "http://localhost:5010/ads?profile_id=fitness_enthusiast" | python3 -m json.tool
```

Response:
```json
{
  "ad_id": "fitness_equipment_ad",
  "ad_name": "Premium Fitness Equipment",
  "category": "Fitness",
  "duration": 10,
  "targeting_reason": "Matched interests: Fitness, Health, Wellness",
  "video_url": "https://mediagenai-ad-insertion.s3.us-east-1.amazonaws.com/ads/fitness_equipment_ad.mp4"
}
```

## 📡 API Reference

### Health Check
```http
GET /health
```

Returns service status and AWS configuration.

### Get All Profiles
```http
GET /profiles
```

Returns list of all 10 user profiles with demographics and interests.

**Response:**
```json
{
  "profiles": [
    {
      "id": "tech_enthusiast",
      "name": "Tech Enthusiast",
      "demographics": {
        "age": "25-34",
        "gender": "All",
        "location": "Urban"
      },
      "interests": ["Technology", "Gaming", "Innovation", "AI"],
      "viewing_history": ["Tech Reviews", "Startup Stories", "Gaming Content"]
    },
    ...
  ]
}
```

### Request Personalized Ad
```http
GET /ads?profile_id=<profile_id>&session_id=<optional_session_id>
```

**Parameters:**
- `profile_id` (required): One of the 10 profile IDs
- `session_id` (optional): Session identifier for tracking

**Response:**
```json
{
  "ad_id": "gaming_console_ad",
  "ad_name": "Next-Gen Gaming Console",
  "category": "Gaming",
  "duration": 10,
  "targeting_reason": "Matched interests: Gaming, Esports, Technology",
  "session_id": "auto-generated-uuid",
  "video_url": "https://...",
  "hls_url": "https://...",
  "thumbnail": "https://..."
}
```

### Get Statistics
```http
GET /stats
```

Returns real-time analytics:
```json
{
  "total_requests": 42,
  "unique_profiles": 8,
  "ads_served": {
    "tech_gadget_ad": 12,
    "gaming_console_ad": 8,
    ...
  }
}
```

### Get Request Logs
```http
GET /logs?limit=50
```

Returns recent ad requests with targeting decisions.

### Clear Logs
```http
POST /logs/clear
```

Clears all request logs (useful for testing).

## 🎨 Frontend Integration

The React frontend is located at `/dynamic-ad-insertion`:

**Features:**
- 10 profile cards with visual selection
- Real-time ad request display
- Analytics dashboard with statistics
- Request logs viewer

**Access:** http://localhost:3000/dynamic-ad-insertion

## 🎬 Generate Advertisements

Currently, ads use placeholder S3 URLs. To generate real GenAI advertisements:

### Option 1: Automated Script (20-30 minutes)

```bash
cd /Users/tarun_bhardwaj/mydrive/Projects/mediaGenAI/dynamicAdInsertion
python3 generate_ads.py
```

This will:
- Generate all 10 advertisements using Amazon Nova Reel
- Monitor progress and save results
- Provide instructions to update `app.py`

### Option 2: Quick Test (4 ads, 10 minutes)

```bash
python3 quick_generate.py
```

Generates priority ads: Tech, Fitness, Gaming, Luxury

### Option 3: Manual Generation

See **[AD_GENERATION_GUIDE.md](./AD_GENERATION_GUIDE.md)** for detailed instructions.

## 🔧 Configuration

### Update Ad Inventory

After generating videos, update `app.py` (line ~120):

```python
AD_INVENTORY = {
    "tech_gadget_ad": {
        "video_url": "https://mediagenai-video-generation.s3.us-east-1.amazonaws.com/...",
        # ... rest of config
    }
}
```

### Restart Service

```bash
lsof -ti:5010 | xargs kill -9
source .venv/bin/activate
python dynamicAdInsertion/app.py > dynamic-ad-insertion.log 2>&1 &
```

## 🧪 Testing

### Test All Profiles

```bash
# Fitness Enthusiast
curl "http://localhost:5010/ads?profile_id=fitness_enthusiast"

# Gamer
curl "http://localhost:5010/ads?profile_id=gamer"

# Luxury Shopper
curl "http://localhost:5010/ads?profile_id=luxury_shopper"

# Eco-Conscious
curl "http://localhost:5010/ads?profile_id=eco_conscious"
```

### Verify Targeting

Each profile should receive ads matching their interests:
- ✅ Tech Enthusiast → Tech Gadget Ad
- ✅ Fitness Enthusiast → Fitness Equipment Ad
- ✅ Gamer → Gaming Console Ad
- ✅ Luxury Shopper → Luxury Watch Ad

### Check Logs

```bash
tail -f dynamic-ad-insertion.log
```

## 📁 Project Structure

```
dynamicAdInsertion/
├── app.py                      # Main Flask service (10 profiles, 10 ads)
├── generate_ads.py             # Automated ad generation script
├── quick_generate.py           # Quick 4-ad generation
├── AD_GENERATION_GUIDE.md      # Complete ad generation guide
├── README.md                   # This file
├── QUICKSTART.md               # 5-minute setup guide
├── AWS_SETUP.md                # AWS MediaTailor setup
├── setup-mediatailor.sh        # Automated AWS setup script
├── start-ngrok.sh              # ngrok tunnel for local ADS
└── cleanup-mediatailor.sh      # AWS resource cleanup
```

## 🌐 AWS MediaTailor Integration (Optional)

For production server-side ad insertion:

1. **Setup AWS MediaTailor:**
   ```bash
   ./setup-mediatailor.sh
   ```

2. **Expose local ADS:**
   ```bash
   ./start-ngrok.sh
   ```

3. **Configure MediaTailor** with ngrok URL

See **[AWS_SETUP.md](./AWS_SETUP.md)** for details.

## 📈 Analytics & Monitoring

The service tracks:
- Total ad requests
- Requests per profile
- Ads served by category
- Targeting match scores
- Complete request history

Access via:
- **Frontend Dashboard**: http://localhost:3000/dynamic-ad-insertion
- **API Endpoint**: `GET /stats`
- **Logs Endpoint**: `GET /logs`

## 🐛 Troubleshooting

### Service Won't Start

```bash
# Check if port is in use
lsof -i:5010

# Kill existing process
lsof -ti:5010 | xargs kill -9

# Check Python environment
source .venv/bin/activate
python --version  # Should be 3.x
```

### Ads Not Matching Profiles

Check the targeting algorithm in `app.py`:
```python
def select_ad_for_profile(profile_id: str) -> dict:
    # Interest matching logic
```

### Video Generation Fails

Ensure video generation service is running:
```bash
curl http://localhost:5009/health
```

## 📚 Documentation

- **[AD_GENERATION_GUIDE.md](./AD_GENERATION_GUIDE.md)** - Generate GenAI advertisements
- **[QUICKSTART.md](./QUICKSTART.md)** - 5-minute demo setup
- **[AWS_SETUP.md](./AWS_SETUP.md)** - AWS MediaTailor integration

## 🎯 Next Steps

1. ✅ Service running with 10 profiles
2. ⏳ Generate GenAI advertisements (see AD_GENERATION_GUIDE.md)
3. ⏳ Update AD_INVENTORY with real video URLs
4. ⏳ Test all profile-ad combinations
5. 🔄 Optional: Integrate with AWS MediaTailor

## 🔗 Related Services

- **Video Generation** (Port 5009): Amazon Nova Reel text-to-video
- **Frontend** (Port 3000): React UI with DAI feature
- **AWS MediaTailor**: Optional server-side ad stitching

## 📝 License

Part of the MediaGenAI project.

---

**Status:** ✅ Enhanced with 10 profiles, ready for ad generation

**Last Updated:** October 24, 2025
