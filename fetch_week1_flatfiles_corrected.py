#!/usr/bin/env python3
"""
Week-1 CoinAPI Flat Files fetch with correct URL encoding
Fixes 403 errors by properly encoding "+" characters in object keys
"""

import os
import sys
import pathlib
import urllib.parse
import xml.etree.ElementTree as ET
import requests
import gzip
import pandas as pd
import json
from datetime import datetime

# Configuration
BASE = "https://s3.flatfiles.coinapi.io"
HEAD = {"X-CoinAPI-Key": os.environ["COINAPI_KEY"]}
DATES = ["20250801", "20250802", "20250803", "20250804", "20250805", "20250806", "20250807"]
VENUE_SYMBOL = {
    "BINANCE": "BTCUSDT",
    "BYBITSPOT": "BTCUSDT", 
    "BITGET": "BTCUSDT",
    "COINBASE": "BTCUSD",
}

def list_keys(prefix):
    """List all keys for a given prefix"""
    r = requests.get(f"{BASE}/bucket/", headers=HEAD, params={"prefix": prefix}, timeout=60)
    r.raise_for_status()
    root = ET.fromstring(r.text)
    # S3 listings: each <Contents><Key>...</Key>
    return [e.findtext("{http://s3.amazonaws.com/doc/2006-03-01/}Key")
            for e in root.findall("{http://s3.amazonaws.com/doc/2006-03-01/}Contents")]

def want_btc_key(k, venue, symbol):
    """Check if key matches our BTC symbol criteria"""
    # Keep the TRADES csv.gz line for the symbol; keys contain + separators
    # e.g. .../SC-BINANCE_SPOT_BTCUSDT+S-BTCUSDT.csv.gz (or BTCUSD for Coinbase)
    return ("SC-" in k) and (f"_{symbol}" in k or f"+S-{symbol}" in k) and k.endswith(".csv.gz")

def download_key(key, outpath):
    """Download a file with proper URL encoding"""
    # URL-encode *each path segment* (so '+' becomes '%2B')
    enc = "/".join(urllib.parse.quote(seg, safe="") for seg in key.split("/"))
    url = f"{BASE}/{enc}"
    
    print(f"  📥 Downloading: {key}")
    print(f"  🔗 Encoded URL: {url}")
    
    with requests.get(url, headers=HEAD, stream=True, timeout=300) as r:
        if r.status_code != 200:
            print(f"  ❌ ERROR {r.status_code} on {url}")
            print(f"  📋 Response headers: {dict(r.headers)}")
            r.raise_for_status()
        
        outpath.parent.mkdir(parents=True, exist_ok=True)
        tmp = outpath.with_suffix(outpath.suffix + ".part")
        
        with open(tmp, "wb") as f:
            for chunk in r.iter_content(1<<20):  # 1MB chunks
                if chunk: 
                    f.write(chunk)
        
        tmp.rename(outpath)
        print(f"  ✅ Downloaded to: {outpath}")

def validate_file(file_path):
    """Validate downloaded file and compute basic stats"""
    try:
        # Try to read as gzipped CSV
        with gzip.open(file_path, 'rt') as f:
            lines = []
            for i, line in enumerate(f):
                lines.append(line.strip())
                if i >= 9:  # Read first 10 lines
                    break
        
        if len(lines) < 2:
            return False, "File too short", {}
        
        # Check format
        header = lines[0].lower()
        has_timestamp = any(col in header for col in ['time', 'timestamp', 'date'])
        has_price = any(col in header for col in ['price', 'rate'])
        has_volume = any(col in header for col in ['volume', 'size', 'amount', 'base_amount'])
        
        if not (has_timestamp and has_price and has_volume):
            return False, f"Invalid format. Header: {lines[0]}", {}
        
        # Compute basic stats
        stats = {
            'total_lines': len(lines),
            'header': lines[0],
            'sample_rows': lines[1:6] if len(lines) > 1 else [],
            'file_size_bytes': file_path.stat().st_size
        }
        
        return True, "Valid trade data format", stats
        
    except Exception as e:
        return False, f"Error reading file: {e}", {}

def save_qc_report(venue, date, is_valid, message, stats, file_path):
    """Save QC report for this venue/date"""
    qc_dir = pathlib.Path("analysis/flatfiles_ticks_v5/qc")
    qc_dir.mkdir(parents=True, exist_ok=True)
    
    qc_data = {
        'venue': venue,
        'date': date,
        'file_path': str(file_path),
        'valid': is_valid,
        'message': message,
        'stats': stats,
        'timestamp': datetime.now().isoformat()
    }
    
    qc_file = qc_dir / f"{venue}_{date}_qc.json"
    with open(qc_file, 'w') as f:
        json.dump(qc_data, f, indent=2)
    
    print(f"  💾 QC report saved: {qc_file}")

def main():
    """Main function to fetch and validate Week-1 files"""
    print("🚀 Starting Week-1 CoinAPI Flat Files fetch with correct URL encoding...")
    print(f"📅 Dates: {DATES}")
    print(f"🏢 Venues: {list(VENUE_SYMBOL.keys())}")
    
    # Track results
    results = {
        'successful_downloads': 0,
        'failed_downloads': 0,
        'valid_files': 0,
        'invalid_files': 0,
        'files': []
    }
    
    for venue, symbol in VENUE_SYMBOL.items():
        print(f"\n🏢 Processing venue: {venue} (symbol: {symbol})")
        
        for d in DATES:
            print(f"  📅 Processing date: {d}")
            
            try:
                # List files for this venue/date
                prefix = f"T-TRADES/D-{d}/E-{venue}/"
                keys = list_keys(prefix)
                print(f"    Found {len(keys)} total files")
                
                # Find BTC files
                cand = [k for k in keys if want_btc_key(k, venue, symbol)]
                print(f"    Found {len(cand)} {symbol} files")
                
                if not cand:
                    print(f"    ⚠️  No {symbol} key for {venue} {d}")
                    results['files'].append({
                        'venue': venue,
                        'date': d,
                        'status': 'NO_BTC_FILES',
                        'message': f'No {symbol} files found'
                    })
                    continue
                
                # Choose the largest-looking file if multiple
                k = sorted(cand, key=len)[-1]
                out = pathlib.Path(f"analysis/flatfiles_ticks_v5/raw/{venue}/{d}/btc.csv.gz")
                
                # Download file
                download_key(k, out)
                results['successful_downloads'] += 1
                
                # Validate file
                is_valid, message, stats = validate_file(out)
                
                if is_valid:
                    print(f"    ✅ File is valid: {message}")
                    results['valid_files'] += 1
                else:
                    print(f"    ❌ File is invalid: {message}")
                    results['invalid_files'] += 1
                
                # Save QC report
                save_qc_report(venue, d, is_valid, message, stats, out)
                
                # Record file info
                results['files'].append({
                    'venue': venue,
                    'date': d,
                    'file_key': k,
                    'local_path': str(out),
                    'valid': is_valid,
                    'message': message,
                    'stats': stats
                })
                
            except Exception as e:
                print(f"    ❌ Error processing {venue} {d}: {e}")
                results['failed_downloads'] += 1
                results['files'].append({
                    'venue': venue,
                    'date': d,
                    'status': 'ERROR',
                    'message': str(e)
                })
    
    # Print summary
    print(f"\n📊 Summary:")
    print(f"  ✅ Successful downloads: {results['successful_downloads']}")
    print(f"  ❌ Failed downloads: {results['failed_downloads']}")
    print(f"  ✅ Valid files: {results['valid_files']}")
    print(f"  ❌ Invalid files: {results['invalid_files']}")
    
    # Save results
    results_file = pathlib.Path("analysis/flatfiles_ticks_v5/fetch_results.json")
    results_file.parent.mkdir(parents=True, exist_ok=True)
    with open(results_file, 'w') as f:
        json.dump(results, f, indent=2)
    
    print(f"\n💾 Results saved to: {results_file}")
    
    # Print file list
    print(f"\n📁 Downloaded files:")
    for file_info in results['files']:
        if 'status' in file_info:
            status = "❌" if file_info['status'] in ['ERROR', 'NO_BTC_FILES'] else "✅"
            print(f"  {status} {file_info['venue']} {file_info['date']}: {file_info.get('message', file_info['status'])}")
        else:
            status = "✅" if file_info['valid'] else "❌"
            print(f"  {status} {file_info['venue']} {file_info['date']}: {file_info['local_path']}")

if __name__ == "__main__":
    main()





