#!/usr/bin/env python3
"""
CI Audit Environment Surface Script
"""

import json
import os
import platform
import sys


def main():
    env = {
        "platform": platform.platform(),
        "python": platform.python_version(),
        "has_AWS_ACCESS_KEY_ID": "AWS_ACCESS_KEY_ID" in os.environ,
        "has_AWS_SECRET_ACCESS_KEY": "AWS_SECRET_ACCESS_KEY" in os.environ,
        "AWS_REGION": os.environ.get("AWS_REGION") or os.environ.get("AWS_DEFAULT_REGION"),
    }

    print(json.dumps(env, indent=2))

    if len(sys.argv) > 1:
        output_file = sys.argv[1]
        with open(output_file, "w") as f:
            json.dump(env, f, indent=2)


if __name__ == "__main__":
    main()
