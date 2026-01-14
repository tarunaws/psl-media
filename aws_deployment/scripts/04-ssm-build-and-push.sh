#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/../.." && pwd)"

# shellcheck source=00-env.sh
source "${SCRIPT_DIR}/00-env.sh"

INSTANCE_ID="${1:-}"
BUNDLE_S3_URI="${2:-}"

if [[ -z "${INSTANCE_ID}" || -z "${BUNDLE_S3_URI}" ]]; then
  echo "Usage: $0 <ec2-instance-id> <bundle-s3-uri>" >&2
  echo "Example: $0 i-0123456789abcdef0 s3://${STAGING_BUCKET}/${STAGING_PREFIX}/aws_deployment_20260101T000000Z.tgz" >&2
  exit 1
fi

# Command that will run on the instance.
# Installs Docker, downloads bundle, builds images, pushes to ECR.
read -r -d '' REMOTE_COMMAND <<'CMD' || true
set -euo pipefail

sudo dnf -y update
sudo dnf -y install docker tar gzip
sudo systemctl enable docker
sudo systemctl start docker
sudo usermod -aG docker ec2-user

mkdir -p /home/ec2-user/work
cd /home/ec2-user/work

echo "Downloading bundle: ${BUNDLE_S3_URI}"
aws s3 cp "${BUNDLE_S3_URI}" bundle.tgz --region "${AWS_REGION}"

tar -xzf bundle.tgz
cd aws_deployment

aws ecr get-login-password --region "${AWS_REGION}" | docker login --username AWS --password-stdin "${ECR_REGISTRY}"

build_push() {
  local repo="$1"
  local dockerfile="$2"
  local tag="${ECR_REGISTRY}/${repo}:latest"
  echo "Building ${tag}"
  docker build -f "${dockerfile}" -t "${tag}" .
  echo "Pushing ${tag}"
  docker push "${tag}"
}

build_push "${ECR_REPO_AI_SUBTITLE}" "aiSubtitle/Dockerfile"
build_push "${ECR_REPO_HIGHLIGHT_TRAILER}" "highlightTrailer/Dockerfile"
build_push "${ECR_REPO_DYNAMIC_AD_INSERTION}" "dynamicAdInsertion/Dockerfile"
build_push "${ECR_REPO_FRONTEND}" "frontend/Dockerfile"

echo "OK: All images built and pushed." 
CMD

# Inject env values into the remote command (safe minimal templating).
REMOTE_COMMAND_RENDERED="$REMOTE_COMMAND"
REMOTE_COMMAND_RENDERED="${REMOTE_COMMAND_RENDERED//\$\{AWS_REGION\}/${AWS_REGION}}"
REMOTE_COMMAND_RENDERED="${REMOTE_COMMAND_RENDERED//\$\{ECR_REGISTRY\}/${ECR_REGISTRY}}"
REMOTE_COMMAND_RENDERED="${REMOTE_COMMAND_RENDERED//\$\{ECR_REPO_AI_SUBTITLE\}/${ECR_REPO_AI_SUBTITLE}}"
REMOTE_COMMAND_RENDERED="${REMOTE_COMMAND_RENDERED//\$\{ECR_REPO_HIGHLIGHT_TRAILER\}/${ECR_REPO_HIGHLIGHT_TRAILER}}"
REMOTE_COMMAND_RENDERED="${REMOTE_COMMAND_RENDERED//\$\{ECR_REPO_DYNAMIC_AD_INSERTION\}/${ECR_REPO_DYNAMIC_AD_INSERTION}}"
REMOTE_COMMAND_RENDERED="${REMOTE_COMMAND_RENDERED//\$\{ECR_REPO_FRONTEND\}/${ECR_REPO_FRONTEND}}"
REMOTE_COMMAND_RENDERED="${REMOTE_COMMAND_RENDERED//\$\{BUNDLE_S3_URI\}/${BUNDLE_S3_URI}}"

export INSTANCE_ID
export REMOTE_COMMAND_RENDERED

# Send command via SSM.
# NOTE: On this machine awscli v1 `ssm send-command` errors with "badly formed help string",
# so we use botocore directly via Python.
REMOTE_SCRIPT_FILE=$(mktemp)
printf "%s" "${REMOTE_COMMAND_RENDERED}" > "${REMOTE_SCRIPT_FILE}"

python3 "${SCRIPT_DIR}/ssm_send_command.py" \
  --region "${AWS_REGION}" \
  --instance-id "${INSTANCE_ID}" \
  --script-file "${REMOTE_SCRIPT_FILE}" \
  --output-s3-bucket "${SSM_OUTPUT_BUCKET}" \
  --output-s3-prefix "${SSM_OUTPUT_PREFIX}"

rm -f "${REMOTE_SCRIPT_FILE}"

echo "OK: Images are in ECR." 
