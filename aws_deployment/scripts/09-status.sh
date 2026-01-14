#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# shellcheck source=00-env.sh
source "${SCRIPT_DIR}/00-env.sh"

aws eks describe-cluster --region "${AWS_REGION}" --name "${EKS_CLUSTER_NAME}" --query 'cluster.status' --output text >/dev/null
aws eks update-kubeconfig --region "${AWS_REGION}" --name "${EKS_CLUSTER_NAME}" >/dev/null

echo "=== EKS cluster ==="
echo "Region: ${AWS_REGION}"
echo "Cluster: ${EKS_CLUSTER_NAME}"
echo "Namespace: ${EKS_NAMESPACE}"
echo

echo "=== Kubernetes resources ==="
kubectl -n "${EKS_NAMESPACE}" get deploy,po,svc,ingress

echo
alb="$(kubectl -n "${EKS_NAMESPACE}" get ingress frontend -o jsonpath='{.status.loadBalancer.ingress[0].hostname}' 2>/dev/null || true)"
if [[ -n "${alb}" ]]; then
  echo "ALB hostname: ${alb}"
else
  echo "ALB hostname: (not ready yet)"
fi
