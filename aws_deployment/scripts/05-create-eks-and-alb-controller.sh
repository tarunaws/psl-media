#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=00-env.sh
source "${SCRIPT_DIR}/00-env.sh"

: "${K8S_VERSION:=}"
: "${NODE_TYPE:=t3.large}"
: "${NODE_COUNT:=2}"

# This script requires: eksctl, kubectl, helm

ensure_nodegroup() {
  local ng_name="ng-default"

  if eksctl get nodegroup --cluster "${EKS_CLUSTER_NAME}" --region "${AWS_REGION}" --name "${ng_name}" >/dev/null 2>&1; then
    echo "Nodegroup exists: ${ng_name}"
    return 0
  fi

  echo "Creating managed nodegroup: ${ng_name} (type=${NODE_TYPE}, nodes=${NODE_COUNT})"
  eksctl create nodegroup \
    --cluster "${EKS_CLUSTER_NAME}" \
    --region "${AWS_REGION}" \
    --name "${ng_name}" \
    --managed \
    --node-type "${NODE_TYPE}" \
    --nodes "${NODE_COUNT}" \
    --nodes-min "${NODE_COUNT}" \
    --nodes-max "${NODE_COUNT}" \
    --tags "Project=mediagenai-aws"
}

create_cluster() {
  local status
  status=$(aws eks describe-cluster --region "${AWS_REGION}" --name "${EKS_CLUSTER_NAME}" --query 'cluster.status' --output text 2>/dev/null || true)
  if [[ -n "${status}" && "${status}" != "None" ]]; then
    if [[ "${status}" == "ACTIVE" ]]; then
      echo "EKS cluster exists: ${EKS_CLUSTER_NAME} (ACTIVE)"
      return 0
    fi

    echo "EKS cluster exists: ${EKS_CLUSTER_NAME} (status=${status}); waiting until ACTIVE..."
    for _ in {1..80}; do
      status=$(aws eks describe-cluster --region "${AWS_REGION}" --name "${EKS_CLUSTER_NAME}" --query 'cluster.status' --output text 2>/dev/null || true)
      if [[ "${status}" == "ACTIVE" ]]; then
        echo "EKS cluster is ACTIVE."
        return 0
      fi
      if [[ "${status}" == "FAILED" || "${status}" == "DELETING" ]]; then
        echo "ERROR: EKS cluster is in terminal status: ${status}" >&2
        exit 1
      fi
      sleep 30
    done

    echo "ERROR: Timed out waiting for EKS cluster to become ACTIVE." >&2
    exit 1
  fi

  echo "Creating EKS cluster: ${EKS_CLUSTER_NAME} (this can take ~15-25 min)"
  if [[ -n "${K8S_VERSION}" ]]; then
    eksctl create cluster \
      --name "${EKS_CLUSTER_NAME}" \
      --region "${AWS_REGION}" \
      --version "${K8S_VERSION}" \
      --managed \
      --nodegroup-name "ng-default" \
      --node-type "${NODE_TYPE}" \
      --nodes "${NODE_COUNT}" \
      --nodes-min "${NODE_COUNT}" \
      --nodes-max "${NODE_COUNT}" \
      --with-oidc \
      --tags "Project=mediagenai-aws"
  else
    eksctl create cluster \
      --name "${EKS_CLUSTER_NAME}" \
      --region "${AWS_REGION}" \
      --managed \
      --nodegroup-name "ng-default" \
      --node-type "${NODE_TYPE}" \
      --nodes "${NODE_COUNT}" \
      --nodes-min "${NODE_COUNT}" \
      --nodes-max "${NODE_COUNT}" \
      --with-oidc \
      --tags "Project=mediagenai-aws"
  fi
}

install_alb_controller() {
  echo "Ensuring aws-load-balancer-controller is installed" 

  eksctl utils associate-iam-oidc-provider \
    --region "${AWS_REGION}" \
    --cluster "${EKS_CLUSTER_NAME}" \
    --approve

  # Create service account with required permissions (managed policy from AWS docs via JSON)
  local policy_name="AWSLoadBalancerControllerIAMPolicy"
  local policy_arn

  policy_arn=$(aws iam list-policies --scope Local --query "Policies[?PolicyName=='${policy_name}'].Arn | [0]" --output text)

  if [[ "${policy_arn}" == "None" || -z "${policy_arn}" ]]; then
    echo "Creating IAM policy: ${policy_name}" 
    tmp=$(mktemp)
    cat > "${tmp}" <<'JSON'
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "iam:CreateServiceLinkedRole",
        "ec2:DescribeAccountAttributes",
        "ec2:DescribeAddresses",
        "ec2:DescribeAvailabilityZones",
        "ec2:DescribeInternetGateways",
        "ec2:DescribeVpcs",
        "ec2:DescribeVpcPeeringConnections",
        "ec2:DescribeSubnets",
        "ec2:DescribeSecurityGroups",
        "ec2:DescribeInstances",
        "ec2:DescribeNetworkInterfaces",
        "ec2:DescribeTags",
        "ec2:GetCoipPoolUsage",
        "ec2:DescribeCoipPools",
        "elasticloadbalancing:DescribeLoadBalancers",
        "elasticloadbalancing:DescribeLoadBalancerAttributes",
        "elasticloadbalancing:DescribeListeners",
        "elasticloadbalancing:DescribeListenerCertificates",
        "elasticloadbalancing:DescribeSSLPolicies",
        "elasticloadbalancing:DescribeRules",
        "elasticloadbalancing:DescribeTargetGroups",
        "elasticloadbalancing:DescribeTargetGroupAttributes",
        "elasticloadbalancing:DescribeTargetHealth",
        "elasticloadbalancing:DescribeTags",
        "elasticloadbalancing:DescribeTrustStores",
        "elasticloadbalancing:DescribeListenerAttributes",
        "elasticloadbalancing:DescribeCapacityReservation"
      ],
      "Resource": "*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "cognito-idp:DescribeUserPoolClient",
        "acm:ListCertificates",
        "acm:DescribeCertificate",
        "iam:ListServerCertificates",
        "iam:GetServerCertificate",
        "waf-regional:GetWebACL",
        "waf-regional:GetWebACLForResource",
        "waf-regional:AssociateWebACL",
        "waf-regional:DisassociateWebACL",
        "wafv2:GetWebACL",
        "wafv2:GetWebACLForResource",
        "wafv2:AssociateWebACL",
        "wafv2:DisassociateWebACL",
        "shield:GetSubscriptionState",
        "shield:DescribeProtection",
        "shield:CreateProtection",
        "shield:DeleteProtection"
      ],
      "Resource": "*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "ec2:AuthorizeSecurityGroupIngress",
        "ec2:RevokeSecurityGroupIngress"
      ],
      "Resource": "*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "ec2:CreateSecurityGroup"
      ],
      "Resource": "*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "ec2:CreateTags"
      ],
      "Resource": "arn:aws:ec2:*:*:security-group/*",
      "Condition": {
        "StringEquals": {
          "ec2:CreateAction": "CreateSecurityGroup"
        },
        "Null": {
          "aws:RequestTag/elbv2.k8s.aws/cluster": "false"
        }
      }
    },
    {
      "Effect": "Allow",
      "Action": [
        "ec2:CreateTags",
        "ec2:DeleteTags"
      ],
      "Resource": "arn:aws:ec2:*:*:security-group/*",
      "Condition": {
        "Null": {
          "aws:RequestTag/elbv2.k8s.aws/cluster": "true",
          "aws:ResourceTag/elbv2.k8s.aws/cluster": "false"
        }
      }
    },
    {
      "Effect": "Allow",
      "Action": [
        "ec2:AuthorizeSecurityGroupIngress",
        "ec2:RevokeSecurityGroupIngress",
        "ec2:DeleteSecurityGroup"
      ],
      "Resource": "*",
      "Condition": {
        "Null": {
          "aws:ResourceTag/elbv2.k8s.aws/cluster": "false"
        }
      }
    },
    {
      "Effect": "Allow",
      "Action": [
        "elasticloadbalancing:CreateLoadBalancer",
        "elasticloadbalancing:CreateTargetGroup"
      ],
      "Resource": "*",
      "Condition": {
        "Null": {
          "aws:RequestTag/elbv2.k8s.aws/cluster": "false"
        }
      }
    },
    {
      "Effect": "Allow",
      "Action": [
        "elasticloadbalancing:CreateListener",
        "elasticloadbalancing:DeleteListener",
        "elasticloadbalancing:CreateRule",
        "elasticloadbalancing:DeleteRule"
      ],
      "Resource": "*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "elasticloadbalancing:AddTags",
        "elasticloadbalancing:RemoveTags"
      ],
      "Resource": [
        "arn:aws:elasticloadbalancing:*:*:targetgroup/*/*",
        "arn:aws:elasticloadbalancing:*:*:loadbalancer/net/*/*",
        "arn:aws:elasticloadbalancing:*:*:loadbalancer/app/*/*"
      ],
      "Condition": {
        "Null": {
          "aws:RequestTag/elbv2.k8s.aws/cluster": "true",
          "aws:ResourceTag/elbv2.k8s.aws/cluster": "false"
        }
      }
    },
    {
      "Effect": "Allow",
      "Action": [
        "elasticloadbalancing:AddTags",
        "elasticloadbalancing:RemoveTags"
      ],
      "Resource": [
        "arn:aws:elasticloadbalancing:*:*:listener/net/*/*/*",
        "arn:aws:elasticloadbalancing:*:*:listener/app/*/*/*",
        "arn:aws:elasticloadbalancing:*:*:listener-rule/net/*/*/*",
        "arn:aws:elasticloadbalancing:*:*:listener-rule/app/*/*/*"
      ]
    },
    {
      "Effect": "Allow",
      "Action": [
        "elasticloadbalancing:ModifyLoadBalancerAttributes",
        "elasticloadbalancing:SetIpAddressType",
        "elasticloadbalancing:SetSecurityGroups",
        "elasticloadbalancing:SetSubnets",
        "elasticloadbalancing:DeleteLoadBalancer",
        "elasticloadbalancing:ModifyTargetGroup",
        "elasticloadbalancing:ModifyTargetGroupAttributes",
        "elasticloadbalancing:DeleteTargetGroup"
      ],
      "Resource": "*",
      "Condition": {
        "Null": {
          "aws:ResourceTag/elbv2.k8s.aws/cluster": "false"
        }
      }
    },
    {
      "Effect": "Allow",
      "Action": [
        "elasticloadbalancing:RegisterTargets",
        "elasticloadbalancing:DeregisterTargets"
      ],
      "Resource": "arn:aws:elasticloadbalancing:*:*:targetgroup/*/*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "elasticloadbalancing:SetWebAcl",
        "elasticloadbalancing:ModifyListener",
        "elasticloadbalancing:AddListenerCertificates",
        "elasticloadbalancing:RemoveListenerCertificates",
        "elasticloadbalancing:ModifyRule"
      ],
      "Resource": "*"
    }
  ]
}
JSON
    policy_arn=$(aws iam create-policy --policy-name "${policy_name}" --policy-document "file://${tmp}" --query 'Policy.Arn' --output text)
    rm -f "${tmp}"
  else
    echo "IAM policy exists: ${policy_arn}" 
  fi

  eksctl create iamserviceaccount \
    --cluster "${EKS_CLUSTER_NAME}" \
    --region "${AWS_REGION}" \
    --namespace kube-system \
    --name aws-load-balancer-controller \
    --attach-policy-arn "${policy_arn}" \
    --override-existing-serviceaccounts \
    --approve

  aws eks update-kubeconfig --region "${AWS_REGION}" --name "${EKS_CLUSTER_NAME}" >/dev/null

  helm repo add eks https://aws.github.io/eks-charts >/dev/null 2>&1 || true
  helm repo update >/dev/null

  local vpc_id
  vpc_id=$(aws eks describe-cluster --region "${AWS_REGION}" --name "${EKS_CLUSTER_NAME}" --query 'cluster.resourcesVpcConfig.vpcId' --output text)

  helm upgrade --install aws-load-balancer-controller eks/aws-load-balancer-controller \
    -n kube-system \
    --set clusterName="${EKS_CLUSTER_NAME}" \
    --set serviceAccount.create=false \
    --set serviceAccount.name=aws-load-balancer-controller \
    --set region="${AWS_REGION}" \
    --set vpcId="${vpc_id}"

  echo "OK: aws-load-balancer-controller installed." 
}

create_cluster
ensure_nodegroup
install_alb_controller

echo "OK: EKS ready." 
