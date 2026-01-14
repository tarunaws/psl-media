#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/../.." && pwd)"
AWS_DEPLOY_DIR="${ROOT_DIR}/aws_deployment"

# shellcheck source=00-env.sh
source "${SCRIPT_DIR}/00-env.sh"

if [[ ! -d "${AWS_DEPLOY_DIR}" ]]; then
  echo "ERROR: aws_deployment folder not found at: ${AWS_DEPLOY_DIR}" >&2
  exit 1
fi

STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
BUNDLE_NAME="aws_deployment_${STAMP}.tgz"
BUNDLE_PATH="${ROOT_DIR}/${BUNDLE_NAME}"

echo "Packaging aws_deployment -> ${BUNDLE_PATH}"
(
  cd "${ROOT_DIR}"
  tar -czf "${BUNDLE_PATH}" aws_deployment
)

echo "Uploading bundle to s3://${STAGING_BUCKET}/${STAGING_PREFIX}/${BUNDLE_NAME}" 
aws s3 cp "${BUNDLE_PATH}" "s3://${STAGING_BUCKET}/${STAGING_PREFIX}/${BUNDLE_NAME}" --region "${AWS_REGION}"

echo "OK: Uploaded bundle." 

echo "Bundle key: s3://${STAGING_BUCKET}/${STAGING_PREFIX}/${BUNDLE_NAME}" 
