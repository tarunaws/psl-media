#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/../.." && pwd)"
AWS_DEPLOY_DIR="${ROOT_DIR}/aws_deployment"

# shellcheck source=00-env.sh
source "${SCRIPT_DIR}/00-env.sh"

aws eks update-kubeconfig --region "${AWS_REGION}" --name "${EKS_CLUSTER_NAME}" >/dev/null

echo "Waiting for AWS Load Balancer Controller to be ready..." 
kubectl -n kube-system rollout status deploy/aws-load-balancer-controller --timeout=5m

echo "Applying base manifests..." 
kubectl apply -f "${AWS_DEPLOY_DIR}/k8s/base"

echo "Applying ingress manifests..." 
kubectl apply -f "${AWS_DEPLOY_DIR}/k8s/ingress/30-frontend-ingress.yaml"

echo "Waiting for deployments..." 
kubectl -n "${EKS_NAMESPACE}" rollout status deploy/frontend --timeout=5m
kubectl -n "${EKS_NAMESPACE}" rollout status deploy/ai-subtitle --timeout=5m
kubectl -n "${EKS_NAMESPACE}" rollout status deploy/highlight-trailer --timeout=5m
kubectl -n "${EKS_NAMESPACE}" rollout status deploy/dynamic-ad-insertion --timeout=5m

echo "Waiting for ingress ALB hostname..." 
for i in {1..60}; do
  HOST=$(kubectl -n "${EKS_NAMESPACE}" get ingress frontend -o jsonpath='{.status.loadBalancer.ingress[0].hostname}' 2>/dev/null || true)
  if [[ -n "${HOST}" ]]; then
    echo "Frontend ALB hostname: ${HOST}"
    exit 0
  fi
  sleep 10
done

echo "ERROR: Ingress hostname not ready yet. Check: kubectl -n ${EKS_NAMESPACE} describe ingress frontend" >&2
exit 1
