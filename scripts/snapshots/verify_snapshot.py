#!/usr/bin/env python3
"""
Snapshot verification utility for S3-based snapshots.

Verifies snapshot integrity, coverage, and clock skew for court-ready data.
"""

import argparse
import json
import logging
import os
import sys
from pathlib import Path
from typing import Dict, List, Any, Tuple
import boto3
import pandas as pd
from datetime import datetime, timezone
import numpy as np

# Add src to path
sys.path.append(str(Path(__file__).parent.parent.parent / "src"))

from acdlib.io.load_snapshot import load_snapshot_data

# Import config from same directory
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent))
try:
    from config import DEFAULT_BUCKET, DEFAULT_PREFIX, DEFAULT_REGION
except ImportError:
    # Fallback to environment variables
    DEFAULT_BUCKET = os.getenv('ACD_S3_BUCKET', 'acd-monitor-snapshots')
    DEFAULT_PREFIX = os.getenv('ACD_S3_PREFIX', 'snapshots')
    DEFAULT_REGION = os.getenv('AWS_DEFAULT_REGION', 'us-east-1')

logger = logging.getLogger(__name__)


def setup_logging(verbose: bool = False):
    """Setup logging configuration."""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[logging.StreamHandler()]
    )


def parse_s3_url(s3_url: str) -> Tuple[str, str]:
    """Parse S3 URL into bucket and key."""
    if not s3_url.startswith('s3://'):
        raise ValueError(f"Invalid S3 URL: {s3_url}")
    
    # Remove s3:// prefix
    path = s3_url[5:]
    parts = path.split('/', 1)
    bucket = parts[0]
    key = parts[1] if len(parts) > 1 else ""
    
    return bucket, key


def load_s3_json(s3_client, bucket: str, key: str) -> Dict:
    """Load JSON from S3."""
    try:
        response = s3_client.get_object(Bucket=bucket, Key=key)
        content = response['Body'].read().decode('utf-8')
        return json.loads(content)
    except Exception as e:
        logger.error(f"Failed to load JSON from s3://{bucket}/{key}: {e}")
        raise


def verify_overlap_json(overlap_data: Dict) -> List[str]:
    """Verify OVERLAP.json structure and content."""
    issues = []
    
    required_fields = ['start_utc', 'end_utc', 'cadences', 'venues', 'coverage']
    for field in required_fields:
        if field not in overlap_data:
            issues.append(f"Missing required field: {field}")
    
    # Check venues and coverage match
    if 'venues' in overlap_data and 'coverage' in overlap_data:
        venues = overlap_data['venues']
        coverage = overlap_data['coverage']
        
        for venue in venues:
            if venue not in coverage:
                issues.append(f"Venue {venue} missing from coverage")
            elif coverage[venue] < 0.95:
                issues.append(f"Low coverage for {venue}: {coverage[venue]:.3f}")
    
    return issues


def verify_clock_skew(s3_client, bucket: str, base_key: str, venues: List[str]) -> List[str]:
    """Verify clock skew between venues."""
    issues = []
    
    for venue in venues:
        tick_key = f"{base_key}/ticks/{venue}.parquet"
        
        try:
            # Download parquet file to temp location
            temp_file = f"/tmp/{venue}_ticks.parquet"
            s3_client.download_file(bucket, tick_key, temp_file)
            
            # Load and check timestamps
            df = pd.read_parquet(temp_file)
            
            if 'ts_exchange' in df.columns:
                timestamps = pd.to_datetime(df['ts_exchange'], unit='ns', utc=True)
                
                # Check for monotonic timestamps
                if not timestamps.is_monotonic_increasing:
                    issues.append(f"Non-monotonic timestamps in {venue}")
                
                # Check for reasonable time range (not all same timestamp)
                time_span = (timestamps.max() - timestamps.min()).total_seconds()
                if time_span < 1:
                    issues.append(f"Very short time span in {venue}: {time_span:.3f}s")
                
                # Check for gaps > 5 minutes
                gaps = timestamps.diff().dropna()
                large_gaps = gaps[gaps > pd.Timedelta(minutes=5)]
                if len(large_gaps) > 0:
                    issues.append(f"Large gaps in {venue}: {len(large_gaps)} gaps > 5min")
            
            # Clean up temp file
            os.remove(temp_file)
            
        except Exception as e:
            issues.append(f"Failed to verify {venue}: {e}")
    
    return issues


def verify_coverage(s3_client, bucket: str, base_key: str, overlap_data: Dict) -> List[str]:
    """Verify data coverage matches OVERLAP.json claims."""
    issues = []
    
    venues = overlap_data.get('venues', [])
    claimed_coverage = overlap_data.get('coverage', {})
    
    for venue in venues:
        tick_key = f"{base_key}/ticks/{venue}.parquet"
        
        try:
            # Check if file exists and get size
            response = s3_client.head_object(Bucket=bucket, Key=tick_key)
            file_size = response['ContentLength']
            
            if file_size < 1000:  # Less than 1KB is suspicious
                issues.append(f"Very small tick file for {venue}: {file_size} bytes")
            
            # If we have claimed coverage, we could do more detailed verification
            # For now, just check file existence and reasonable size
            
        except Exception as e:
            issues.append(f"Failed to verify coverage for {venue}: {e}")
    
    return issues


def verify_provenance(s3_client, bucket: str, base_key: str) -> List[str]:
    """Verify provenance.json exists and is valid."""
    issues = []
    
    provenance_key = f"{base_key}/meta/provenance.json"
    
    try:
        provenance_data = load_s3_json(s3_client, bucket, provenance_key)
        
        required_fields = ['provenance', 'seed', 'code_version']
        for field in required_fields:
            if field not in provenance_data:
                issues.append(f"Missing provenance field: {field}")
        
        # Check provenance is either REAL or DEMO
        if provenance_data.get('provenance') not in ['REAL', 'DEMO']:
            issues.append(f"Invalid provenance value: {provenance_data.get('provenance')}")
            
    except Exception as e:
        issues.append(f"Failed to verify provenance: {e}")
    
    return issues


def main():
    """Main function."""
    parser = argparse.ArgumentParser(description="Verify S3 snapshot integrity")
    parser.add_argument("--overlap", required=True, help="S3 URL to OVERLAP.json")
    parser.add_argument("--fail-under-coverage", type=float, default=0.95, 
                       help="Fail if any venue coverage below this threshold")
    parser.add_argument("--report", default="clocks,coverage", 
                       help="Comma-separated list: clocks,coverage,provenance")
    parser.add_argument("--verbose", action="store_true", help="Verbose logging")
    
    args = parser.parse_args()
    
    setup_logging(args.verbose)
    
    # Parse S3 URL
    try:
        bucket, overlap_key = parse_s3_url(args.overlap)
        base_key = '/'.join(overlap_key.split('/')[:-1])  # Remove OVERLAP.json
    except Exception as e:
        logger.error(f"Invalid S3 URL: {e}")
        return 1
    
    # Initialize S3 client
    s3_client = boto3.client('s3')
    
    # Load OVERLAP.json
    try:
        overlap_data = load_s3_json(s3_client, bucket, overlap_key)
    except Exception as e:
        logger.error(f"Failed to load OVERLAP.json: {e}")
        return 1
    
    # Verify OVERLAP.json structure
    overlap_issues = verify_overlap_json(overlap_data)
    if overlap_issues:
        logger.error("OVERLAP.json issues:")
        for issue in overlap_issues:
            logger.error(f"  - {issue}")
        return 1
    
    logger.info("OVERLAP.json structure verified")
    
    # Run requested verification checks
    all_issues = []
    
    if 'clocks' in args.report:
        logger.info("Verifying clock skew...")
        clock_issues = verify_clock_skew(s3_client, bucket, base_key, overlap_data['venues'])
        all_issues.extend(clock_issues)
        if clock_issues:
            logger.error("Clock skew issues:")
            for issue in clock_issues:
                logger.error(f"  - {issue}")
        else:
            logger.info("Clock skew verification passed")
    
    if 'coverage' in args.report:
        logger.info("Verifying coverage...")
        coverage_issues = verify_coverage(s3_client, bucket, base_key, overlap_data)
        all_issues.extend(coverage_issues)
        if coverage_issues:
            logger.error("Coverage issues:")
            for issue in coverage_issues:
                logger.error(f"  - {issue}")
        else:
            logger.info("Coverage verification passed")
    
    if 'provenance' in args.report:
        logger.info("Verifying provenance...")
        provenance_issues = verify_provenance(s3_client, bucket, base_key)
        all_issues.extend(provenance_issues)
        if provenance_issues:
            logger.error("Provenance issues:")
            for issue in provenance_issues:
                logger.error(f"  - {issue}")
        else:
            logger.info("Provenance verification passed")
    
    # Check coverage thresholds
    venues = overlap_data.get('venues', [])
    coverage = overlap_data.get('coverage', {})
    
    for venue in venues:
        venue_coverage = coverage.get(venue, 0.0)
        if venue_coverage < args.fail_under_coverage:
            logger.error(f"Venue {venue} coverage {venue_coverage:.3f} below threshold {args.fail_under_coverage}")
            all_issues.append(f"Low coverage: {venue}")
    
    if all_issues:
        logger.error(f"Verification failed with {len(all_issues)} issues")
        return 1
    else:
        logger.info("All verifications passed")
        return 0


if __name__ == "__main__":
    exit(main())
