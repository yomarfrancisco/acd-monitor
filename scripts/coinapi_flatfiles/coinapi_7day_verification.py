#!/usr/bin/env python3
"""
ACD — 7-day 1s verification pass (spreads/lag consistency + Kraken status)

Evidence-first verification with strict overlap discipline and CI reporting.
"""

import os
import json
import time
import tempfile
import logging
import numpy as np
import pandas as pd
import boto3
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
import matplotlib.pyplot as plt
import seaborn as sns
from scipy import stats
from scipy.stats import pearsonr
import warnings
warnings.filterwarnings('ignore')

# Setup
BUCKET = "acd-monitor-snapshots"
DATE_RANGE = "2025-09-25_to_2025-10-01"
OUTPUT_DIR = f"analysis/coinapi_1s/{DATE_RANGE}/verify_v1"

def setup_logging():
    """Setup logging configuration."""
    import logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s",
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler("coinapi_7day_verification.log")
        ]
    )
    return logging.getLogger(__name__)

def get_s3_object_content(s3_client, bucket: str, key: str) -> Optional[bytes]:
    """Helper to get content from S3, returns None if key not found."""
    try:
        response = s3_client.get_object(Bucket=bucket, Key=key)
        return response['Body'].read()
    except s3_client.exceptions.NoSuchKey:
        return None
    except Exception as e:
        logging.getLogger(__name__).error(f"Error getting S3 object {key}: {e}")
        return None

def load_venue_data(s3_client, bucket: str, date: str, venue: str) -> Optional[pd.DataFrame]:
    """Load venue data for a specific date."""
    logger = logging.getLogger(__name__)
    
    # Try different paths for the data
    data_paths = [
        f"backfill/coinapi_1s/{venue.lower()}/{date}/candles_1s.parquet",
        f"backfill/coinapi_1s/{venue}/{date}/candles_1s.parquet",
        f"backfill/coinapi_1s/{venue.lower()}/{date}/part-0000.parquet",
        f"backfill/coinapi_1s/{venue}/{date}/part-0000.parquet"
    ]
    
    for path in data_paths:
        parquet_data = get_s3_object_content(s3_client, bucket, path)
        if parquet_data:
            try:
                with tempfile.NamedTemporaryFile(suffix='.parquet', delete=False) as tmp_file:
                    tmp_file.write(parquet_data)
                    tmp_file.flush()
                    df = pd.read_parquet(tmp_file.name)
                    Path(tmp_file.name).unlink()
                
                logger.info(f"Loaded {venue} {date}: {len(df)} rows from {path}")
                return df
            except Exception as e:
                logger.warning(f"Error loading {path}: {e}")
    
    logger.warning(f"No data found for {venue} {date}")
    return None

def load_panel_data(s3_client, bucket: str) -> Optional[pd.DataFrame]:
    """Load the existing panel data."""
    logger = logging.getLogger(__name__)
    
    panel_path = f"analysis/coinapi_1s/panel/candles_1s_panel.parquet"
    parquet_data = get_s3_object_content(s3_client, bucket, panel_path)
    
    if parquet_data:
        try:
            with tempfile.NamedTemporaryFile(suffix='.parquet', delete=False) as tmp_file:
                tmp_file.write(parquet_data)
                tmp_file.flush()
                df = pd.read_parquet(tmp_file.name)
                Path(tmp_file.name).unlink()
            
            logger.info(f"Loaded panel data: {len(df)} rows")
            return df
        except Exception as e:
            logger.error(f"Error loading panel data: {e}")
    
    return None

def task1_alignment_coverage_audit(s3_client, bucket: str, dates: List[str]) -> pd.DataFrame:
    """Task 1: Alignment & coverage audit (per pair, per day)."""
    logger = logging.getLogger(__name__)
    logger.info("🔍 Task 1: Alignment & coverage audit...")
    
    coverage_results = []
    
    for date in dates:
        logger.info(f"   📊 Processing {date}...")
        
        # Load data for each venue
        venue_data = {}
        for venue in ['BINANCE', 'COINBASE', 'KRAKEN']:
            df = load_venue_data(s3_client, bucket, date, venue)
            if df is not None and not df.empty:
                # Ensure timestamp is datetime and set as index
                df['timestamp'] = pd.to_datetime(df['time_period_start'], utc=True)
                df = df.set_index('timestamp')
                venue_data[venue] = df
                logger.info(f"      {venue}: {len(df)} rows")
            else:
                logger.warning(f"      {venue}: No data")
        
        # Compute pairwise coverage
        pairs = [('BINANCE', 'COINBASE'), ('BINANCE', 'KRAKEN'), ('COINBASE', 'KRAKEN')]
        
        for venue1, venue2 in pairs:
            if venue1 in venue_data and venue2 in venue_data:
                df1 = venue_data[venue1]
                df2 = venue_data[venue2]
                
                # Inner join on second timestamps
                common_times = df1.index.intersection(df2.index)
                seconds_total = 86400  # Total seconds in a day
                seconds_union = len(df1.index.union(df2.index))
                seconds_intersection = len(common_times)
                coverage_pair = seconds_intersection / seconds_total
                
                coverage_results.append({
                    'date': date,
                    'venue1': venue1,
                    'venue2': venue2,
                    'seconds_total': seconds_total,
                    'seconds_union': seconds_union,
                    'seconds_intersection': seconds_intersection,
                    'coverage_pair': coverage_pair,
                    'venue1_rows': len(df1),
                    'venue2_rows': len(df2),
                    'common_rows': seconds_intersection
                })
                
                logger.info(f"      {venue1}↔{venue2}: {coverage_pair:.1%} coverage ({seconds_intersection}/{seconds_total}s)")
            else:
                logger.warning(f"      {venue1}↔{venue2}: Missing data")
    
    coverage_df = pd.DataFrame(coverage_results)
    
    # Save coverage table
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    coverage_df.to_parquet(f"{OUTPUT_DIR}/coverage_table.parquet", index=False)
    
    # Create markdown report
    with open(f"{OUTPUT_DIR}/coverage_table.md", 'w') as f:
        f.write("# Coverage Analysis\n\n")
        f.write("## Daily Coverage by Pair\n\n")
        if not coverage_df.empty:
            f.write(coverage_df.to_markdown(index=False))
            f.write("\n\n## Summary Statistics\n\n")
            f.write(f"- **Total pairs analyzed**: {len(coverage_df)}\n")
            f.write(f"- **Mean coverage**: {coverage_df['coverage_pair'].mean():.1%}\n")
            f.write(f"- **Median coverage**: {coverage_df['coverage_pair'].median():.1%}\n")
            f.write(f"- **Pairs with ≥30% coverage**: {(coverage_df['coverage_pair'] >= 0.30).sum()}\n")
            f.write(f"- **Pairs with ≥50% coverage**: {(coverage_df['coverage_pair'] >= 0.50).sum()}\n")
        else:
            f.write("No coverage data available - no overlapping data found between venues.\n")
    
    logger.info(f"✅ Coverage audit complete: {len(coverage_df)} pairs analyzed")
    return coverage_df

def task2_spreads_analysis(s3_client, bucket: str, dates: List[str], coverage_df: pd.DataFrame) -> Tuple[pd.DataFrame, Dict]:
    """Task 2: Spreads analysis using two formulas on intersection seconds only."""
    logger = logging.getLogger(__name__)
    logger.info("🔍 Task 2: Spreads analysis...")
    
    daily_spreads = []
    pooled_spreads = {}
    
    for date in dates:
        logger.info(f"   📊 Processing {date}...")
        
        # Load data for each venue
        venue_data = {}
        for venue in ['BINANCE', 'COINBASE', 'KRAKEN']:
            df = load_venue_data(s3_client, bucket, date, venue)
            if df is not None and not df.empty:
                df['timestamp'] = pd.to_datetime(df['time_period_start'], utc=True)
                df = df.set_index('timestamp')
                venue_data[venue] = df
        
        # Compute spreads for each pair
        pairs = [('BINANCE', 'COINBASE'), ('BINANCE', 'KRAKEN'), ('COINBASE', 'KRAKEN')]
        
        for venue1, venue2 in pairs:
            if venue1 in venue_data and venue2 in venue_data:
                df1 = venue_data[venue1]
                df2 = venue_data[venue2]
                
                # Get coverage for this pair
                pair_coverage = coverage_df[
                    (coverage_df['date'] == date) & 
                    (coverage_df['venue1'] == venue1) & 
                    (coverage_df['venue2'] == venue2)
                ]
                
                if pair_coverage.empty or pair_coverage['coverage_pair'].iloc[0] < 0.30:
                    logger.warning(f"      {venue1}↔{venue2}: Skipping (low coverage)")
                    continue
                
                # Inner join on intersection seconds
                common_times = df1.index.intersection(df2.index)
                df1_aligned = df1.loc[common_times]
                df2_aligned = df2.loc[common_times]
                
                # Extract close prices
                p1 = df1_aligned['price_close'].values
                p2 = df2_aligned['price_close'].values
                
                # Compute spreads using two formulas
                # Formula 1: Mid spread
                spread_mid = np.abs(p1 - p2) / ((p1 + p2) / 2)
                
                # Formula 2: Log spread
                spread_log = np.abs(np.log(p1) - np.log(p2))
                
                # Compute statistics
                spread_mid_mean = np.mean(spread_mid)
                spread_mid_median = np.median(spread_mid)
                spread_mid_p95 = np.percentile(spread_mid, 95)
                spread_mid_max = np.max(spread_mid)
                
                spread_log_mean = np.mean(spread_log)
                spread_log_median = np.median(spread_log)
                spread_log_p95 = np.percentile(spread_log, 95)
                spread_log_max = np.max(spread_log)
                
                daily_spreads.append({
                    'date': date,
                    'venue1': venue1,
                    'venue2': venue2,
                    'n_seconds': len(common_times),
                    'coverage_pair': pair_coverage['coverage_pair'].iloc[0],
                    'spread_mid_mean': spread_mid_mean,
                    'spread_mid_median': spread_mid_median,
                    'spread_mid_p95': spread_mid_p95,
                    'spread_mid_max': spread_mid_max,
                    'spread_log_mean': spread_log_mean,
                    'spread_log_median': spread_log_median,
                    'spread_log_p95': spread_log_p95,
                    'spread_log_max': spread_log_max
                })
                
                logger.info(f"      {venue1}↔{venue2}: Mid={spread_mid_mean:.4f}, Log={spread_log_mean:.4f}")
    
    daily_spreads_df = pd.DataFrame(daily_spreads)
    
    # Compute pooled spreads (coverage-weighted averages)
    if not daily_spreads_df.empty:
        # Weight by coverage
        weights = daily_spreads_df['coverage_pair']
        
        pooled_spreads = {
            'spread_mid_mean_pooled': np.average(daily_spreads_df['spread_mid_mean'], weights=weights),
            'spread_mid_median_pooled': np.average(daily_spreads_df['spread_mid_median'], weights=weights),
            'spread_mid_p95_pooled': np.average(daily_spreads_df['spread_mid_p95'], weights=weights),
            'spread_mid_max_pooled': np.average(daily_spreads_df['spread_mid_max'], weights=weights),
            'spread_log_mean_pooled': np.average(daily_spreads_df['spread_log_mean'], weights=weights),
            'spread_log_median_pooled': np.average(daily_spreads_df['spread_log_median'], weights=weights),
            'spread_log_p95_pooled': np.average(daily_spreads_df['spread_log_p95'], weights=weights),
            'spread_log_max_pooled': np.average(daily_spreads_df['spread_log_max'], weights=weights),
            'total_pairs': len(daily_spreads_df),
            'coverage_weighted_avg': np.average(weights)
        }
    else:
        pooled_spreads = {}
    
    # Save results
    daily_spreads_df.to_parquet(f"{OUTPUT_DIR}/daily_spreads.parquet", index=False)
    
    with open(f"{OUTPUT_DIR}/pooled_spreads.json", 'w') as f:
        json.dump(pooled_spreads, f, indent=2)
    
    # Print reconciliation
    logger.info("📊 SPREAD RECONCILIATION:")
    if pooled_spreads:
        logger.info(f"   Mid spread (pooled): {pooled_spreads['spread_mid_mean_pooled']:.6f} ({pooled_spreads['spread_mid_mean_pooled']*100:.3f}%)")
        logger.info(f"   Log spread (pooled): {pooled_spreads['spread_log_mean_pooled']:.6f} ({pooled_spreads['spread_log_mean_pooled']*100:.3f}%)")
        logger.info(f"   Previous report: 0.225%")
        logger.info(f"   Previous pooled: 0.037%")
        logger.info(f"   Difference: {abs(pooled_spreads['spread_mid_mean_pooled']*100 - 0.225):.3f}%")
    
    logger.info(f"✅ Spreads analysis complete: {len(daily_spreads_df)} pairs analyzed")
    return daily_spreads_df, pooled_spreads

def task3_returns_lag_analysis(s3_client, bucket: str, dates: List[str], coverage_df: pd.DataFrame) -> pd.DataFrame:
    """Task 3: Returns & lag grid analysis with bootstrap CIs."""
    logger = logging.getLogger(__name__)
    logger.info("🔍 Task 3: Returns & lag grid analysis...")
    
    leadlag_results = []
    
    for date in dates:
        logger.info(f"   📊 Processing {date}...")
        
        # Load data for each venue
        venue_data = {}
        for venue in ['BINANCE', 'COINBASE', 'KRAKEN']:
            df = load_venue_data(s3_client, bucket, date, venue)
            if df is not None and not df.empty:
                df['timestamp'] = pd.to_datetime(df['time_period_start'], utc=True)
                df = df.set_index('timestamp')
                venue_data[venue] = df
        
        # Compute returns and lag analysis for each pair
        pairs = [('BINANCE', 'COINBASE'), ('BINANCE', 'KRAKEN'), ('COINBASE', 'KRAKEN')]
        
        for venue1, venue2 in pairs:
            if venue1 in venue_data and venue2 in venue_data:
                df1 = venue_data[venue1]
                df2 = venue_data[venue2]
                
                # Get coverage for this pair
                pair_coverage = coverage_df[
                    (coverage_df['date'] == date) & 
                    (coverage_df['venue1'] == venue1) & 
                    (coverage_df['venue2'] == venue2)
                ]
                
                if pair_coverage.empty or pair_coverage['coverage_pair'].iloc[0] < 0.30:
                    logger.warning(f"      {venue1}↔{venue2}: Skipping (low coverage)")
                    continue
                
                # Inner join on intersection seconds
                common_times = df1.index.intersection(df2.index)
                df1_aligned = df1.loc[common_times]
                df2_aligned = df2.loc[common_times]
                
                # Compute returns: r = Δln(close)
                r1 = np.diff(np.log(df1_aligned['price_close'].values))
                r2 = np.diff(np.log(df2_aligned['price_close'].values))
                
                # Ensure same length
                min_len = min(len(r1), len(r2))
                r1 = r1[:min_len]
                r2 = r2[:min_len]
                
                if len(r1) < 10:  # Need minimum data for correlation
                    logger.warning(f"      {venue1}↔{venue2}: Insufficient data for lag analysis")
                    continue
                
                # Compute lag grid L ∈ {-5, ..., +5} seconds
                lags = list(range(-5, 6))
                correlations = []
                
                for lag in lags:
                    if lag == 0:
                        corr, _ = pearsonr(r1, r2)
                    elif lag > 0:
                        # venue1 leads venue2
                        if len(r1) > lag:
                            corr, _ = pearsonr(r1[:-lag], r2[lag:])
                        else:
                            corr = np.nan
                    else:
                        # venue2 leads venue1
                        lag_abs = abs(lag)
                        if len(r2) > lag_abs:
                            corr, _ = pearsonr(r1[lag_abs:], r2[:-lag_abs])
                        else:
                            corr = np.nan
                    
                    correlations.append(corr)
                
                # Find argmax lag
                valid_corrs = [c for c in correlations if not np.isnan(c)]
                if valid_corrs:
                    argmax_idx = np.argmax(valid_corrs)
                    argmax_lag = lags[argmax_idx]
                    max_corr = valid_corrs[argmax_idx]
                else:
                    argmax_lag = 0
                    max_corr = np.nan
                
                # Bootstrap 95% CIs (simplified - using block bootstrap)
                n_bootstrap = 1000
                block_size = 30  # 30-second blocks
                bootstrap_corrs = []
                
                for _ in range(n_bootstrap):
                    # Simple bootstrap (not true block bootstrap for simplicity)
                    if len(r1) > 100:
                        indices = np.random.choice(len(r1), size=len(r1), replace=True)
                        r1_boot = r1[indices]
                        r2_boot = r2[indices]
                        
                        if argmax_lag == 0:
                            corr_boot, _ = pearsonr(r1_boot, r2_boot)
                        elif argmax_lag > 0:
                            if len(r1_boot) > argmax_lag:
                                corr_boot, _ = pearsonr(r1_boot[:-argmax_lag], r2_boot[argmax_lag:])
                            else:
                                corr_boot = np.nan
                        else:
                            lag_abs = abs(argmax_lag)
                            if len(r2_boot) > lag_abs:
                                corr_boot, _ = pearsonr(r1_boot[lag_abs:], r2_boot[:-lag_abs])
                            else:
                                corr_boot = np.nan
                        
                        if not np.isnan(corr_boot):
                            bootstrap_corrs.append(corr_boot)
                
                # Compute CI
                if bootstrap_corrs:
                    ci_lower = np.percentile(bootstrap_corrs, 2.5)
                    ci_upper = np.percentile(bootstrap_corrs, 97.5)
                else:
                    ci_lower = ci_upper = np.nan
                
                leadlag_results.append({
                    'date': date,
                    'venue1': venue1,
                    'venue2': venue2,
                    'n_returns': len(r1),
                    'coverage_pair': pair_coverage['coverage_pair'].iloc[0],
                    'argmax_lag': argmax_lag,
                    'max_correlation': max_corr,
                    'ci_lower': ci_lower,
                    'ci_upper': ci_upper,
                    'lag_0_correlation': correlations[lags.index(0)] if 0 in lags else np.nan,
                    'lag_5_correlation': correlations[lags.index(5)] if 5 in lags else np.nan,
                    'lag_minus5_correlation': correlations[lags.index(-5)] if -5 in lags else np.nan
                })
                
                logger.info(f"      {venue1}↔{venue2}: argmax_lag={argmax_lag}, max_corr={max_corr:.4f}")
    
    leadlag_df = pd.DataFrame(leadlag_results)
    
    # Save results
    leadlag_df.to_parquet(f"{OUTPUT_DIR}/leadlag_grid.parquet", index=False)
    
    # Create heatmaps
    os.makedirs(f"{OUTPUT_DIR}/leadlag_heatmaps", exist_ok=True)
    
    for pair in [('BINANCE', 'COINBASE'), ('BINANCE', 'KRAKEN'), ('COINBASE', 'KRAKEN')]:
        pair_data = leadlag_df[
            ((leadlag_df['venue1'] == pair[0]) & (leadlag_df['venue2'] == pair[1])) |
            ((leadlag_df['venue1'] == pair[1]) & (leadlag_df['venue2'] == pair[0]))
        ]
        
        if not pair_data.empty:
            plt.figure(figsize=(10, 6))
            plt.plot(pair_data['date'], pair_data['argmax_lag'], 'o-', label='Argmax Lag')
            plt.axhline(y=0, color='r', linestyle='--', alpha=0.5, label='No Lead')
            plt.title(f'Lead-Lag Analysis: {pair[0]} ↔ {pair[1]}')
            plt.xlabel('Date')
            plt.ylabel('Lag (seconds)')
            plt.xticks(rotation=45)
            plt.legend()
            plt.tight_layout()
            plt.savefig(f"{OUTPUT_DIR}/leadlag_heatmaps/{pair[0]}_{pair[1]}_leadlag.png", dpi=150)
            plt.close()
    
    logger.info(f"✅ Lead-lag analysis complete: {len(leadlag_df)} pairs analyzed")
    return leadlag_df

def task4_kraken_recovery(s3_client, bucket: str, dates: List[str]) -> Dict:
    """Task 4: Kraken recovery visibility."""
    logger = logging.getLogger(__name__)
    logger.info("🔍 Task 4: Kraken recovery analysis...")
    
    kraken_recovery = {
        'recovery_status': 'failed',
        'days_analyzed': len(dates),
        'days_passed': 0,
        'days_failed': 0,
        'daily_results': [],
        'summary': {}
    }
    
    for date in dates:
        logger.info(f"   📊 Analyzing Kraken {date}...")
        
        # Load Kraken data
        df = load_venue_data(s3_client, bucket, date, 'KRAKEN')
        
        if df is None or df.empty:
            kraken_recovery['daily_results'].append({
                'date': date,
                'status': 'no_data',
                'reason': 'No data found',
                'cv_dt': None,
                'dup_ratio': None,
                'price_std': None,
                'coverage': None
            })
            kraken_recovery['days_failed'] += 1
            continue
        
        # Provenance checks
        df['timestamp'] = pd.to_datetime(df['time_period_start'], utc=True)
        df = df.sort_values('timestamp')
        
        # CV(Δt) check
        time_diffs = df['timestamp'].diff().dt.total_seconds().dropna()
        if len(time_diffs) > 1:
            cv_dt = time_diffs.std() / time_diffs.mean() if time_diffs.mean() > 0 else 0
        else:
            cv_dt = 0
        
        # Duplicate ratio
        dup_ratio = df.duplicated(subset=['timestamp', 'price_close', 'volume_traded']).sum() / len(df)
        
        # Price std
        price_std = df['price_close'].std()
        
        # Coverage (simplified)
        coverage = len(df) / 86400  # Rough coverage estimate
        
        # Pass/fail criteria
        passes_cv = cv_dt > 0.05
        passes_dup = dup_ratio <= 0.05
        passes_std = price_std >= 0.10
        passes_coverage = coverage >= 0.40
        
        passes_all = passes_cv and passes_dup and passes_std and passes_coverage
        
        kraken_recovery['daily_results'].append({
            'date': date,
            'status': 'passed' if passes_all else 'failed',
            'reason': 'All criteria met' if passes_all else f"Failed: CV={cv_dt:.3f}, Dup={dup_ratio:.3f}, Std=${price_std:.2f}, Cov={coverage:.3f}",
            'cv_dt': cv_dt,
            'dup_ratio': dup_ratio,
            'price_std': price_std,
            'coverage': coverage,
            'passes_cv': passes_cv,
            'passes_dup': passes_dup,
            'passes_std': passes_std,
            'passes_coverage': passes_coverage
        })
        
        if passes_all:
            kraken_recovery['days_passed'] += 1
        else:
            kraken_recovery['days_failed'] += 1
        
        logger.info(f"      Kraken {date}: {'✅ PASSED' if passes_all else '❌ FAILED'} - {cv_dt:.3f} CV, {dup_ratio:.1%} dup, ${price_std:.2f} std")
    
    # Overall status
    if kraken_recovery['days_passed'] > 0:
        kraken_recovery['recovery_status'] = 'partial_success'
    if kraken_recovery['days_passed'] == len(dates):
        kraken_recovery['recovery_status'] = 'full_success'
    
    # Save results
    with open(f"{OUTPUT_DIR}/kraken_recovery_report.json", 'w') as f:
        json.dump(kraken_recovery, f, indent=2)
    
    logger.info(f"✅ Kraken recovery analysis complete: {kraken_recovery['days_passed']}/{len(dates)} days passed")
    return kraken_recovery

def task5_robustness_analysis(s3_client, bucket: str, dates: List[str], coverage_df: pd.DataFrame) -> str:
    """Task 5: Robustness across resolutions."""
    logger = logging.getLogger(__name__)
    logger.info("🔍 Task 5: Robustness analysis across resolutions...")
    
    resolutions = [2, 5, 10, 60]  # seconds
    robustness_results = []
    
    for date in dates:
        logger.info(f"   📊 Processing {date}...")
        
        # Load data for each venue
        venue_data = {}
        for venue in ['BINANCE', 'COINBASE']:  # Focus on main pair
            df = load_venue_data(s3_client, bucket, date, venue)
            if df is not None and not df.empty:
                df['timestamp'] = pd.to_datetime(df['time_period_start'], utc=True)
                df = df.set_index('timestamp')
                venue_data[venue] = df
        
        if 'BINANCE' not in venue_data or 'COINBASE' not in venue_data:
            continue
        
        # Get coverage for this pair
        pair_coverage = coverage_df[
            (coverage_df['date'] == date) & 
            (coverage_df['venue1'] == 'BINANCE') & 
            (coverage_df['venue2'] == 'COINBASE')
        ]
        
        if pair_coverage.empty or pair_coverage['coverage_pair'].iloc[0] < 0.30:
            continue
        
        # Inner join on intersection seconds
        common_times = venue_data['BINANCE'].index.intersection(venue_data['COINBASE'].index)
        df1_aligned = venue_data['BINANCE'].loc[common_times]
        df2_aligned = venue_data['COINBASE'].loc[common_times]
        
        for resolution in resolutions:
            # Resample to new resolution (right-aligned)
            df1_resampled = df1_aligned['price_close'].resample(f'{resolution}s').last().dropna()
            df2_resampled = df2_aligned['price_close'].resample(f'{resolution}s').last().dropna()
            
            # Align resampled data
            common_resampled = df1_resampled.index.intersection(df2_resampled.index)
            if len(common_resampled) < 10:
                continue
            
            p1 = df1_resampled.loc[common_resampled].values
            p2 = df2_resampled.loc[common_resampled].values
            
            # Compute spreads
            spread_mid = np.abs(p1 - p2) / ((p1 + p2) / 2)
            spread_log = np.abs(np.log(p1) - np.log(p2))
            
            # Compute returns and lag
            r1 = np.diff(np.log(p1))
            r2 = np.diff(np.log(p2))
            
            min_len = min(len(r1), len(r2))
            if min_len < 5:
                continue
            
            r1 = r1[:min_len]
            r2 = r2[:min_len]
            
            # Lag analysis (simplified)
            corr_0, _ = pearsonr(r1, r2)
            
            robustness_results.append({
                'date': date,
                'resolution': resolution,
                'n_points': len(common_resampled),
                'spread_mid_mean': np.mean(spread_mid),
                'spread_log_mean': np.mean(spread_log),
                'correlation_0': corr_0
            })
    
    # Create comparison table
    robustness_df = pd.DataFrame(robustness_results)
    
    with open(f"{OUTPUT_DIR}/robustness_spreads_lag.md", 'w') as f:
        f.write("# Robustness Analysis Across Resolutions\n\n")
        f.write("## Spread Analysis\n\n")
        f.write(robustness_df.groupby('resolution')[['spread_mid_mean', 'spread_log_mean']].mean().to_markdown())
        f.write("\n\n## Correlation Analysis\n\n")
        f.write(robustness_df.groupby('resolution')['correlation_0'].mean().to_markdown())
        f.write("\n\n## Summary\n\n")
        f.write(f"- **Total observations**: {len(robustness_df)}\n")
        f.write(f"- **Resolutions tested**: {sorted(robustness_df['resolution'].unique())}\n")
        f.write(f"- **Mean spread (1s)**: {robustness_df[robustness_df['resolution']==1]['spread_mid_mean'].mean():.6f}\n")
        f.write(f"- **Mean spread (60s)**: {robustness_df[robustness_df['resolution']==60]['spread_mid_mean'].mean():.6f}\n")
    
    logger.info(f"✅ Robustness analysis complete: {len(robustness_df)} observations")
    return f"{OUTPUT_DIR}/robustness_spreads_lag.md"

def task6_sensitivity_analysis(s3_client, bucket: str, dates: List[str], coverage_df: pd.DataFrame) -> str:
    """Task 6: Sensitivity analysis on high/low volatility subsets."""
    logger = logging.getLogger(__name__)
    logger.info("🔍 Task 6: Sensitivity analysis...")
    
    sensitivity_results = []
    
    for date in dates:
        logger.info(f"   📊 Processing {date}...")
        
        # Load data for BINANCE↔COINBASE
        df1 = load_venue_data(s3_client, bucket, date, 'BINANCE')
        df2 = load_venue_data(s3_client, bucket, date, 'COINBASE')
        
        if df1 is None or df2 is None:
            continue
        
        df1['timestamp'] = pd.to_datetime(df1['time_period_start'], utc=True)
        df2['timestamp'] = pd.to_datetime(df2['time_period_start'], utc=True)
        df1 = df1.set_index('timestamp')
        df2 = df2.set_index('timestamp')
        
        # Get coverage for this pair
        pair_coverage = coverage_df[
            (coverage_df['date'] == date) & 
            (coverage_df['venue1'] == 'BINANCE') & 
            (coverage_df['venue2'] == 'COINBASE')
        ]
        
        if pair_coverage.empty or pair_coverage['coverage_pair'].iloc[0] < 0.30:
            continue
        
        # Inner join on intersection seconds
        common_times = df1.index.intersection(df2.index)
        df1_aligned = df1.loc[common_times]
        df2_aligned = df2.loc[common_times]
        
        # Compute returns for volatility analysis
        r1 = np.diff(np.log(df1_aligned['price_close'].values))
        r2 = np.diff(np.log(df2_aligned['price_close'].values))
        
        min_len = min(len(r1), len(r2))
        if min_len < 20:  # Need sufficient data
            continue
        
        r1 = r1[:min_len]
        r2 = r2[:min_len]
        
        # Compute volatility (absolute returns)
        vol = np.abs(r1) + np.abs(r2)  # Combined volatility measure
        
        # Split into high/low volatility
        vol_threshold_high = np.percentile(vol, 75)
        vol_threshold_low = np.percentile(vol, 25)
        
        high_vol_mask = vol >= vol_threshold_high
        low_vol_mask = vol <= vol_threshold_low
        
        # Analyze each subset
        for subset_name, mask in [('high_vol', high_vol_mask), ('low_vol', low_vol_mask)]:
            if np.sum(mask) < 5:  # Need minimum data
                continue
            
            r1_subset = r1[mask]
            r2_subset = r2[mask]
            
            # Compute spreads for this subset
            p1_subset = df1_aligned['price_close'].iloc[1:][mask].values  # Align with returns
            p2_subset = df2_aligned['price_close'].iloc[1:][mask].values
            
            if len(p1_subset) != len(p2_subset) or len(p1_subset) < 5:
                continue
            
            spread_mid = np.abs(p1_subset - p2_subset) / ((p1_subset + p2_subset) / 2)
            
            # Lag analysis
            corr_0, _ = pearsonr(r1_subset, r2_subset)
            
            sensitivity_results.append({
                'date': date,
                'subset': subset_name,
                'n_points': len(p1_subset),
                'spread_mid_mean': np.mean(spread_mid),
                'correlation_0': corr_0,
                'volatility_mean': np.mean(vol[mask])
            })
    
    # Create sensitivity report
    sensitivity_df = pd.DataFrame(sensitivity_results)
    
    with open(f"{OUTPUT_DIR}/sensitivity.md", 'w') as f:
        f.write("# Sensitivity Analysis: High vs Low Volatility\n\n")
        f.write("## Results by Subset\n\n")
        f.write(sensitivity_df.groupby('subset')[['spread_mid_mean', 'correlation_0', 'volatility_mean']].mean().to_markdown())
        f.write("\n\n## Daily Results\n\n")
        f.write(sensitivity_df.to_markdown(index=False))
        f.write("\n\n## Summary\n\n")
        f.write(f"- **Total observations**: {len(sensitivity_df)}\n")
        f.write(f"- **High volatility subset**: {len(sensitivity_df[sensitivity_df['subset']=='high_vol'])} observations\n")
        f.write(f"- **Low volatility subset**: {len(sensitivity_df[sensitivity_df['subset']=='low_vol'])} observations\n")
        
        if not sensitivity_df.empty:
            high_vol = sensitivity_df[sensitivity_df['subset']=='high_vol']
            low_vol = sensitivity_df[sensitivity_df['subset']=='low_vol']
            
            if not high_vol.empty and not low_vol.empty:
                f.write(f"- **Spread difference (high - low)**: {high_vol['spread_mid_mean'].mean() - low_vol['spread_mid_mean'].mean():.6f}\n")
                f.write(f"- **Correlation difference (high - low)**: {high_vol['correlation_0'].mean() - low_vol['correlation_0'].mean():.6f}\n")
    
    logger.info(f"✅ Sensitivity analysis complete: {len(sensitivity_df)} observations")
    return f"{OUTPUT_DIR}/sensitivity.md"

def main():
    """Main execution function."""
    logger = setup_logging()
    s3_client = boto3.client('s3')
    
    # Date range
    dates = [
        '2025-09-25', '2025-09-26', '2025-09-27', '2025-09-28',
        '2025-09-29', '2025-09-30', '2025-10-01'
    ]
    
    logger.info("🚀 Starting ACD 7-day 1s verification pass...")
    
    # Task 1: Alignment & coverage audit
    logger.info("\n" + "="*60)
    logger.info("TASK 1: ALIGNMENT & COVERAGE AUDIT")
    logger.info("="*60)
    coverage_df = task1_alignment_coverage_audit(s3_client, BUCKET, dates)
    
    # Task 2: Spreads analysis
    logger.info("\n" + "="*60)
    logger.info("TASK 2: SPREADS ANALYSIS")
    logger.info("="*60)
    daily_spreads_df, pooled_spreads = task2_spreads_analysis(s3_client, BUCKET, dates, coverage_df)
    
    # Task 3: Returns & lag analysis
    logger.info("\n" + "="*60)
    logger.info("TASK 3: RETURNS & LAG ANALYSIS")
    logger.info("="*60)
    leadlag_df = task3_returns_lag_analysis(s3_client, BUCKET, dates, coverage_df)
    
    # Task 4: Kraken recovery
    logger.info("\n" + "="*60)
    logger.info("TASK 4: KRAKEN RECOVERY")
    logger.info("="*60)
    kraken_recovery = task4_kraken_recovery(s3_client, BUCKET, dates)
    
    # Task 5: Robustness analysis
    logger.info("\n" + "="*60)
    logger.info("TASK 5: ROBUSTNESS ANALYSIS")
    logger.info("="*60)
    robustness_file = task5_robustness_analysis(s3_client, BUCKET, dates, coverage_df)
    
    # Task 6: Sensitivity analysis
    logger.info("\n" + "="*60)
    logger.info("TASK 6: SENSITIVITY ANALYSIS")
    logger.info("="*60)
    sensitivity_file = task6_sensitivity_analysis(s3_client, BUCKET, dates, coverage_df)
    
    # Final summary
    logger.info("\n" + "="*60)
    logger.info("VERIFICATION COMPLETE")
    logger.info("="*60)
    logger.info(f"✅ Coverage analysis: {len(coverage_df)} pairs")
    logger.info(f"✅ Spreads analysis: {len(daily_spreads_df)} pairs")
    logger.info(f"✅ Lead-lag analysis: {len(leadlag_df)} pairs")
    logger.info(f"✅ Kraken recovery: {kraken_recovery['days_passed']}/{len(dates)} days passed")
    logger.info(f"✅ Robustness analysis: {robustness_file}")
    logger.info(f"✅ Sensitivity analysis: {sensitivity_file}")
    
    logger.info(f"\n📁 All outputs saved to: {OUTPUT_DIR}")
    logger.info("🎯 Verification pass complete!")

if __name__ == "__main__":
    main()
