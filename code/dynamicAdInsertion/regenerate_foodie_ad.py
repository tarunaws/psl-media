#!/usr/bin/env python3
"""
Regenerate the foodie/gourmet food advertisement.
"""

import os
import boto3
import json
import time
import sys

# Configuration
AWS_REGION = os.environ.get("AWS_REGION")
if not AWS_REGION:
    raise RuntimeError("Set AWS_REGION before running regenerate_foodie_ad")
MODEL_ID = "amazon.nova-reel-v1:0"

# Ad prompt
AD_PROMPT = "Delicious gourmet food with chef preparing exquisite dishes, steam rising, elegant plating, warm restaurant ambiance, cinematic food photography"

def generate_ad():
    """Generate the gourmet food ad."""
    print("=" * 70)
    print("Regenerating Gourmet Food Advertisement")
    print("=" * 70)
    print()
    
    bedrock = boto3.client('bedrock-runtime', region_name=AWS_REGION)
    
    print(f"📝 Prompt: {AD_PROMPT}")
    print()
    print("🚀 Starting video generation...")
    
    # Request body
    request_body = {
        "taskType": "TEXT_VIDEO",
        "textToVideoParams": {
            "text": AD_PROMPT
        },
        "videoGenerationConfig": {
            "durationSeconds": 6,
            "fps": 24,
            "dimension": "1280x720",
            "seed": int(time.time())  # Random seed for variation
        }
    }
    
    try:
        # Invoke model asynchronously
        response = bedrock.start_async_invoke(
            modelId=MODEL_ID,
            modelInput=request_body,
            outputDataConfig={
                "s3OutputDataConfig": {
                    "s3Uri": f"s3://mediagenai-video-generation/generated-videos/"
                }
            }
        )
        
        invocation_arn = response.get('invocationArn', '')
        generation_id = invocation_arn.split('/')[-1]
        
        if not generation_id:
            print("❌ Failed to get generation ID")
            return None
        
        print(f"✅ Generation started!")
        print(f"   Generation ID: {generation_id}")
        print()
        print("⏳ Waiting for video generation to complete...")
        print("   This typically takes 1-2 minutes...")
        print()
        
        # Poll for completion
        max_attempts = 60
        attempt = 0
        
        while attempt < max_attempts:
            attempt += 1
            time.sleep(5)
            
            try:
                # Check status
                status_response = bedrock.get_async_invoke(
                    invocationArn=invocation_arn
                )
                
                status = status_response.get('status', 'UNKNOWN')
                
                if status == 'Completed':
                    output_location = status_response.get('outputDataConfig', {}).get('s3OutputDataConfig', {}).get('s3Uri', '')
                    
                    # Parse S3 location
                    if output_location.startswith('s3://'):
                        s3_path = output_location.replace('s3://', '').split('/', 1)[1]
                        bucket = output_location.replace('s3://', '').split('/')[0]
                        
                        # Get the actual video file path
                        s3 = boto3.client('s3', region_name=AWS_REGION)
                        objects = s3.list_objects_v2(Bucket=bucket, Prefix=s3_path)
                        
                        video_url = None
                        for obj in objects.get('Contents', []):
                            if obj['Key'].endswith('output.mp4'):
                                video_url = f"https://{bucket}.s3.{AWS_REGION}.amazonaws.com/{obj['Key']}"
                                s3_path = obj['Key']
                                break
                        
                        print()
                        print("=" * 70)
                        print("✅ GENERATION COMPLETE!")
                        print("=" * 70)
                        print(f"Generation ID: {generation_id}")
                        print(f"S3 Path: {s3_path}")
                        print(f"CDN URL: {video_url}")
                        print()
                        
                        return {
                            'generation_id': generation_id,
                            'video_url': video_url,
                            's3_path': s3_path
                        }
                    
                elif status == 'Failed':
                    print(f"❌ Generation failed: {status_response.get('failureMessage', 'Unknown error')}")
                    return None
                
                else:
                    print(f"   [{attempt}/{max_attempts}] Status: {status}")
                    
            except Exception as e:
                print(f"   Error checking status: {e}")
        
        print("❌ Timeout waiting for generation")
        return None
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return None

if __name__ == "__main__":
    result = generate_ad()
    
    if result:
        print("=" * 70)
        print("📋 UPDATE REQUIRED:")
        print("=" * 70)
        print()
        print("Update dynamicAdInsertion/app.py:")
        print(f"""
In the gourmet_food_ad section, update:
  "generation_id": "{result['generation_id']}",
  "video_url": "{result['video_url']}",
        """)
        print()
        print("Then restart the DAI service:")
        print("  lsof -ti:5010 | xargs kill -9")
        print("  python dynamicAdInsertion/app.py &")
        print()
        sys.exit(0)
    else:
        print("❌ Failed to generate ad")
        sys.exit(1)
