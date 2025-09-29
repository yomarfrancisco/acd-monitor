#!/usr/bin/env python3
"""
S3 Lifecycle Configuration for Continuous Operations

This script configures S3 lifecycle policies for cost management and data retention.
"""

import argparse
import json
import logging
import sys
from typing import Dict

import boto3

logger = logging.getLogger(__name__)

def setup_logging(verbose: bool = False):
    """Setup logging configuration."""
    level = logging.INFO if verbose else logging.WARNING
    logging.basicConfig(level=level, format='%(asctime)s - %(levelname)s - %(message)s')

def create_lifecycle_policy(bucket: str, prefix: str) -> Dict:
    """Create S3 lifecycle policy for cost management."""
    lifecycle_policy = {
        "Rules": [
            {
                "ID": "acd-monitor-raw-ticks-lifecycle",
                "Status": "Enabled",
                "Filter": {
                    "Prefix": f"{prefix}/"
                },
                "Transitions": [
                    {
                        "Days": 30,
                        "StorageClass": "STANDARD_IA"
                    },
                    {
                        "Days": 60,
                        "StorageClass": "GLACIER"
                    }
                ],
                "Expiration": {
                    "Days": 90
                }
            }
        ]
    }
    
    return lifecycle_policy

def configure_s3_lifecycle(bucket: str, prefix: str) -> bool:
    """Configure S3 lifecycle policy for the bucket."""
    try:
        s3_client = boto3.client('s3')
        
        # Create lifecycle policy
        lifecycle_policy = create_lifecycle_policy(bucket, prefix)
        
        # Apply lifecycle policy
        s3_client.put_bucket_lifecycle_configuration(
            Bucket=bucket,
            LifecycleConfiguration=lifecycle_policy
        )
        
        logger.info(f"Successfully configured lifecycle policy for bucket {bucket}")
        return True
        
    except Exception as e:
        logger.error(f"Failed to configure lifecycle policy: {e}")
        return False

def estimate_daily_costs(bucket: str, prefix: str) -> Dict:
    """Estimate daily storage costs."""
    try:
        s3_client = boto3.client('s3')
        
        # List objects in the bucket
        response = s3_client.list_objects_v2(
            Bucket=bucket,
            Prefix=prefix
        )
        
        total_size = 0
        object_count = 0
        
        for obj in response.get('Contents', []):
            total_size += obj['Size']
            object_count += 1
        
        # Cost estimates (as of 2024)
        # Standard: $0.023 per GB per month
        # Standard-IA: $0.0125 per GB per month
        # Glacier: $0.004 per GB per month
        
        gb_size = total_size / (1024 ** 3)
        monthly_cost_standard = gb_size * 0.023
        daily_cost_standard = monthly_cost_standard / 30
        
        return {
            "total_size_gb": round(gb_size, 2),
            "object_count": object_count,
            "estimated_daily_cost_standard": round(daily_cost_standard, 2),
            "estimated_monthly_cost_standard": round(monthly_cost_standard, 2)
        }
        
    except Exception as e:
        logger.error(f"Failed to estimate costs: {e}")
        return {"error": str(e)}

def main():
    """Main function for S3 lifecycle configuration."""
    parser = argparse.ArgumentParser(description="Configure S3 lifecycle policy")
    parser.add_argument("--bucket", default="acd-monitor-snapshots", help="S3 bucket")
    parser.add_argument("--prefix", default="snapshots", help="S3 prefix")
    parser.add_argument("--estimate-costs", action="store_true", help="Estimate daily costs")
    parser.add_argument("--verbose", action="store_true", help="Verbose logging")
    
    args = parser.parse_args()
    
    setup_logging(args.verbose)
    
    try:
        # Configure lifecycle policy
        success = configure_s3_lifecycle(args.bucket, args.prefix)
        
        if not success:
            logger.error("Failed to configure lifecycle policy")
            sys.exit(1)
        
        # Estimate costs if requested
        if args.estimate_costs:
            costs = estimate_daily_costs(args.bucket, args.prefix)
            if "error" in costs:
                logger.error(f"Cost estimation failed: {costs['error']}")
            else:
                print(f"Cost Estimation:")
                print(f"  Total size: {costs['total_size_gb']} GB")
                print(f"  Object count: {costs['object_count']}")
                print(f"  Estimated daily cost: ${costs['estimated_daily_cost_standard']}")
                print(f"  Estimated monthly cost: ${costs['estimated_monthly_cost_standard']}")
        
        logger.info("S3 lifecycle configuration completed successfully")
        sys.exit(0)
        
    except Exception as e:
        logger.error(f"S3 lifecycle configuration failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
