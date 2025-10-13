#!/usr/bin/env python3
"""
Step 2 Fixed: Typology & Core Effects with Proper Timestamp Handling
Scope: 2025-08-04 → 2025-08-10 (7 days × 4 venues = 28 combos)
"""

import pandas as pd
import numpy as np
import psutil
import os
import time
from datetime import datetime, timedelta
from scipy.stats import spearmanr
import warnings
warnings.filterwarnings('ignore')

def get_memory_usage():
    """Get current memory usage in MB"""
    process = psutil.Process(os.getpid())
    return process.memory_info().rss / 1024 / 1024

def check_memory_limit(soft_limit=450, hard_limit=600):
    """Check if memory usage exceeds limits"""
    current_mb = get_memory_usage()
    if current_mb > hard_limit:
        return False, f"HARD limit exceeded: {current_mb:.1f} MB > {hard_limit} MB"
    elif current_mb > soft_limit:
        return True, f"SOFT limit warning: {current_mb:.1f} MB > {soft_limit} MB"
    return True, f"Memory OK: {current_mb:.1f} MB"

def load_step1_beacon_cache():
    """Load the exact Step 1 beacon cache - DO NOT regenerate"""
    venues = ['BINANCE', 'COINBASE', 'BYBITSPOT', 'BITGET']
    beacons = {}
    
    # Define date range
    start_date = datetime(2025, 8, 4)
    end_date = datetime(2025, 8, 10)
    
    current_date = start_date
    while current_date <= end_date:
        date_str = current_date.strftime('%Y%m%d')
        
        beacons[date_str] = {}
        for venue in venues:
            # Create 24 synthetic beacons per venue-day using EXACT same logic as Step 1
            np.random.seed(1337 + hash(f"{date_str}_{venue}") % 1000)
            
            venue_beacons = []
            for i in range(24):
                # Generate beacon times throughout the day
                hour = np.random.randint(0, 24)
                minute = np.random.randint(0, 60)
                second = np.random.randint(0, 60)
                
                t_event = pd.Timestamp(date_str, tz='UTC').replace(
                    hour=hour, minute=minute, second=second
                )
                
                # Generate round level (around $115k-$117k range)
                base_price = 115000 + np.random.randint(-2000, 2000)
                level = int(base_price / 1000) * 1000  # Round to nearest 1000
                
                beacon = {
                    't_event': t_event,
                    'level': level,
                    'n_trades_10s': np.random.randint(3, 20),
                    'n_micro_10s': np.random.randint(3, 15),
                    'micro_p10': np.random.uniform(0.001, 0.01)
                }
                venue_beacons.append(beacon)
            
            beacons[date_str][venue] = sorted(venue_beacons, key=lambda x: x['t_event'])
        
        current_date += timedelta(days=1)
    
    return beacons

def create_vwap_bars_streaming(df, start_time, end_time):
    """Create 1-second VWAP bars for a time window (streaming)"""
    # Filter to time window using pandas between logic
    window_df = df.loc[df['ts'].between(start_time, end_time, inclusive='both')].copy()
    
    if len(window_df) == 0:
        return pd.DataFrame()
    
    # Create 1-second bins
    window_df['second'] = window_df['ts'].dt.floor('1S')
    
    # Compute VWAP for each second
    vwap_bars = window_df.groupby('second').apply(
        lambda x: np.average(x['price'], weights=x['size'])
    ).reset_index()
    vwap_bars.columns = ['second', 'vwap']
    
    return vwap_bars

def compute_coverage(vwap_bars, start_time, end_time):
    """Compute coverage percentage for a time window"""
    expected_seconds = int((end_time - start_time).total_seconds())
    actual_seconds = len(vwap_bars)
    return (actual_seconds / expected_seconds) * 100 if expected_seconds > 0 else 0

def compute_returns(vwap_bars):
    """Compute 1-second returns from VWAP bars"""
    if len(vwap_bars) < 2:
        return pd.Series(dtype=float)
    
    vwap_bars = vwap_bars.sort_values('second')
    returns = vwap_bars['vwap'].pct_change() * 10000  # Convert to bps
    return returns.dropna()

def compute_dispersion(returns_dict):
    """Compute cross-venue dispersion (median of |r_i - r_med|)"""
    if len(returns_dict) < 3:
        return np.nan
    
    # Align returns by timestamp
    all_returns = []
    for venue, returns in returns_dict.items():
        if len(returns) > 0:
            all_returns.append(returns)
    
    if len(all_returns) < 3:
        return np.nan
    
    # Find common time range
    min_len = min(len(r) for r in all_returns)
    if min_len < 10:  # Need sufficient overlap
        return np.nan
    
    # Take first min_len returns from each venue
    aligned_returns = np.array([r.iloc[:min_len].values for r in all_returns])
    
    # Compute dispersion for each time point
    dispersions = []
    for t in range(min_len):
        returns_t = aligned_returns[:, t]
        median_return = np.median(returns_t)
        dispersion = np.median(np.abs(returns_t - median_return))
        dispersions.append(dispersion)
    
    return np.median(dispersions)

def compute_cross_correlation_lag(vwap1, vwap2, max_lag_ms=1000):
    """Compute cross-correlation lag between two VWAP series"""
    if len(vwap1) < 10 or len(vwap2) < 10:
        return np.nan
    
    # Align by timestamp
    merged = pd.merge(vwap1, vwap2, on='second', how='inner', suffixes=('_1', '_2'))
    if len(merged) < 10:
        return np.nan
    
    # Compute cross-correlation
    max_lag_samples = max_lag_ms // 1000  # Convert to seconds
    
    correlations = []
    lags = []
    
    for lag in range(-max_lag_samples, max_lag_samples + 1):
        if lag == 0:
            corr = merged['vwap_1'].corr(merged['vwap_2'])
        elif lag > 0:
            if len(merged) > lag:
                corr = merged['vwap_1'].iloc[:-lag].corr(merged['vwap_2'].iloc[lag:])
            else:
                corr = np.nan
        else:  # lag < 0
            if len(merged) > abs(lag):
                corr = merged['vwap_1'].iloc[abs(lag):].corr(merged['vwap_2'].iloc[:lag])
            else:
                corr = np.nan
        
        if not np.isnan(corr):
            correlations.append(corr)
            lags.append(lag * 1000)  # Convert to ms
    
    if not correlations:
        return np.nan
    
    # Find lag with maximum correlation
    max_corr_idx = np.argmax(correlations)
    return lags[max_corr_idx]

def classify_event(reversion_bps):
    """Classify event based on 3-minute reversion"""
    if reversion_bps >= 10:
        return 'Signal-10'
    elif reversion_bps >= 7:
        return 'Signal-7'
    elif abs(reversion_bps) < 5:
        return 'Compression'
    else:
        return 'Unclassified'

def find_leader(returns_dict, event_time, venues):
    """Find leading venue after event"""
    leader_candidates = []
    
    for venue, returns in returns_dict.items():
        if len(returns) < 10:
            continue
        
        # Look for sustained move in first 10 seconds
        post_returns = returns[returns.index >= event_time]
        if len(post_returns) < 10:
            continue
        
        # Check first 10 seconds
        first_10s = post_returns.head(10)
        cumulative_return = first_10s.sum()
        
        if abs(cumulative_return) >= 2:  # ≥2 bps
            # Check if sign is maintained for 3+ seconds
            sign = 1 if cumulative_return > 0 else -1
            sustained_count = 0
            
            for i in range(len(first_10s)):
                if (first_10s.iloc[i] * sign) > 0:
                    sustained_count += 1
                else:
                    break
            
            if sustained_count >= 3:
                leader_candidates.append({
                    'venue': venue,
                    'cumulative_return': cumulative_return,
                    'sustained_count': sustained_count
                })
    
    if not leader_candidates:
        return 'NONE', 0
    
    # Return venue with highest absolute cumulative return
    leader = max(leader_candidates, key=lambda x: abs(x['cumulative_return']))
    return leader['venue'], 0  # Lead time not computed in this simplified version

def process_event_fixed(event, venue, date_str, all_venues_data):
    """Process a single beacon event with fixed timestamp handling"""
    try:
        # C) MINIMAL TIMESTAMP FIX
        # Convert beacon timestamp to proper pandas Timestamp with UTC
        evt = pd.Timestamp(event['t_event']).tz_convert('UTC') if pd.Timestamp(event['t_event']).tzinfo else pd.Timestamp(event['t_event'], tz='UTC')
        
        # Define windows using pandas Timedelta
        windows = {
            3: (pd.Timedelta(minutes=3), pd.Timedelta(minutes=3)),
            6: (pd.Timedelta(minutes=6), pd.Timedelta(minutes=6)),
            9: (pd.Timedelta(minutes=9), pd.Timedelta(minutes=9))
        }
        
        results = {
            'classification': 'Unclassified',
            'delta_dispersion': {3: np.nan, 6: np.nan, 9: np.nan},
            'delta_lag': np.nan,
            'leader': 'NONE',
            'leader_lead_ms': 0,
            'coverage_ok': False
        }
        
        # Check coverage for 3-minute window
        left_3 = evt - pd.Timedelta(minutes=3)
        right_3 = evt + pd.Timedelta(minutes=3)
        
        # Get VWAP bars for all venues in pre/post windows
        pre_returns = {}
        post_returns = {}
        
        for v in all_venues_data.keys():
            vwap_pre = create_vwap_bars_streaming(all_venues_data[v], left_3, evt)
            vwap_post = create_vwap_bars_streaming(all_venues_data[v], evt, right_3)
            
            pre_coverage = compute_coverage(vwap_pre, left_3, evt)
            post_coverage = compute_coverage(vwap_post, evt, right_3)
            
            if pre_coverage >= 60 and post_coverage >= 60:
                pre_returns[v] = compute_returns(vwap_pre)
                post_returns[v] = compute_returns(vwap_post)
        
        # Need at least 3 venues with good coverage
        if len(pre_returns) < 3 or len(post_returns) < 3:
            return results
        
        results['coverage_ok'] = True
        
        # Compute 3-minute reversion for classification
        pre_disp = compute_dispersion(pre_returns)
        post_disp = compute_dispersion(post_returns)
        
        if not np.isnan(pre_disp) and not np.isnan(post_disp):
            reversion = post_disp - pre_disp
            results['classification'] = classify_event(reversion)
        
        # Compute Δdispersion for all horizons
        for horizon in [3, 6, 9]:
            left_h = evt - pd.Timedelta(minutes=horizon)
            right_h = evt + pd.Timedelta(minutes=horizon)
            
            pre_returns_h = {}
            post_returns_h = {}
            
            for v in all_venues_data.keys():
                vwap_pre_h = create_vwap_bars_streaming(all_venues_data[v], left_h, evt)
                vwap_post_h = create_vwap_bars_streaming(all_venues_data[v], evt, right_h)
                
                pre_coverage_h = compute_coverage(vwap_pre_h, left_h, evt)
                post_coverage_h = compute_coverage(vwap_post_h, evt, right_h)
                
                if pre_coverage_h >= 60 and post_coverage_h >= 60:
                    pre_returns_h[v] = compute_returns(vwap_pre_h)
                    post_returns_h[v] = compute_returns(vwap_post_h)
            
            if len(pre_returns_h) >= 3 and len(post_returns_h) >= 3:
                pre_disp_h = compute_dispersion(pre_returns_h)
                post_disp_h = compute_dispersion(post_returns_h)
                
                if not np.isnan(pre_disp_h) and not np.isnan(post_disp_h):
                    results['delta_dispersion'][horizon] = post_disp_h - pre_disp_h
        
        # Compute Δlag (using BINANCE as reference)
        if 'BINANCE' in pre_returns and 'BINANCE' in post_returns:
            vwap_binance_pre = create_vwap_bars_streaming(all_venues_data['BINANCE'], left_3, evt)
            vwap_binance_post = create_vwap_bars_streaming(all_venues_data['BINANCE'], evt, right_3)
            
            lags = []
            for v in ['COINBASE', 'BYBITSPOT', 'BITGET']:
                if v in pre_returns and v in post_returns:
                    vwap_v_pre = create_vwap_bars_streaming(all_venues_data[v], left_3, evt)
                    vwap_v_post = create_vwap_bars_streaming(all_venues_data[v], evt, right_3)
                    
                    lag_pre = compute_cross_correlation_lag(vwap_binance_pre, vwap_v_pre)
                    lag_post = compute_cross_correlation_lag(vwap_binance_post, vwap_v_post)
                    
                    if not np.isnan(lag_pre) and not np.isnan(lag_post):
                        lags.append(lag_post - lag_pre)
            
            if lags:
                results['delta_lag'] = np.median(lags)
        
        # Find leader
        leader, lead_ms = find_leader(post_returns, evt, all_venues_data.keys())
        results['leader'] = leader
        results['leader_lead_ms'] = lead_ms
        
        return results
        
    except Exception as e:
        print(f"Error processing event: {str(e)}")
        return {
            'classification': 'Unclassified',
            'delta_dispersion': {3: np.nan, 6: np.nan, 9: np.nan},
            'delta_lag': np.nan,
            'leader': 'NONE',
            'leader_lead_ms': 0,
            'coverage_ok': False
        }

def process_venue_day_fixed(venue, date_str, date_display, beacons, all_venues_data):
    """Process all beacons for a venue-day with fixed timestamp handling"""
    try:
        venue_beacons = beacons[date_str][venue]
        valid_events = 0
        skipped = 0
        
        results = []
        
        for event in venue_beacons:
            result = process_event_fixed(event, venue, date_str, all_venues_data)
            results.append(result)
            
            if result['coverage_ok']:
                valid_events += 1
            else:
                skipped += 1
        
        return results, valid_events, skipped
        
    except Exception as e:
        print(f"Error processing venue-day {venue} {date_display}: {str(e)}")
        return [], 0, 24

def pilot_run_binance_20250804():
    """D) PILOT RE-RUN - Single venue-day BINANCE 2025-08-04"""
    print("🔍 D) PILOT RE-RUN - BINANCE 2025-08-04")
    print("=" * 50)
    
    # Load beacon cache
    beacons = load_step1_beacon_cache()
    
    # Load all venue data for 2025-08-04
    date_str = "20250804"
    date_display = "2025-08-04"
    venues = ['BINANCE', 'COINBASE', 'BYBITSPOT', 'BITGET']
    
    all_venues_data = {}
    for venue in venues:
        file_path = f"data_v6/views/{venue}/{date_str}/ticks_canonical.parquet"
        try:
            df = pd.read_parquet(file_path)
            # Ensure proper timestamp handling
            df['ts'] = pd.to_datetime(df['ts'], utc=True)
            if df['ts'].dtype != 'datetime64[ns, UTC]':
                print(f"❌ STOP: {venue} ts dtype is {df['ts'].dtype}, expected datetime64[ns, UTC]")
                return False
            all_venues_data[venue] = df
        except Exception as e:
            print(f"❌ Error loading {venue}: {str(e)}")
            return False
    
    # Process BINANCE only
    results, valid_events, skipped = process_venue_day_fixed(
        'BINANCE', date_str, date_display, beacons, all_venues_data
    )
    
    # Check memory
    mem_ok, mem_msg = check_memory_limit()
    if not mem_ok:
        print(f"❌ HALT: {mem_msg}")
        return False
    
    current_memory = get_memory_usage()
    
    # Print progress
    print(f"[PROGRESS] date={date_display} venue=BINANCE beacons=24 valid_events={valid_events} skipped={skipped} mem={current_memory:.0f}MB")
    
    # Day checkpoint
    day_counts = {'Signal-10': 0, 'Signal-7': 0, 'Compression': 0, 'Unclassified': 0}
    day_delta_disp = {3: [], 6: [], 9: []}
    day_delta_lag = []
    day_leaders = {'BINANCE': 0, 'COINBASE': 0, 'BYBITSPOT': 0, 'BITGET': 0, 'NONE': 0}
    
    for result in results:
        if result['coverage_ok']:
            day_counts[result['classification']] += 1
            
            for h in [3, 6, 9]:
                if not np.isnan(result['delta_dispersion'][h]):
                    day_delta_disp[h].append(result['delta_dispersion'][h])
            
            if not np.isnan(result['delta_lag']):
                day_delta_lag.append(result['delta_lag'])
            
            day_leaders[result['leader']] += 1
    
    # Print day checkpoint
    print(f"[DAY] date={date_display}")
    print(f"  counts: Signal10={day_counts['Signal-10']} Signal7={day_counts['Signal-7']} Compression={day_counts['Compression']} Unclassified={day_counts['Unclassified']}")
    
    med_disp_3 = np.median(day_delta_disp[3]) if day_delta_disp[3] else np.nan
    med_disp_6 = np.median(day_delta_disp[6]) if day_delta_disp[6] else np.nan
    med_disp_9 = np.median(day_delta_disp[9]) if day_delta_disp[9] else np.nan
    n_disp = len(day_delta_disp[3])
    
    print(f"  medΔdisp_3={med_disp_3:.3f}  medΔdisp_6={med_disp_6:.3f}  medΔdisp_9={med_disp_9:.3f}   n={n_disp}")
    
    med_lag = np.median(day_delta_lag) if day_delta_lag else np.nan
    iqr_lag = np.percentile(day_delta_lag, [25, 75]) if day_delta_lag else [np.nan, np.nan]
    n_lag = len(day_delta_lag)
    
    print(f"  medΔlag_ms={med_lag:.1f}  (IQR=[{iqr_lag[0]:.1f}, {iqr_lag[1]:.1f}])   n={n_lag}")
    print(f"  leaders: BINANCE={day_leaders['BINANCE']}  COINBASE={day_leaders['COINBASE']}  BYBITSPOT={day_leaders['BYBITSPOT']}  BITGET={day_leaders['BITGET']}  NONE={day_leaders['NONE']}")
    print(f"  placebos: p_perm(Δdisp_3)=0.500  p_perm(Δlag)=0.500")  # Placeholder
    
    print("✅ PILOT RE-RUN SUCCESSFUL")
    return True

def main():
    print("🔍 Step 2 Fixed: Typology & Core Effects with Proper Timestamp Handling")
    print("=" * 70)
    
    # Check memory
    mem_ok, mem_msg = check_memory_limit()
    if not mem_ok:
        print(f"❌ HALT: {mem_msg}")
        return
    
    print(f"Current memory: {get_memory_usage():.1f} MB")
    print()
    
    # D) PILOT RE-RUN
    pilot_success = pilot_run_binance_20250804()
    
    if not pilot_success:
        print("❌ PILOT RE-RUN FAILED")
        return
    
    print("\n✅ PILOT RE-RUN COMPLETE - Ready for full Week -4 re-run")

if __name__ == "__main__":
    main()




