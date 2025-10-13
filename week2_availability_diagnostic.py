#!/usr/bin/env python3
"""
Week 2 Data Availability Diagnostic (Read-Only Mode)
Checks if 2025-09-08 → 2025-09-14 data exists in CoinAPI flat files
"""

import os
import sys
import pathlib
import xml.etree.ElementTree as ET
import requests
import psutil
from datetime import datetime

# Configuration
BASE = "https://s3.flatfiles.coinapi.io"
HEAD = {"X-CoinAPI-Key": "7f036b38-38d6-4ed6-9fce-00a06280a0f6"}
DATES = ["20250908", "20250909", "20250910", "20250911", "20250912", "20250913", "20250914"]
VENUES = ["BINANCE", "COINBASE", "BYBITSPOT", "BITGET"]

def get_memory_usage():
    """Get current memory usage in MB"""
    process = psutil.Process(os.getpid())
    return process.memory_info().rss / 1024 / 1024

def check_venue_date_availability(venue, date):
    """Check availability for a specific venue and date (read-only)"""
    prefix = f"T-TRADES/D-{date}/E-{venue}/"
    url = f"{BASE}/bucket/"
    
    try:
        # Make request to list objects
        response = requests.get(url, headers=HEAD, params={"prefix": prefix}, timeout=30)
        
        if response.status_code == 200:
            # Parse XML response
            root = ET.fromstring(response.text)
            objects = root.findall("{http://s3.amazonaws.com/doc/2006-03-01/}Contents")
            
            object_count = len(objects)
            example_file = None
            total_size = 0
            
            if objects:
                # Get first object as example
                first_obj = objects[0]
                example_file = first_obj.findtext("{http://s3.amazonaws.com/doc/2006-03-01/}Key")
                
                # Calculate total size
                for obj in objects:
                    size_elem = obj.find("{http://s3.amazonaws.com/doc/2006-03-01/}Size")
                    if size_elem is not None:
                        total_size += int(size_elem.text)
            
            return {
                'status': '200 OK',
                'objects': object_count,
                'example_file': example_file,
                'total_size_bytes': total_size,
                'total_size_mb': round(total_size / (1024 * 1024), 1)
            }
            
        elif response.status_code == 404:
            return {
                'status': '404 Not Found',
                'objects': 0,
                'example_file': None,
                'total_size_bytes': 0,
                'total_size_mb': 0
            }
            
        elif response.status_code == 403:
            return {
                'status': '403 Forbidden',
                'objects': 0,
                'example_file': None,
                'total_size_bytes': 0,
                'total_size_mb': 0
            }
            
        else:
            return {
                'status': f'{response.status_code} Error',
                'objects': 0,
                'example_file': None,
                'total_size_bytes': 0,
                'total_size_mb': 0
            }
            
    except Exception as e:
        return {
            'status': f'Exception: {str(e)}',
            'objects': 0,
            'example_file': None,
            'total_size_bytes': 0,
            'total_size_mb': 0
        }

def main():
    """Main diagnostic function"""
    print("🔍 Week 2 Data Availability Diagnostic (Read-Only Mode)")
    print("=" * 60)
    print(f"📅 Checking dates: {DATES}")
    print(f"🏢 Checking venues: {VENUES}")
    print(f"🧠 Initial memory: {get_memory_usage():.1f} MB")
    print()
    
    # Results table
    results = []
    available_days = set()
    available_venues = set()
    
    # Check each venue for each date
    for date in DATES:
        print(f"📅 Checking date: {date}")
        
        for venue in VENUES:
            # Check memory before each request
            memory_mb = get_memory_usage()
            if memory_mb > 150:
                print(f"    ⚠️  Memory limit exceeded: {memory_mb:.1f} MB")
                break
            
            print(f"  🏢 Checking {venue}...")
            
            # Check availability
            result = check_venue_date_availability(venue, date)
            
            # Format date for display
            display_date = f"2025-{date[4:6]}-{date[6:8]}"
            
            # Add to results
            results.append({
                'date': display_date,
                'venue': venue,
                'http_status': result['status'],
                'objects': result['objects'],
                'example_file': result['example_file'],
                'size_mb': result['total_size_mb']
            })
            
            # Track availability
            if result['objects'] > 0:
                available_days.add(date)
                available_venues.add(venue)
            
            print(f"    📊 {result['status']} - {result['objects']} objects, {result['total_size_mb']} MB")
            
            # Memory check after processing
            memory_mb = get_memory_usage()
            print(f"    🧠 Memory: {memory_mb:.1f} MB")
    
    # Print results table
    print("\n📊 Availability Report:")
    print("=" * 80)
    print(f"{'Date':<12} {'Venue':<10} {'HTTP Status':<15} {'Objects':<8} {'Example File':<30} {'Size (MB)':<10}")
    print("-" * 80)
    
    for result in results:
        example_display = result['example_file'][:27] + "..." if result['example_file'] and len(result['example_file']) > 30 else result['example_file'] or "–"
        print(f"{result['date']:<12} {result['venue']:<10} {result['http_status']:<15} {result['objects']:<8} {example_display:<30} {result['size_mb']:<10}")
    
    # Diagnostic summary
    print("\n📋 Diagnostic Summary:")
    print(f"✅ Available days: {len(available_days)} out of {len(DATES)}")
    print(f"✅ Available venues: {len(available_venues)} out of {len(VENUES)}")
    
    if available_days:
        available_days_sorted = sorted(available_days)
        print(f"📅 Available dates: {', '.join(available_days_sorted)}")
        
        # Find the last available date
        last_date = available_days_sorted[-1]
        print(f"📅 Data likely ends on: {last_date}")
    else:
        print("❌ No data found for any of the Week 2 dates")
        print("📅 Data likely ends before: 2025-09-08")
    
    print(f"🧠 Final memory: {get_memory_usage():.1f} MB")
    
    # Save diagnostic results
    diagnostic_file = pathlib.Path("data_v6/week2_availability_diagnostic.json")
    diagnostic_file.parent.mkdir(parents=True, exist_ok=True)
    
    diagnostic_data = {
        'timestamp': datetime.now().isoformat(),
        'dates_checked': DATES,
        'venues_checked': VENUES,
        'results': results,
        'available_days': list(available_days),
        'available_venues': list(available_venues),
        'memory_usage_mb': get_memory_usage()
    }
    
    import json
    with open(diagnostic_file, 'w') as f:
        json.dump(diagnostic_data, f, indent=2)
    
    print(f"\n💾 Diagnostic results saved to: {diagnostic_file}")

if __name__ == "__main__":
    main()




