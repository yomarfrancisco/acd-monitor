#!/usr/bin/env python3
"""
🔧 Schema Probe (Step 1) - Discover actual CSV headers and field mappings
"""

import os
import pandas as pd
import gzip

def probe_file_schema(file_path, venue, date):
    """Probe a single file to discover its schema"""
    print(f"\n🔍 Probing {venue} {date}: {os.path.basename(file_path)}")
    
    if not os.path.exists(file_path):
        print(f"  ❌ File not found: {file_path}")
        return None
    
    try:
        # Read just the header to get column names
        with gzip.open(file_path, 'rt') as f:
            header_line = f.readline().strip()
        
        print(f"  📋 Raw header: {header_line}")
        
        # Use pandas to get column names
        df_headers = pd.read_csv(file_path, compression='gzip', nrows=0, sep=';')
        columns = list(df_headers.columns)
        print(f"  📊 Column names: {columns}")
        
        # Read a small sample to inspect values
        df_sample = pd.read_csv(file_path, compression='gzip', nrows=20, sep=';')
        print(f"  📈 Sample shape: {df_sample.shape}")
        
        # Find timestamp candidates
        timestamp_candidates = ['time_exchange', 'time_coinapi', 'timestamp', 'time', 'ts']
        timestamp_col = None
        for candidate in timestamp_candidates:
            if candidate in columns:
                timestamp_col = candidate
                break
        
        if timestamp_col:
            print(f"  ⏰ Timestamp column: {timestamp_col}")
            # Show 10 example timestamp values
            ts_values = df_sample[timestamp_col].dropna().head(10)
            print(f"  ⏰ Sample timestamps: {list(ts_values)}")
        else:
            print(f"  ❌ No timestamp column found in candidates: {timestamp_candidates}")
            return None
        
        # Find price candidates
        price_candidates = ['price', 'price_trade', 'trade_price']
        price_col = None
        for candidate in price_candidates:
            if candidate in columns:
                price_col = candidate
                break
        
        if price_col:
            print(f"  💰 Price column: {price_col}")
            # Show 5 example price values
            price_values = df_sample[price_col].dropna().head(5)
            print(f"  💰 Sample prices: {list(price_values)}")
        else:
            print(f"  ❌ No price column found in candidates: {price_candidates}")
            return None
        
        # Find size/amount candidates
        size_candidates = ['size', 'amount', 'quantity', 'volume', 'base_amount']
        size_col = None
        for candidate in size_candidates:
            if candidate in columns:
                size_col = candidate
                break
        
        if size_col:
            print(f"  📏 Size column: {size_col}")
            # Show 5 example size values
            size_values = df_sample[size_col].dropna().head(5)
            print(f"  📏 Sample sizes: {list(size_values)}")
        else:
            print(f"  ❌ No size column found in candidates: {size_candidates}")
            return None
        
        return {
            'venue': venue,
            'date': date,
            'timestamp_col': timestamp_col,
            'price_col': price_col,
            'size_col': size_col,
            'all_columns': columns
        }
        
    except Exception as e:
        print(f"  ❌ Error probing file: {e}")
        return None

def main():
    """Main function - Schema Probe Step 1"""
    print("🔧 Schema Probe (Step 1) - Discover CSV Headers and Field Mappings")
    print("=" * 80)
    
    # Representative files to probe
    probe_files = [
        # 2025-08-04
        ('BINANCE', '20250804', 'analysis/flatfiles_ticks_v4/raw/BINANCE_20250804_BTCUSDT.csv.gz'),
        ('COINBASE', '20250804', 'analysis/flatfiles_ticks_v4/raw/COINBASE_20250804_BTCUSD.csv.gz'),
        ('BYBITSPOT', '20250804', 'analysis/flatfiles_ticks_v4/raw/BYBITSPOT_20250804_BTCUSDT.csv.gz'),
        ('BITGET', '20250804', 'analysis/flatfiles_ticks_v4/raw/BITGET_20250804_BTCUSDT.csv.gz'),
        # 2025-08-25
        ('BINANCE', '20250825', 'analysis/flatfiles_ticks_v4/raw/BINANCE_20250825_BTCUSDT.csv.gz'),
        ('COINBASE', '20250825', 'analysis/flatfiles_ticks_v4/raw/COINBASE_20250825_BTCUSD.csv.gz'),
        ('BYBITSPOT', '20250825', 'analysis/flatfiles_ticks_v4/raw/BYBITSPOT_20250825_BTCUSDT.csv.gz'),
        ('BITGET', '20250825', 'analysis/flatfiles_ticks_v4/raw/BITGET_20250825_BTCUSDT.csv.gz'),
    ]
    
    print(f"📋 Probing {len(probe_files)} representative files...")
    
    results = []
    venue_mappings = {}
    
    for venue, date, file_path in probe_files:
        result = probe_file_schema(file_path, venue, date)
        if result:
            results.append(result)
            venue_mappings[venue] = result
    
    print(f"\n{'='*80}")
    print(f"📊 SCHEMA PROBE RESULTS")
    print(f"{'='*80}")
    
    # Check if all venues have required mappings
    required_venues = ['BINANCE', 'COINBASE', 'BYBITSPOT', 'BITGET']
    missing_venues = []
    
    for venue in required_venues:
        if venue not in venue_mappings:
            missing_venues.append(venue)
        else:
            mapping = venue_mappings[venue]
            print(f"[MAPPING] VENUE={venue}: ts={mapping['timestamp_col']}, price={mapping['price_col']}, size={mapping['size_col']}")
    
    if missing_venues:
        print(f"\n❌ STOP: Missing mappings for venues: {missing_venues}")
        return False
    
    # Check if all venues have the same mapping (consistency check)
    base_mapping = venue_mappings['BINANCE']
    consistent = True
    
    for venue in required_venues:
        mapping = venue_mappings[venue]
        if (mapping['timestamp_col'] != base_mapping['timestamp_col'] or
            mapping['price_col'] != base_mapping['price_col'] or
            mapping['size_col'] != base_mapping['size_col']):
            print(f"⚠️  {venue} has different mapping than BINANCE")
            consistent = False
    
    if consistent:
        print(f"\n✅ All venues have consistent mapping:")
        print(f"   ts → {base_mapping['timestamp_col']}")
        print(f"   price → {base_mapping['price_col']}")
        print(f"   size → {base_mapping['size_col']}")
        print(f"\n✅ Schema probe completed successfully - ready for Step 2")
        return True
    else:
        print(f"\n❌ STOP: Inconsistent mappings across venues")
        return False

if __name__ == "__main__":
    success = main()
    if not success:
        exit(1)
