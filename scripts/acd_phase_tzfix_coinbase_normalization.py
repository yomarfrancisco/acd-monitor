#!/usr/bin/env python3
"""
ACD Phase TZ-FIX - Coinbase Timestamp Normalization

Proves/repairs Coinbase timestamps to strict UTC trades time.
No backfill yet - just timestamp normalization and correction.
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
            logging.FileHandler("acd_phase_tzfix_coinbase_normalization.log"),
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

def list_coinbase_slices(s3_client, bucket: str, date: str) -> List[str]:
    """List all available Coinbase slices for a given date."""
    prefix = f"raw_probes/{date}/venue=coinbase/"
    response = s3_client.list_objects_v2(Bucket=bucket, Prefix=prefix, Delimiter='/')
    slices = []
    if 'CommonPrefixes' in response:
        for common_prefix in response['CommonPrefixes']:
            slice_name = common_prefix['Prefix'].split('=')[-1].strip('/')
            if slice_name:
                slices.append(slice_name)
    return sorted(slices)

def analyze_coinbase_timestamps(s3_client, bucket: str, date: str, slice_name: str) -> Dict[str, Any]:
    """Analyze Coinbase timestamps for a single slice."""
    logger = logging.getLogger(__name__)
    
    # Load parquet data
    sample_key = f"raw_probes/{date}/venue=coinbase/slice={slice_name}/sample.parquet"
    parquet_data_content = get_s3_object_content(s3_client, bucket, sample_key)
    if parquet_data_content is None:
        return {"status": "failed", "error": "No parquet data found"}
    
    try:
        with tempfile.NamedTemporaryFile(suffix='.parquet', delete=False) as tmp_file:
            tmp_file.write(parquet_data_content)
            tmp_file.flush()
            df = pd.read_parquet(tmp_file.name)
            Path(tmp_file.name).unlink()
        
        if df.empty:
            return {"status": "failed", "error": "Empty dataframe"}
        
        # Load manifest
        manifest_key = f"raw_probes/{date}/venue=coinbase/slice={slice_name}/probe_manifest.json"
        manifest_content = get_s3_object_text(s3_client, bucket, manifest_key)
        manifest = None
        if manifest_content:
            try:
                manifest = json.loads(manifest_content)
            except json.JSONDecodeError:
                pass
        
        # Analyze timestamp field
        if 'timestamp' not in df.columns:
            return {"status": "failed", "error": "No timestamp column found"}
        
        # Get raw timestamp values
        raw_timestamps = df['timestamp']
        n_rows = len(df)
        
        # Convert to datetime for analysis
        if raw_timestamps.dtype == 'object':
            ts_parsed = pd.to_datetime(raw_timestamps, utc=True)
        else:
            ts_parsed = pd.to_datetime(raw_timestamps, unit='ms', utc=True)
        
        # Basic stats
        ts_min_raw = raw_timestamps.min()
        ts_max_raw = raw_timestamps.max()
        ts_min_utc = ts_parsed.min()
        ts_max_utc = ts_parsed.max()
        duration_seconds = (ts_max_utc - ts_min_utc).total_seconds()
        
        # Check monotonicity
        is_monotonic = ts_parsed.is_monotonic_increasing
        non_monotonic_count = 0
        if not is_monotonic:
            non_monotonic_count = (ts_parsed.diff() < pd.Timedelta(0)).sum()
        
        non_monotonic_ratio = non_monotonic_count / n_rows if n_rows > 0 else 0
        
        # Sample timestamps (first 3 and last 3)
        sample_timestamps = []
        for i in range(min(3, len(df))):
            sample_timestamps.append({
                "index": i,
                "timestamp_raw": str(raw_timestamps.iloc[i]),
                "timestamp_parsed": ts_parsed.iloc[i].isoformat(),
                "price": float(df.iloc[i]['price']) if 'price' in df.columns else None
            })
        
        for i in range(max(0, len(df)-3), len(df)):
            sample_timestamps.append({
                "index": i,
                "timestamp_raw": str(raw_timestamps.iloc[i]),
                "timestamp_parsed": ts_parsed.iloc[i].isoformat(),
                "price": float(df.iloc[i]['price']) if 'price' in df.columns else None
            })
        
        # Identify source field and normalization path
        source_field = "timestamp"  # Default assumption
        normalization_path = "unknown"
        
        if manifest:
            fields_present = manifest.get('fields_present', [])
            if 'time' in fields_present:
                source_field = "time"
            elif 'created_at' in fields_present:
                source_field = "created_at"
            elif 'trade_time' in fields_present:
                source_field = "trade_time"
            
            # Try to determine normalization path from manifest
            if 'timestamp' in fields_present:
                normalization_path = "timestamp field -> UTC (via pd.to_datetime)"
            else:
                normalization_path = "unknown"
        
        # Check for timezone issues
        issues = []
        if not is_monotonic:
            issues.append("Non-monotonic timestamps")
        
        # Check if timestamps look like local time
        time_patterns = []
        for ts in ts_parsed.head(10):
            hour = ts.hour
            if 12 <= hour <= 18:  # Afternoon hours
                time_patterns.append(hour)
        
        if len(set(time_patterns)) > 0 and max(time_patterns) > 12:
            issues.append("Timestamps appear to be in local time (afternoon hours)")
        
        # Check for timezone offset issues
        if hasattr(ts_parsed, 'dt'):
            tz_info = ts_parsed.dt.tz
            if tz_info != timezone.utc and tz_info is not None:
                issues.append(f"Non-UTC timezone detected: {tz_info}")
        
        return {
            "status": "success",
            "slice_name": slice_name,
            "n_rows": n_rows,
            "ts_min_raw": str(ts_min_raw),
            "ts_max_raw": str(ts_max_raw),
            "ts_min_utc": ts_min_utc.isoformat(),
            "ts_max_utc": ts_max_utc.isoformat(),
            "duration_seconds": duration_seconds,
            "is_monotonic": is_monotonic,
            "non_monotonic_count": int(non_monotonic_count),
            "non_monotonic_ratio": float(non_monotonic_ratio),
            "source_field": source_field,
            "normalization_path": normalization_path,
            "sample_timestamps": sample_timestamps,
            "issues": issues,
            "manifest_provenance": manifest.get("provenance", "unknown") if manifest else "unknown"
        }
        
    except Exception as e:
        logger.error(f"Error analyzing Coinbase {slice_name}: {e}")
        return {"status": "failed", "error": str(e)}

def attempt_timestamp_correction(df: pd.DataFrame, analysis: Dict[str, Any]) -> Tuple[Optional[pd.DataFrame], Dict[str, Any]]:
    """Attempt to correct timestamps if possible."""
    logger = logging.getLogger(__name__)
    
    if analysis['status'] != 'success':
        return None, {"correction_status": "failed", "reason": "Analysis failed"}
    
    # Check if correction is needed
    if not analysis['issues']:
        return None, {"correction_status": "not_needed", "reason": "No issues found"}
    
    # Try different correction methods
    correction_methods = []
    
    # Method 1: If timestamps are in local time, try to convert to UTC
    if "Timestamps appear to be in local time" in analysis['issues']:
        try:
            # Assume timestamps are in local time and need UTC conversion
            # This is a heuristic - in practice, we'd need to know the exact timezone
            raw_timestamps = df['timestamp']
            
            # Try parsing as local time first, then convert to UTC
            if raw_timestamps.dtype == 'object':
                # Try different timezone assumptions
                for tz_offset in [-8, -7, -6, -5, -4, -3, -2, -1, 0, 1, 2, 3, 4, 5, 6, 7, 8]:
                    try:
                        tz = timezone(timedelta(hours=tz_offset))
                        ts_local = pd.to_datetime(raw_timestamps, utc=False)
                        ts_utc = ts_local.dt.tz_localize(tz).dt.tz_convert(timezone.utc)
                        
                        # Check if this makes the timestamps more reasonable
                        if ts_utc.is_monotonic_increasing:
                            correction_methods.append({
                                "method": f"timezone_offset_{tz_offset}h",
                                "timezone_offset": tz_offset,
                                "corrected_timestamps": ts_utc,
                                "is_monotonic": True
                            })
                    except:
                        continue
            
            # If we found a good correction, use it
            if correction_methods:
                best_method = max(correction_methods, key=lambda x: x['is_monotonic'])
                df_corrected = df.copy()
                df_corrected['timestamp'] = best_method['corrected_timestamps']
                
                return df_corrected, {
                    "correction_status": "success",
                    "method": best_method['method'],
                    "timezone_offset": best_method['timezone_offset'],
                    "is_monotonic": best_method['is_monotonic']
                }
                
        except Exception as e:
            logger.warning(f"Timezone correction failed: {e}")
    
    # Method 2: If timestamps are non-monotonic, try to sort them
    if "Non-monotonic timestamps" in analysis['issues']:
        try:
            df_corrected = df.copy()
            df_corrected = df_corrected.sort_values('timestamp').reset_index(drop=True)
            
            # Check if sorting helped
            ts_parsed = pd.to_datetime(df_corrected['timestamp'], utc=True)
            is_monotonic_after = ts_parsed.is_monotonic_increasing
            
            if is_monotonic_after:
                return df_corrected, {
                    "correction_status": "success",
                    "method": "sort_by_timestamp",
                    "is_monotonic": True
                }
                
        except Exception as e:
            logger.warning(f"Sorting correction failed: {e}")
    
    # If no correction method worked
    return None, {
        "correction_status": "failed",
        "reason": "No safe correction method found",
        "attempted_methods": [m['method'] for m in correction_methods]
    }

def main():
    """Main Phase TZ-FIX function."""
    parser = argparse.ArgumentParser(description='ACD Phase TZ-FIX - Coinbase Timestamp Normalization')
    parser.add_argument('--verbose', action='store_true', help='Verbose logging')
    parser.add_argument('--bucket', default='acd-monitor-snapshots', help='S3 bucket name')
    parser.add_argument('--date', default='20251002', help='Date to process (YYYYMMDD)')
    
    args = parser.parse_args()
    setup_logging(args.verbose)
    logger = logging.getLogger(__name__)
    
    # Initialize S3 client
    s3_client = boto3.client('s3')
    
    print("\n" + "="*80)
    print("🔍 ACD PHASE TZ-FIX - COINBASE TIMESTAMP NORMALIZATION")
    print("="*80)
    
    print(f"📅 Processing date: {args.date}")
    
    # List Coinbase slices
    print(f"\n🔍 Listing Coinbase slices...")
    try:
        slices = list_coinbase_slices(s3_client, args.bucket, args.date)
        print(f"✅ Found {len(slices)} Coinbase slices: {slices}")
    except Exception as e:
        print(f"❌ Error listing Coinbase slices: {e}")
        sys.exit(1)
    
    # Analyze each slice
    print(f"\n📊 Analyzing Coinbase timestamps...")
    all_analyses = {}
    all_corrections = {}
    
    for slice_name in slices:
        print(f"\n🔍 Analyzing {slice_name}...")
        
        # Analyze timestamps
        analysis = analyze_coinbase_timestamps(s3_client, args.bucket, args.date, slice_name)
        all_analyses[slice_name] = analysis
        
        if analysis['status'] == 'success':
            print(f"   ✅ {analysis['n_rows']} rows, {analysis['duration_seconds']:.1f}s")
            print(f"   Raw range: {analysis['ts_min_raw']} → {analysis['ts_max_raw']}")
            print(f"   UTC range: {analysis['ts_min_utc']} → {analysis['ts_max_utc']}")
            print(f"   Monotonic: {'✅' if analysis['is_monotonic'] else '❌'}")
            print(f"   Non-monotonic: {analysis['non_monotonic_count']} ({analysis['non_monotonic_ratio']:.1%})")
            print(f"   Source field: {analysis['source_field']}")
            print(f"   Normalization: {analysis['normalization_path']}")
            
            if analysis['issues']:
                print(f"   ⚠️  Issues: {', '.join(analysis['issues'])}")
                
                # Attempt correction
                print(f"   🔧 Attempting correction...")
                
                # Load the data again for correction
                sample_key = f"raw_probes/{args.date}/venue=coinbase/slice={slice_name}/sample.parquet"
                parquet_data_content = get_s3_object_content(s3_client, args.bucket, sample_key)
                
                if parquet_data_content:
                    with tempfile.NamedTemporaryFile(suffix='.parquet', delete=False) as tmp_file:
                        tmp_file.write(parquet_data_content)
                        tmp_file.flush()
                        df = pd.read_parquet(tmp_file.name)
                        Path(tmp_file.name).unlink()
                    
                    df_corrected, correction_result = attempt_timestamp_correction(df, analysis)
                    all_corrections[slice_name] = correction_result
                    
                    if correction_result['correction_status'] == 'success':
                        print(f"   ✅ Correction successful: {correction_result['method']}")
                        
                        # Save corrected data
                        corrected_key = f"analysis/{args.date}/ACD/_tzfix/coinbase/corrected_{slice_name}.parquet"
                        
                        with tempfile.NamedTemporaryFile(suffix='.parquet', delete=False) as tmp_file:
                            df_corrected.to_parquet(tmp_file.name, index=False)
                            with open(tmp_file.name, 'rb') as f:
                                corrected_data = f.read()
                            Path(tmp_file.name).unlink()
                        
                        s3_client.put_object(
                            Bucket=args.bucket,
                            Key=corrected_key,
                            Body=corrected_data,
                            ContentType='application/octet-stream'
                        )
                        
                        print(f"   💾 Saved corrected data: s3://{args.bucket}/{corrected_key}")
                        
                        # Create correction manifest
                        tz_fix_manifest = {
                            "original_slice": slice_name,
                            "correction_timestamp": datetime.now(timezone.utc).isoformat(),
                            "correction_method": correction_result['method'],
                            "original_issues": analysis['issues'],
                            "correction_result": correction_result,
                            "original_analysis": analysis
                        }
                        
                        manifest_key = f"analysis/{args.date}/ACD/_tzfix/coinbase/tz_fix_manifest_{slice_name}.json"
                        s3_client.put_object(
                            Bucket=args.bucket,
                            Key=manifest_key,
                            Body=json.dumps(tz_fix_manifest, indent=2),
                            ContentType='application/json'
                        )
                        
                        print(f"   💾 Saved correction manifest: s3://{args.bucket}/{manifest_key}")
                        
                    else:
                        print(f"   ❌ Correction failed: {correction_result['reason']}")
                else:
                    print(f"   ❌ Could not load data for correction")
            else:
                print(f"   ✅ No issues found")
        else:
            print(f"   ❌ Analysis failed: {analysis['error']}")
    
    # Generate summary
    print(f"\n📊 COINBASE TIMESTAMP NORMALIZATION SUMMARY")
    print("="*60)
    
    successful_analyses = [a for a in all_analyses.values() if a.get('status') == 'success']
    successful_corrections = [c for c in all_corrections.values() if c.get('correction_status') == 'success']
    
    print(f"Total slices analyzed: {len(all_analyses)}")
    print(f"Successful analyses: {len(successful_analyses)}")
    print(f"Successful corrections: {len(successful_corrections)}")
    
    # Check if Coinbase is repairable
    coinbase_unrepairable = len(successful_corrections) == 0 and len(successful_analyses) > 0
    
    if coinbase_unrepairable:
        print(f"\n❌ COINBASE UNREPAIRABLE")
        print(f"   No safe correction methods found for any slice")
        print(f"   Cannot proceed to CLN phase")
    else:
        print(f"\n✅ COINBASE REPAIRABLE")
        print(f"   {len(successful_corrections)} slices successfully corrected")
    
    # Save summary
    summary_data = {
        "date": args.date,
        "analyses": all_analyses,
        "corrections": all_corrections,
        "coinbase_unrepairable": coinbase_unrepairable,
        "summary_timestamp": datetime.now(timezone.utc).isoformat()
    }
    
    summary_key = f"analysis/{args.date}/ACD/_tzfix/coinbase/tz_fix_summary.json"
    s3_client.put_object(
        Bucket=args.bucket,
        Key=summary_key,
        Body=json.dumps(summary_data, indent=2),
        ContentType='application/json'
    )
    
    print(f"\n💾 Saved summary: s3://{args.bucket}/{summary_key}")
    
    # Final decision
    if coinbase_unrepairable:
        print(f"\n🛑 STOP: Coinbase unrepairable. Cannot proceed to CLN phase.")
        sys.exit(1)
    else:
        print(f"\n✅ Coinbase timestamp normalization completed successfully")
    
    print(f"\n📁 Generated artifacts:")
    print(f"  Summary: s3://{args.bucket}/{summary_key}")
    for slice_name in slices:
        if slice_name in all_corrections and all_corrections[slice_name].get('correction_status') == 'success':
            print(f"  Corrected {slice_name}: s3://{args.bucket}/analysis/{args.date}/ACD/_tzfix/coinbase/corrected_{slice_name}.parquet")

if __name__ == "__main__":
    main()
