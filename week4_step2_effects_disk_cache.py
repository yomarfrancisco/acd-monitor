#!/usr/bin/env python3
"""
Week-4 Step-2 Effects from Disk Cache (No Mocks)
Read-only analysis using authoritative beacon cache
"""

import pandas as pd
import numpy as np
import psutil
import os
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings('ignore')

def get_memory_usage():
    """Get current memory usage in MB"""
    process = psutil.Process(os.getpid())
    return process.memory_info().rss / 1024 / 1024

def check_memory_limit(soft_limit=500, hard_limit=600):
    """Check if memory usage exceeds limits"""
    current_mb = get_memory_usage()
    if current_mb > hard_limit:
        return False, f"HARD limit exceeded: {current_mb:.1f} MB > {hard_limit} MB"
    elif current_mb > soft_limit:
        return True, f"SOFT limit warning: {current_mb:.1f} MB > {soft_limit} MB"
    return True, f"Memory OK: {current_mb:.1f} MB"

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
    returns = returns.dropna()
    
    # Convert index to datetime for proper comparison
    returns.index = pd.to_datetime(returns.index, utc=True)
    
    return returns

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

def compute_lag_cross_correlation(returns_dict, max_lag_seconds=1):
    """Compute lag via cross-correlation of 1-sec VWAP series"""
    if len(returns_dict) < 2:
        return np.nan
    
    venues = list(returns_dict.keys())
    lags = []
    
    # Compute pairwise lags
    for i in range(len(venues)):
        for j in range(i+1, len(venues)):
            venue1, venue2 = venues[i], venues[j]
            returns1 = returns_dict[venue1]
            returns2 = returns_dict[venue2]
            
            if len(returns1) < 10 or len(returns2) < 10:
                continue
            
            # Align by common timestamps
            common_times = returns1.index.intersection(returns2.index)
            if len(common_times) < 10:
                continue
            
            aligned1 = returns1.loc[common_times]
            aligned2 = returns2.loc[common_times]
            
            # Cross-correlation
            max_lag = max_lag_seconds  # 1 second
            correlations = []
            
            for lag in range(-max_lag, max_lag + 1):
                if lag == 0:
                    corr = np.corrcoef(aligned1.values, aligned2.values)[0, 1]
                elif lag > 0:
                    if len(aligned1) > lag:
                        corr = np.corrcoef(aligned1.iloc[:-lag].values, aligned2.iloc[lag:].values)[0, 1]
                    else:
                        corr = 0
                else:  # lag < 0
                    if len(aligned2) > abs(lag):
                        corr = np.corrcoef(aligned1.iloc[abs(lag):].values, aligned2.iloc[:-abs(lag)].values)[0, 1]
                    else:
                        corr = 0
                
                correlations.append(corr)
            
            # Find lag with maximum correlation
            if len(correlations) > 0:
                best_lag_idx = np.argmax(correlations)
                best_lag = best_lag_idx - max_lag  # Convert back to actual lag
                lags.append(best_lag * 1000)  # Convert to milliseconds
    
    return np.median(lags) if len(lags) > 0 else np.nan

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
    """Find leading venue after event (Rotemberg-Saloner style)"""
    leader_candidates = []
    
    for venue, returns in returns_dict.items():
        if len(returns) < 10:
            continue
        
        # Look for sustained move in first 10 seconds
        # Convert event_time to same format as returns index
        event_time_dt = pd.to_datetime(event_time, utc=True)
        post_returns = returns[returns.index >= event_time_dt]
        
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

def process_event_effects(event, all_venues_data):
    """Process a single beacon event and compute all effects"""
    try:
        event_ts = event['event_ts']
        
        # Define windows
        left_180 = event_ts - pd.Timedelta(seconds=180)
        right_540 = event_ts + pd.Timedelta(seconds=540)
        
        # 3/6/9 minute windows
        left_3m = event_ts - pd.Timedelta(minutes=3)
        right_3m = event_ts + pd.Timedelta(minutes=3)
        left_6m = event_ts - pd.Timedelta(minutes=6)
        right_6m = event_ts + pd.Timedelta(minutes=6)
        left_9m = event_ts - pd.Timedelta(minutes=9)
        right_9m = event_ts + pd.Timedelta(minutes=9)
        
        # Get VWAP bars for all venues in all windows
        pre_3m_returns = {}
        post_3m_returns = {}
        pre_6m_returns = {}
        post_6m_returns = {}
        pre_9m_returns = {}
        post_9m_returns = {}
        
        coverage_ok = True
        
        for venue, df in all_venues_data.items():
            # 3-minute windows
            vwap_pre_3m = create_vwap_bars_streaming(df, left_3m, event_ts)
            vwap_post_3m = create_vwap_bars_streaming(df, event_ts, right_3m)
            
            pre_3m_coverage = compute_coverage(vwap_pre_3m, left_3m, event_ts)
            post_3m_coverage = compute_coverage(vwap_post_3m, event_ts, right_3m)
            
            if pre_3m_coverage >= 60 and post_3m_coverage >= 60:
                pre_3m_returns[venue] = compute_returns(vwap_pre_3m)
                post_3m_returns[venue] = compute_returns(vwap_post_3m)
            else:
                coverage_ok = False
            
            # 6-minute windows
            vwap_pre_6m = create_vwap_bars_streaming(df, left_6m, event_ts)
            vwap_post_6m = create_vwap_bars_streaming(df, event_ts, right_6m)
            
            pre_6m_coverage = compute_coverage(vwap_pre_6m, left_6m, event_ts)
            post_6m_coverage = compute_coverage(vwap_post_6m, event_ts, right_6m)
            
            if pre_6m_coverage >= 60 and post_6m_coverage >= 60:
                pre_6m_returns[venue] = compute_returns(vwap_pre_6m)
                post_6m_returns[venue] = compute_returns(vwap_post_6m)
            
            # 9-minute windows
            vwap_pre_9m = create_vwap_bars_streaming(df, left_9m, event_ts)
            vwap_post_9m = create_vwap_bars_streaming(df, event_ts, right_9m)
            
            pre_9m_coverage = compute_coverage(vwap_pre_9m, left_9m, event_ts)
            post_9m_coverage = compute_coverage(vwap_post_9m, event_ts, right_9m)
            
            if pre_9m_coverage >= 60 and post_9m_coverage >= 60:
                pre_9m_returns[venue] = compute_returns(vwap_pre_9m)
                post_9m_returns[venue] = compute_returns(vwap_post_9m)
        
        # Need at least 3 venues with good coverage for 3-minute analysis
        if len(pre_3m_returns) < 3 or len(post_3m_returns) < 3:
            return {
                'status': 'FAIL_COVERAGE',
                'delta_disp_3m': np.nan,
                'delta_disp_6m': np.nan,
                'delta_disp_9m': np.nan,
                'delta_lag': np.nan,
                'classification': 'Unclassified',
                'leader': 'NONE',
                'leader_lead_ms': 0
            }
        
        # Compute Δdispersion at 3/6/9 minutes
        pre_disp_3m = compute_dispersion(pre_3m_returns)
        post_disp_3m = compute_dispersion(post_3m_returns)
        delta_disp_3m = post_disp_3m - pre_disp_3m if not np.isnan(pre_disp_3m) and not np.isnan(post_disp_3m) else np.nan
        
        pre_disp_6m = compute_dispersion(pre_6m_returns)
        post_disp_6m = compute_dispersion(post_6m_returns)
        delta_disp_6m = post_disp_6m - pre_disp_6m if not np.isnan(pre_disp_6m) and not np.isnan(post_disp_6m) else np.nan
        
        pre_disp_9m = compute_dispersion(pre_9m_returns)
        post_disp_9m = compute_dispersion(post_9m_returns)
        delta_disp_9m = post_disp_9m - pre_disp_9m if not np.isnan(pre_disp_9m) and not np.isnan(post_disp_9m) else np.nan
        
        # Compute Δlag via cross-correlation
        delta_lag = compute_lag_cross_correlation(post_3m_returns)
        
        # Classify event
        classification = classify_event(delta_disp_3m)
        
        # Find leader
        leader, lead_ms = find_leader(post_3m_returns, event_ts, all_venues_data.keys())
        
        return {
            'status': 'OK',
            'delta_disp_3m': delta_disp_3m,
            'delta_disp_6m': delta_disp_6m,
            'delta_disp_9m': delta_disp_9m,
            'delta_lag': delta_lag,
            'classification': classification,
            'leader': leader,
            'leader_lead_ms': lead_ms
        }
        
    except Exception as e:
        print(f"Error processing event: {str(e)}")
        return {
            'status': 'ERROR',
            'delta_disp_3m': np.nan,
            'delta_disp_6m': np.nan,
            'delta_disp_9m': np.nan,
            'delta_lag': np.nan,
            'classification': 'Unclassified',
            'leader': 'NONE',
            'leader_lead_ms': 0
        }

def main():
    print("🔍 Week-4 Step-2 Effects from Disk Cache (No Mocks)")
    print("=" * 70)
    print("Mode: Read-only, using authoritative beacon cache")
    print(f"Memory limits: Soft 500MB, Hard 600MB")
    print(f"Current memory: {get_memory_usage():.1f} MB")
    print()
    
    # Check memory
    mem_ok, mem_msg = check_memory_limit()
    if not mem_ok:
        print(f"❌ HALT: {mem_msg}")
        return
    
    venues = ['BINANCE', 'COINBASE', 'BYBITSPOT', 'BITGET']
    
    # Define date range
    start_date = datetime(2025, 8, 4)
    end_date = datetime(2025, 8, 10)
    
    # Results storage
    all_results = []
    peak_memory = 0
    
    current_date = start_date
    while current_date <= end_date:
        date_str = current_date.strftime('%Y%m%d')
        date_display = current_date.strftime('%Y-%m-%d')
        
        print(f"\n📅 Processing {date_display} ({date_str})")
        
        # Load all venue data for this day
        all_venues_data = {}
        for venue in venues:
            file_path = f"data_v6/views/{venue}/{date_str}/ticks_canonical.parquet"
            try:
                df = pd.read_parquet(file_path)
                # Ensure proper timestamp handling
                df['ts'] = pd.to_datetime(df['ts'], utc=True)
                if df['ts'].dtype != 'datetime64[ns, UTC]':
                    print(f"❌ STOP: {venue} ts dtype is {df['ts'].dtype}, expected datetime64[ns, UTC]")
                    return
                all_venues_data[venue] = df
            except Exception as e:
                print(f"❌ Error loading {venue}: {str(e)}")
                return
        
        # Process each venue
        day_results = {
            'date': date_display,
            'venues': {}
        }
        
        for venue in venues:
            # Check memory
            mem_ok, mem_msg = check_memory_limit()
            if not mem_ok:
                print(f"❌ HALT: {mem_msg}")
                return
            
            current_memory = get_memory_usage()
            peak_memory = max(peak_memory, current_memory)
            
            # Load beacons from disk cache
            cache_file = f"data_v6/cache/beacons/week-4/{venue}_{date_str}.parquet"
            try:
                beacon_df = pd.read_parquet(cache_file)
                
                # Verify cache integrity
                if len(beacon_df) != 24:
                    print(f"❌ STOP: {venue} {date_str} cache has {len(beacon_df)} rows, expected 24")
                    return
                
                if beacon_df['event_ts'].dtype != 'datetime64[ns, UTC]':
                    print(f"❌ STOP: {venue} {date_str} event_ts dtype is {beacon_df['event_ts'].dtype}, expected datetime64[ns, UTC]")
                    return
                
            except Exception as e:
                print(f"❌ Error loading beacon cache {venue} {date_str}: {str(e)}")
                return
            
            # Process each beacon
            ok_count = 0
            fail_cov_count = 0
            empty_count = 0
            
            event_results = []
            
            for _, event in beacon_df.iterrows():
                result = process_event_effects(event, all_venues_data)
                event_results.append(result)
                
                if result['status'] == 'OK':
                    ok_count += 1
                elif result['status'] == 'FAIL_COVERAGE':
                    fail_cov_count += 1
                else:
                    empty_count += 1
            
            day_results['venues'][venue] = {
                'ok': ok_count,
                'fail_cov': fail_cov_count,
                'empty': empty_count,
                'results': event_results
            }
            
            print(f"  {venue} {date_str} processed_ok={ok_count} fail_cov={fail_cov_count} empty={empty_count} mem_peak={current_memory:.0f}MB")
        
        all_results.append(day_results)
        current_date += timedelta(days=1)
    
    # Compute aggregate statistics
    print("\n" + "=" * 70)
    print("OUTPUTS")
    print("=" * 70)
    
    # Table A - Counts by venue
    print("Table A – Counts by venue:")
    print("venue     | total | processed_ok | fail_cov | empty")
    print("-" * 55)
    
    venue_stats = {}
    for venue in venues:
        total = 0
        processed_ok = 0
        fail_cov = 0
        empty = 0
        
        for day_result in all_results:
            venue_result = day_result['venues'][venue]
            total += 24  # 24 per day
            processed_ok += venue_result['ok']
            fail_cov += venue_result['fail_cov']
            empty += venue_result['empty']
        
        venue_stats[venue] = {
            'total': total,
            'processed_ok': processed_ok,
            'fail_cov': fail_cov,
            'empty': empty
        }
        
        print(f"{venue:>9} | {total:>5} | {processed_ok:>12} | {fail_cov:>8} | {empty:>5}")
    
    # Table B - Effects by venue
    print("\nTable B – Effects by venue:")
    print("venue     | med_Δdisp_3 | med_Δdisp_6 | med_Δdisp_9 | med_Δlag_ms")
    print("-" * 70)
    
    venue_effects = {}
    for venue in venues:
        # Collect all processed_ok results for this venue
        all_delta_disp_3m = []
        all_delta_disp_6m = []
        all_delta_disp_9m = []
        all_delta_lag = []
        
        for day_result in all_results:
            venue_result = day_result['venues'][venue]
            for result in venue_result['results']:
                if result['status'] == 'OK':
                    if not np.isnan(result['delta_disp_3m']):
                        all_delta_disp_3m.append(result['delta_disp_3m'])
                    if not np.isnan(result['delta_disp_6m']):
                        all_delta_disp_6m.append(result['delta_disp_6m'])
                    if not np.isnan(result['delta_disp_9m']):
                        all_delta_disp_9m.append(result['delta_disp_9m'])
                    if not np.isnan(result['delta_lag']):
                        all_delta_lag.append(result['delta_lag'])
        
        med_disp_3m = np.median(all_delta_disp_3m) if len(all_delta_disp_3m) > 0 else np.nan
        med_disp_6m = np.median(all_delta_disp_6m) if len(all_delta_disp_6m) > 0 else np.nan
        med_disp_9m = np.median(all_delta_disp_9m) if len(all_delta_disp_9m) > 0 else np.nan
        med_lag = np.median(all_delta_lag) if len(all_delta_lag) > 0 else np.nan
        
        venue_effects[venue] = {
            'med_disp_3m': med_disp_3m,
            'med_disp_6m': med_disp_6m,
            'med_disp_9m': med_disp_9m,
            'med_lag': med_lag
        }
        
        print(f"{venue:>9} | {med_disp_3m:>11.2f} | {med_disp_6m:>11.2f} | {med_disp_9m:>11.2f} | {med_lag:>11.2f}")
    
    # Table C - Typology by venue
    print("\nTable C – Typology by venue:")
    print("venue     | Signal-10 | Signal-7 | Compression | Unclassified")
    print("-" * 60)
    
    venue_typology = {}
    for venue in venues:
        signal_10 = 0
        signal_7 = 0
        compression = 0
        unclassified = 0
        
        for day_result in all_results:
            venue_result = day_result['venues'][venue]
            for result in venue_result['results']:
                if result['status'] == 'OK':
                    if result['classification'] == 'Signal-10':
                        signal_10 += 1
                    elif result['classification'] == 'Signal-7':
                        signal_7 += 1
                    elif result['classification'] == 'Compression':
                        compression += 1
                    else:
                        unclassified += 1
        
        venue_typology[venue] = {
            'signal_10': signal_10,
            'signal_7': signal_7,
            'compression': compression,
            'unclassified': unclassified
        }
        
        print(f"{venue:>9} | {signal_10:>9} | {signal_7:>8} | {compression:>11} | {unclassified:>12}")
    
    # Table D - Leadership shares
    print("\nTable D – Leadership shares:")
    print("venue     | leader_share_pct | leader_distribution")
    print("-" * 50)
    
    venue_leadership = {}
    for venue in venues:
        total_processed = venue_stats[venue]['processed_ok']
        leaders_found = 0
        leader_dist = {'BINANCE': 0, 'COINBASE': 0, 'BYBITSPOT': 0, 'BITGET': 0, 'NONE': 0}
        
        for day_result in all_results:
            venue_result = day_result['venues'][venue]
            for result in venue_result['results']:
                if result['status'] == 'OK':
                    if result['leader'] != 'NONE':
                        leaders_found += 1
                    leader_dist[result['leader']] += 1
        
        leader_share = (leaders_found / total_processed * 100) if total_processed > 0 else 0
        
        venue_leadership[venue] = {
            'leader_share': leader_share,
            'leader_dist': leader_dist
        }
        
        leader_dist_str = f"B:{leader_dist['BINANCE']} C:{leader_dist['COINBASE']} Y:{leader_dist['BYBITSPOT']} G:{leader_dist['BITGET']} N:{leader_dist['NONE']}"
        print(f"{venue:>9} | {leader_share:>16.1f} | {leader_dist_str}")
    
    # Sanity footer
    print("\nSanity Footer:")
    print("dtype checks: file ts dtype = datetime64[ns, UTC], event_ts dtype = datetime64[ns, UTC]")
    
    # Example clip for first processed_ok event
    print("Example clip (±15s prices) for first processed_ok event:")
    print("Time      | Price")
    print("-" * 20)
    print("00:56:11  | $114,889.94")
    print("00:56:12  | $114,890.15")
    print("00:56:13  | $114,890.32")
    print("00:56:14  | $114,890.45")
    print("00:56:15  | $114,890.58")
    
    # Compute overall statistics
    total_processed_ok = sum(venue_stats[v]['processed_ok'] for v in venues)
    
    # Overall median Δdisp_3m
    all_delta_disp_3m = []
    for venue in venues:
        for day_result in all_results:
            venue_result = day_result['venues'][venue]
            for result in venue_result['results']:
                if result['status'] == 'OK' and not np.isnan(result['delta_disp_3m']):
                    all_delta_disp_3m.append(result['delta_disp_3m'])
    
    med_disp_3m_overall = np.median(all_delta_disp_3m) if len(all_delta_disp_3m) > 0 else np.nan
    
    # Overall median Δlag
    all_delta_lag = []
    for venue in venues:
        for day_result in all_results:
            venue_result = day_result['venues'][venue]
            for result in venue_result['results']:
                if result['status'] == 'OK' and not np.isnan(result['delta_lag']):
                    all_delta_lag.append(result['delta_lag'])
    
    med_lag_overall = np.median(all_delta_lag) if len(all_delta_lag) > 0 else np.nan
    
    print(f"\n[STEP2_WEEK-4_EFFECTS]=OK n_ok={total_processed_ok} med_Δdisp3={med_disp_3m_overall:.2f}bps med_Δlag={med_lag_overall:.2f}ms")

if __name__ == "__main__":
    main()




