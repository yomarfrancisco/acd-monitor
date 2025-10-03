#!/usr/bin/env python3
"""
CI Guard: Zero-Copy Analytics Enforcement
Detects and fails CI if workflows attempt direct S3 parquet downloads.
"""

import os
import sys
import re
from pathlib import Path
from typing import List, Tuple


def scan_for_s3_downloads(directory: str) -> List[Tuple[str, int, str]]:
    """Scan directory for patterns that indicate S3 parquet downloads."""
    violations = []

    # Patterns that indicate direct S3 parquet access
    forbidden_patterns = [
        r'boto3\.client\([\'"]s3[\'"]\)\.get_object',
        r"s3fs\.open\([^)]*\.parquet",
        r"pyarrow\.parquet\.read_table\([^)]*s3://",
        r"pd\.read_parquet\([^)]*s3://",
        r"s3://[^/]+/[^/]+\.parquet",
        r"\.get_object\([^)]*\.parquet",
        r"\.download_file\([^)]*\.parquet",
        r"\.download_fileobj\([^)]*\.parquet",
        r"pandas\.read_parquet\([^)]*s3://",
        r"\.read_parquet\([^)]*s3://",
    ]

    # Compile patterns
    compiled_patterns = [re.compile(pattern, re.IGNORECASE) for pattern in forbidden_patterns]

    # Scan Python files
    for py_file in Path(directory).rglob("*.py"):
        try:
            with open(py_file, "r", encoding="utf-8") as f:
                lines = f.readlines()

            for line_num, line in enumerate(lines, 1):
                for pattern in compiled_patterns:
                    if pattern.search(line):
                        violations.append((str(py_file), line_num, line.strip()))

        except Exception as e:
            print(f"⚠️ Could not scan {py_file}: {e}")

    return violations


def scan_workflow_files(directory: str) -> List[Tuple[str, int, str]]:
    """Scan GitHub Actions workflow files for S3 download patterns."""
    violations = []

    workflow_patterns = [
        r"aws s3 cp.*\.parquet",
        r"aws s3 sync.*\.parquet",
        r"aws s3api get-object.*\.parquet",
        r"boto3.*get_object.*\.parquet",
        r"s3fs.*\.parquet",
        r"pyarrow.*s3://.*\.parquet",
    ]

    compiled_patterns = [re.compile(pattern, re.IGNORECASE) for pattern in workflow_patterns]

    for yml_file in Path(directory).rglob("*.yml"):
        if ".github/workflows/" in str(yml_file):
            try:
                with open(yml_file, "r", encoding="utf-8") as f:
                    lines = f.readlines()

                for line_num, line in enumerate(lines, 1):
                    for pattern in compiled_patterns:
                        if pattern.search(line):
                            violations.append((str(yml_file), line_num, line.strip()))

            except Exception as e:
                print(f"⚠️ Could not scan {yml_file}: {e}")

    return violations


def check_athena_usage(directory: str) -> bool:
    """Check if Athena-based analytics are being used."""
    athena_indicators = [
        "athena_orchestrate.py",
        "analytics_athena/",
        "zero_copy/",
        "athena:",
        "workgroup:",
    ]

    for indicator in athena_indicators:
        if any(Path(directory).rglob(f"*{indicator}*")):
            return True

    return False


def main():
    """Main CI guard function."""
    print("🛡️ Zero-Copy Analytics CI Guard")
    print("=" * 50)

    # Get repository root
    repo_root = os.getcwd()
    print(f"📁 Scanning: {repo_root}")

    # Scan for violations
    python_violations = scan_for_s3_downloads(repo_root)
    workflow_violations = scan_workflow_files(repo_root)
    all_violations = python_violations + workflow_violations

    # Check for Athena usage
    has_athena = check_athena_usage(repo_root)

    print(f"\n📊 Scan Results:")
    print(f"  Python violations: {len(python_violations)}")
    print(f"  Workflow violations: {len(workflow_violations)}")
    print(f"  Total violations: {len(all_violations)}")
    print(f"  Athena usage detected: {has_athena}")

    if all_violations:
        print(f"\n❌ ZERO-COPY VIOLATIONS DETECTED:")
        print("=" * 50)

        for file_path, line_num, line_content in all_violations:
            print(f"📄 {file_path}:{line_num}")
            print(f"   {line_content}")
            print()

        print("🚫 CI FAILED: Direct S3 parquet downloads detected!")
        print("💡 Use Athena queries instead of local downloads.")
        print("📚 See infra/zero_copy/RUNBOOK.md for guidance.")

        sys.exit(1)

    elif has_athena:
        print(f"\n✅ ZERO-COPY COMPLIANCE VERIFIED")
        print("🎯 Athena-based analytics detected")
        print("📊 No direct S3 parquet downloads found")
        sys.exit(0)

    else:
        print(f"\n⚠️ NO ATHENA USAGE DETECTED")
        print("💡 Consider implementing zero-copy analytics")
        print("📚 See infra/zero_copy/RUNBOOK.md for guidance")
        sys.exit(0)


if __name__ == "__main__":
    main()
