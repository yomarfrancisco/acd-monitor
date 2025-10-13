#!/usr/bin/env python3
"""
Check what dates are actually available in CoinAPI around July 28-31, 2025
"""

import requests
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta

# CoinAPI configuration
COINAPI_BASE_URL = 'https://s3.flatfiles.coinapi.io'
COINAPI_KEY = '7f036b38-38d6-4ed6-9fce-00a06280a0f6'
HEADERS = {
    'X-CoinAPI-Key': COINAPI_KEY,
    'User-Agent': 'ACD-Monitor/1.0'
}

def check_date_availability(date_str, venue="BINANCE"):
    """Check if a specific date has data available"""
    list_url = f"{COINAPI_BASE_URL}/bucket/?prefix=T-TRADES/D-{date_str}/E-{venue}/"
    
    try:
        response = requests.get(list_url, headers=HEADERS, timeout=30)
        if response.status_code == 200:
            root = ET.fromstring(response.text)
            files = []
            for content in root.findall('.//Contents'):
                key_elem = content.find('Key')
                if key_elem is not None:
                    key = key_elem.text
                    if key.endswith('.csv.gz') and 'BTC' in key.upper():
                        files.append(key)
            return len(files), files[:3] if files else []
        else:
            return 0, []
    except Exception as e:
        return 0, []

def main():
    """Check availability around July 28-31, 2025"""
    print("🔍 Checking date availability around July 28-31, 2025...")
    
    # Check a range of dates
    base_date = datetime(2025, 7, 25)
    venues = ["BINANCE", "COINBASE", "BYBITSPOT", "BITGET"]
    
    print(f"\n📅 Date Availability Check:")
    print(f"{'Date':<12} {'BINANCE':<10} {'COINBASE':<10} {'BYBITSPOT':<10} {'BITGET':<10}")
    print("-" * 60)
    
    for i in range(15):  # Check 15 days starting from July 25
        check_date = base_date + timedelta(days=i)
        date_str = check_date.strftime("%Y%m%d")
        
        row = f"{date_str:<12}"
        
        for venue in venues:
            count, _ = check_date_availability(date_str, venue)
            if count > 0:
                row += f"{count:<10}"
            else:
                row += f"{'N/A':<10}"
        
        print(row)
        
        # Stop if we find a date with no data for any venue
        if all(check_date_availability(date_str, venue)[0] == 0 for venue in venues):
            print(f"  ⚠️ No data available for any venue on {date_str}")
    
    print(f"\n🎯 Target dates (Jul 28-31):")
    target_dates = ["20250728", "20250729", "20250730", "20250731"]
    
    for date_str in target_dates:
        print(f"\n📅 {date_str}:")
        for venue in venues:
            count, sample_files = check_date_availability(date_str, venue)
            if count > 0:
                print(f"  {venue}: {count} BTC files")
                if sample_files:
                    print(f"    Sample: {sample_files[0]}")
            else:
                print(f"  {venue}: No data")

if __name__ == "__main__":
    main()
