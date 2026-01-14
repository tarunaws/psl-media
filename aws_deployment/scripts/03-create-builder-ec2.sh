#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=00-env.sh
source "${SCRIPT_DIR}/00-env.sh"

ROLE_NAME="${BUILDER_NAME}-role"
PROFILE_NAME="${BUILDER_NAME}-instance-profile"
SG_NAME="${BUILDER_NAME}-sg"

ACCOUNT_PARTITION="aws"

create_role_and_profile() {
  if aws iam get-role --role-name "${ROLE_NAME}" >/dev/null 2>&1; then
    echo "IAM role exists: ${ROLE_NAME}"
  else
    echo "Creating IAM role: ${ROLE_NAME}"
    cat > /tmp/${ROLE_NAME}-trust.json <<'JSON'
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {"Service": "ec2.amazonaws.com"},
      "Action": "sts:AssumeRole"
    }
  ]
}
JSON
    aws iam create-role --role-name "${ROLE_NAME}" --assume-role-policy-document file:///tmp/${ROLE_NAME}-trust.json >/dev/null

    # SSM core + ECR push/pull (PowerUser is simplest for a demo builder)
    aws iam attach-role-policy --role-name "${ROLE_NAME}" --policy-arn "arn:${ACCOUNT_PARTITION}:iam::aws:policy/AmazonSSMManagedInstanceCore" >/dev/null
    aws iam attach-role-policy --role-name "${ROLE_NAME}" --policy-arn "arn:${ACCOUNT_PARTITION}:iam::aws:policy/AmazonEC2ContainerRegistryPowerUser" >/dev/null
    aws iam attach-role-policy --role-name "${ROLE_NAME}" --policy-arn "arn:${ACCOUNT_PARTITION}:iam::aws:policy/AmazonS3ReadOnlyAccess" >/dev/null
  fi

  if aws iam get-instance-profile --instance-profile-name "${PROFILE_NAME}" >/dev/null 2>&1; then
    echo "Instance profile exists: ${PROFILE_NAME}"
  else
    echo "Creating instance profile: ${PROFILE_NAME}"
    aws iam create-instance-profile --instance-profile-name "${PROFILE_NAME}" >/dev/null
    # IAM eventual consistency
    sleep 8
    aws iam add-role-to-instance-profile --instance-profile-name "${PROFILE_NAME}" --role-name "${ROLE_NAME}" >/dev/null
  fi
}

get_default_vpc_id() {
  aws ec2 describe-vpcs --region "${AWS_REGION}" \
    --filters Name=isDefault,Values=true \
    --query 'Vpcs[0].VpcId' --output text
}

get_default_subnet_id() {
  local vpc_id="$1"
  aws ec2 describe-subnets --region "${AWS_REGION}" \
    --filters Name=vpc-id,Values="${vpc_id}" Name=default-for-az,Values=true \
    --query 'Subnets[0].SubnetId' --output text
}

ensure_security_group() {
  local vpc_id="$1"

  local sg_id
  sg_id=$(aws ec2 describe-security-groups --region "${AWS_REGION}" \
    --filters Name=vpc-id,Values="${vpc_id}" Name=group-name,Values="${SG_NAME}" \
    --query 'SecurityGroups[0].GroupId' --output text)

  if [[ "${sg_id}" != "None" && -n "${sg_id}" ]]; then
    echo "Security group exists: ${sg_id}"
    echo "${sg_id}"
    return 0
  fi

  echo "Creating security group: ${SG_NAME}"
  sg_id=$(aws ec2 create-security-group --region "${AWS_REGION}" --group-name "${SG_NAME}" \
    --description "${BUILDER_NAME} builder SG" --vpc-id "${vpc_id}" \
    --query 'GroupId' --output text)

  # No inbound rules (SSM only). Default outbound allows all egress.
  echo "${sg_id}"
}

get_latest_al2023_ami() {
  aws ssm get-parameter --region "${AWS_REGION}" \
    --name "/aws/service/ami-amazon-linux-latest/al2023-ami-kernel-default-x86_64" \
    --query 'Parameter.Value' --output text
}

create_instance() {
  local subnet_id="$1"
  local sg_id="$2"
  local ami_id="$3"

  # Check if there is already a running instance with this Name tag
  local existing
  existing=$(aws ec2 describe-instances --region "${AWS_REGION}" \
    --filters "Name=tag:Name,Values=${BUILDER_NAME}" "Name=instance-state-name,Values=pending,running,stopping,stopped" \
    --query 'Reservations[0].Instances[0].InstanceId' --output text)

  if [[ "${existing}" != "None" && -n "${existing}" ]]; then
    echo "Builder instance already exists: ${existing}"
    echo "${existing}"
    return 0
  fi

  echo "Launching EC2 builder instance (${BUILDER_INSTANCE_TYPE})..."
  local instance_id
  instance_id=$(aws ec2 run-instances --region "${AWS_REGION}" \
    --image-id "${ami_id}" \
    --instance-type "${BUILDER_INSTANCE_TYPE}" \
    --iam-instance-profile Name="${PROFILE_NAME}" \
    --subnet-id "${subnet_id}" \
    --security-group-ids "${sg_id}" \
    --tag-specifications "ResourceType=instance,Tags=[{Key=Name,Value=${BUILDER_NAME}}]" \
    --metadata-options "HttpTokens=required" \
    --query 'Instances[0].InstanceId' --output text)

  echo "InstanceId: ${instance_id}"
  echo "Waiting for instance running..."
  aws ec2 wait instance-running --region "${AWS_REGION}" --instance-ids "${instance_id}"

  echo "Waiting for SSM to register (can take ~1-3 minutes)..."
  # Poll SSM
  for i in {1..60}; do
    if aws ssm describe-instance-information --region "${AWS_REGION}" \
      --filters "Key=InstanceIds,Values=${instance_id}" \
      --query 'InstanceInformationList[0].InstanceId' --output text 2>/dev/null | grep -q "${instance_id}"; then
      echo "SSM ready: ${instance_id}"
      break
    fi
    sleep 5
  done

  echo "${instance_id}"
}

main() {
  create_role_and_profile

  local vpc_id
  vpc_id=$(get_default_vpc_id)
  if [[ -z "${vpc_id}" || "${vpc_id}" == "None" ]]; then
    echo "ERROR: No default VPC found in ${AWS_REGION}." >&2
    exit 1
  fi

  local subnet_id
  subnet_id=$(get_default_subnet_id "${vpc_id}")
  if [[ -z "${subnet_id}" || "${subnet_id}" == "None" ]]; then
    echo "ERROR: No default subnet found in ${AWS_REGION}." >&2
    exit 1
  fi

  local sg_id
  sg_id=$(ensure_security_group "${vpc_id}")

  local ami_id
  ami_id=$(get_latest_al2023_ami)

  local instance_id
  instance_id=$(create_instance "${subnet_id}" "${sg_id}" "${ami_id}")

  echo "OK: Builder ready: ${instance_id}"
  echo "You can connect via: aws ssm start-session --target ${instance_id} --region ${AWS_REGION}"
}

main "$@"
