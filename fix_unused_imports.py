#!/usr/bin/env python3
"""
Script to fix remaining unused imports by commenting them out.
"""
import os
import re
import glob


def fix_unused_imports(filepath):
    """Comment out unused imports in a single file."""
    with open(filepath, "r") as f:
        content = f.read()

    original_content = content

    # List of specific unused imports to comment out
    unused_imports = [
        "from unittest.mock import patch, MagicMock",
        "from unittest.mock import MagicMock",
        "from unittest.mock import Mock",
        "from typing import Dict",
        "from typing import Any",
        "from typing import List",
        "from typing import Tuple",
        "from acd.data.quality_profiles import QualityProfileManager",
        "from acd.evidence.timestamping import TSAClient",
        "from acd.validation.lead_lag import LeadLagValidator",
        "from acd.validation.mirroring import MirroringValidator",
        "from acd.validation.hmm import HMMValidator",
        "from acd.validation.infoflow import InfoFlowValidator",
        "from acd.vmm.adaptive_thresholds import DEFAULT_PROFILES",
    ]

    for unused in unused_imports:
        if unused in content:
            content = content.replace(unused, f"# {unused}  # noqa: F401")

    if content != original_content:
        with open(filepath, "w") as f:
            f.write(content)
        print(f"Fixed unused imports in: {filepath}")
        return True
    return False


def main():
    """Fix unused imports in all test files."""
    test_files = glob.glob("tests/**/*.py", recursive=True)

    fixed_count = 0
    for filepath in test_files:
        if fix_unused_imports(filepath):
            fixed_count += 1

    print(f"Fixed unused imports in {fixed_count} files")


if __name__ == "__main__":
    main()
