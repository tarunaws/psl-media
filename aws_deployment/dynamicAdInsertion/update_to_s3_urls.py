#!/usr/bin/env python3
"""
Update ad video URLs to use direct S3 CDN URLs instead of proxy.
"""

import boto3
import json
import os

# Configuration
AWS_REGION = os.environ.get("AWS_REGION")
if not AWS_REGION:
    raise RuntimeError("Set AWS_REGION before running update_to_s3_urls")

DEFAULT_MEDIA_BUCKET = os.environ.get("MEDIA_S3_BUCKET")
S3_BUCKET = os.environ.get("VIDEO_GEN_S3_BUCKET") or DEFAULT_MEDIA_BUCKET

if not S3_BUCKET:
    raise RuntimeError("Set VIDEO_GEN_S3_BUCKET or MEDIA_S3_BUCKET before running update_to_s3_urls")

# Mapping of ad IDs to their generation IDs (from S3)
AD_TO_GENERATION = {
    "tech_gadget_ad": "864f4e14-dab4-4335-a285-bb45e6bd369a",
    "sports_drink_ad": "2dcfe1d1-0634-49e3-b3b3-e9f1eaf7dcbe",
    "streaming_service_ad": "c144f25c-46d6-4f2a-a7fb-5d84c704d838",
    "family_vacation_ad": "a3cbdc6d-3908-47f5-96c2-53e258ea949e",
    "fitness_equipment_ad": "cfaf9984-4e94-40b9-9235-785f3cde6cd7",
    "gaming_console_ad": "586d4158-b513-40e5-bfdf-90f65e86772e",
    "gourmet_food_ad": "31a45da9-6685-4572-9922-bf8d4324d83e",
    "travel_booking_ad": "44801165-cca2-4360-89ff-2b81e9bd8e12",
    "eco_products_ad": "c5490916-79cc-4ae2-92ed-dad79e06112f",
    "luxury_watch_ad": "88fca849-e73e-46f0-9ffb-8509aac9a84a"
}

def get_s3_path(generation_id):
    """Get the full S3 path for a generation ID."""
    s3 = boto3.client('s3', region_name=AWS_REGION)
    
    try:
        response = s3.list_objects_v2(
            Bucket=S3_BUCKET,
            Prefix=f'generated-videos/{generation_id}/'
        )
        
        for obj in response.get('Contents', []):
            if obj['Key'].endswith('output.mp4'):
                return obj['Key']
    except Exception as e:
        print(f"Error finding video for {generation_id}: {e}")
    
    return None

def make_bucket_public():
    """Make S3 bucket public for CDN access."""
    s3 = boto3.client('s3', region_name=AWS_REGION)
    
    # Remove block public access
    try:
        s3.delete_public_access_block(Bucket=S3_BUCKET)
        print(f"✓ Removed public access block from {S3_BUCKET}")
    except Exception as e:
        print(f"Note: {e}")
    
    # Add bucket policy for public read access to generated-videos/*
    policy = {
        "Version": "2012-10-17",
        "Statement": [{
            "Sid": "PublicReadGetObject",
            "Effect": "Allow",
            "Principal": "*",
            "Action": "s3:GetObject",
            "Resource": f"arn:aws:s3:::{S3_BUCKET}/generated-videos/*"
        }]
    }
    
    try:
        s3.put_bucket_policy(Bucket=S3_BUCKET, Policy=json.dumps(policy))
        print(f"✓ Applied public read policy to {S3_BUCKET}/generated-videos/*")
    except Exception as e:
        print(f"Error applying bucket policy: {e}")

def main():
    print("Updating ad video URLs to use S3 CDN...")
    print()
    
    # Make bucket public for CDN access
    make_bucket_public()
    print()
    
    # Generate URL mapping
    url_mapping = {}
    for ad_id, generation_id in AD_TO_GENERATION.items():
        s3_path = get_s3_path(generation_id)
        if s3_path:
            # Use S3 HTTP URL (acts as CDN)
            s3_url = f"https://{S3_BUCKET}.s3.{AWS_REGION}.amazonaws.com/{s3_path}"
            url_mapping[ad_id] = {
                "generation_id": generation_id,
                "s3_path": s3_path,
                "cdn_url": s3_url
            }
            print(f"✓ {ad_id}: {s3_url}")
        else:
            print(f"✗ {ad_id}: Video not found in S3")
    
    # Save mapping
    with open('dynamicAdInsertion/s3_url_mapping.json', 'w') as f:
        json.dump(url_mapping, f, indent=2)
    
    print()
    print("✓ URL mapping saved to s3_url_mapping.json")
    print()
    print("Next steps:")
    print("1. Update app.py to use the CDN URLs from s3_url_mapping.json")
    print("2. Restart the DAI service")

if __name__ == "__main__":
    main()
