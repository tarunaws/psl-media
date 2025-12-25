#!/bin/bash

# Cleanup AWS MediaTailor Configuration
# Removes MediaTailor config and optionally S3 resources

set -e

echo "🧹 AWS MediaTailor Cleanup Script"
echo "================================="

# Configuration
CONFIG_NAME="mediagenai-dai-demo"
BUCKET_NAME="${DAI_S3_BUCKET:-${MEDIA_S3_BUCKET}}"
AWS_REGION="${AWS_REGION}"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo ""
echo "This will remove:"
echo "  • MediaTailor playback configuration: $CONFIG_NAME"
read -p "Do you also want to delete S3 bucket contents? (y/N): " DELETE_S3

if [ -z "$BUCKET_NAME" ]; then
    echo -e "${RED}❌ Set DAI_S3_BUCKET or MEDIA_S3_BUCKET before running this script${NC}"
    exit 1
fi

if [ -z "$AWS_REGION" ]; then
    echo -e "${RED}❌ Set AWS_REGION before running this script${NC}"
    exit 1
fi

# Delete MediaTailor configuration
echo ""
echo "🗑️  Deleting MediaTailor configuration..."

if aws mediatailor get-playback-configuration \
    --name $CONFIG_NAME \
    --region $AWS_REGION &> /dev/null; then
    
    aws mediatailor delete-playback-configuration \
        --name $CONFIG_NAME \
        --region $AWS_REGION
    
    echo -e "${GREEN}✅ MediaTailor configuration deleted${NC}"
else
    echo -e "${YELLOW}⚠️  MediaTailor configuration not found${NC}"
fi

# Delete S3 contents if requested
if [[ "$DELETE_S3" =~ ^[Yy]$ ]]; then
    echo ""
    echo "🗑️  Deleting S3 bucket contents..."
    
    if aws s3 ls "s3://$BUCKET_NAME" &> /dev/null; then
        echo "Removing all objects from $BUCKET_NAME..."
        aws s3 rm s3://$BUCKET_NAME --recursive
        
        echo "Deleting bucket..."
        aws s3api delete-bucket \
            --bucket $BUCKET_NAME \
            --region $AWS_REGION
        
        echo -e "${GREEN}✅ S3 bucket deleted${NC}"
    else
        echo -e "${YELLOW}⚠️  S3 bucket not found${NC}"
    fi
fi

# Remove local config file
if [ -f "dynamicAdInsertion/mediatailor-config.json" ]; then
    rm dynamicAdInsertion/mediatailor-config.json
    echo -e "${GREEN}✅ Local configuration file removed${NC}"
fi

echo ""
echo -e "${GREEN}🎉 Cleanup complete!${NC}"
echo ""

if [[ ! "$DELETE_S3" =~ ^[Yy]$ ]]; then
    echo "Note: S3 bucket $BUCKET_NAME was not deleted"
    echo "To delete manually:"
    echo "  aws s3 rm s3://$BUCKET_NAME --recursive"
    echo "  aws s3api delete-bucket --bucket $BUCKET_NAME"
fi
