#!/usr/bin/env bash
set -euo pipefail

# Centralized config for AWS deployment scripts.
# Override via environment variables when needed.

: "${AWS_REGION:=us-east-1}"
: "${AWS_ACCOUNT_ID:=462634386586}"

: "${EKS_CLUSTER_NAME:=mediagenai-aws}"
: "${EKS_NAMESPACE:=mediagenai-aws}"

: "${ECR_REGISTRY:=${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com}"

# ECR repo names (slashes are allowed in ECR repository names)
: "${ECR_REPO_AI_SUBTITLE:=mediagenai/ai-subtitle}"
: "${ECR_REPO_HIGHLIGHT_TRAILER:=mediagenai/highlight-trailer}"
: "${ECR_REPO_DYNAMIC_AD_INSERTION:=mediagenai/dynamic-ad-insertion}"
: "${ECR_REPO_FRONTEND:=mediagenai/frontend}"

# S3 bucket used to stage the aws_deployment bundle for the EC2 builder.
# Must be writable by your AWS identity.
: "${STAGING_BUCKET:=mediagenai-462634386586}"
: "${STAGING_PREFIX:=aws-deployment}"

# Optional: Persist SSM RunCommand stdout/stderr to S3 to avoid truncation.
# Defaults to the same staging bucket.
: "${SSM_OUTPUT_BUCKET:=${STAGING_BUCKET}}"
: "${SSM_OUTPUT_PREFIX:=${STAGING_PREFIX}/ssm-output}"

# EC2 builder parameters
: "${BUILDER_NAME:=mediagenai-docker-builder}"
: "${BUILDER_INSTANCE_TYPE:=t3.large}"

# NOTE: These scripts assume AWS CLI is already authenticated (e.g. via AWS_PROFILE).
