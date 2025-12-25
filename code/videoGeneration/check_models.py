#!/usr/bin/env python3
"""
Check available AWS Bedrock models, especially video generation models
"""

import os
import boto3
import json

# Initialize Bedrock client
region = os.environ.get('AWS_REGION')
if not region:
    raise RuntimeError("Set AWS_REGION before running check_models")

bedrock_client = boto3.client('bedrock', region_name=region)

print(f"Checking available models in region: {region}\n")

try:
    # List all foundation models
    response = bedrock_client.list_foundation_models()
    
    all_models = response.get('modelSummaries', [])
    
    print(f"Total models available: {len(all_models)}\n")
    
    # Filter for video models
    video_models = [m for m in all_models if 'VIDEO' in m.get('outputModalities', [])]
    
    print("=" * 80)
    print("VIDEO GENERATION MODELS:")
    print("=" * 80)
    
    if video_models:
        for model in video_models:
            print(f"\nModel ID: {model['modelId']}")
            print(f"  Name: {model.get('modelName', 'N/A')}")
            print(f"  Provider: {model.get('providerName', 'N/A')}")
            print(f"  Input Modalities: {', '.join(model.get('inputModalities', []))}")
            print(f"  Output Modalities: {', '.join(model.get('outputModalities', []))}")
            print(f"  Lifecycle: {model.get('modelLifecycle', {}).get('status', 'N/A')}")
    else:
        print("\nNo video generation models found!")
        print("\nThis could mean:")
        print("1. Video generation models are not available in your region")
        print("2. You need to request access to Nova models in the AWS Console")
        print("3. Try a different region (e.g., us-west-2)")
    
    # Show all models with their modalities for reference
    print("\n" + "=" * 80)
    print("ALL AVAILABLE MODELS (showing output modalities):")
    print("=" * 80)
    
    modality_groups = {}
    for model in all_models:
        output_mods = ', '.join(sorted(model.get('outputModalities', [])))
        if output_mods not in modality_groups:
            modality_groups[output_mods] = []
        modality_groups[output_mods].append(model['modelId'])
    
    for modality, models in sorted(modality_groups.items()):
        print(f"\n{modality}:")
        for model_id in sorted(models):
            print(f"  - {model_id}")
    
    # Check for Nova models specifically
    nova_models = [m for m in all_models if 'nova' in m['modelId'].lower()]
    
    print("\n" + "=" * 80)
    print("AMAZON NOVA MODELS:")
    print("=" * 80)
    
    if nova_models:
        for model in nova_models:
            print(f"\n{model['modelId']}")
            print(f"  Status: {model.get('modelLifecycle', {}).get('status', 'N/A')}")
            print(f"  Modalities: {model.get('inputModalities', [])} → {model.get('outputModalities', [])}")
    else:
        print("\nNo Amazon Nova models found!")
        print("\n🔧 NEXT STEPS:")
        print("1. Go to AWS Console → Bedrock → Model access")
        print("2. Request access to Amazon Nova models")
        print("3. Wait for approval (usually instant for most regions)")
        print("4. Try again after access is granted")
        
except Exception as e:
    print(f"Error: {e}")
    print("\nMake sure you have proper AWS credentials configured")
