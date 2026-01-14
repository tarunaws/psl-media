Scripts overview (run from repo root)

- Configure AWS auth first (recommended: AWS_PROFILE).
- Then run in order:
  1) aws_deployment/scripts/02-create-ecr-repos.sh
  2) aws_deployment/scripts/01-package-and-upload.sh
  3) aws_deployment/scripts/03-create-builder-ec2.sh
  4) aws_deployment/scripts/04-ssm-build-and-push.sh <instance-id> <bundle-s3-uri>
  5) aws_deployment/scripts/05-create-eks-and-alb-controller.sh
  6) aws_deployment/scripts/06-deploy-to-eks.sh (prints ALB hostname)
  7) aws_deployment/scripts/07-create-cloudfront.sh <alb-hostname>

Convenience
- Cloud-only deploy (package -> build/push -> deploy -> wait -> status):
  - bash aws_deployment/scripts/08-run-cloud-only.sh <builder-instance-id> [bundle-s3-uri]
- Status only:
  - bash aws_deployment/scripts/09-status.sh

Notes
- If the scripts aren't executable, run them as: bash aws_deployment/scripts/<script>.sh
- The EC2 builder is accessed via SSM Session Manager; no SSH needed.
- Backend services remain private (ClusterIP). Only the frontend Ingress is internet-facing.
- CloudFront gives you an AWS-provided public HTTPS domain (dxxxx.cloudfront.net).
