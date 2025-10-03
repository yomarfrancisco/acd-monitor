#!/usr/bin/env python3
"""
ICP-VMM Evidence Integrity Test

Asserts all 9 blocks exist and none are zero-byte.
"""

import sys
from pathlib import Path
from typing import List, Dict


def check_evidence_integrity(output_dir: str) -> bool:
    """Check that all evidence files exist and are not empty."""
    required_files = [
        "MANIFEST.json",
        "EVIDENCE.md",
        "LIMITATIONS.md",
        "SUMMARY.md",
        "REPRO.md",
        "vmm_results.json",
        "icp_tests.json",
    ]

    output_path = Path(output_dir)
    missing_files = []
    empty_files = []

    for file_name in required_files:
        file_path = output_path / file_name

        if not file_path.exists():
            missing_files.append(file_name)
        elif file_path.stat().st_size == 0:
            empty_files.append(file_name)

    if missing_files:
        print(f"❌ Missing files: {missing_files}")
        return False

    if empty_files:
        print(f"❌ Empty files: {empty_files}")
        return False

    # Check EVIDENCE.md has all 9 blocks
    evidence_path = output_path / "EVIDENCE.md"
    with open(evidence_path, "r") as f:
        evidence_content = f.read()

    required_blocks = [
        "## 1. Window Metadata",
        "## 2. Status",
        "## 3. Preconditions",
        "## 4. VMM Analysis",
        "## 5. Information Shares",
        "## 6. ICP Invariance",
        "## 7. Provisional Banner",
        "## 8. Provenance",
        "## 9. Reproduction",
    ]

    missing_blocks = []
    for block in required_blocks:
        if block not in evidence_content:
            missing_blocks.append(block)

    if missing_blocks:
        print(f"❌ Missing evidence blocks: {missing_blocks}")
        return False

    # Check for power banner
    if "PROVISIONAL" not in evidence_content or "integration testing only" not in evidence_content:
        print("❌ Missing power banner in EVIDENCE.md")
        return False

    print("✅ Evidence integrity test passed")
    return True


def main():
    """Main test function."""
    if len(sys.argv) != 2:
        print("Usage: python evidence_integrity_test.py <output_dir>")
        sys.exit(1)

    output_dir = sys.argv[1]

    if not Path(output_dir).exists():
        print(f"❌ Output directory not found: {output_dir}")
        sys.exit(1)

    if check_evidence_integrity(output_dir):
        sys.exit(0)
    else:
        sys.exit(1)


if __name__ == "__main__":
    main()
