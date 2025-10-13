#!/usr/bin/env python3
"""
Phase 1.B - Canonicalization Audit (Ultra-Safe, Metadata-Only)
Determine if timestamp offsets are real market latency or canonicalization artifacts
"""

import os
import sys
import pandas as pd
import numpy as np
import pyarrow.parquet as pq
import gc
from datetime import datetime

def get_memory_usage():
    """Get current memory usage in MB"""
    import psutil
    process = psutil.Process(os.getpid())
    return process.memory_info().rss / 1024 / 1024

def check_memory_limit():
    """Check if memory usage exceeds limits"""
    memory_mb = get_memory_usage()
    if memory_mb >= 200:
        print(f"HALT: MEMORY_THRESHOLD - {memory_mb:.1f} MB")
        return True
    return False

def inspect_raw_csv_metadata(venue, date):
    """Inspect raw CSV metadata without loading full data"""
    # Try different possible raw file patterns
    possible_paths = [
        f"analysis/flatfiles_ticks_v4/raw/{venue}_{date}_BTCUSDT.csv.gz",
        f"analysis/flatfiles_ticks_v4/raw/{venue}_{date}_BTCUSD.csv.gz",
        f"analysis/flatfiles_ticks_v4/raw/{venue}_{date}_ticks.csv.gz"
    ]
    
    raw_path = None
    for path in possible_paths:
        if os.path.exists(path):
            raw_path = path
            break
    
    if raw_path is None:
        return None, f"Raw file not found. Tried: {possible_paths}"
    
    try:
        # Read just the header and first few rows to inspect schema
        import gzip
        
        with gzip.open(raw_path, 'rt') as f:
            header = f.readline().strip()
            first_line = f.readline().strip()
        
        # Parse header to find timestamp column
        columns = header.split(';')
        ts_column = None
        for col in columns:
            if col.lower() in ['time_exchange', 'timestamp', 'ts', 'time']:
                ts_column = col
                break
        
        if ts_column is None:
            return None, f"No timestamp column found in raw file. Columns: {columns}"
        
        # Parse first line to get sample timestamp
        values = first_line.split(';')
        ts_idx = columns.index(ts_column)
        sample_ts_str = values[ts_idx]
        
        # Try to parse the timestamp to understand its format
        try:
            # Try different timestamp formats
            sample_ts = pd.to_datetime(sample_ts_str)
            sample_dtype = str(sample_ts.dtype)
        except:
            sample_dtype = "string"
            sample_ts = sample_ts_str
        
        return {
            'file_path': raw_path,
            'columns': columns,
            'ts_column': ts_column,
            'sample_ts_str': sample_ts_str,
            'sample_ts': sample_ts,
            'pandas_dtype': sample_dtype,
            'file_size_mb': os.path.getsize(raw_path) / 1024 / 1024
        }, None
        
    except Exception as e:
        return None, f"Error inspecting raw file: {e}"

def inspect_canonical_parquet_metadata(venue, date):
    """Inspect canonical parquet metadata without loading data"""
    canon_path = f"data_v6/views/{venue}/{date}/ticks_canonical.parquet"
    
    if not os.path.exists(canon_path):
        return None, f"Canonical file not found: {canon_path}"
    
    try:
        f = pq.ParquetFile(canon_path)
        meta = f.metadata
        schema = f.schema
        
        # Find timestamp column
        ts_field = None
        for field in schema:
            if field.name == 'ts':
                ts_field = field
                break
        
        if ts_field is None:
            return None, "No 'ts' column found in canonical file"
        
        # Get physical type and logical type
        physical_type = str(ts_field.physical_type)
        logical_type = None
        if hasattr(ts_field, 'logical_type'):
            logical_type = str(ts_field.logical_type)
        
        # Read a tiny sample to check actual data type
        sample = f.read_row_group(0, columns=['ts']).to_pandas()
        if len(sample) == 0:
            return None, "No data in first row group"
        
        sample_dtype = str(sample['ts'].dtype)
        sample_value = sample['ts'].iloc[0]
        
        return {
            'physical_type': physical_type,
            'logical_type': logical_type,
            'pandas_dtype': sample_dtype,
            'sample_value': sample_value,
            'sample_str': str(sample_value),
            'num_rows': meta.num_rows,
            'created_by': meta.created_by
        }, None
        
    except Exception as e:
        return None, f"Error inspecting canonical file: {e}"

def analyze_canonicalization_script(venue):
    """Analyze the canonicalization script for venue-specific logic"""
    # Look for venue-specific canonicalization scripts
    script_paths = [
        f"week1_download.py",
        f"week2_redownload_day1_correct.py",
        f"week3_redownload_day1.py"
    ]
    
    canonicalization_logic = {
        'scaling_applied': 'Unknown',
        'rounding_method': 'Unknown',
        'tz_handling': 'Unknown',
        'venue_specific': 'Unknown'
    }
    
    for script_path in script_paths:
        if os.path.exists(script_path):
            try:
                with open(script_path, 'r') as f:
                    content = f.read()
                
                # Look for timestamp processing patterns
                if 'pd.to_datetime' in content:
                    canonicalization_logic['tz_handling'] = 'pd.to_datetime used'
                
                if 'utc=True' in content:
                    canonicalization_logic['tz_handling'] = 'UTC normalization applied'
                
                if 'floor' in content and 'ts' in content:
                    canonicalization_logic['rounding_method'] = 'floor() detected'
                elif 'round' in content and 'ts' in content:
                    canonicalization_logic['rounding_method'] = 'round() detected'
                
                if '/1000' in content or '/1e3' in content:
                    canonicalization_logic['scaling_applied'] = 'Division by 1000 detected'
                elif '/1e6' in content:
                    canonicalization_logic['scaling_applied'] = 'Division by 1e6 detected'
                
                if venue.lower() in content.lower():
                    canonicalization_logic['venue_specific'] = 'Venue-specific logic detected'
                
            except Exception as e:
                continue
    
    return canonicalization_logic

def detect_drift_sources(raw_meta, canon_meta, venue):
    """Detect potential sources of timestamp drift"""
    drift_sources = []
    
    if raw_meta is None or canon_meta is None:
        return "Cannot analyze - missing metadata"
    
    # Check for type changes
    if raw_meta['pandas_dtype'] != canon_meta['pandas_dtype']:
        drift_sources.append(f"Type change: {raw_meta['pandas_dtype']} → {canon_meta['pandas_dtype']}")
    
    # Check for timestamp format changes
    raw_ts_str = raw_meta['sample_ts_str']
    canon_ts_str = canon_meta['sample_str']
    
    # Check for timezone handling
    if '+00:00' in raw_ts_str and '+00:00' in canon_ts_str:
        if raw_ts_str != canon_ts_str:
            drift_sources.append("Timezone normalization applied")
    
    # Check for precision changes
    if '.' in raw_ts_str and '.' in canon_ts_str:
        raw_precision = len(raw_ts_str.split('.')[-1].split('+')[0])
        canon_precision = len(canon_ts_str.split('.')[-1].split('+')[0])
        if raw_precision != canon_precision:
            drift_sources.append(f"Precision change: {raw_precision} → {canon_precision} decimal places")
    
    # Check for rounding artifacts
    if 'floor' in str(canon_meta.get('created_by', '')):
        drift_sources.append("Floor rounding detected in creation")
    
    # Check for venue-specific patterns
    if venue == 'COINBASE' and 'BTCUSD' in raw_meta.get('file_path', ''):
        drift_sources.append("COINBASE BTCUSD specific processing")
    elif venue != 'COINBASE' and 'BTCUSDT' in raw_meta.get('file_path', ''):
        drift_sources.append("BTCUSDT specific processing")
    
    if not drift_sources:
        drift_sources.append("No obvious drift sources detected")
    
    return "; ".join(drift_sources)

def run_canonicalization_audit():
    """Run the canonicalization audit for 2025-09-08"""
    print("🔍 Phase 1.B - Canonicalization Audit (Metadata-Only)")
    print("=" * 60)
    
    date = "20250908"
    venues = ["BINANCE", "COINBASE", "BYBITSPOT", "BITGET"]
    
    print(f"🧠 Initial memory: {get_memory_usage():.1f} MB")
    
    audit_results = {}
    
    for venue in venues:
        print(f"\n🔍 Auditing {venue}...")
        
        if check_memory_limit():
            print(f"❌ HALT: Memory limit exceeded")
            return False
        
        # Inspect raw CSV
        print(f"  📊 Inspecting raw CSV...")
        raw_meta, error = inspect_raw_csv_metadata(venue, date)
        if error:
            print(f"    ❌ {error}")
            # Continue with canonical only
            raw_meta = None
        
        # Inspect canonical parquet
        print(f"  📊 Inspecting canonical parquet...")
        canon_meta, error = inspect_canonical_parquet_metadata(venue, date)
        if error:
            print(f"    ❌ {error}")
            return False
        
        # Analyze canonicalization logic
        print(f"  📊 Analyzing canonicalization logic...")
        canon_logic = analyze_canonicalization_script(venue)
        
        # Detect drift sources
        drift_sources = detect_drift_sources(raw_meta, canon_meta, venue)
        
        # Store results
        audit_results[venue] = {
            'raw_meta': raw_meta,
            'canon_meta': canon_meta,
            'canon_logic': canon_logic,
            'drift_sources': drift_sources
        }
        
        print(f"    ✅ {venue} audit completed")
        
        # Clean up
        gc.collect()
        
        if check_memory_limit():
            print(f"❌ HALT: Memory limit exceeded after {venue}")
            return False
    
    # Generate summary table
    print(f"\n📊 Canonicalization Audit Results:")
    print("Venue | RawType | CanonType | ScalingApplied | RoundingMethod | TZ | PotentialDriftSource")
    print("-" * 120)
    
    for venue in venues:
        result = audit_results[venue]
        raw_meta = result['raw_meta']
        canon_meta = result['canon_meta']
        canon_logic = result['canon_logic']
        drift_sources = result['drift_sources']
        
        raw_type = raw_meta['pandas_dtype'] if raw_meta else "N/A"
        canon_type = canon_meta['pandas_dtype']
        scaling = canon_logic['scaling_applied']
        rounding = canon_logic['rounding_method']
        tz = canon_logic['tz_handling']
        
        print(f"{venue} | {raw_type} | {canon_type} | {scaling} | {rounding} | {tz} | {drift_sources}")
    
    # Interpret results
    print(f"\n🧮 Interpretation:")
    
    # Check for patterns
    has_scaling = any('Division' in audit_results[v]['canon_logic']['scaling_applied'] for v in venues)
    has_rounding = any('detected' in audit_results[v]['canon_logic']['rounding_method'] for v in venues)
    has_tz_norm = any('UTC normalization' in audit_results[v]['canon_logic']['tz_handling'] for v in venues)
    has_venue_specific = any('detected' in audit_results[v]['canon_logic']['venue_specific'] for v in venues)
    
    if has_scaling or has_rounding:
        interpretation = "Likely canonicalization artifact"
    elif has_tz_norm and has_venue_specific:
        interpretation = "Mixed pattern"
    else:
        interpretation = "Likely real market latency"
    
    print(f"🎯 {interpretation}")
    print(f"🧠 Peak memory: {get_memory_usage():.1f} MB")
    
    return True

def main():
    """Main function"""
    success = run_canonicalization_audit()
    
    if success:
        print(f"\n✅ Canonicalization audit completed successfully.")
    else:
        print(f"\n❌ Canonicalization audit failed. Waiting for instructions.")
        sys.exit(1)

if __name__ == "__main__":
    main()
