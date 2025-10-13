#!/usr/bin/env python3
"""
Corrected CoinAPI Query for 2025-09-12
Using the correct URL format: https://s3.flatfiles.coinapi.io/bucket/?prefix=T-TRADES/D-{date}/E-{venue}/
"""

import os
import requests
import xml.etree.ElementTree as ET

def get_coinapi_key():
    """Get CoinAPI key from environment"""
    return os.environ.get('COINAPI_KEY', '7f036b38-38d6-4ed6-9fce-00a06280a0f6')

def list_coinapi_objects_corrected(venue, date):
    """List objects using the correct CoinAPI URL format"""
    base_url = "https://s3.flatfiles.coinapi.io/bucket/"
    prefix = f"T-TRADES/D-{date}/E-{venue}/"
    
    headers = {
        'X-CoinAPI-Key': get_coinapi_key()
    }
    
    params = {
        'prefix': prefix
    }
    
    try:
        response = requests.get(base_url, headers=headers, params=params, timeout=30)
        return response.status_code, response.text
    except Exception as e:
        return None, str(e)

def parse_s3_listing(xml_content):
    """Parse S3 XML listing response"""
    try:
        root = ET.fromstring(xml_content)
        objects = []
        
        for contents in root.findall('.//{http://s3.amazonaws.com/doc/2006-03-01/}Contents'):
            key = contents.find('{http://s3.amazonaws.com/doc/2006-03-01/}Key').text
            size = int(contents.find('{http://s3.amazonaws.com/doc/2006-03-01/}Size').text)
            last_modified = contents.find('{http://s3.amazonaws.com/doc/2006-03-01/}LastModified').text
            objects.append({
                'key': key, 
                'size': size, 
                'last_modified': last_modified
            })
        
        return objects
    except Exception as e:
        return []

def main():
    """Main query function"""
    print("🔍 Corrected CoinAPI Query for 2025-09-12")
    print("=" * 60)
    print("Using URL format: https://s3.flatfiles.coinapi.io/bucket/?prefix=T-TRADES/D-{date}/E-{venue}/")
    print()
    
    date = "20250912"
    venues = ["BINANCE", "COINBASE", "BYBITSPOT", "BITGET"]
    
    results = []
    
    for venue in venues:
        print(f"🔍 Checking {venue}...")
        print("-" * 30)
        
        # List objects in CoinAPI using corrected URL
        status_code, xml_content = list_coinapi_objects_corrected(venue, date)
        
        if status_code is None:
            print(f"❌ Request failed: {xml_content}")
            results.append({
                'venue': venue,
                'http_status': 'ERROR',
                'object_count': 0,
                'total_size_mb': 0,
                'objects': [],
                'has_data': False
            })
            continue
        
        print(f"📡 HTTP Status: {status_code}")
        
        if status_code != 200:
            print(f"❌ HTTP {status_code}")
            print(f"Response: {xml_content[:200]}...")
            results.append({
                'venue': venue,
                'http_status': status_code,
                'object_count': 0,
                'total_size_mb': 0,
                'objects': [],
                'has_data': False
            })
            continue
        
        # Parse objects
        objects = parse_s3_listing(xml_content)
        object_count = len(objects)
        total_size_bytes = sum(obj['size'] for obj in objects)
        total_size_mb = total_size_bytes / 1024 / 1024
        
        print(f"📊 Objects found: {object_count}")
        print(f"📊 Total size: {total_size_mb:.2f} MB")
        
        if object_count > 0:
            print(f"✅ DATA AVAILABLE!")
            print(f"📁 Files:")
            for i, obj in enumerate(objects[:5]):  # Show first 5 files
                size_mb = obj['size'] / 1024 / 1024
                print(f"  {i+1}. {obj['key']} ({size_mb:.2f} MB)")
                if obj['last_modified']:
                    print(f"     Modified: {obj['last_modified']}")
            
            if object_count > 5:
                print(f"  ... and {object_count - 5} more files")
            
            results.append({
                'venue': venue,
                'http_status': status_code,
                'object_count': object_count,
                'total_size_mb': total_size_mb,
                'objects': objects,
                'has_data': True
            })
        else:
            print(f"❌ No data found")
            results.append({
                'venue': venue,
                'http_status': status_code,
                'object_count': 0,
                'total_size_mb': 0,
                'objects': [],
                'has_data': False
            })
    
    # Summary table
    print(f"\n## 📊 CoinAPI Data Availability for 2025-09-12 (Corrected Query)")
    print("| Venue | HTTP | Objects | Size (MB) | Status |")
    print("|-------|------|---------|-----------|--------|")
    
    for result in results:
        status = "✅ AVAILABLE" if result['has_data'] else "❌ NOT_FOUND"
        print(f"| {result['venue']} | {result['http_status']} | {result['object_count']} | {result['total_size_mb']:.2f} | {status} |")
    
    # Detailed results for venues with data
    print(f"\n## 📋 Detailed Results")
    
    for result in results:
        if result['has_data']:
            print(f"\n### {result['venue']} - {result['object_count']} objects, {result['total_size_mb']:.2f} MB")
            for obj in result['objects']:
                size_mb = obj['size'] / 1024 / 1024
                print(f"  📁 {obj['key']} ({size_mb:.2f} MB)")
                if obj['last_modified']:
                    print(f"     Modified: {obj['last_modified']}")
    
    # Final assessment
    available_venues = [r for r in results if r['has_data']]
    missing_venues = [r for r in results if not r['has_data']]
    
    print(f"\n## 🎯 Final Assessment")
    print(f"✅ Available on CoinAPI: {len(available_venues)} venues")
    for venue in available_venues:
        print(f"  - {venue['venue']}: {venue['object_count']} objects, {venue['total_size_mb']:.2f} MB")
    
    print(f"❌ Missing on CoinAPI: {len(missing_venues)} venues")
    for venue in missing_venues:
        print(f"  - {venue['venue']}: No data found")

if __name__ == "__main__":
    main()




