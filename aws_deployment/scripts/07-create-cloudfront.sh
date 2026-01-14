#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=00-env.sh
source "${SCRIPT_DIR}/00-env.sh"

ALB_HOSTNAME="${1:-}"
if [[ -z "${ALB_HOSTNAME}" ]]; then
  echo "Usage: $0 <frontend-alb-hostname>" >&2
  exit 1
fi

CALLER_REF="mediagenai-aws-$(date -u +%Y%m%dT%H%M%SZ)"

TMP=$(mktemp)
cat > "${TMP}" <<JSON
{
  "CallerReference": "${CALLER_REF}",
  "Comment": "mediagenai-aws frontend",
  "Enabled": true,
  "Origins": {
    "Quantity": 1,
    "Items": [
      {
        "Id": "frontend-alb",
        "DomainName": "${ALB_HOSTNAME}",
        "CustomOriginConfig": {
          "HTTPPort": 80,
          "HTTPSPort": 443,
          "OriginProtocolPolicy": "http-only",
          "OriginSslProtocols": {"Quantity": 1, "Items": ["TLSv1.2"]}
        }
      }
    ]
  },
  "DefaultCacheBehavior": {
    "TargetOriginId": "frontend-alb",
    "ViewerProtocolPolicy": "redirect-to-https",
    "AllowedMethods": {"Quantity": 2, "Items": ["GET", "HEAD"], "CachedMethods": {"Quantity": 2, "Items": ["GET", "HEAD"]}},
    "Compress": true,
    "ForwardedValues": {
      "QueryString": true,
      "Cookies": {"Forward": "all"}
    },
    "MinTTL": 0
  },
  "PriceClass": "PriceClass_100",
  "ViewerCertificate": {
    "CloudFrontDefaultCertificate": true
  }
}
JSON

echo "Creating CloudFront distribution (this is global; may take ~10-20 min to fully deploy)..." 
OUT=$(aws cloudfront create-distribution --distribution-config file://"${TMP}")
rm -f "${TMP}"

ID=$(echo "${OUT}" | python3 -c 'import sys, json; print(json.load(sys.stdin)["Distribution"]["Id"])')
DOMAIN=$(echo "${OUT}" | python3 -c 'import sys, json; print(json.load(sys.stdin)["Distribution"]["DomainName"])')

echo "CloudFront DistributionId: ${ID}" 
echo "CloudFront DomainName: ${DOMAIN}" 
