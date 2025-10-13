#!/usr/bin/env python3
"""
CoinAPI Prefix Validation for BITGET 2025-09-13
Test different prefix patterns to find the correct data location
"""

import os
import requests
import xml.etree.ElementTree as ET

def get_coinapi_key():
    """Get CoinAPI key from environment"""
    return os.environ.get('COINAPI_KEY', '7f036b38-38d6-4ed6-9fce-00a06280a0f6')

def list_coinapi_prefix(prefix):
    """List objects for a specific prefix"""
    base_url = "https://s3.flatfiles.coinapi.io"
    
    headers = {
        'X-CoinAPI-Key': get_coinapi_key()
    }
    
    params = {
        'list-type': '2',
        'prefix': prefix,
        'max-keys': '10'  # Limit to first 10 objects
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
            objects.append({'key': key, 'size': size})
        
        return objects
    except Exception as e:
        return []

def main():
    """Main prefix validation function"""
    print("🔍 CoinAPI Prefix Validation for BITGET 2025-09-13")
    print("=" * 60)
    
    date = "20250913"
    venue = "BITGET"
    
    # Define the four prefix patterns to test
    prefixes = [
        f"T-TRADES/D-{date}/E-{venue}/",
        f"T-TRADES-EXCHANGE/D-{date}/E-{venue}/",
        f"T-TRADES/D-{date}/E-SPOT_{venue}/",
        f"T-TRADES/D-{date}/E-SPOT-{venue}/"
    ]
    
    results = []
    
    for i, prefix in enumerate(prefixes, 1):
        print(f"\n{i}️⃣ Testing prefix: {prefix}")
        print("-" * 50)
        
        # List objects for this prefix
        status_code, xml_content = list_coinapi_prefix(prefix)
        
        if status_code is None:
            print(f"❌ Request failed: {xml_content}")
            results.append({
                'prefix': prefix,
                'http_status': 'ERROR',
                'object_count': 0,
                'example_keys': [],
                'has_objects': False
            })
            continue
        
        print(f"📡 HTTP Status: {status_code}")
        
        if status_code != 200:
            print(f"❌ HTTP {status_code}: {xml_content[:200]}...")
            results.append({
                'prefix': prefix,
                'http_status': status_code,
                'object_count': 0,
                'example_keys': [],
                'has_objects': False
            })
            continue
        
        # Parse objects
        objects = parse_s3_listing(xml_content)
        object_count = len(objects)
        
        print(f"📊 Object count: {object_count}")
        
        if object_count > 0:
            print(f"✅ FOUND DATA! First {min(2, object_count)} object(s):")
            example_keys = []
            for j, obj in enumerate(objects[:2]):
                print(f"  {j+1}. {obj['key']} ({obj['size']:,} bytes)")
                example_keys.append(obj['key'])
            
            results.append({
                'prefix': prefix,
                'http_status': status_code,
                'object_count': object_count,
                'example_keys': example_keys,
                'has_objects': True
            })
            
            print(f"\n🎯 WORKING PREFIX FOUND: {prefix}")
            print(f"📁 Total objects: {object_count}")
            print(f"📋 Example keys: {example_keys}")
            print(f"\n✅ STOPPING - Found working prefix with {object_count} objects")
            break
        else:
            print(f"❌ No objects found")
            results.append({
                'prefix': prefix,
                'http_status': status_code,
                'object_count': 0,
                'example_keys': [],
                'has_objects': False
            })
    
    # Summary table
    print(f"\n## 📊 Prefix Validation Results")
    print("| Prefix | HTTP Status | Objects | Example Key | Has Data? |")
    print("|--------|-------------|---------|-------------|-----------|")
    
    for result in results:
        status = result['http_status']
        count = result['object_count']
        example = result['example_keys'][0] if result['example_keys'] else "N/A"
        has_data = "✅" if result['has_objects'] else "❌"
        
        print(f"| {result['prefix']} | {status} | {count} | {example[:50]}... | {has_data} |")
    
    # Final assessment
    working_prefixes = [r for r in results if r['has_objects']]
    
    if working_prefixes:
        print(f"\n🎯 **WORKING PREFIX FOUND:** {working_prefixes[0]['prefix']}")
        print(f"📁 Objects available: {working_prefixes[0]['object_count']}")
        print(f"📋 Ready for download from this prefix")
    else:
        print(f"\n❌ **NO WORKING PREFIXES FOUND**")
        print(f"📁 All prefixes returned 0 objects")
        print(f"📋 BITGET data may not be available for 2025-09-13")

if __name__ == "__main__":
    main()




