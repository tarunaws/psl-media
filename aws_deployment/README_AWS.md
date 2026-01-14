# aws_deployment (EKS + CloudFront)

This folder is a deployable subset of the repo for **3 use cases only**:
- AI Subtitling (`aiSubtitle`, port `5001`)
- Highlight & Trailer (`highlightTrailer`, port `5013`)
- Dynamic Ad Insertion (`dynamicAdInsertion`, port `5010`)

Frontend is the duplicated CRA app in `aws_deployment/frontend/`, trimmed to only show these 3 use cases and **no admin page**.

## Architecture (only frontend public; no custom domain)

### Frontend (public)
- Frontend is deployed as an **nginx container** on EKS.
- Users access the **CloudFront default domain** (e.g. `https://dxxxx.cloudfront.net`).
- CloudFront origin is the **frontend ALB** created by the frontend Ingress.

### Backend services (private)
- Each backend service is a Kubernetes `Deployment` + `Service` (**ClusterIP only**).
- No backend Ingress is required.
- The frontend nginx reverse-proxies requests to the private services over in-cluster DNS.

This preserves a simple security posture:
- Only the frontend endpoint is public.
- Backends are reachable only from inside the cluster.

## Recommended deploy flow (no local Docker required)

If you cannot run Docker locally (e.g. Docker Desktop install is blocked), use the scripts in `aws_deployment/scripts/`:

```bash
# Run from repo root

# 1) Create ECR repos
bash aws_deployment/scripts/02-create-ecr-repos.sh

# 2) Package + upload aws_deployment bundle to S3 (prints a s3://... bundle URI)
bash aws_deployment/scripts/01-package-and-upload.sh

# 3) Create an EC2 builder VM (SSM)
bash aws_deployment/scripts/03-create-builder-ec2.sh

# 4) Build + push images from the builder
#    (Pass instance id + bundle URI from step 2)
bash aws_deployment/scripts/04-ssm-build-and-push.sh <instance-id> <bundle-s3-uri>

# 5) Create EKS + install AWS Load Balancer Controller
bash aws_deployment/scripts/05-create-eks-and-alb-controller.sh

# 6) Deploy manifests (prints the frontend ALB hostname)
bash aws_deployment/scripts/06-deploy-to-eks.sh

# 7) Create CloudFront distribution for the frontend ALB
bash aws_deployment/scripts/07-create-cloudfront.sh <frontend-alb-hostname>
```

## Build & push images (ECR)

This section is the **manual** Docker path (if you have Docker available on your machine). Otherwise use the scripts above.

From repo root:

```bash
# Set these
export AWS_REGION=us-east-1
export AWS_ACCOUNT_ID=YOUR_ACCOUNT_ID

aws ecr create-repository --repository-name mediagenai/ai-subtitle || true
aws ecr create-repository --repository-name mediagenai/highlight-trailer || true
aws ecr create-repository --repository-name mediagenai/dynamic-ad-insertion || true
aws ecr create-repository --repository-name mediagenai/frontend || true

aws ecr get-login-password --region "$AWS_REGION" | docker login --username AWS --password-stdin "$AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com"

docker build -f aws_deployment/aiSubtitle/Dockerfile -t "$AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/mediagenai/ai-subtitle:latest" aws_deployment
docker build -f aws_deployment/highlightTrailer/Dockerfile -t "$AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/mediagenai/highlight-trailer:latest" aws_deployment
docker build -f aws_deployment/dynamicAdInsertion/Dockerfile -t "$AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/mediagenai/dynamic-ad-insertion:latest" aws_deployment
docker build -f frontend/Dockerfile -t "$AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/mediagenai/frontend:latest" aws_deployment

docker push "$AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/mediagenai/ai-subtitle:latest"
docker push "$AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/mediagenai/highlight-trailer:latest"
docker push "$AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/mediagenai/dynamic-ad-insertion:latest"
docker push "$AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/mediagenai/frontend:latest"
```

## Deploy to EKS (private backends + public frontend)

```bash
kubectl apply -f aws_deployment/k8s/base
```

This creates only ClusterIP services (including the frontend service).

## Create ALB Ingress (frontend only)

Prereq: AWS Load Balancer Controller installed in your cluster.

```bash
kubectl apply -f aws_deployment/k8s/ingress/30-frontend-ingress.yaml
```

After apply, fetch the frontend ALB DNS name:

```bash
kubectl -n mediagenai-aws get ingress frontend
```

## Create CloudFront distribution (frontend only)

- **Origin domain**: the frontend ALB DNS from the frontend Ingress.
- **Origin protocol policy**: HTTP only (simplest).

Then use the CloudFront default domain for the whole app.
