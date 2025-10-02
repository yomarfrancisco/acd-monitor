#!/usr/bin/env python3
"""
CoinAPI Flat Files - Task 0: Access Check

Verify account/credits access and list available datasets for BTC spot trades.
"""

import argparse
import json
import logging
import os
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Dict, List, Any, Optional

import boto3
import requests

def setup_logging(verbose: bool = False):
    """Setup logging configuration."""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler("coinapi_task0_access_check.log"),
        ],
    )

def get_coinapi_key() -> str:
    """Get CoinAPI key from environment variable."""
    api_key = os.getenv('COINAPI_KEY')
    if not api_key:
        raise ValueError("COINAPI_KEY environment variable not set")
    return api_key

def check_api_access(api_key: str) -> Dict[str, Any]:
    """Check basic API access and credits."""
    logger = logging.getLogger(__name__)
    
    headers = {"X-CoinAPI-Key": api_key}
    
    # Test basic endpoints
    test_endpoints = [
        "https://rest.coinapi.io/v1/exchanges",
        "https://rest.coinapi.io/v1/symbols",
        "https://rest.coinapi.io/v1/assets"
    ]
    
    access_results = {}
    
    for endpoint in test_endpoints:
        try:
            logger.info(f"Testing endpoint: {endpoint}")
            response = requests.get(endpoint, headers=headers, timeout=30)
            
            access_results[endpoint] = {
                "status_code": response.status_code,
                "success": response.status_code == 200,
                "error": None
            }
            
            if response.status_code == 200:
                data = response.json()
                access_results[endpoint]["data_count"] = len(data) if isinstance(data, list) else 1
                logger.info(f"✅ {endpoint}: {response.status_code}")
            else:
                access_results[endpoint]["error"] = response.text[:200]
                logger.warning(f"❌ {endpoint}: {response.status_code} - {response.text[:100]}")
                
        except Exception as e:
            access_results[endpoint] = {
                "status_code": None,
                "success": False,
                "error": str(e)
            }
            logger.error(f"❌ {endpoint}: Exception - {e}")
    
    return access_results

def check_flat_files_access(api_key: str) -> Dict[str, Any]:
    """Check Flat Files API access for BTC spot trades."""
    logger = logging.getLogger(__name__)
    
    headers = {"X-CoinAPI-Key": api_key}
    
    # Test Flat Files for recent dates
    today = datetime.now(timezone.utc)
    test_dates = [
        (today - timedelta(days=1)).strftime("%Y%m%d"),
        (today - timedelta(days=2)).strftime("%Y%m%d"),
        (today - timedelta(days=3)).strftime("%Y%m%d")
    ]
    
    # Test exchanges and symbols
    test_combinations = [
        ("BINANCE", "BTC_USDT"),
        ("KRAKEN", "BTC_USD"), 
        ("COINBASE", "BTC_USD"),
        ("OKX", "BTC_USDT"),
        ("BYBIT", "BTC_USDT")
    ]
    
    flat_files_results = {}
    
    for date in test_dates:
        flat_files_results[date] = {}
        
        for exchange, symbol in test_combinations:
            # Try trades flat file
            endpoint = f"https://rest.coinapi.io/v1/flatfiles/trades/{exchange}_SPOT_{symbol}/{date}"
            
            try:
                logger.info(f"Testing Flat File: {exchange}_{symbol} for {date}")
                response = requests.get(endpoint, headers=headers, timeout=30)
                
                flat_files_results[date][f"{exchange}_{symbol}"] = {
                    "status_code": response.status_code,
                    "success": response.status_code == 200,
                    "content_type": response.headers.get('content-type', ''),
                    "content_length": response.headers.get('content-length', ''),
                    "error": None
                }
                
                if response.status_code == 200:
                    logger.info(f"✅ {exchange}_{symbol} for {date}: {response.status_code}")
                else:
                    flat_files_results[date][f"{exchange}_{symbol}"]["error"] = response.text[:200]
                    logger.warning(f"❌ {exchange}_{symbol} for {date}: {response.status_code}")
                    
            except Exception as e:
                flat_files_results[date][f"{exchange}_{symbol}"] = {
                    "status_code": None,
                    "success": False,
                    "error": str(e)
                }
                logger.error(f"❌ {exchange}_{symbol} for {date}: Exception - {e}")
    
    return flat_files_results

def discover_available_exchanges(api_key: str) -> List[Dict[str, Any]]:
    """Discover available exchanges from CoinAPI."""
    logger = logging.getLogger(__name__)
    
    headers = {"X-CoinAPI-Key": api_key}
    url = "https://rest.coinapi.io/v1/exchanges"
    
    try:
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()
        exchanges = response.json()
        
        logger.info(f"Found {len(exchanges)} exchanges")
        return exchanges
        
    except requests.exceptions.RequestException as e:
        logger.error(f"Error discovering exchanges: {e}")
        return []

def discover_available_symbols(api_key: str) -> List[Dict[str, Any]]:
    """Discover available symbols from CoinAPI."""
    logger = logging.getLogger(__name__)
    
    headers = {"X-CoinAPI-Key": api_key}
    url = "https://rest.coinapi.io/v1/symbols"
    
    try:
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()
        symbols = response.json()
        
        logger.info(f"Found {len(symbols)} symbols")
        return symbols
        
    except requests.exceptions.RequestException as e:
        logger.error(f"Error discovering symbols: {e}")
        return []

def filter_btc_spot_symbols(symbols: List[Dict[str, Any]], target_exchanges: List[str]) -> Dict[str, List[Dict[str, Any]]]:
    """Filter symbols for BTC spot pairs on target exchanges."""
    logger = logging.getLogger(__name__)
    
    btc_symbols = {}
    
    for symbol in symbols:
        symbol_id = symbol.get('symbol_id', '')
        exchange_id = symbol.get('exchange_id', '')
        
        # Check if it's a BTC spot pair
        if not (symbol_id.startswith('BTC') and 'SPOT' in symbol_id):
            continue
        
        # Check if it's on a target exchange
        if exchange_id.upper() not in [e.upper() for e in target_exchanges]:
            continue
        
        # Extract pair type
        if 'USDT' in symbol_id:
            pair_type = 'USDT'
        elif 'USD' in symbol_id:
            pair_type = 'USD'
        else:
            continue
        
        if exchange_id not in btc_symbols:
            btc_symbols[exchange_id] = []
        
        btc_symbols[exchange_id].append({
            'symbol_id': symbol_id,
            'exchange_id': exchange_id,
            'pair_type': pair_type,
            'asset_id_base': symbol.get('asset_id_base'),
            'asset_id_quote': symbol.get('asset_id_quote'),
            'data_start': symbol.get('data_start'),
            'data_end': symbol.get('data_end'),
            'volume_1day_usd': symbol.get('volume_1day_usd')
        })
    
    # Sort by preference (USDT first, then by volume)
    for exchange_id in btc_symbols:
        btc_symbols[exchange_id].sort(
            key=lambda x: (x['pair_type'] != 'USDT', -x.get('volume_1day_usd', 0))
        )
    
    logger.info(f"Found BTC spot symbols for {len(btc_symbols)} exchanges")
    return btc_symbols

def save_access_check(s3_client, bucket: str, access_results: Dict[str, Any], flat_files_results: Dict[str, Any], btc_symbols: Dict[str, List[Dict[str, Any]]]) -> str:
    """Save access check results to S3."""
    logger = logging.getLogger(__name__)
    
    # Check if any basic access succeeded
    basic_access_ok = any(result.get('success', False) for result in access_results.values())
    
    # Check if any flat files access succeeded
    flat_files_ok = False
    for date_results in flat_files_results.values():
        if any(result.get('success', False) for result in date_results.values()):
            flat_files_ok = True
            break
    
    access_check = {
        "check_timestamp": datetime.now(timezone.utc).isoformat(),
        "basic_access_ok": basic_access_ok,
        "flat_files_ok": flat_files_ok,
        "access_results": access_results,
        "flat_files_results": flat_files_results,
        "btc_symbols": btc_symbols,
        "summary": {
            "total_exchanges_with_btc": len(btc_symbols),
            "exchanges_with_btc": list(btc_symbols.keys()),
            "total_btc_symbols": sum(len(symbols) for symbols in btc_symbols.values())
        }
    }
    
    s3_key = "analysis/coinapi_bf1/_inv/access_check.json"
    s3_client.put_object(
        Bucket=bucket,
        Key=s3_key,
        Body=json.dumps(access_check, indent=2),
        ContentType='application/json'
    )
    
    logger.info(f"Saved access check: s3://{bucket}/{s3_key}")
    return s3_key

def main():
    """Main access check function."""
    parser = argparse.ArgumentParser(description='CoinAPI Flat Files - Task 0: Access Check')
    parser.add_argument('--verbose', action='store_true', help='Verbose logging')
    parser.add_argument('--bucket', default='acd-monitor-snapshots', help='S3 bucket name')
    
    args = parser.parse_args()
    setup_logging(args.verbose)
    logger = logging.getLogger(__name__)
    
    # Initialize S3 client
    s3_client = boto3.client('s3')
    
    print("\n" + "="*80)
    print("🔍 COINAPI FLAT FILES - TASK 0: ACCESS CHECK")
    print("="*80)
    
    # Get API key
    try:
        api_key = get_coinapi_key()
        print(f"✅ CoinAPI key loaded: {api_key[:8]}...")
    except ValueError as e:
        print(f"❌ {e}")
        sys.exit(1)
    
    # Check basic API access
    print(f"\n🔍 Checking basic API access...")
    access_results = check_api_access(api_key)
    
    basic_access_ok = any(result.get('success', False) for result in access_results.values())
    if basic_access_ok:
        print(f"✅ Basic API access confirmed")
    else:
        print(f"❌ Basic API access failed")
        print(f"   All endpoints returned errors")
        sys.exit(1)
    
    # Check Flat Files access
    print(f"\n🔍 Checking Flat Files access...")
    flat_files_results = check_flat_files_access(api_key)
    
    flat_files_ok = False
    for date_results in flat_files_results.values():
        if any(result.get('success', False) for result in date_results.values()):
            flat_files_ok = True
            break
    
    if flat_files_ok:
        print(f"✅ Flat Files access confirmed")
    else:
        print(f"❌ Flat Files access failed")
        print(f"   No flat files accessible for any date/exchange combination")
        sys.exit(1)
    
    # Discover exchanges and symbols
    print(f"\n🔍 Discovering exchanges and symbols...")
    
    exchanges = discover_available_exchanges(api_key)
    symbols = discover_available_symbols(api_key)
    
    if not exchanges or not symbols:
        print(f"❌ Failed to discover exchanges or symbols")
        sys.exit(1)
    
    # Filter BTC spot symbols
    target_exchanges = ['BINANCE', 'KRAKEN', 'COINBASE', 'OKX', 'BYBIT']
    btc_symbols = filter_btc_spot_symbols(symbols, target_exchanges)
    
    if not btc_symbols:
        print(f"❌ No BTC spot symbols found for target exchanges")
        sys.exit(1)
    
    print(f"✅ Found BTC spot symbols for {len(btc_symbols)} exchanges")
    
    # Save access check results
    print(f"\n💾 Saving access check results...")
    try:
        s3_key = save_access_check(s3_client, args.bucket, access_results, flat_files_results, btc_symbols)
        print(f"✅ Saved: s3://{args.bucket}/{s3_key}")
    except Exception as e:
        print(f"❌ Error saving access check: {e}")
        sys.exit(1)
    
    # Display summary
    print(f"\n📊 ACCESS CHECK SUMMARY")
    print("="*60)
    print(f"Basic API access: {'✅' if basic_access_ok else '❌'}")
    print(f"Flat Files access: {'✅' if flat_files_ok else '❌'}")
    print(f"Exchanges with BTC: {len(btc_symbols)}")
    print(f"Total BTC symbols: {sum(len(symbols) for symbols in btc_symbols.values())}")
    
    for exchange_id, symbols_list in btc_symbols.items():
        print(f"\n{exchange_id.upper()}:")
        for i, symbol in enumerate(symbols_list[:3]):  # Show top 3
            print(f"  {i+1}. {symbol['symbol_id']} ({symbol['pair_type']})")
        if len(symbols_list) > 3:
            print(f"     ... and {len(symbols_list) - 3} more")
    
    if basic_access_ok and flat_files_ok and len(btc_symbols) >= 3:
        print(f"\n✅ ACCESS CHECK PASSED - Proceeding to Task 1")
    else:
        print(f"\n❌ ACCESS CHECK FAILED - Cannot proceed")
        sys.exit(1)

if __name__ == "__main__":
    main()
