#!/bin/bash

# Setup AWS MediaTailor for Dynamic Ad Insertion
# This script automates the MediaTailor configuration

set -e

echo "🚀 AWS MediaTailor Setup Script"
echo "================================"

# Configuration
BUCKET_NAME="${DAI_S3_BUCKET:-${MEDIA_S3_BUCKET}}"
AWS_REGION="${AWS_REGION}"
CONFIG_NAME="mediagenai-dai-demo"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check prerequisites
echo ""
echo "📋 Checking prerequisites..."

if [ -z "$BUCKET_NAME" ]; then
    echo -e "${RED}❌ Set DAI_S3_BUCKET or MEDIA_S3_BUCKET before running this script${NC}"
    exit 1
fi

if [ -z "$AWS_REGION" ]; then
    echo -e "${RED}❌ Set AWS_REGION before running this script${NC}"
    exit 1
fi

if ! command -v aws &> /dev/null; then
    echo -e "${RED}❌ AWS CLI is not installed${NC}"
    echo "Install: https://aws.amazon.com/cli/"
    exit 1
fi

if ! command -v jq &> /dev/null; then
    echo -e "${YELLOW}⚠️  jq is not installed (optional but recommended)${NC}"
    echo "Install: brew install jq"
fi

# Check AWS credentials
if ! aws sts get-caller-identity &> /dev/null; then
    echo -e "${RED}❌ AWS credentials not configured${NC}"
    echo "Run: aws configure"
    exit 1
fi

echo -e "${GREEN}✅ Prerequisites met${NC}"

# Get ngrok URL
echo ""
echo "🌐 Enter your ngrok public URL"
echo "   (e.g., https://abc123.ngrok.io)"
echo "   Start ngrok first: ngrok http 5010"
read -p "ngrok URL: " NGROK_URL

if [ -z "$NGROK_URL" ]; then
    echo -e "${RED}❌ ngrok URL is required${NC}"
    exit 1
fi

# Validate ngrok URL
echo "🔍 Testing ngrok endpoint..."
if curl -s -f "$NGROK_URL/health" > /dev/null; then
    echo -e "${GREEN}✅ ngrok endpoint is accessible${NC}"
else
    echo -e "${RED}❌ Cannot reach ngrok endpoint${NC}"
    echo "Make sure:"
    echo "  1. ngrok is running: ngrok http 5010"
    echo "  2. Local ADS is running on port 5010"
    exit 1
fi

# Create S3 bucket if it doesn't exist
echo ""
echo "📦 Setting up S3 bucket: $BUCKET_NAME"

if aws s3 ls "s3://$BUCKET_NAME" 2>&1 | grep -q 'NoSuchBucket'; then
    echo "Creating bucket..."
    if [ "$AWS_REGION" = "us-east-1" ]; then
        aws s3api create-bucket \
            --bucket $BUCKET_NAME \
            --region $AWS_REGION
    else
        aws s3api create-bucket \
            --bucket $BUCKET_NAME \
            --region $AWS_REGION \
            --create-bucket-configuration LocationConstraint=$AWS_REGION
    fi
    echo -e "${GREEN}✅ Bucket created${NC}"
else
    echo -e "${GREEN}✅ Bucket already exists${NC}"
fi

# Configure CORS
echo "Setting up CORS..."
cat > /tmp/cors-config.json << EOF
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
EOF

aws s3api put-bucket-cors \
    --bucket $BUCKET_NAME \
    --cors-configuration file:///tmp/cors-config.json

echo -e "${GREEN}✅ CORS configured${NC}"

# Create MediaTailor configuration
echo ""
echo "🎬 Configuring AWS MediaTailor..."

VIDEO_SOURCE_URL="https://$BUCKET_NAME.s3.$AWS_REGION.amazonaws.com/content/main-video/"
ADS_URL="$NGROK_URL/ads"

# Check if configuration exists
if aws mediatailor get-playback-configuration \
    --name $CONFIG_NAME \
    --region $AWS_REGION &> /dev/null; then
    echo "Updating existing configuration..."
else
    echo "Creating new configuration..."
fi

aws mediatailor put-playback-configuration \
    --name $CONFIG_NAME \
    --video-content-source-url $VIDEO_SOURCE_URL \
    --ad-decision-server-url $ADS_URL \
    --cdn-configuration AdSegmentUrlPrefix="https://$BUCKET_NAME.s3.$AWS_REGION.amazonaws.com/ads/" \
    --region $AWS_REGION \
    > /tmp/mediatailor-response.json

echo -e "${GREEN}✅ MediaTailor configured${NC}"

# Get playback URL
echo ""
echo "📺 MediaTailor Endpoints:"
echo "========================"

if command -v jq &> /dev/null; then
    HLS_URL=$(cat /tmp/mediatailor-response.json | jq -r '.HlsConfiguration.ManifestEndpointPrefix')
    DASH_URL=$(cat /tmp/mediatailor-response.json | jq -r '.DashConfiguration.ManifestEndpointPrefix')
    
    echo ""
    echo -e "${GREEN}HLS Playback URL:${NC}"
    echo "$HLS_URL"
    echo ""
    echo -e "${GREEN}DASH Playback URL:${NC}"
    echo "$DASH_URL"
else
    cat /tmp/mediatailor-response.json
fi

# Save configuration
echo ""
echo "💾 Saving configuration..."

cat > dynamicAdInsertion/mediatailor-config.json << EOF
{
  "name": "$CONFIG_NAME",
  "region": "$AWS_REGION",
  "bucket": "$BUCKET_NAME",
  "ngrok_url": "$NGROK_URL",
  "video_source_url": "$VIDEO_SOURCE_URL",
  "ads_url": "$ADS_URL",
  "hls_endpoint": "$(cat /tmp/mediatailor-response.json | jq -r '.HlsConfiguration.ManifestEndpointPrefix' 2>/dev/null || echo 'See full response above')"
}
EOF

echo -e "${GREEN}✅ Configuration saved to dynamicAdInsertion/mediatailor-config.json${NC}"

# Test endpoints
echo ""
echo "🧪 Testing setup..."

echo "Testing ADS endpoint..."
if curl -s "$ADS_URL?profile_id=tech_enthusiast" > /dev/null; then
    echo -e "${GREEN}✅ ADS responding correctly${NC}"
else
    echo -e "${YELLOW}⚠️  ADS test failed${NC}"
fi

# Cleanup
rm -f /tmp/cors-config.json /tmp/mediatailor-response.json

echo ""
echo "🎉 Setup complete!"
echo ""
echo "Next steps:"
echo "  1. Upload video content to: s3://$BUCKET_NAME/content/main-video/"
echo "  2. Upload ad creatives to: s3://$BUCKET_NAME/ads/"
echo "  3. Keep ngrok running in a separate terminal"
echo "  4. Test playback using the HLS endpoint above"
echo ""
echo "To view configuration:"
echo "  aws mediatailor get-playback-configuration --name $CONFIG_NAME --region $AWS_REGION"
echo ""
echo "To delete configuration:"
echo "  ./scripts/cleanup-mediatailor.sh"
