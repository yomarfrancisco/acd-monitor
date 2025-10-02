#!/usr/bin/env python3
"""
ACD Phase PROV - Provenance & Synthetic-Detection

Forensic provenance audit for each venue using objective evidence only.
"""

import argparse
import json
import logging
import sys
import tempfile
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Dict, List, Any, Tuple, Optional

import boto3
import pandas as pd
import numpy as np

def setup_logging(verbose: bool = False):
    """Setup logging configuration."""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler("acd_phase_prov_provenance_audit.log"),
        ],
    )

def get_s3_object_content(s3_client, bucket: str, key: str) -> Optional[bytes]:
    """Helper to get content from S3, returns None if key not found."""
    try:
        response = s3_client.get_object(Bucket=bucket, Key=key)
        return response['Body'].read()
    except s3_client.exceptions.NoSuchKey:
        return None
    except Exception as e:
        logging.getLogger(__name__).error(f"Error getting S3 object {key}: {e}")
        return None

def get_s3_object_text(s3_client, bucket: str, key: str) -> Optional[str]:
    """Helper to get text content from S3, returns None if key not found."""
    try:
        response = s3_client.get_object(Bucket=bucket, Key=key)
        return response['Body'].read().decode('utf-8')
    except s3_client.exceptions.NoSuchKey:
        return None
    except Exception as e:
        logging.getLogger(__name__).error(f"Error getting S3 object {key}: {e}")
        return None

def discover_available_data(s3_client, bucket: str) -> Dict[str, Any]:
    """Discover available dates and venues in S3."""
    logger = logging.getLogger(__name__)
    
    discovery = {
        "raw_probes": {},
        "backfill": {},
        "earliest_date": None,
        "latest_date": None
    }
    
    # Discover raw_probes data
    logger.info("Discovering raw_probes data...")
    try:
        response = s3_client.list_objects_v2(Bucket=bucket, Prefix="raw_probes/", Delimiter='/')
        if 'CommonPrefixes' in response:
            for prefix in response['CommonPrefixes']:
                date_str = prefix['Prefix'].split('/')[1]
                if date_str and len(date_str) == 8:  # YYYYMMDD format
                    discovery["raw_probes"][date_str] = {}
                    
                    # List venues for this date
                    venue_response = s3_client.list_objects_v2(
                        Bucket=bucket, 
                        Prefix=f"raw_probes/{date_str}/", 
                        Delimiter='/'
                    )
                    if 'CommonPrefixes' in venue_response:
                        for venue_prefix in venue_response['CommonPrefixes']:
                            venue = venue_prefix['Prefix'].split('=')[-1].strip('/')
                            if venue:
                                discovery["raw_probes"][date_str][venue] = []
                                
                                # List slices for this venue
                                slice_response = s3_client.list_objects_v2(
                                    Bucket=bucket,
                                    Prefix=f"raw_probes/{date_str}/venue={venue}/",
                                    Delimiter='/'
                                )
                                if 'CommonPrefixes' in slice_response:
                                    for slice_prefix in slice_response['CommonPrefixes']:
                                        slice_name = slice_prefix['Prefix'].split('=')[-1].strip('/')
                                        if slice_name:
                                            discovery["raw_probes"][date_str][venue].append(slice_name)
    except Exception as e:
        logger.error(f"Error discovering raw_probes: {e}")
    
    # Discover backfill data
    logger.info("Discovering backfill data...")
    try:
        response = s3_client.list_objects_v2(Bucket=bucket, Prefix="backfill/", Delimiter='/')
        if 'CommonPrefixes' in response:
            for prefix in response['CommonPrefixes']:
                venue = prefix['Prefix'].split('/')[1]
                if venue:
                    discovery["backfill"][venue] = {}
                    
                    # List dates for this venue
                    date_response = s3_client.list_objects_v2(
                        Bucket=bucket,
                        Prefix=f"backfill/{venue}/",
                        Delimiter='/'
                    )
                    if 'CommonPrefixes' in date_response:
                        for date_prefix in date_response['CommonPrefixes']:
                            date_str = date_prefix['Prefix'].split('/')[2]
                            if date_str and len(date_str) == 8:
                                discovery["backfill"][venue][date_str] = []
                                
                                # List windows for this venue/date
                                window_response = s3_client.list_objects_v2(
                                    Bucket=bucket,
                                    Prefix=f"backfill/{venue}/{date_str}/",
                                    Delimiter='/'
                                )
                                if 'CommonPrefixes' in window_response:
                                    for window_prefix in window_response['CommonPrefixes']:
                                        window_name = window_prefix['Prefix'].split('/')[3]
                                        if window_name:
                                            discovery["backfill"][venue][date_str].append(window_name)
    except Exception as e:
        logger.error(f"Error discovering backfill: {e}")
    
    # Find earliest and latest dates
    all_dates = set()
    for date_str in discovery["raw_probes"].keys():
        all_dates.add(date_str)
    for venue_data in discovery["backfill"].values():
        for date_str in venue_data.keys():
            all_dates.add(date_str)
    
    if all_dates:
        discovery["earliest_date"] = min(all_dates)
        discovery["latest_date"] = max(all_dates)
    
    logger.info(f"Discovered data from {discovery['earliest_date']} to {discovery['latest_date']}")
    return discovery

def get_window_metadata(s3_client, bucket: str, data_type: str, date: str, venue: str, window: str) -> Dict[str, Any]:
    """Get metadata for a specific window."""
    logger = logging.getLogger(__name__)
    
    metadata = {
        "data_type": data_type,
        "date": date,
        "venue": venue,
        "window": window,
        "s3_key": None,
        "file_size": 0,
        "row_count": 0,
        "first_timestamp": None,
        "last_timestamp": None,
        "manifest": None,
        "provenance_flags": []
    }
    
    if data_type == "raw_probes":
        s3_key = f"raw_probes/{date}/venue={venue}/slice={window}/sample.parquet"
        manifest_key = f"raw_probes/{date}/venue={venue}/slice={window}/probe_manifest.json"
    else:  # backfill
        s3_key = f"backfill/{venue}/{date}/{window}/part-0000.parquet"
        manifest_key = None
    
    # Get file size
    try:
        response = s3_client.head_object(Bucket=bucket, Key=s3_key)
        metadata["file_size"] = response['ContentLength']
        metadata["s3_key"] = s3_key
    except Exception as e:
        logger.warning(f"Could not get metadata for {s3_key}: {e}")
        return metadata
    
    # Try to load and analyze data
    try:
        parquet_content = get_s3_object_content(s3_client, bucket, s3_key)
        if parquet_content:
            with tempfile.NamedTemporaryFile(suffix='.parquet', delete=False) as tmp_file:
                tmp_file.write(parquet_content)
                tmp_file.flush()
                df = pd.read_parquet(tmp_file.name)
                Path(tmp_file.name).unlink()
            
            metadata["row_count"] = len(df)
            
            if 'timestamp' in df.columns:
                df['timestamp'] = pd.to_datetime(df['timestamp'], utc=True)
                metadata["first_timestamp"] = df['timestamp'].min().isoformat()
                metadata["last_timestamp"] = df['timestamp'].max().isoformat()
    except Exception as e:
        logger.warning(f"Could not analyze data for {s3_key}: {e}")
    
    # Load manifest if available
    if manifest_key:
        try:
            manifest_content = get_s3_object_text(s3_client, bucket, manifest_key)
            if manifest_content:
                metadata["manifest"] = json.loads(manifest_content)
        except Exception as e:
            logger.warning(f"Could not load manifest for {manifest_key}: {e}")
    
    return metadata

def compute_temporal_integrity(df: pd.DataFrame) -> Dict[str, Any]:
    """Compute temporal integrity metrics."""
    if df.empty or 'timestamp' not in df.columns:
        return {"error": "No timestamp data"}
    
    df['timestamp'] = pd.to_datetime(df['timestamp'], utc=True)
    df = df.sort_values('timestamp')
    
    # Time deltas
    time_deltas = df['timestamp'].diff().dropna()
    time_deltas_seconds = time_deltas.dt.total_seconds()
    
    # Monotonicity failures
    monotonicity_failures = (time_deltas_seconds <= 0).sum()
    monotonicity_failure_ratio = monotonicity_failures / len(time_deltas_seconds)
    
    # Inter-arrival stats
    median_dt = time_deltas_seconds.median()
    mean_dt = time_deltas_seconds.mean()
    std_dt = time_deltas_seconds.std()
    cv_dt = std_dt / mean_dt if mean_dt > 0 else 0
    
    # Regular interval detection
    mode_interval = time_deltas_seconds.mode().iloc[0] if len(time_deltas_seconds.mode()) > 0 else 0
    within_5pct = ((time_deltas_seconds >= mode_interval * 0.95) & 
                   (time_deltas_seconds <= mode_interval * 1.05)).sum()
    regular_interval_ratio = within_5pct / len(time_deltas_seconds)
    regular_interval_flag = (cv_dt < 0.05) and (regular_interval_ratio >= 0.8)
    
    # Unique timestamp ratio
    unique_timestamp_ratio = df['timestamp'].nunique() / len(df)
    
    return {
        "monotonicity_failures": int(monotonicity_failures),
        "monotonicity_failure_ratio": float(monotonicity_failure_ratio),
        "median_dt": float(median_dt),
        "mean_dt": float(mean_dt),
        "std_dt": float(std_dt),
        "cv_dt": float(cv_dt),
        "regular_interval_flag": bool(regular_interval_flag),
        "unique_timestamp_ratio": float(unique_timestamp_ratio)
    }

def compute_price_sanity(df: pd.DataFrame) -> Dict[str, Any]:
    """Compute price sanity metrics."""
    if df.empty or 'price' not in df.columns:
        return {"error": "No price data"}
    
    prices = pd.to_numeric(df['price'], errors='coerce').dropna()
    
    if len(prices) == 0:
        return {"error": "No valid price data"}
    
    last_price = float(prices.iloc[-1])
    min_price = float(prices.min())
    max_price = float(prices.max())
    mean_price = float(prices.mean())
    std_price = float(prices.std())
    
    # Degenerate flag
    degenerate_flag = (std_price < 0.10) and (len(prices) >= 100)
    
    # Staleness (consecutive identical prices)
    price_changes = prices.diff().dropna()
    identical_prices = (price_changes == 0).sum()
    staleness_ratio = identical_prices / len(price_changes) if len(price_changes) > 0 else 0
    
    return {
        "last_price": last_price,
        "min_price": min_price,
        "max_price": max_price,
        "mean_price": mean_price,
        "std_price": std_price,
        "degenerate_flag": bool(degenerate_flag),
        "staleness_ratio": float(staleness_ratio)
    }

def compute_duplicates(df: pd.DataFrame) -> Dict[str, Any]:
    """Compute duplicate metrics."""
    if df.empty:
        return {"error": "No data"}
    
    # Exact duplicate ratio
    exact_duplicates = df.duplicated().sum()
    exact_duplicate_ratio = exact_duplicates / len(df)
    
    # Keyed duplicates using (timestamp_rounded_us, price, volume)
    if all(col in df.columns for col in ['timestamp', 'price', 'volume']):
        df['timestamp_rounded_us'] = pd.to_datetime(df['timestamp'], utc=True).dt.round('us')
        keyed_duplicates = df.duplicated(subset=['timestamp_rounded_us', 'price', 'volume']).sum()
        keyed_duplicate_ratio = keyed_duplicates / len(df)
    else:
        keyed_duplicate_ratio = 0
    
    return {
        "exact_duplicate_ratio": float(exact_duplicate_ratio),
        "keyed_duplicate_ratio": float(keyed_duplicate_ratio)
    }

def compute_volume_sanity(df: pd.DataFrame) -> Dict[str, Any]:
    """Compute volume sanity metrics."""
    if df.empty or 'volume' not in df.columns:
        return {"error": "No volume data"}
    
    volumes = pd.to_numeric(df['volume'], errors='coerce').dropna()
    
    if len(volumes) == 0:
        return {"error": "No valid volume data"}
    
    total_volume = float(volumes.sum())
    mean_volume = float(volumes.mean())
    median_volume = float(volumes.median())
    zero_volume_ratio = (volumes == 0).sum() / len(volumes)
    
    return {
        "total_volume": total_volume,
        "mean_volume": mean_volume,
        "median_volume": median_volume,
        "zero_volume_ratio": float(zero_volume_ratio)
    }

def check_provenance_evidence(metadata: Dict[str, Any]) -> Dict[str, Any]:
    """Check for provenance evidence in logs and manifests."""
    evidence = {
        "log_evidence": False,
        "manifest_evidence": False,
        "api_traces": False,
        "websocket_traces": False,
        "evidence_snippets": []
    }
    
    # Check manifest for provenance flags
    if metadata.get("manifest"):
        manifest = metadata["manifest"]
        
        # Look for provenance indicators
        if "provenance" in manifest:
            evidence["manifest_evidence"] = True
            evidence["evidence_snippets"].append(f"Manifest provenance: {manifest['provenance']}")
        
        if "data_source" in manifest:
            if manifest["data_source"] == "real":
                evidence["log_evidence"] = True
                evidence["evidence_snippets"].append(f"Data source: {manifest['data_source']}")
        
        # Look for API/WebSocket indicators
        manifest_str = json.dumps(manifest, default=str).lower()
        if "api" in manifest_str or "http" in manifest_str:
            evidence["api_traces"] = True
            evidence["evidence_snippets"].append("API traces found in manifest")
        
        if "websocket" in manifest_str or "ws" in manifest_str:
            evidence["websocket_traces"] = True
            evidence["evidence_snippets"].append("WebSocket traces found in manifest")
    
    return evidence

def classify_window(metrics: Dict[str, Any], evidence: Dict[str, Any]) -> str:
    """Classify window based on deterministic rules."""
    
    # Extract key metrics
    temporal = metrics.get("temporal_integrity", {})
    price = metrics.get("price_sanity", {})
    duplicates = metrics.get("duplicates", {})
    
    # Check for errors
    if any("error" in v for v in [temporal, price, duplicates]):
        return "CORRUPTED"
    
    # SYNTHETIC: Regular-interval flag TRUE and price std < $0.10 and/or staleness ≥ 90%
    if (temporal.get("regular_interval_flag", False) and 
        price.get("degenerate_flag", False) and 
        price.get("staleness_ratio", 0) >= 0.9):
        return "SYNTHETIC"
    
    # LIKELY_SYNTHETIC: Regular-interval TRUE or degenerate std < $0.10 with duplicate ratio ≥ 30% and no log evidence
    if ((temporal.get("regular_interval_flag", False) or price.get("degenerate_flag", False)) and
        duplicates.get("exact_duplicate_ratio", 0) >= 0.3 and
        not evidence.get("log_evidence", False)):
        return "LIKELY_SYNTHETIC"
    
    # CORRUPTED: Monotonicity failures ≥ 10% or exact duplicates ≥ 50%
    if (temporal.get("monotonicity_failure_ratio", 0) >= 0.1 or
        duplicates.get("exact_duplicate_ratio", 0) >= 0.5):
        return "CORRUPTED"
    
    # REAL: CV(Δt) ≥ 0.10 and price std ≥ $0.10 and duplicates < 30% and monotonicity failures < 1%, with log evidence, plus staleness < 50% and unique-timestamp ratio ≥ 0.7
    if (temporal.get("cv_dt", 0) >= 0.10 and
        price.get("std_price", 0) >= 0.10 and
        duplicates.get("exact_duplicate_ratio", 0) < 0.3 and
        temporal.get("monotonicity_failure_ratio", 0) < 0.01 and
        evidence.get("log_evidence", False) and
        price.get("staleness_ratio", 0) < 0.5 and
        temporal.get("unique_timestamp_ratio", 0) >= 0.7):
        return "REAL"
    
    # LIKELY_REAL: Same as REAL but without staleness and unique-timestamp requirements
    if (temporal.get("cv_dt", 0) >= 0.10 and
        price.get("std_price", 0) >= 0.10 and
        duplicates.get("exact_duplicate_ratio", 0) < 0.3 and
        temporal.get("monotonicity_failure_ratio", 0) < 0.01 and
        evidence.get("log_evidence", False)):
        return "LIKELY_REAL"
    
    # Default to INDETERMINATE
    return "INDETERMINATE"

def main():
    """Main Phase PROV function."""
    parser = argparse.ArgumentParser(description='ACD Phase PROV - Provenance & Synthetic-Detection')
    parser.add_argument('--verbose', action='store_true', help='Verbose logging')
    parser.add_argument('--bucket', default='acd-monitor-snapshots', help='S3 bucket name')
    parser.add_argument('--date', default='20251002', help='Date to process (YYYYMMDD)')
    
    args = parser.parse_args()
    setup_logging(args.verbose)
    logger = logging.getLogger(__name__)
    
    # Initialize S3 client
    s3_client = boto3.client('s3')
    
    print("\n" + "="*80)
    print("🔍 ACD PHASE PROV - PROVENANCE & SYNTHETIC-DETECTION")
    print("="*80)
    
    print(f"📅 Processing date: {args.date}")
    
    # Discover available data
    print(f"\n🔍 Discovering available data...")
    try:
        discovery = discover_available_data(s3_client, args.bucket)
        
        print(f"✅ Discovery completed")
        print(f"   Raw probes: {len(discovery['raw_probes'])} dates")
        print(f"   Backfill: {len(discovery['backfill'])} venues")
        print(f"   Date range: {discovery['earliest_date']} to {discovery['latest_date']}")
            
    except Exception as e:
        print(f"❌ Error during discovery: {e}")
        sys.exit(1)
    
    # Build inventory
    print(f"\n📋 Building inventory...")
    
    inventory = {
        "discovery": discovery,
        "windows": [],
        "summary_timestamp": datetime.now(timezone.utc).isoformat()
    }
    
    # Process raw_probes data
    for date_str, venues in discovery["raw_probes"].items():
        for venue, slices in venues.items():
            for slice_name in slices:
                metadata = get_window_metadata(s3_client, args.bucket, "raw_probes", date_str, venue, slice_name)
                inventory["windows"].append(metadata)
    
    # Process backfill data
    for venue, dates in discovery["backfill"].items():
        for date_str, windows in dates.items():
            for window_name in windows:
                metadata = get_window_metadata(s3_client, args.bucket, "backfill", date_str, venue, window_name)
                inventory["windows"].append(metadata)
    
    print(f"✅ Inventory built: {len(inventory['windows'])} windows")
    
    # Compute metrics for each window
    print(f"\n📊 Computing provenance metrics...")
    
    per_window_metrics = {}
    classifications = {}
    
    for window in inventory["windows"]:
        if not window["s3_key"]:
            continue
        
        venue = window["venue"]
        window_name = window["window"]
        key = f"{venue}_{window_name}"
        
        print(f"   Processing {venue} {window_name}...")
        
        try:
            # Load data
            parquet_content = get_s3_object_content(s3_client, args.bucket, window["s3_key"])
            if not parquet_content:
                print(f"     ❌ Could not load data")
                continue
            
            with tempfile.NamedTemporaryFile(suffix='.parquet', delete=False) as tmp_file:
                tmp_file.write(parquet_content)
                tmp_file.flush()
                df = pd.read_parquet(tmp_file.name)
                Path(tmp_file.name).unlink()
            
            # Compute metrics
            metrics = {
                "temporal_integrity": compute_temporal_integrity(df),
                "price_sanity": compute_price_sanity(df),
                "duplicates": compute_duplicates(df),
                "volume_sanity": compute_volume_sanity(df)
            }
            
            # Check provenance evidence
            evidence = check_provenance_evidence(window)
            
            # Classify window
            classification = classify_window(metrics, evidence)
            
            per_window_metrics[key] = metrics
            classifications[key] = {
                "classification": classification,
                "evidence": evidence,
                "rule_hits": {
                    "regular_interval": metrics["temporal_integrity"].get("regular_interval_flag", False),
                    "degenerate_price": metrics["price_sanity"].get("degenerate_flag", False),
                    "high_duplicates": metrics["duplicates"].get("exact_duplicate_ratio", 0) >= 0.3,
                    "log_evidence": evidence.get("log_evidence", False)
                }
            }
            
            print(f"     ✅ {classification}")
            
        except Exception as e:
            print(f"     ❌ Error processing {venue} {window_name}: {e}")
            continue
    
    # Find overlap windows
    print(f"\n🔍 Finding overlap windows...")
    
    real_likely_real_windows = []
    for key, classification_data in classifications.items():
        if classification_data["classification"] in ["REAL", "LIKELY_REAL"]:
            real_likely_real_windows.append(key)
    
    overlap_report = {
        "real_likely_real_windows": real_likely_real_windows,
        "overlap_feasibility": len(real_likely_real_windows) >= 3,
        "summary_timestamp": datetime.now(timezone.utc).isoformat()
    }
    
    print(f"✅ Found {len(real_likely_real_windows)} REAL/LIKELY_REAL windows")
    
    # Save all artifacts
    print(f"\n💾 Saving artifacts...")
    
    # Save inventory
    inventory_key = f"analysis/{args.date}/ACD/_prov/inventory.json"
    s3_client.put_object(
        Bucket=args.bucket,
        Key=inventory_key,
        Body=json.dumps(inventory, indent=2),
        ContentType='application/json'
    )
    
    # Save metrics
    metrics_key = f"analysis/{args.date}/ACD/_prov/per_window_metrics.json"
    s3_client.put_object(
        Bucket=args.bucket,
        Key=metrics_key,
        Body=json.dumps(per_window_metrics, indent=2),
        ContentType='application/json'
    )
    
    # Save classifications
    classifications_key = f"analysis/{args.date}/ACD/_prov/classifications.json"
    s3_client.put_object(
        Bucket=args.bucket,
        Key=classifications_key,
        Body=json.dumps(classifications, indent=2),
        ContentType='application/json'
    )
    
    # Save overlap report
    overlap_key = f"analysis/{args.date}/ACD/_prov/overlap_report.json"
    s3_client.put_object(
        Bucket=args.bucket,
        Key=overlap_key,
        Body=json.dumps(overlap_report, indent=2),
        ContentType='application/json'
    )
    
    print(f"💾 Saved artifacts to analysis/{args.date}/ACD/_prov/")
    
    # Final summary
    print(f"\n📊 PHASE PROV SUMMARY")
    print("="*60)
    print(f"Total windows analyzed: {len(per_window_metrics)}")
    print(f"REAL/LIKELY_REAL windows: {len(real_likely_real_windows)}")
    print(f"Overlap feasibility: {'✅ YES' if overlap_report['overlap_feasibility'] else '❌ NO'}")
    
    if overlap_report['overlap_feasibility']:
        print(f"\n✅ READY_FOR_ACD")
        print(f"   Sufficient REAL/LIKELY_REAL windows found")
        print(f"   Ready for ACD analysis")
    else:
        print(f"\n❌ NOT_READY")
        print(f"   Insufficient REAL/LIKELY_REAL windows")
        print(f"   Backfill required")
    
    print(f"\n📁 Generated artifacts:")
    print(f"  Inventory: s3://{args.bucket}/{inventory_key}")
    print(f"  Metrics: s3://{args.bucket}/{metrics_key}")
    print(f"  Classifications: s3://{args.bucket}/{classifications_key}")
    print(f"  Overlap report: s3://{args.bucket}/{overlap_key}")

if __name__ == "__main__":
    main()
