#!/usr/bin/env python3
import argparse
import sys
import time

import botocore.session


TERMINAL_STATUSES = {"Success", "Cancelled", "TimedOut", "Failed", "Cancelling"}


def get_ssm_client(region: str):
    session = botocore.session.get_session()
    return session.create_client("ssm", region_name=region)


def send_shell_script(
    region: str,
    instance_id: str,
    script: str,
    output_s3_bucket: str | None,
    output_s3_prefix: str | None,
) -> str:
    ssm = get_ssm_client(region)

    kwargs: dict = {}
    if output_s3_bucket:
        kwargs["OutputS3BucketName"] = output_s3_bucket
        if output_s3_prefix:
            kwargs["OutputS3KeyPrefix"] = output_s3_prefix

    resp = ssm.send_command(
        InstanceIds=[instance_id],
        DocumentName="AWS-RunShellScript",
        Parameters={"commands": [script]},
        TimeoutSeconds=60 * 60,
        **kwargs,
    )
    return resp["Command"]["CommandId"]


def wait_and_print(region: str, command_id: str, instance_id: str, poll_seconds: int) -> str:
    ssm = get_ssm_client(region)

    last_status = None
    while True:
        try:
            inv = ssm.get_command_invocation(CommandId=command_id, InstanceId=instance_id)
        except ssm.exceptions.InvocationDoesNotExist:  # type: ignore[attr-defined]
            time.sleep(poll_seconds)
            continue

        status = inv.get("Status")
        if status != last_status:
            print(f"Status: {status}")
            last_status = status

        if status in TERMINAL_STATUSES:
            stdout = inv.get("StandardOutputContent") or ""
            stderr = inv.get("StandardErrorContent") or ""

            print("--- SSM Output (stdout) ---")
            print(stdout)
            print("--- SSM Output (stderr) ---", file=sys.stderr)
            print(stderr, file=sys.stderr)
            return status or "Unknown"

        time.sleep(poll_seconds)


def main() -> int:
    parser = argparse.ArgumentParser(description="Send an SSM RunShellScript command and stream results.")
    parser.add_argument("--region", required=True)
    parser.add_argument("--instance-id", required=True)
    parser.add_argument("--script-file", required=True)
    parser.add_argument("--poll-seconds", type=int, default=10)
    parser.add_argument("--output-s3-bucket")
    parser.add_argument("--output-s3-prefix")
    args = parser.parse_args()

    with open(args.script_file, "r", encoding="utf-8") as f:
        script = f.read()

    if args.output_s3_bucket:
        print(f"SSM output bucket: s3://{args.output_s3_bucket}/{args.output_s3_prefix or ''}")

    command_id = send_shell_script(
        args.region,
        args.instance_id,
        script,
        args.output_s3_bucket,
        args.output_s3_prefix,
    )
    print(f"SSM command started: {command_id}")
    status = wait_and_print(args.region, command_id, args.instance_id, args.poll_seconds)

    if status != "Success":
        print(f"ERROR: SSM command finished with status: {status}", file=sys.stderr)
        return 1

    print("OK: SSM command succeeded")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
