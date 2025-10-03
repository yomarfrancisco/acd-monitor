#!/usr/bin/env python3
"""
CI Guard: Check that workflows using aws-actions/configure-aws-credentials
have the required permissions block.
"""

import os
import sys
from pathlib import Path

import yaml


def check_workflow_permissions(workflow_path):
    """Check if workflow has required OIDC permissions."""
    try:
        with open(workflow_path, "r") as f:
            workflow = yaml.safe_load(f)

        # Check if workflow uses aws-actions/configure-aws-credentials
        uses_aws_creds = False
        if "jobs" in workflow:
            for job_name, job in workflow["jobs"].items():
                if "steps" in job:
                    for step in job["steps"]:
                        if isinstance(step, dict) and "uses" in step:
                            if "aws-actions/configure-aws-credentials" in step["uses"]:
                                uses_aws_creds = True
                                break

        if not uses_aws_creds:
            return True, "No AWS credentials usage"

        # Check for permissions block
        if "permissions" not in workflow:
            return False, f"Missing permissions block in {workflow_path}"

        permissions = workflow["permissions"]
        if not isinstance(permissions, dict):
            return False, f"Invalid permissions format in {workflow_path}"

        if "id-token" not in permissions or permissions["id-token"] != "write":
            return False, f"Missing 'id-token: write' permission in {workflow_path}"

        if "contents" not in permissions or permissions["contents"] != "read":
            return False, f"Missing 'contents: read' permission in {workflow_path}"

        return True, f"✅ OIDC permissions correct in {workflow_path}"

    except Exception as e:
        return False, f"Error parsing {workflow_path}: {e}"


def main():
    """Check all workflows for OIDC permissions."""
    workflows_dir = Path(".github/workflows")
    if not workflows_dir.exists():
        print("❌ No .github/workflows directory found")
        sys.exit(1)

    failed_checks = []

    for workflow_file in workflows_dir.glob("*.yml"):
        is_valid, message = check_workflow_permissions(workflow_file)
        print(message)

        if not is_valid:
            failed_checks.append(str(workflow_file))

    if failed_checks:
        print(f"\n❌ {len(failed_checks)} workflows failed OIDC permissions check:")
        for workflow in failed_checks:
            print(f"  - {workflow}")
        print("\nRequired permissions block:")
        print("permissions:")
        print("  id-token: write")
        print("  contents: read")
        sys.exit(1)

    print(f"\n✅ All workflows have correct OIDC permissions")
    sys.exit(0)


if __name__ == "__main__":
    main()
