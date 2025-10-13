#!/usr/bin/env python3
"""
Phase 42A-v7c-Forensics: Zero-API Inventory & Coverage Truth
Produce authoritative, tamper-proof inventory of what was actually downloaded
"""

import os
import hashlib
import pandas as pd
import numpy as np
import time
import psutil
import re
from datetime import datetime, timezone
from pathlib import Path
import glob

# Global start time for runtime tracking
START_TIME = time.time()

def check_guardrails():
    """Check memory and runtime guardrails"""
    current_mb = psutil.Process().memory_info().rss / 1024 / 1024
    runtime_s = time.time() - START_TIME
    
    if current_mb > 750:  # 750 MB limit
        print(f"🚫 HALT: Memory usage {current_mb:.1f} MB exceeds 750 MB limit")
        return False
    
    if runtime_s > 1800:  # 30 minutes
        print(f"🚫 HALT: Runtime {runtime_s:.1f}s exceeds 30 minutes")
        return False
    
    print(f"📊 Memory: {current_mb:.1f} MB, Runtime: {runtime_s:.1f}s")
    return True

def scan_filesystem():
    """Scan all known data roots recursively for raw files"""
    print("🔍 **Phase 42A-v7c-Forensics: Zero-API Inventory & Coverage Truth**")
    print("=" * 60)
    
    # Define search roots
    search_roots = [
        'data_v6/raw/coinapi_jul/',
        'data_v6/raw/coinapi_oct/',
        'data_v6/raw/coinapi_aug/',
        'data_v6/raw/coinapi_sep/',
        'data_v6/cache/beacons/',
        'data_v7/raw/coinapi_jul_extension/',
        'data_v7/reports/',
        'logs/',
        'data_v6/logs/',
        'data_v7/logs/'
    ]
    
    print(f"📊 **Scanning Filesystem Roots:**")
    
    all_files = []
    
    for root in search_roots:
        if os.path.exists(root):
            print(f"   ✅ {root}")
            
            # Recursively find all files
            for root_path, dirs, files in os.walk(root):
                for file in files:
                    full_path = os.path.join(root_path, file)
                    rel_path = os.path.relpath(full_path, '.')
                    
                    try:
                        stat = os.stat(full_path)
                        all_files.append({
                            'root_path': root,
                            'rel_path': rel_path,
                            'filename': file,
                            'bytes': stat.st_size,
                            'mtime_utc': datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc),
                            'full_path': full_path
                        })
                    except (OSError, IOError) as e:
                        print(f"   ⚠️ Error accessing {full_path}: {e}")
        else:
            print(f"   ❌ {root} (not found)")
    
    print(f"📊 Total files found: {len(all_files)}")
    return all_files

def parse_filenames(files):
    """Parse filenames using week1_download.py conventions"""
    print(f"\n📊 **Parsing Filenames**")
    print("=" * 60)
    
    # Read week1_download.py to understand naming conventions
    week1_script_path = '/Users/ygorfrancisco/Desktop/acd-monitor/week1_download.py'
    naming_conventions = {}
    
    if os.path.exists(week1_script_path):
        try:
            with open(week1_script_path, 'r') as f:
                content = f.read()
                print(f"📊 Read naming conventions from {week1_script_path}")
        except Exception as e:
            print(f"⚠️ Could not read {week1_script_path}: {e}")
    else:
        print(f"⚠️ {week1_script_path} not found")
    
    # Define parsing patterns
    patterns = {
        # Pattern: VENUE_YYYYMMDD_BTCUSDT.csv.gz
        'venue_date_btcusdt': r'([A-Z]+)_(\d{8})_BTCUSDT\.csv\.gz$',
        # Pattern: T-TRADES/D-YYYYMMDD/E-VENUE/...
        'ttrades_path': r'T-TRADES/D-(\d{8})/E-([A-Z]+)/',
        # Pattern: 2025-MM-DD_VENUE.gz
        'date_venue_gz': r'(\d{4}-\d{2}-\d{2})_([A-Z]+)\.gz$',
        # Pattern: VENUE_YYYYMMDD_BTCUSDT.csv.gz (alternative)
        'venue_date_alt': r'([A-Z]+)_(\d{8})_BTCUSDT\.csv\.gz$'
    }
    
    venues = ['BINANCE', 'COINBASE', 'BYBITSPOT', 'BITGET']
    
    parsed_files = []
    
    for file_info in files:
        filename = file_info['filename']
        rel_path = file_info['rel_path']
        
        # Initialize parsed fields
        date_yyyymmdd = None
        venue = None
        phase_hint = None
        
        # Determine phase hint from root path
        root_path = file_info['root_path']
        if 'v6_jul' in root_path or 'coinapi_jul' in root_path:
            phase_hint = 'v6_jul'
        elif 'v7_jul_ext' in root_path or 'jul_extension' in root_path:
            phase_hint = 'v7_jul_ext'
        elif 'oct' in root_path:
            phase_hint = 'oct'
        elif 'aug' in root_path:
            phase_hint = 'aug'
        elif 'sep' in root_path:
            phase_hint = 'sep'
        elif 'beacons' in root_path:
            phase_hint = 'beacons'
        else:
            phase_hint = 'unknown'
        
        # Try different parsing patterns
        for pattern_name, pattern in patterns.items():
            match = re.search(pattern, filename)
            if not match:
                match = re.search(pattern, rel_path)
            
            if match:
                if pattern_name == 'venue_date_btcusdt':
                    venue, date_yyyymmdd = match.groups()
                elif pattern_name == 'ttrades_path':
                    date_yyyymmdd, venue = match.groups()
                elif pattern_name == 'date_venue_gz':
                    date_str, venue = match.groups()
                    # Convert YYYY-MM-DD to YYYYMMDD
                    date_yyyymmdd = date_str.replace('-', '')
                elif pattern_name == 'venue_date_alt':
                    venue, date_yyyymmdd = match.groups()
                
                break
        
        # Validate venue
        if venue and venue not in venues:
            venue = None
        
        # Validate date format
        if date_yyyymmdd and len(date_yyyymmdd) == 8:
            try:
                datetime.strptime(date_yyyymmdd, '%Y%m%d')
            except ValueError:
                date_yyyymmdd = None
        
        parsed_files.append({
            **file_info,
            'date_yyyymmdd': date_yyyymmdd,
            'venue': venue,
            'phase_hint': phase_hint
        })
    
    # Count parsed files
    parsed_count = sum(1 for f in parsed_files if f['date_yyyymmdd'] and f['venue'])
    print(f"📊 Successfully parsed: {parsed_count}/{len(parsed_files)} files")
    
    return parsed_files

def compute_hashes(files):
    """Compute SHA-256 hashes for all files > 0 bytes"""
    print(f"\n📊 **Computing SHA-256 Hashes**")
    print("=" * 60)
    
    files_with_hashes = []
    
    for i, file_info in enumerate(files):
        if i % 100 == 0:
            print(f"📊 Processing file {i+1}/{len(files)}")
        
        full_path = file_info['full_path']
        bytes_size = file_info['bytes']
        
        if bytes_size > 0:
            try:
                # Compute SHA-256 using streaming for memory safety
                sha256_hash = hashlib.sha256()
                with open(full_path, 'rb') as f:
                    for chunk in iter(lambda: f.read(8192), b""):
                        sha256_hash.update(chunk)
                
                file_info['sha256'] = sha256_hash.hexdigest()
                file_info['is_zero_byte'] = False
                
            except (OSError, IOError) as e:
                print(f"⚠️ Error hashing {full_path}: {e}")
                file_info['sha256'] = None
                file_info['is_zero_byte'] = False
        else:
            file_info['sha256'] = None
            file_info['is_zero_byte'] = True
        
        files_with_hashes.append(file_info)
    
    zero_byte_count = sum(1 for f in files_with_hashes if f['is_zero_byte'])
    print(f"📊 Zero-byte files: {zero_byte_count}")
    
    return files_with_hashes

def detect_duplicates(files):
    """Detect duplicate names and hashes"""
    print(f"\n📊 **Detecting Duplicates**")
    print("=" * 60)
    
    # Group by date+venue+filename for duplicate names
    name_groups = {}
    for file_info in files:
        if file_info['date_yyyymmdd'] and file_info['venue']:
            key = (file_info['date_yyyymmdd'], file_info['venue'], file_info['filename'])
            if key not in name_groups:
                name_groups[key] = []
            name_groups[key].append(file_info)
    
    # Group by SHA-256 for duplicate hashes
    hash_groups = {}
    for file_info in files:
        if file_info['sha256']:
            if file_info['sha256'] not in hash_groups:
                hash_groups[file_info['sha256']] = []
            hash_groups[file_info['sha256']].append(file_info)
    
    # Mark duplicates
    for file_info in files:
        # Check for duplicate names
        if file_info['date_yyyymmdd'] and file_info['venue']:
            key = (file_info['date_yyyymmdd'], file_info['venue'], file_info['filename'])
            file_info['is_duplicate_name'] = len(name_groups[key]) > 1
        else:
            file_info['is_duplicate_name'] = False
        
        # Check for duplicate hashes
        if file_info['sha256']:
            file_info['is_duplicate_hash'] = len(hash_groups[file_info['sha256']]) > 1
        else:
            file_info['is_duplicate_hash'] = False
    
    duplicate_name_count = sum(1 for f in files if f['is_duplicate_name'])
    duplicate_hash_count = sum(1 for f in files if f['is_duplicate_hash'])
    
    print(f"📊 Duplicate names: {duplicate_name_count}")
    print(f"📊 Duplicate hashes: {duplicate_hash_count}")
    
    return files

def generate_manifest(files):
    """Generate master manifest CSV"""
    print(f"\n📊 **Generating Master Manifest**")
    print("=" * 60)
    
    # Create output directory
    os.makedirs('data_forensics/manifests', exist_ok=True)
    
    # Prepare manifest data
    manifest_data = []
    for file_info in files:
        manifest_data.append({
            'root_path': file_info['root_path'],
            'rel_path': file_info['rel_path'],
            'filename': file_info['filename'],
            'bytes': file_info['bytes'],
            'sha256': file_info['sha256'],
            'mtime_utc': file_info['mtime_utc'].isoformat(),
            'date_yyyymmdd': file_info['date_yyyymmdd'],
            'venue': file_info['venue'],
            'phase_hint': file_info['phase_hint'],
            'is_zero_byte': file_info['is_zero_byte'],
            'is_duplicate_name': file_info['is_duplicate_name'],
            'is_duplicate_hash': file_info['is_duplicate_hash']
        })
    
    # Create DataFrame and save
    manifest_df = pd.DataFrame(manifest_data)
    manifest_path = 'data_forensics/manifests/raw_flatfiles_manifest.csv'
    manifest_df.to_csv(manifest_path, index=False)
    
    print(f"📊 Manifest saved: {manifest_path}")
    print(f"📊 Total records: {len(manifest_df)}")
    
    return manifest_df

def generate_coverage_matrix(files):
    """Generate coverage matrix per day × venue"""
    print(f"\n📊 **Generating Coverage Matrix**")
    print("=" * 60)
    
    # Create output directory
    os.makedirs('data_forensics/reports', exist_ok=True)
    
    # Define target windows
    target_windows = [
        ('2025-07-22', '2025-07-31', 'JUL22-31'),
        ('2025-08-01', '2025-08-04', 'AUG01-04'),
        ('2025-10-01', '2025-10-07', 'OCT01-07'),
        ('2025-07-01', '2025-07-21', 'JUL01-21')
    ]
    
    venues = ['BINANCE', 'COINBASE', 'BYBITSPOT', 'BITGET']
    coverage_data = []
    
    for start_date, end_date, window_name in target_windows:
        print(f"📊 Processing window: {window_name}")
        
        # Generate expected dates
        start_dt = datetime.strptime(start_date, '%Y-%m-%d')
        end_dt = datetime.strptime(end_date, '%Y-%m-%d')
        
        expected_dates = []
        current_dt = start_dt
        while current_dt <= end_dt:
            expected_dates.append(current_dt.strftime('%Y%m%d'))
            current_dt += pd.Timedelta(days=1)
        
        expected_count = len(expected_dates) * len(venues)
        
        # Count found files
        found_files = []
        for file_info in files:
            if (file_info['date_yyyymmdd'] and 
                file_info['venue'] and 
                file_info['date_yyyymmdd'] in expected_dates and
                file_info['venue'] in venues and
                not file_info['is_zero_byte']):
                found_files.append(file_info)
        
        found_count = len(found_files)
        coverage_pct = (found_count / expected_count * 100) if expected_count > 0 else 0
        
        # Create coverage matrix entry
        coverage_data.append({
            'window': window_name,
            'start_date': start_date,
            'end_date': end_date,
            'expected': expected_count,
            'found': found_count,
            'coverage_pct': coverage_pct,
            'BINANCE': sum(1 for f in found_files if f['venue'] == 'BINANCE'),
            'COINBASE': sum(1 for f in found_files if f['venue'] == 'COINBASE'),
            'BYBITSPOT': sum(1 for f in found_files if f['venue'] == 'BYBITSPOT'),
            'BITGET': sum(1 for f in found_files if f['venue'] == 'BITGET')
        })
    
    # Create DataFrame and save
    coverage_df = pd.DataFrame(coverage_data)
    coverage_path = 'data_forensics/reports/coverage_matrix.csv'
    coverage_df.to_csv(coverage_path, index=False)
    
    print(f"📊 Coverage matrix saved: {coverage_path}")
    
    return coverage_df

def audit_api_budget():
    """Reconstruct API budget from logs"""
    print(f"\n📊 **Auditing API Budget from Logs**")
    print("=" * 60)
    
    # Search for log files
    log_patterns = [
        'logs/*.log',
        'data_v6/logs/*.log',
        'data_v7/logs/*.log',
        '*.log',
        '*.out',
        '*.err'
    ]
    
    log_files = []
    for pattern in log_patterns:
        log_files.extend(glob.glob(pattern))
    
    print(f"📊 Found {len(log_files)} log files")
    
    # Parse logs for API budget information
    api_budget_data = []
    
    for log_file in log_files:
        try:
            with open(log_file, 'r') as f:
                content = f.read()
                
                # Look for HTTP status codes
                http_codes = re.findall(r'HTTP (\d{3})', content)
                for code in http_codes:
                    api_budget_data.append({
                        'ts_utc': datetime.now(timezone.utc).isoformat(),
                        'date_yyyymmdd': None,
                        'venue': None,
                        'http_code': int(code),
                        'attempts': 1,
                        'elapsed_ms': None,
                        'noted_headers': None,
                        'script_name': os.path.basename(log_file),
                        'log_path': log_file
                    })
                
                # Look for rate limit headers
                rate_limits = re.findall(r'X-RateLimit-(\w+):\s*(\d+)', content)
                for header, value in rate_limits:
                    api_budget_data.append({
                        'ts_utc': datetime.now(timezone.utc).isoformat(),
                        'date_yyyymmdd': None,
                        'venue': None,
                        'http_code': None,
                        'attempts': 1,
                        'elapsed_ms': None,
                        'noted_headers': f'X-RateLimit-{header}: {value}',
                        'script_name': os.path.basename(log_file),
                        'log_path': log_file
                    })
                
        except Exception as e:
            print(f"⚠️ Error reading {log_file}: {e}")
    
    # Create DataFrame and save
    if api_budget_data:
        api_budget_df = pd.DataFrame(api_budget_data)
        api_budget_path = 'data_forensics/reports/api_budget_summary.csv'
        api_budget_df.to_csv(api_budget_path, index=False)
        print(f"📊 API budget summary saved: {api_budget_path}")
    else:
        print(f"📊 No API budget information found in logs")
        api_budget_df = pd.DataFrame()
    
    return api_budget_df

def index_beacon_panels():
    """Index all beacon panels"""
    print(f"\n📊 **Indexing Beacon Panels**")
    print("=" * 60)
    
    # Search for parquet files in beacon directories
    beacon_patterns = [
        'data_v6/cache/beacons/*.parquet',
        'data_v7/cache/beacons/*.parquet'
    ]
    
    beacon_files = []
    for pattern in beacon_patterns:
        beacon_files.extend(glob.glob(pattern))
    
    print(f"📊 Found {len(beacon_files)} beacon panel files")
    
    beacon_data = []
    
    for beacon_file in beacon_files:
        try:
            # Read parquet file
            df = pd.read_parquet(beacon_file)
            
            # Compute SHA-256
            with open(beacon_file, 'rb') as f:
                sha256_hash = hashlib.sha256(f.read()).hexdigest()
            
            # Get file stats
            stat = os.stat(beacon_file)
            
            # Extract version tag from filename
            filename = os.path.basename(beacon_file)
            version_tag = filename.split('.')[0] if '.' in filename else filename
            
            # Determine months covered
            if 'timestamp' in df.columns:
                start_ts = df['timestamp'].min()
                end_ts = df['timestamp'].max()
                months_covered = len(df['timestamp'].dt.to_period('M').unique())
            else:
                start_ts = None
                end_ts = None
                months_covered = None
            
            beacon_data.append({
                'filename': filename,
                'rows': len(df),
                'sha256': sha256_hash,
                'start_ts': start_ts,
                'end_ts': end_ts,
                'months_covered': months_covered,
                'version_tag': version_tag,
                'bytes': stat.st_size,
                'mtime_utc': datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc).isoformat()
            })
            
        except Exception as e:
            print(f"⚠️ Error reading {beacon_file}: {e}")
    
    # Create DataFrame and save
    if beacon_data:
        beacon_df = pd.DataFrame(beacon_data)
        beacon_path = 'data_forensics/reports/beacon_panels.csv'
        beacon_df.to_csv(beacon_path, index=False)
        print(f"📊 Beacon panels index saved: {beacon_path}")
    else:
        print(f"📊 No beacon panels found")
        beacon_df = pd.DataFrame()
    
    return beacon_df

def audit_quarantine_candidates(files):
    """Audit for synthetic/quarantine files"""
    print(f"\n📊 **Auditing Quarantine Candidates**")
    print("=" * 60)
    
    # Look for files that might be synthetic or quarantine
    quarantine_patterns = [
        '*sim*', '*synthetic*', '*.mock.*', '*_sim/*', '*_quarantine/*'
    ]
    
    quarantine_candidates = []
    
    for file_info in files:
        filename = file_info['filename'].lower()
        rel_path = file_info['rel_path'].lower()
        
        # Check for synthetic indicators
        synthetic_indicators = ['sim', 'synthetic', 'mock', 'fake', 'test', 'dummy']
        
        is_quarantine = False
        reason = None
        
        for indicator in synthetic_indicators:
            if indicator in filename or indicator in rel_path:
                is_quarantine = True
                reason = f"Contains '{indicator}'"
                break
        
        # Check for quarantine directories
        if '_quarantine' in rel_path or '_sim' in rel_path:
            is_quarantine = True
            reason = "In quarantine/sim directory"
        
        if is_quarantine:
            quarantine_candidates.append({
                'rel_path': file_info['rel_path'],
                'filename': file_info['filename'],
                'reason': reason,
                'bytes': file_info['bytes'],
                'phase_hint': file_info['phase_hint']
            })
    
    # Create DataFrame and save
    if quarantine_candidates:
        quarantine_df = pd.DataFrame(quarantine_candidates)
        quarantine_path = 'data_forensics/reports/quarantine_candidates.csv'
        quarantine_df.to_csv(quarantine_path, index=False)
        print(f"📊 Quarantine candidates saved: {quarantine_path}")
        print(f"📊 Found {len(quarantine_candidates)} quarantine candidates")
    else:
        print(f"📊 No quarantine candidates found")
        quarantine_df = pd.DataFrame()
    
    return quarantine_df

def generate_console_summary(manifest_df, coverage_df, api_budget_df, beacon_df, quarantine_df):
    """Generate console summary and verdict"""
    print(f"\n📊 **Console Summary**")
    print("=" * 60)
    
    print(f"PHASE 42A-v7c-FORENSICS — ZERO-API INVENTORY")
    print()
    
    # Windows audited
    print(f"Windows audited:")
    for _, row in coverage_df.iterrows():
        window = row['window']
        expected = row['expected']
        found = row['found']
        coverage_pct = row['coverage_pct']
        
        status = "✅" if coverage_pct >= 95 else "❌"
        print(f"  • {window} (expected {expected}): found {found} → {coverage_pct:.1f}% {status}")
    
    print()
    
    # File integrity
    zero_byte_count = manifest_df['is_zero_byte'].sum()
    duplicate_name_count = manifest_df['is_duplicate_name'].sum()
    duplicate_hash_count = manifest_df['is_duplicate_hash'].sum()
    
    print(f"File integrity:")
    print(f"  • zero-byte files: {zero_byte_count}")
    print(f"  • duplicate names: {duplicate_name_count}")
    print(f"  • duplicate hashes: {duplicate_hash_count}")
    
    print()
    
    # API budget
    print(f"API budget (from logs; no new calls):")
    if not api_budget_df.empty:
        http_codes = api_budget_df['http_code'].value_counts()
        if not http_codes.empty:
            print(f"  • error codes observed: {dict(http_codes)}")
        else:
            print(f"  • no HTTP codes found in logs")
    else:
        print(f"  • no API budget information found")
    
    print()
    
    # Verdict
    print(f"Verdict:")
    
    # Check if all targeted windows have sufficient coverage
    sufficient_coverage = all(row['coverage_pct'] >= 95 for _, row in coverage_df.iterrows())
    no_zero_bytes = zero_byte_count == 0
    
    if sufficient_coverage and no_zero_bytes:
        print(f"  ✅ Coverage sufficient for existing panels")
        print(f"  ✅ All windows ≥95% actual files found and no zero-byte")
        verdict = "PROCEED"
    else:
        print(f"  ❌ Coverage insufficient")
        if not sufficient_coverage:
            print(f"  ❌ Some windows <95% coverage")
        if not no_zero_bytes:
            print(f"  ❌ Found {zero_byte_count} zero-byte files")
        verdict = "HOLD"
    
    print()
    
    # Artifacts written
    print(f"Artifacts written:")
    print(f"  - raw_flatfiles_manifest.csv ({len(manifest_df)} rows)")
    print(f"  - coverage_matrix.csv")
    if not api_budget_df.empty:
        print(f"  - api_budget_summary.csv")
    if not beacon_df.empty:
        print(f"  - beacon_panels.csv")
    if not quarantine_df.empty:
        print(f"  - quarantine_candidates.csv")
    
    return verdict

def main():
    print('🔍 Phase 42A-v7c-Forensics: Zero-API Inventory & Coverage Truth')
    print('=' * 60)
    
    # Check guardrails
    if not check_guardrails():
        return
    
    try:
        # Step 1: Scan filesystem
        files = scan_filesystem()
        
        # Step 2: Parse filenames
        parsed_files = parse_filenames(files)
        
        # Step 3: Compute hashes
        files_with_hashes = compute_hashes(parsed_files)
        
        # Step 4: Detect duplicates
        files_with_duplicates = detect_duplicates(files_with_hashes)
        
        # Step 5: Generate manifest
        manifest_df = generate_manifest(files_with_duplicates)
        
        # Step 6: Generate coverage matrix
        coverage_df = generate_coverage_matrix(files_with_duplicates)
        
        # Step 7: Audit API budget
        api_budget_df = audit_api_budget()
        
        # Step 8: Index beacon panels
        beacon_df = index_beacon_panels()
        
        # Step 9: Audit quarantine candidates
        quarantine_df = audit_quarantine_candidates(files_with_duplicates)
        
        # Step 10: Generate console summary
        verdict = generate_console_summary(manifest_df, coverage_df, api_budget_df, beacon_df, quarantine_df)
        
        print(f"\n📊 **Final Verdict: {verdict}**")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        # Final guardrail check
        check_guardrails()

if __name__ == '__main__':
    main()
