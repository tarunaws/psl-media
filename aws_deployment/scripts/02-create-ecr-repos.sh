#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=00-env.sh
source "${SCRIPT_DIR}/00-env.sh"

ensure_repo() {
  local repo_name="$1"
  if aws ecr describe-repositories --region "${AWS_REGION}" --repository-names "${repo_name}" >/dev/null 2>&1; then
    echo "ECR repo exists: ${repo_name}"
    return 0
  fi

  echo "Creating ECR repo: ${repo_name}"
  aws ecr create-repository --region "${AWS_REGION}" --repository-name "${repo_name}" >/dev/null
}

ensure_repo "${ECR_REPO_AI_SUBTITLE}"
ensure_repo "${ECR_REPO_HIGHLIGHT_TRAILER}"
ensure_repo "${ECR_REPO_DYNAMIC_AD_INSERTION}"
ensure_repo "${ECR_REPO_FRONTEND}"

echo "OK: ECR repos ready." 

echo "Registry: ${ECR_REGISTRY}" 
