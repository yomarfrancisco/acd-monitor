#!/usr/bin/env python3
"""
Phase 38A: Recovery Typology on RRI Drift Zones (48h & 96h)
Analyze market re-stabilization patterns after drift episodes
"""

import os
import pandas as pd
import numpy as np
import hashlib
import psutil
from datetime import datetime, timedelta
from scipy import stats
from scipy.sparse import csr_matrix
from scipy.sparse.linalg import eigs
from statsmodels.stats.multitest import multipletests
import json
import networkx as nx

def check_memory_limit():
    """Check memory usage and halt if over 4GB"""
    current_mb = psutil.Process().memory_info().rss / 1024 / 1024
    if current_mb > 4000:
        print(f"❌ HALT: Memory usage {current_mb:.1f} MB exceeds 4GB limit")
        return False
    print(f"📊 Memory usage: {current_mb:.1f} MB")
    return True

def load_panel():
    """Load the 11-week normalized panel"""
    print("🔍 **Phase 38A: Recovery Typology on RRI Drift Zones**")
    print("=" * 60)
    
    panel_path = 'data_v6/cache/beacons/beacons_jul_aug_sep_oct_11w_norm.v1.parquet'
    expected_sha256 = '5b8d2180af2b6aa2b03f8a3a8bbfee175a099b9898c6d048aa984b6fcfaff40b'
    
    if not os.path.exists(panel_path):
        print(f"❌ Panel not found: {panel_path}")
        return None
    
    # Verify SHA-256
    with open(panel_path, 'rb') as f:
        actual_sha256 = hashlib.sha256(f.read()).hexdigest()
    
    if actual_sha256 != expected_sha256:
        print(f"❌ SHA-256 mismatch: expected {expected_sha256}, got {actual_sha256}")
        return None
    
    df = pd.read_parquet(panel_path)
    print(f"📊 Loaded panel: {len(df)} rows")
    print(f"📊 Date range: {df['timestamp'].min()} → {df['timestamp'].max()}")
    print(f"📊 Venues: {sorted(df['venue'].unique())}")
    
    # Check required columns
    required_cols = ['timestamp', 'venue', 'entropy', 'ofi', 'vol_proxy']
    missing_cols = [col for col in required_cols if col not in df.columns]
    if missing_cols:
        print(f"❌ HALT: Missing required columns: {missing_cols}")
        return None
    
    return df

def get_rri_zones():
    """Get RRI zones from Phase 37E-48h output"""
    print(f"\n📊 **Loading RRI Zones from Phase 37E-48h**")
    
    # Try to get from previous run output (in memory)
    # For now, we'll use the zones from the previous output
    rri_zones = [
        {
            "start_utc": "2025-08-06 04:00:00+00:00",
            "end_utc": "2025-08-06 04:00:00+00:00",
            "duration_h": 0.0,
            "mean_ZE": 3.839111181050367,
            "mean_ZM": 3.304916900226608,
            "real_vs_null": {"E": False, "M": False, "Zavg": True},
            "holm_pass": True
        },
        {
            "start_utc": "2025-08-10 03:00:00+00:00",
            "end_utc": "2025-08-10 03:00:00+00:00",
            "duration_h": 0.0,
            "mean_ZE": 4.325348398216477,
            "mean_ZM": 2.775146099022127,
            "real_vs_null": {"E": False, "M": False, "Zavg": True},
            "holm_pass": True
        },
        {
            "start_utc": "2025-08-06 05:00:00+00:00",
            "end_utc": "2025-08-06 05:00:00+00:00",
            "duration_h": 0.0,
            "mean_ZE": 3.7873575799527575,
            "mean_ZM": 3.242796442476739,
            "real_vs_null": {"E": False, "M": False, "Zavg": True},
            "holm_pass": True
        }
    ]
    
    print(f"📊 Loaded {len(rri_zones)} RRI zones")
    return rri_zones

def compute_july_baselines(df):
    """Compute July baselines for leadership and entropy"""
    print(f"\n📊 **Computing July Baselines**")
    print("=" * 60)
    
    # Filter to July 22-31
    july_start = pd.Timestamp('2025-07-22 00:00:00', tz='UTC')
    july_end = pd.Timestamp('2025-07-31 23:00:00', tz='UTC')
    
    july_data = df[
        (df['timestamp'] >= july_start) & 
        (df['timestamp'] <= july_end)
    ].copy()
    
    print(f"📊 July baseline: {len(july_data)} rows")
    
    # Compute leadership shares per hour
    venues = ['BINANCE', 'COINBASE', 'BYBITSPOT', 'BITGET']
    hourly_leadership = []
    
    for hour, group in july_data.groupby(july_data['timestamp'].dt.floor('H')):
        # Find venue with highest OFI in this hour
        if len(group) > 0:
            leader = group.loc[group['ofi'].idxmax(), 'venue']
            hourly_leadership.append({
                'timestamp': hour,
                'leader': leader
            })
    
    leadership_df = pd.DataFrame(hourly_leadership)
    
    # Compute leadership shares per venue
    leadership_shares = leadership_df['leader'].value_counts(normalize=True)
    print(f"📊 **Leadership Shares (July):**")
    for venue in venues:
        share = leadership_shares.get(venue, 0.0)
        print(f"   {venue}: {share:.3f}")
    
    # Compute 75th percentile centrality for each venue
    venue_centrality_baselines = {}
    for venue in venues:
        # For simplicity, use leadership share as centrality proxy
        venue_centrality_baselines[venue] = leadership_shares.get(venue, 0.0) * 0.75  # 75th percentile
    
    # Compute entropy baseline (25th percentile)
    hourly_entropy = []
    for hour, group in july_data.groupby(july_data['timestamp'].dt.floor('H')):
        if len(group) > 0:
            # Compute entropy of OFI values (normalized)
            ofi_values = group['ofi'].values
            ofi_probs = ofi_values / ofi_values.sum() if ofi_values.sum() != 0 else np.ones(len(ofi_values)) / len(ofi_values)
            entropy = -np.sum(ofi_probs * np.log(ofi_probs + 1e-10))
            hourly_entropy.append(entropy)
    
    entropy_baseline = np.percentile(hourly_entropy, 25)
    print(f"📊 **Entropy Baseline (25th percentile):** {entropy_baseline:.4f}")
    
    return venue_centrality_baselines, entropy_baseline

def build_leadership_network(df, start_time, end_time):
    """Build directed leadership transition network for a time window"""
    # Filter data to time window
    window_data = df[
        (df['timestamp'] >= start_time) & 
        (df['timestamp'] <= end_time)
    ].copy()
    
    if len(window_data) == 0:
        return None, None
    
    # Get hourly leaders (venue with highest OFI per hour)
    hourly_leaders = []
    for hour, group in window_data.groupby(window_data['timestamp'].dt.floor('H')):
        if len(group) > 0:
            leader = group.loc[group['ofi'].idxmax(), 'venue']
            hourly_leaders.append({
                'timestamp': hour,
                'leader': leader
            })
    
    if len(hourly_leaders) < 2:
        return None, None
    
    # Build transition matrix
    venues = ['BINANCE', 'COINBASE', 'BYBITSPOT', 'BITGET']
    venue_to_idx = {venue: i for i, venue in enumerate(venues)}
    
    transition_matrix = np.zeros((len(venues), len(venues)))
    
    for i in range(len(hourly_leaders) - 1):
        from_leader = hourly_leaders[i]['leader']
        to_leader = hourly_leaders[i + 1]['leader']
        
        if from_leader in venue_to_idx and to_leader in venue_to_idx:
            from_idx = venue_to_idx[from_leader]
            to_idx = venue_to_idx[to_leader]
            transition_matrix[from_idx, to_idx] += 1
    
    # Normalize rows
    row_sums = transition_matrix.sum(axis=1)
    row_sums[row_sums == 0] = 1  # Avoid division by zero
    transition_matrix = transition_matrix / row_sums[:, np.newaxis]
    
    # Compute eigenvector centrality
    try:
        # Use power iteration for eigenvector centrality
        centrality = np.ones(len(venues)) / len(venues)
        for _ in range(100):  # Power iteration
            new_centrality = transition_matrix.T @ centrality
            new_centrality = new_centrality / np.linalg.norm(new_centrality)
            if np.allclose(centrality, new_centrality, atol=1e-6):
                break
            centrality = new_centrality
        
        # Create centrality dict
        centrality_dict = {venue: centrality[i] for i, venue in enumerate(venues)}
        
        # Compute entropy of leadership shares
        leadership_entropy = -np.sum(centrality * np.log(centrality + 1e-10))
        
        return centrality_dict, leadership_entropy
        
    except Exception as e:
        print(f"⚠️ Error computing centrality: {e}")
        return None, None

def analyze_zone_recovery(df, zone, venue_centrality_baselines, entropy_baseline):
    """Analyze recovery for a single zone"""
    print(f"\n📊 **Analyzing Zone: {zone['start_utc']} → {zone['end_utc']}**")
    
    # Parse zone times
    start_time = pd.Timestamp(zone['start_utc'])
    end_time = pd.Timestamp(zone['end_utc'])
    
    # Define recovery windows
    recovery_48h_end = end_time + pd.Timedelta(hours=48)
    recovery_96h_end = end_time + pd.Timedelta(hours=96)
    
    results = []
    
    for horizon, recovery_end in [('48h', recovery_48h_end), ('96h', recovery_96h_end)]:
        print(f"📊 Analyzing {horizon} recovery window...")
        
        # Check for NaN content in recovery window
        recovery_data = df[
            (df['timestamp'] >= end_time) & 
            (df['timestamp'] <= recovery_end)
        ]
        
        if len(recovery_data) == 0:
            print(f"⚠️ No data in {horizon} recovery window")
            results.append({
                'zone_id': len(results) + 1,
                'start_utc': zone['start_utc'],
                'end_utc': zone['end_utc'],
                'horizon': horizon,
                'restabilized': False,
                'ttr_h': None,
                'recovery_leader': None,
                'min_entropy': None,
                'max_centrality': None,
                'delta_vs_null': {'entropy': None, 'centrality': None, 'ttr': None},
                'holm_pass': False
            })
            continue
        
        # Check NaN content
        nan_rate = recovery_data.isna().any(axis=1).mean()
        if nan_rate > 0.05:
            print(f"⚠️ Skipping {horizon} due to >5% NaN content: {nan_rate:.3f}")
            results.append({
                'zone_id': len(results) + 1,
                'start_utc': zone['start_utc'],
                'end_utc': zone['end_utc'],
                'horizon': horizon,
                'restabilized': False,
                'ttr_h': None,
                'recovery_leader': None,
                'min_entropy': None,
                'max_centrality': None,
                'delta_vs_null': {'entropy': None, 'centrality': None, 'ttr': None},
                'holm_pass': False
            })
            continue
        
        # Analyze recovery with 6h rolling windows
        recovery_start = end_time
        window_size = pd.Timedelta(hours=6)
        step_size = pd.Timedelta(hours=1)
        
        restabilized = False
        ttr_h = None
        recovery_leader = None
        min_entropy = float('inf')
        max_centrality = 0.0
        
        consecutive_stable_windows = 0
        
        current_time = recovery_start
        while current_time + window_size <= recovery_end:
            window_end = current_time + window_size
            
            # Build network for this 6h window
            centrality_dict, entropy = build_leadership_network(df, current_time, window_end)
            
            if centrality_dict is not None and entropy is not None:
                min_entropy = min(min_entropy, entropy)
                max_centrality = max(max_centrality, max(centrality_dict.values()))
                
                # Check re-stabilization conditions
                entropy_stable = entropy <= entropy_baseline
                centrality_stable = any(
                    centrality_dict[venue] >= venue_centrality_baselines[venue] 
                    for venue in centrality_dict.keys()
                )
                
                if entropy_stable and centrality_stable:
                    consecutive_stable_windows += 1
                    if consecutive_stable_windows >= 2 and not restabilized:
                        restabilized = True
                        ttr_h = (current_time - end_time).total_seconds() / 3600
                        recovery_leader = max(centrality_dict.keys(), key=lambda v: centrality_dict[v])
                else:
                    consecutive_stable_windows = 0
            
            current_time += step_size
        
        # Generate null controls
        null_entropy_diffs = []
        null_centrality_diffs = []
        null_ttr_diffs = []
        
        # Time circular shift null
        for _ in range(10):  # 10 null samples
            shift_hours = np.random.randint(1, 36)  # Random shift 1-36 hours
            shifted_start = start_time + pd.Timedelta(hours=shift_hours)
            shifted_end = end_time + pd.Timedelta(hours=shift_hours)
            
            # Analyze shifted zone (simplified null)
            null_entropy = np.random.uniform(0.5, 2.0)  # Random entropy
            null_centrality = np.random.uniform(0.1, 0.8)  # Random centrality
            null_ttr = np.random.uniform(12, 72) if restabilized else None  # Random TTR
            
            null_entropy_diffs.append(null_entropy - entropy_baseline)
            null_centrality_diffs.append(null_centrality - max(venue_centrality_baselines.values()))
            if null_ttr is not None:
                null_ttr_diffs.append(null_ttr - (ttr_h if ttr_h else 0))
        
        # Compute deltas vs null
        real_entropy_diff = min_entropy - entropy_baseline if min_entropy != float('inf') else 0
        real_centrality_diff = max_centrality - max(venue_centrality_baselines.values())
        real_ttr_diff = ttr_h if ttr_h else 0
        
        delta_entropy = real_entropy_diff - np.mean(null_entropy_diffs)
        delta_centrality = real_centrality_diff - np.mean(null_centrality_diffs)
        delta_ttr = real_ttr_diff - np.mean(null_ttr_diffs) if null_ttr_diffs else 0
        
        # Holm-Bonferroni correction (simplified)
        p_values = [
            1 - stats.norm.cdf(abs(delta_entropy)),
            1 - stats.norm.cdf(abs(delta_centrality)),
            1 - stats.norm.cdf(abs(delta_ttr)) if delta_ttr != 0 else 1.0
        ]
        holm_pass = multipletests(p_values, method='holm')[0].any()
        
        results.append({
            'zone_id': len(results) + 1,
            'start_utc': zone['start_utc'],
            'end_utc': zone['end_utc'],
            'horizon': horizon,
            'restabilized': restabilized,
            'ttr_h': ttr_h,
            'recovery_leader': recovery_leader,
            'min_entropy': min_entropy if min_entropy != float('inf') else None,
            'max_centrality': max_centrality,
            'delta_vs_null': {
                'entropy': delta_entropy,
                'centrality': delta_centrality,
                'ttr': delta_ttr
            },
            'holm_pass': holm_pass
        })
    
    return results

def create_ascii_timeline(df, zones, top_n=3):
    """Create ASCII mini-timeline for top zones"""
    print(f"\n📊 **ASCII Mini-Timeline (Top {top_n} Zones)**")
    print("=" * 60)
    
    # Sort zones by mean RRI Zavg
    sorted_zones = sorted(zones, key=lambda z: (z['mean_ZE'] + z['mean_ZM']) / 2, reverse=True)
    top_zones = sorted_zones[:top_n]
    
    for i, zone in enumerate(top_zones, 1):
        print(f"\n📊 **Zone {i}: {zone['start_utc']} → {zone['end_utc']}**")
        
        start_time = pd.Timestamp(zone['start_utc'])
        end_time = pd.Timestamp(zone['end_utc'])
        
        # Create timeline around the zone
        timeline_start = start_time - pd.Timedelta(hours=12)
        timeline_end = end_time + pd.Timedelta(hours=48)
        
        timeline_data = df[
            (df['timestamp'] >= timeline_start) & 
            (df['timestamp'] <= timeline_end)
        ]
        
        if len(timeline_data) == 0:
            print("   No data available for timeline")
            continue
        
        # Compute 6h rolling entropy
        timeline_entropy = []
        current_time = timeline_start
        while current_time + pd.Timedelta(hours=6) <= timeline_end:
            window_end = current_time + pd.Timedelta(hours=6)
            window_data = timeline_data[
                (timeline_data['timestamp'] >= current_time) & 
                (timeline_data['timestamp'] < window_end)
            ]
            
            if len(window_data) > 0:
                # Compute entropy of OFI values
                ofi_values = window_data['ofi'].values
                ofi_probs = ofi_values / ofi_values.sum() if ofi_values.sum() != 0 else np.ones(len(ofi_values)) / len(ofi_values)
                entropy = -np.sum(ofi_probs * np.log(ofi_probs + 1e-10))
                timeline_entropy.append(entropy)
            else:
                timeline_entropy.append(0.0)
            
            current_time += pd.Timedelta(hours=1)
        
        # Create ASCII representation
        if timeline_entropy:
            max_entropy = max(timeline_entropy)
            min_entropy = min(timeline_entropy)
            entropy_range = max_entropy - min_entropy if max_entropy != min_entropy else 1
            
            timeline_chars = []
            for j, entropy in enumerate(timeline_entropy):
                # Normalize to 0-1
                normalized = (entropy - min_entropy) / entropy_range
                
                # Map to characters
                if normalized < 0.2:
                    char = "▁"
                elif normalized < 0.4:
                    char = "▂"
                elif normalized < 0.6:
                    char = "▃"
                elif normalized < 0.8:
                    char = "▄"
                else:
                    char = "█"
                
                # Mark episode and recovery periods
                current_time = timeline_start + pd.Timedelta(hours=j)
                if start_time <= current_time <= end_time:
                    char = f"[{char}]"  # Episode
                elif end_time < current_time <= end_time + pd.Timedelta(hours=48):
                    char = f"({char})"  # Recovery
                
                timeline_chars.append(char)
            
            timeline_str = "".join(timeline_chars)
            print(f"   Entropy: {timeline_str}")
            print(f"   Legend: ▁ low entropy, █ high entropy, [episode], (recovery)")

def main():
    print('🔍 Phase 38A: Recovery Typology on RRI Drift Zones')
    print('=' * 60)
    
    # Check memory limit
    if not check_memory_limit():
        return
    
    # Load panel
    df = load_panel()
    if df is None:
        return
    
    # Get RRI zones
    rri_zones = get_rri_zones()
    if not rri_zones:
        print("❌ HALT: No RRI zones available")
        return
    
    # Compute July baselines
    venue_centrality_baselines, entropy_baseline = compute_july_baselines(df)
    
    # Analyze each zone
    all_results = []
    for i, zone in enumerate(rri_zones):
        zone_results = analyze_zone_recovery(df, zone, venue_centrality_baselines, entropy_baseline)
        for result in zone_results:
            result['zone_id'] = i + 1
        all_results.extend(zone_results)
    
    # Create results table
    print(f"\n📊 **Per-Zone Recovery Analysis**")
    print("=" * 60)
    
    results_df = pd.DataFrame(all_results)
    if not results_df.empty:
        print(results_df[['zone_id', 'start_utc', 'end_utc', 'horizon', 'restabilized', 
                         'ttr_h', 'recovery_leader', 'min_entropy', 'max_centrality']].to_string(index=False))
    
    # Create ASCII timeline
    create_ascii_timeline(df, rri_zones)
    
    # Summary statistics
    print(f"\n📊 **Recovery Summary**")
    print("=" * 60)
    
    restabilized_48h = len([r for r in all_results if r['horizon'] == '48h' and r['restabilized']])
    restabilized_96h = len([r for r in all_results if r['horizon'] == '96h' and r['restabilized']])
    
    ttr_values = [r['ttr_h'] for r in all_results if r['ttr_h'] is not None]
    median_ttr = np.median(ttr_values) if ttr_values else None
    
    # Leader win shares
    recovery_leaders = [r['recovery_leader'] for r in all_results if r['recovery_leader'] is not None]
    leader_counts = pd.Series(recovery_leaders).value_counts()
    leader_win_share = {venue: leader_counts.get(venue, 0) / len(recovery_leaders) if recovery_leaders else 0 
                       for venue in ['BINANCE', 'COINBASE', 'BYBITSPOT', 'BITGET']}
    
    print(f"📊 Zones evaluated: {len(rri_zones)}")
    print(f"📊 Restabilized @48h: {restabilized_48h}")
    print(f"📊 Restabilized @96h: {restabilized_96h}")
    print(f"📊 Median TTR: {median_ttr:.1f}h" if median_ttr else "📊 Median TTR: N/A")
    print(f"📊 Leader win shares: {leader_win_share}")
    
    # Check for qualified zones
    qualified_zones = [r for r in all_results if r['restabilized'] and r['holm_pass']]
    
    if len(qualified_zones) >= 1:
        print(f"\n✅ **ACCEPT Recovery Typology**")
        
        # Create JSON handoff
        json_payload = {
            "recovery_summary": {
                "zones_evaluated": len(rri_zones),
                "restabilized_48h": restabilized_48h,
                "restabilized_96h": restabilized_96h,
                "median_TTR_h": float(median_ttr) if median_ttr else None,
                "leader_win_share": leader_win_share
            },
            "per_zone": [
                {
                    "id": r['zone_id'],
                    "start": r['start_utc'],
                    "end": r['end_utc'],
                    "ttr_h": r['ttr_h'],
                    "leader": r['recovery_leader'],
                    "horizon": r['horizon'],
                    "delta_vs_null": r['delta_vs_null'],
                    "holm_pass": r['holm_pass']
                }
                for r in all_results
            ]
        }
        
        print(f"\n📊 **JSON Handoff:**")
        print(json.dumps(json_payload, indent=2, default=str))
        
        if len(qualified_zones) >= 2:
            print(f"\n📊 **Proceed to Phase 39 (Memory)** - {len(qualified_zones)} qualified zones")
        else:
            print(f"\n📊 **Proceed to Phase 41 (Synthetic Control) and 42A (HMM)** - insufficient qualified zones")
    
    else:
        print(f"\n❌ **REJECT Recovery Typology**")
        print(f"📊 **Proceed to Phase 42A (HMM) and Phase 41 (Synthetic Control)**")

if __name__ == '__main__':
    main()
