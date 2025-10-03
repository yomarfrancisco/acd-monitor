#!/usr/bin/env python3
"""
Apply S3 lifecycle rules and verify bucket configuration.

This script:
- Applies lifecycle rules to optimize storage costs
- Verifies bucket security settings
- Reports on applied configurations
"""

import boto3
import json
import sys
from pathlib import Path


def apply_lifecycle_rules(bucket_name):
    """Apply lifecycle rules to S3 bucket."""
    s3 = boto3.client("s3")

    # Load lifecycle configuration
    lifecycle_path = Path(__file__).parent.parent.parent / "infra/s3/lifecycle_snapshots.json"
    with open(lifecycle_path) as f:
        lifecycle_config = json.load(f)

    try:
        s3.put_bucket_lifecycle_configuration(
            Bucket=bucket_name, LifecycleConfiguration=lifecycle_config
        )
        print(f"✅ Applied lifecycle rules to {bucket_name}")
        return True
    except Exception as e:
        print(f"❌ Failed to apply lifecycle rules: {e}")
        return False


def verify_bucket_security(bucket_name):
    """Verify bucket security settings."""
    s3 = boto3.client("s3")

    security_issues = []

    try:
        # Check public access block
        pab = s3.get_public_access_block(Bucket=bucket_name)
        pab_config = pab["PublicAccessBlockConfiguration"]

        if not all(
            [
                pab_config.get("BlockPublicAcls", False),
                pab_config.get("IgnorePublicAcls", False),
                pab_config.get("BlockPublicPolicy", False),
                pab_config.get("RestrictPublicBuckets", False),
            ]
        ):
            security_issues.append("Public access block not fully enabled")
        else:
            print("✅ Public access block is properly configured")

    except s3.exceptions.NoSuchPublicAccessBlockConfiguration:
        security_issues.append("No public access block configuration found")

    try:
        # Check encryption
        encryption = s3.get_bucket_encryption(Bucket=bucket_name)
        print("✅ Bucket encryption is configured")
    except s3.exceptions.ServerSideEncryptionConfigurationNotFoundError:
        security_issues.append("No server-side encryption configured")

    try:
        # Check versioning
        versioning = s3.get_bucket_versioning(Bucket=bucket_name)
        if versioning.get("Status") != "Enabled":
            print("⚠️ Bucket versioning is not enabled")
        else:
            print("✅ Bucket versioning is enabled")
    except Exception as e:
        print(f"⚠️ Could not check versioning: {e}")

    if security_issues:
        print("❌ Security issues found:")
        for issue in security_issues:
            print(f"  - {issue}")
        return False
    else:
        print("✅ Bucket security configuration is good")
        return True


def get_bucket_info(bucket_name):
    """Get bucket information and costs."""
    s3 = boto3.client("s3")

    try:
        # Get bucket size and object count
        response = s3.list_objects_v2(Bucket=bucket_name, MaxKeys=1000)

        total_size = 0
        object_count = 0

        for obj in response.get("Contents", []):
            total_size += obj["Size"]
            object_count += 1

        # Convert to human readable
        size_gb = total_size / (1024**3)

        print(f"📊 Bucket {bucket_name} info:")
        print(f"  - Objects: {object_count}")
        print(f"  - Size: {size_gb:.2f} GB")

        return {"object_count": object_count, "size_gb": size_gb}

    except Exception as e:
        print(f"❌ Failed to get bucket info: {e}")
        return None


def main():
    """Main function."""
    bucket_name = "acd-monitor-snapshots"

    print(f"🔧 Applying S3 lifecycle rules to {bucket_name}...")

    # Apply lifecycle rules
    if not apply_lifecycle_rules(bucket_name):
        sys.exit(1)

    # Verify security
    if not verify_bucket_security(bucket_name):
        print("⚠️ Security issues found - please review")

    # Get bucket info
    bucket_info = get_bucket_info(bucket_name)

    print("\n✅ S3 lifecycle configuration complete!")
    print("📋 Applied rules:")
    print("  - Snapshots: 45d → IA, 60d → Glacier, 90d → Deep Archive, 365d → Delete")
    print("  - Derived: 30d → IA, 180d → Delete")
    print("  - Multipart cleanup: 7d")

    if bucket_info:
        print(
            f"📊 Current usage: {bucket_info['object_count']} objects, {bucket_info['size_gb']:.2f} GB"
        )

    return True


if __name__ == "__main__":
    main()
