#!/usr/bin/env python3
"""
Configure S3 bucket for snapshot storage with security hardening.
"""

import argparse
import boto3
import json
from botocore.exceptions import ClientError


def configure_s3_bucket(bucket_name: str, region: str = "us-east-1"):
    """Configure S3 bucket with security hardening."""

    s3_client = boto3.client("s3", region_name=region)

    print(f"Configuring S3 bucket: {bucket_name}")

    # 1. Enable versioning
    try:
        s3_client.put_bucket_versioning(
            Bucket=bucket_name, VersioningConfiguration={"Status": "Enabled"}
        )
        print("✅ Versioning enabled")
    except ClientError as e:
        print(f"❌ Failed to enable versioning: {e}")
        return False

    # 2. Configure server-side encryption (SSE-S3)
    try:
        s3_client.put_bucket_encryption(
            Bucket=bucket_name,
            ServerSideEncryptionConfiguration={
                "Rules": [
                    {"ApplyServerSideEncryptionByDefault": {"SSEAlgorithm": "AES256"}}
                ]
            },
        )
        print("✅ Server-side encryption (SSE-S3) configured")
    except ClientError as e:
        print(f"❌ Failed to configure encryption: {e}")
        return False

    # 3. Block public access (should already be enabled)
    try:
        response = s3_client.get_public_access_block(Bucket=bucket_name)
        print("✅ Public access block status:")
        for key, value in response["PublicAccessBlockConfiguration"].items():
            print(f"   {key}: {value}")
    except ClientError as e:
        print(f"❌ Failed to check public access block: {e}")
        return False

    # 4. Optional: Configure lifecycle rules
    try:
        lifecycle_config = {
            "Rules": [
                {
                    "ID": "SnapshotLifecycle",
                    "Status": "Enabled",
                    "Filter": {"Prefix": "snapshots/"},
                    "Transitions": [
                        {"Days": 30, "StorageClass": "STANDARD_IA"},
                        {"Days": 90, "StorageClass": "GLACIER"},
                    ],
                }
            ]
        }

        s3_client.put_bucket_lifecycle_configuration(
            Bucket=bucket_name, LifecycleConfiguration=lifecycle_config
        )
        print("✅ Lifecycle rules configured (30d → IA, 90d → Glacier)")
    except ClientError as e:
        print(f"⚠️  Failed to configure lifecycle (optional): {e}")

    print(f"✅ S3 bucket {bucket_name} configured successfully")
    return True


def main():
    parser = argparse.ArgumentParser(description="Configure S3 bucket for snapshots")
    parser.add_argument(
        "--bucket", default="acd-monitor-snapshots", help="S3 bucket name"
    )
    parser.add_argument("--region", default="us-east-1", help="AWS region")
    parser.add_argument(
        "--dry-run", action="store_true", help="Show what would be configured"
    )

    args = parser.parse_args()

    if args.dry_run:
        print("DRY RUN - Would configure:")
        print(f"  Bucket: {args.bucket}")
        print(f"  Region: {args.region}")
        print("  - Enable versioning")
        print("  - Configure SSE-S3 encryption")
        print("  - Check public access block")
        print("  - Configure lifecycle rules")
        return 0

    success = configure_s3_bucket(args.bucket, args.region)
    return 0 if success else 1


if __name__ == "__main__":
    exit(main())
