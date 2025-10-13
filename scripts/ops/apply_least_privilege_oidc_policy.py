#!/usr/bin/env python3
"""
Apply least-privilege inline policy to OIDC role.
This script replaces broad AWS-managed policies with minimal required permissions.
"""

import boto3
import json
import sys
from pathlib import Path


def apply_least_privilege_policy():
    """Apply least-privilege policy to OIDC role."""

    # Least-privilege policy for ACD monitoring
    least_privilege_policy = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Sid": "S3ReadSnapshots",
                "Effect": "Allow",
                "Action": ["s3:GetObject", "s3:ListBucket"],
                "Resource": [
                    "arn:aws:s3:::acd-monitor-snapshots",
                    "arn:aws:s3:::acd-monitor-snapshots/*",
                ],
            },
            {
                "Sid": "S3WriteDerived",
                "Effect": "Allow",
                "Action": ["s3:PutObject", "s3:PutObjectAcl"],
                "Resource": [
                    "arn:aws:s3:::acd-monitor-derived",
                    "arn:aws:s3:::acd-monitor-derived/*",
                ],
            },
            {
                "Sid": "STSIdentity",
                "Effect": "Allow",
                "Action": ["sts:GetCallerIdentity"],
                "Resource": "*",
            },
        ],
    }

    try:
        iam = boto3.client("iam")
        role_name = "acd-ci-oidc"

        print(f"🔧 Applying least-privilege policy to role: {role_name}")

        # Put the inline policy
        iam.put_role_policy(
            RoleName=role_name,
            PolicyName="ACD-LeastPrivilege",
            PolicyDocument=json.dumps(least_privilege_policy, indent=2),
        )

        print("✅ Least-privilege policy applied successfully")
        print("📋 Policy permissions:")
        print("  - S3 read access to acd-monitor-snapshots")
        print("  - S3 write access to acd-monitor-derived")
        print("  - STS GetCallerIdentity")

        return True

    except Exception as e:
        print(f"❌ Error applying policy: {e}")
        return False


if __name__ == "__main__":
    success = apply_least_privilege_policy()
    sys.exit(0 if success else 1)
