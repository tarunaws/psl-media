#!/usr/bin/env python3
"""
Enable CORS on S3 bucket for video playback from React frontend.
"""

import boto3
import json
import os

AWS_REGION = os.environ.get("AWS_REGION")
if not AWS_REGION:
    raise RuntimeError("Set AWS_REGION before running enable_s3_cors")

DEFAULT_MEDIA_BUCKET = os.environ.get("MEDIA_S3_BUCKET")
S3_BUCKET = os.environ.get("VIDEO_GEN_S3_BUCKET") or DEFAULT_MEDIA_BUCKET

if not S3_BUCKET:
    raise RuntimeError("Set VIDEO_GEN_S3_BUCKET or MEDIA_S3_BUCKET before running enable_s3_cors")

def enable_cors():
    """Enable CORS on S3 bucket."""
    s3 = boto3.client('s3', region_name=AWS_REGION)
    
    cors_configuration = {
        'CORSRules': [{
            'AllowedHeaders': ['*'],
            'AllowedMethods': ['GET', 'HEAD'],
            'AllowedOrigins': ['*'],  # In production, restrict to your domain
            'ExposeHeaders': ['ETag', 'Content-Length', 'Content-Type'],
            'MaxAgeSeconds': 3000
        }]
    }
    
    try:
        s3.put_bucket_cors(
            Bucket=S3_BUCKET,
            CORSConfiguration=cors_configuration
        )
        print(f"✓ CORS enabled on {S3_BUCKET}")
        print("  Allowed Origins: *")
        print("  Allowed Methods: GET, HEAD")
        print("  Allowed Headers: *")
    except Exception as e:
        print(f"Error enabling CORS: {e}")

if __name__ == "__main__":
    print("Enabling CORS on S3 bucket for video playback...")
    print()
    enable_cors()
