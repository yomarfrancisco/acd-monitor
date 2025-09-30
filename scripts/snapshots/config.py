#!/usr/bin/env python3
"""
S3 snapshot configuration defaults.
"""

import os

# S3 Configuration
ACD_S3_BUCKET = os.getenv("ACD_S3_BUCKET", "acd-monitor-snapshots")
ACD_S3_PREFIX = os.getenv("ACD_S3_PREFIX", "snapshots")
AWS_DEFAULT_REGION = os.getenv("AWS_DEFAULT_REGION", "us-east-1")

# Default paths
DEFAULT_BUCKET = ACD_S3_BUCKET
DEFAULT_PREFIX = ACD_S3_PREFIX
DEFAULT_REGION = AWS_DEFAULT_REGION
