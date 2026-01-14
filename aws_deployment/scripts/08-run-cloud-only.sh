#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/../.." && pwd)"

# shellcheck source=00-env.sh
source "${SCRIPT_DIR}/00-env.sh"

usage() {
  cat <<'EOF'
Usage:
  bash aws_deployment/scripts/08-run-cloud-only.sh <builder-instance-id> [bundle-s3-uri]

Behavior:
  - If bundle-s3-uri is omitted, packages aws_deployment and uploads to S3.
  - Builds and pushes images to ECR using the SSM builder.
  - Deploys to EKS and waits for rollouts.
  - Prints current deployment status (pods/services/ingress).

Required:
  - AWS CLI authenticated (recommended: AWS_PROFILE)
  - kubectl installed
EOF
}

if [[ ${1:-} == "-h" || ${1:-} == "--help" ]]; then
  usage
  exit 0
fi

BUILDER_INSTANCE_ID="${1:-}"
BUNDLE_S3_URI="${2:-}"

if [[ -z "${BUILDER_INSTANCE_ID}" ]]; then
  echo "ERROR: Missing builder instance id." >&2
  usage
  exit 1
fi

ensure_kubeconfig() {
  aws eks update-kubeconfig --region "${AWS_REGION}" --name "${EKS_CLUSTER_NAME}" >/dev/null
}

package_if_needed() {
  if [[ -n "${BUNDLE_S3_URI}" ]]; then
    echo "Using provided bundle: ${BUNDLE_S3_URI}"
    return 0
  fi

  echo "Packaging and uploading aws_deployment bundle..."
  local last_line
  last_line="$(bash "${SCRIPT_DIR}/01-package-and-upload.sh" | tail -n 1)"
  BUNDLE_S3_URI="${last_line#Bundle key: }"
  if [[ -z "${BUNDLE_S3_URI}" || "${BUNDLE_S3_URI}" != s3://* ]]; then
    echo "ERROR: Unable to determine bundle S3 URI from packaging output." >&2
    exit 1
  fi
  echo "Bundle: ${BUNDLE_S3_URI}"
}

wait_rollouts() {
  ensure_kubeconfig

  echo "Waiting for deployments to become available..."
  # These names match aws_deployment/k8s manifests.
  kubectl -n "${EKS_NAMESPACE}" rollout status deployment/frontend --timeout=10m
  kubectl -n "${EKS_NAMESPACE}" rollout status deployment/ai-subtitle --timeout=10m
  kubectl -n "${EKS_NAMESPACE}" rollout status deployment/dynamic-ad-insertion --timeout=10m
  kubectl -n "${EKS_NAMESPACE}" rollout status deployment/highlight-trailer --timeout=10m
}

print_status() {
  ensure_kubeconfig

  echo "\n=== Kubernetes status (namespace: ${EKS_NAMESPACE}) ==="
  kubectl -n "${EKS_NAMESPACE}" get deploy,po,svc,ingress

  local alb
  alb="$(kubectl -n "${EKS_NAMESPACE}" get ingress frontend -o jsonpath='{.status.loadBalancer.ingress[0].hostname}' 2>/dev/null || true)"
  if [[ -n "${alb}" ]]; then
    echo "\nALB hostname: ${alb}"
  fi
}

# Main
package_if_needed

echo "Building & pushing images via SSM builder (${BUILDER_INSTANCE_ID})..."
bash "${SCRIPT_DIR}/04-ssm-build-and-push.sh" "${BUILDER_INSTANCE_ID}" "${BUNDLE_S3_URI}"

echo "Deploying to EKS..."
bash "${SCRIPT_DIR}/06-deploy-to-eks.sh"

wait_rollouts
print_status

echo "\nOK: Cloud-only deploy complete."
