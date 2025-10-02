#!/usr/bin/env python3
"""
ACD Phase SIG - Detailed Signal Analysis

Investigates the concerning -1.000 correlations and provides deeper analysis.
"""

import argparse
import json
import logging
import sys
import tempfile
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Dict, List, Any, Tuple, Optional

import boto3
import pandas as pd
import numpy as np
from scipy import stats
from scipy.signal import correlate

def setup_logging(verbose: bool = False):
    """Setup logging configuration."""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler("acd_phase_sig_detailed_analysis.log"),
        ],
    )

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

def load_canonical_data(s3_client, bucket: str, date: str) -> Dict[str, pd.DataFrame]:
    """Load canonical_1200_1300 data for all 5 venues."""
    logger = logging.getLogger(__name__)
    
    venues = ['binance', 'kraken', 'okx', 'coinbase', 'bybit']
    canonical_data = {}
    
    for venue in venues:
        s3_key = f"backfill/{venue}/{date}/canonical_1200_1300/part-0000.parquet"
        
        parquet_content = get_s3_object_content(s3_client, bucket, s3_key)
        if not parquet_content:
            logger.error(f"No canonical data found for {venue} at {s3_key}")
            continue
        
        try:
            with tempfile.NamedTemporaryFile(suffix='.parquet', delete=False) as tmp_file:
                tmp_file.write(parquet_content)
                tmp_file.flush()
                df = pd.read_parquet(tmp_file.name)
                Path(tmp_file.name).unlink()
            
            # Ensure timestamp is datetime
            df['timestamp'] = pd.to_datetime(df['timestamp'], utc=True)
            df['dt'] = pd.to_datetime(df['dt'], utc=True)
            
            canonical_data[venue] = df
            logger.info(f"Loaded {venue}: {len(df)} rows")
            
        except Exception as e:
            logger.error(f"Error loading {venue}: {e}")
    
    return canonical_data

def investigate_data_quality(canonical_data: Dict[str, pd.DataFrame]) -> Dict[str, Any]:
    """Investigate data quality issues that might cause perfect correlations."""
    logger = logging.getLogger(__name__)
    
    quality_analysis = {}
    
    for venue, df in canonical_data.items():
        if df.empty:
            continue
        
        # Basic statistics
        price_stats = {
            "mean": float(df['price'].mean()),
            "std": float(df['price'].std()),
            "min": float(df['price'].min()),
            "max": float(df['price'].max()),
            "unique_values": df['price'].nunique(),
            "duplicate_ratio": (len(df) - df['price'].nunique()) / len(df)
        }
        
        # Check for constant prices
        is_constant = price_stats['std'] < 0.01
        is_near_constant = price_stats['std'] < 1.0
        
        # Check for linear trends
        price_values = df['price'].values
        if len(price_values) > 2:
            # Simple linear trend detection
            x = np.arange(len(price_values))
            slope, intercept, r_value, p_value, std_err = stats.linregress(x, price_values)
            linear_trend = abs(r_value) > 0.9
        else:
            linear_trend = False
        
        # Check for monotonic sequences
        is_monotonic = df['price'].is_monotonic_increasing or df['price'].is_monotonic_decreasing
        
        # Check timestamp patterns
        time_diffs = df['timestamp'].diff().dropna()
        time_stats = {
            "mean_interval": float(time_diffs.mean().total_seconds()),
            "std_interval": float(time_diffs.std().total_seconds()),
            "min_interval": float(time_diffs.min().total_seconds()),
            "max_interval": float(time_diffs.max().total_seconds())
        }
        
        quality_analysis[venue] = {
            "price_stats": price_stats,
            "is_constant": bool(is_constant),
            "is_near_constant": bool(is_near_constant),
            "linear_trend": bool(linear_trend),
            "is_monotonic": bool(is_monotonic),
            "time_stats": time_stats,
            "n_rows": len(df),
            "data_quality_issues": []
        }
        
        # Flag issues
        if is_constant:
            quality_analysis[venue]["data_quality_issues"].append("Constant prices")
        if is_near_constant:
            quality_analysis[venue]["data_quality_issues"].append("Near-constant prices")
        if linear_trend:
            quality_analysis[venue]["data_quality_issues"].append("Strong linear trend")
        if is_monotonic:
            quality_analysis[venue]["data_quality_issues"].append("Monotonic price sequence")
        if time_stats["std_interval"] < 0.1:
            quality_analysis[venue]["data_quality_issues"].append("Regular time intervals")
        
        logger.info(f"{venue}: std=${price_stats['std']:.2f}, unique={price_stats['unique_values']}, issues={quality_analysis[venue]['data_quality_issues']}")
    
    return quality_analysis

def compute_detailed_correlations(canonical_data: Dict[str, pd.DataFrame]) -> Dict[str, Any]:
    """Compute detailed correlation analysis with data quality checks."""
    logger = logging.getLogger(__name__)
    
    venues = list(canonical_data.keys())
    detailed_correlations = {}
    
    for i, venue1 in enumerate(venues):
        for j, venue2 in enumerate(venues):
            if i >= j:
                continue
            
            df1 = canonical_data[venue1]
            df2 = canonical_data[venue2]
            
            # Find overlapping time periods
            start_time = max(df1['timestamp'].min(), df2['timestamp'].min())
            end_time = min(df1['timestamp'].max(), df2['timestamp'].max())
            
            if start_time >= end_time:
                logger.warning(f"No overlap between {venue1} and {venue2}")
                continue
            
            # Filter to overlapping period
            df1_overlap = df1[(df1['timestamp'] >= start_time) & (df1['timestamp'] <= end_time)]
            df2_overlap = df2[(df2['timestamp'] >= start_time) & (df2['timestamp'] <= end_time)]
            
            if len(df1_overlap) < 10 or len(df2_overlap) < 10:
                logger.warning(f"Insufficient overlap between {venue1} and {venue2}")
                continue
            
            # Interpolate to common time grid
            time_grid = pd.date_range(start=start_time, end=end_time, freq='1s', tz=timezone.utc)
            
            df1_interp = df1_overlap.set_index('timestamp')['price'].reindex(time_grid, method='ffill')
            df2_interp = df2_overlap.set_index('timestamp')['price'].reindex(time_grid, method='ffill')
            
            # Remove NaN values
            valid_mask = ~(df1_interp.isna() | df2_interp.isna())
            series1 = df1_interp[valid_mask]
            series2 = df2_interp[valid_mask]
            
            if len(series1) < 10:
                logger.warning(f"Insufficient valid data between {venue1} and {venue2}")
                continue
            
            # Compute various correlation measures
            pearson_corr = series1.corr(series2)
            spearman_corr = series1.corr(series2, method='spearman')
            
            # Check for perfect correlation
            is_perfect_corr = abs(pearson_corr) > 0.999
            
            # Compute price change correlations
            price1_changes = series1.diff().dropna()
            price2_changes = series2.diff().dropna()
            
            if len(price1_changes) > 5 and len(price2_changes) > 5:
                change_corr = price1_changes.corr(price2_changes)
            else:
                change_corr = np.nan
            
            detailed_correlations[f"{venue1}_vs_{venue2}"] = {
                "venue1": venue1,
                "venue2": venue2,
                "pearson_correlation": float(pearson_corr),
                "spearman_correlation": float(spearman_corr),
                "change_correlation": float(change_corr) if not pd.isna(change_corr) else None,
                "is_perfect_correlation": bool(is_perfect_corr),
                "n_points": len(series1),
                "overlap_duration": (end_time - start_time).total_seconds(),
                "series1_stats": {
                    "mean": float(series1.mean()),
                    "std": float(series1.std()),
                    "min": float(series1.min()),
                    "max": float(series1.max())
                },
                "series2_stats": {
                    "mean": float(series2.mean()),
                    "std": float(series2.std()),
                    "min": float(series2.min()),
                    "max": float(series2.max())
                }
            }
            
            logger.info(f"{venue1} vs {venue2}: Pearson={pearson_corr:.3f}, Spearman={spearman_corr:.3f}, Perfect={is_perfect_corr}")
    
    return detailed_correlations

def analyze_volatility_patterns(canonical_data: Dict[str, pd.DataFrame]) -> Dict[str, Any]:
    """Analyze volatility patterns and clustering."""
    logger = logging.getLogger(__name__)
    
    volatility_analysis = {}
    
    for venue, df in canonical_data.items():
        if df.empty:
            continue
        
        # Compute price changes
        price_changes = df['price'].diff().dropna()
        
        # Compute rolling volatility
        rolling_vol = price_changes.rolling(window=30, min_periods=10).std()
        
        # Volatility statistics
        vol_stats = {
            "mean_volatility": float(rolling_vol.mean()),
            "std_volatility": float(rolling_vol.std()),
            "max_volatility": float(rolling_vol.max()),
            "volatility_spikes": int((rolling_vol > rolling_vol.quantile(0.9)).sum()),
            "volatility_clustering": float(rolling_vol.autocorr(lag=1)) if len(rolling_vol) > 1 else 0.0
        }
        
        volatility_analysis[venue] = {
            "vol_stats": vol_stats,
            "n_volatility_points": len(rolling_vol.dropna()),
            "volatility_trend": "increasing" if rolling_vol.iloc[-10:].mean() > rolling_vol.iloc[:10].mean() else "decreasing"
        }
        
        logger.info(f"{venue} volatility: mean={vol_stats['mean_volatility']:.3f}, spikes={vol_stats['volatility_spikes']}")
    
    return volatility_analysis

def generate_detailed_report(quality_analysis: Dict[str, Any], detailed_correlations: Dict[str, Any], volatility_analysis: Dict[str, Any]) -> str:
    """Generate detailed analysis report."""
    
    report_content = f"""# ACD Phase SIG - Detailed Signal Analysis Report

**Date**: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}  
**Window**: canonical_1200_1300 (1 hour)  
**Venues**: {len(quality_analysis)} exchanges  

## Data Quality Analysis

| Venue | Price Std | Unique Values | Constant | Linear Trend | Monotonic | Issues |
|-------|-----------|---------------|----------|--------------|-----------|--------|
"""
    
    for venue, analysis in quality_analysis.items():
        issues_str = ", ".join(analysis['data_quality_issues']) if analysis['data_quality_issues'] else "None"
        report_content += f"| {venue.upper()} | ${analysis['price_stats']['std']:.2f} | {analysis['price_stats']['unique_values']} | {'✅' if analysis['is_constant'] else '❌'} | {'✅' if analysis['linear_trend'] else '❌'} | {'✅' if analysis['is_monotonic'] else '❌'} | {issues_str} |\n"
    
    report_content += f"""

## Detailed Correlation Analysis

| Venue Pair | Pearson | Spearman | Change Corr | Perfect | N Points | Overlap (s) |
|------------|---------|----------|-------------|---------|----------|-------------|
"""
    
    for pair, data in detailed_correlations.items():
        change_corr_str = f"{data['change_correlation']:.3f}" if data['change_correlation'] is not None else "N/A"
        report_content += f"| {pair.upper()} | {data['pearson_correlation']:.3f} | {data['spearman_correlation']:.3f} | {change_corr_str} | {'✅' if data['is_perfect_correlation'] else '❌'} | {data['n_points']} | {data['overlap_duration']:.0f} |\n"
    
    report_content += f"""

## Volatility Analysis

| Venue | Mean Vol | Std Vol | Max Vol | Spikes | Clustering | Trend |
|-------|----------|---------|---------|--------|------------|-------|
"""
    
    for venue, analysis in volatility_analysis.items():
        vol_stats = analysis['vol_stats']
        report_content += f"| {venue.upper()} | {vol_stats['mean_volatility']:.3f} | {vol_stats['std_volatility']:.3f} | {vol_stats['max_volatility']:.3f} | {vol_stats['volatility_spikes']} | {vol_stats['volatility_clustering']:.3f} | {analysis['volatility_trend']} |\n"
    
    report_content += f"""

## Key Findings

### Data Quality Issues

"""
    
    # Count issues
    total_issues = 0
    for venue, analysis in quality_analysis.items():
        total_issues += len(analysis['data_quality_issues'])
        if analysis['data_quality_issues']:
            report_content += f"- **{venue.upper()}**: {', '.join(analysis['data_quality_issues'])}\n"
    
    if total_issues == 0:
        report_content += "- ✅ No data quality issues detected\n"
    
    report_content += f"""

### Correlation Analysis

"""
    
    perfect_correlations = [pair for pair, data in detailed_correlations.items() if data['is_perfect_correlation']]
    if perfect_correlations:
        report_content += f"- **⚠️ Perfect Correlations Detected**: {len(perfect_correlations)} pairs show perfect correlation (-1.000)\n"
        for pair in perfect_correlations:
            report_content += f"  - {pair.upper()}\n"
    else:
        report_content += "- ✅ No perfect correlations detected\n"
    
    report_content += f"""

### Volatility Patterns

"""
    
    high_volatility_venues = [venue for venue, analysis in volatility_analysis.items() 
                             if analysis['vol_stats']['mean_volatility'] > 1.0]
    if high_volatility_venues:
        report_content += f"- **High Volatility Venues**: {', '.join([v.upper() for v in high_volatility_venues])}\n"
    
    clustering_venues = [venue for venue, analysis in volatility_analysis.items() 
                        if analysis['vol_stats']['volatility_clustering'] > 0.5]
    if clustering_venues:
        report_content += f"- **Volatility Clustering**: {', '.join([v.upper() for v in clustering_venues])}\n"
    
    report_content += f"""

## Recommendations

"""
    
    if perfect_correlations:
        report_content += "1. **Investigate Perfect Correlations**: The -1.000 correlations suggest data quality issues or synthetic data patterns.\n"
    
    if total_issues > 0:
        report_content += "2. **Address Data Quality Issues**: Review data generation and validation processes.\n"
    
    report_content += "3. **Validate Data Sources**: Ensure all data comes from real exchange feeds.\n"
    report_content += "4. **Review Correlation Methods**: Consider alternative correlation measures for non-linear relationships.\n"
    
    report_content += f"""

## Next Steps

{'⚠️ Address data quality issues before proceeding with ACD analysis' if perfect_correlations or total_issues > 0 else '✅ Data quality acceptable for ACD analysis'}
"""
    
    return report_content

def main():
    """Main detailed analysis function."""
    parser = argparse.ArgumentParser(description='ACD Phase SIG - Detailed Signal Analysis')
    parser.add_argument('--verbose', action='store_true', help='Verbose logging')
    parser.add_argument('--bucket', default='acd-monitor-snapshots', help='S3 bucket name')
    parser.add_argument('--date', default='20251002', help='Date to process (YYYYMMDD)')
    
    args = parser.parse_args()
    setup_logging(args.verbose)
    logger = logging.getLogger(__name__)
    
    # Initialize S3 client
    s3_client = boto3.client('s3')
    
    print("\n" + "="*80)
    print("🔍 ACD PHASE SIG - DETAILED SIGNAL ANALYSIS")
    print("="*80)
    
    print(f"📅 Processing date: {args.date}")
    print(f"📊 Window: canonical_1200_1300 (1 hour)")
    
    # Load canonical data
    print(f"\n🔄 Loading canonical data...")
    try:
        canonical_data = load_canonical_data(s3_client, args.bucket, args.date)
        
        if len(canonical_data) < 3:
            print(f"❌ Insufficient venues: {len(canonical_data)}/5")
            sys.exit(1)
        
        print(f"✅ Loaded data for {len(canonical_data)} venues")
            
    except Exception as e:
        print(f"❌ Error loading canonical data: {e}")
        sys.exit(1)
    
    # Investigate data quality
    print(f"\n🔍 Investigating data quality...")
    try:
        quality_analysis = investigate_data_quality(canonical_data)
        
        print(f"✅ Completed data quality analysis")
        for venue, analysis in quality_analysis.items():
            if analysis['data_quality_issues']:
                print(f"   ⚠️ {venue}: {', '.join(analysis['data_quality_issues'])}")
            else:
                print(f"   ✅ {venue}: No issues")
            
    except Exception as e:
        print(f"❌ Error investigating data quality: {e}")
        sys.exit(1)
    
    # Compute detailed correlations
    print(f"\n📊 Computing detailed correlations...")
    try:
        detailed_correlations = compute_detailed_correlations(canonical_data)
        
        print(f"✅ Computed detailed correlations for {len(detailed_correlations)} pairs")
        perfect_corrs = [pair for pair, data in detailed_correlations.items() if data['is_perfect_correlation']]
        if perfect_corrs:
            print(f"   ⚠️ Perfect correlations: {', '.join(perfect_corrs)}")
            
    except Exception as e:
        print(f"❌ Error computing detailed correlations: {e}")
        sys.exit(1)
    
    # Analyze volatility patterns
    print(f"\n📊 Analyzing volatility patterns...")
    try:
        volatility_analysis = analyze_volatility_patterns(canonical_data)
        
        print(f"✅ Completed volatility analysis")
        for venue, analysis in volatility_analysis.items():
            print(f"   {venue}: mean_vol={analysis['vol_stats']['mean_volatility']:.3f}, spikes={analysis['vol_stats']['volatility_spikes']}")
            
    except Exception as e:
        print(f"❌ Error analyzing volatility patterns: {e}")
        sys.exit(1)
    
    # Generate detailed report
    print(f"\n📝 Generating detailed report...")
    try:
        detailed_report = generate_detailed_report(quality_analysis, detailed_correlations, volatility_analysis)
        
        # Save detailed report
        report_key = f"analysis/{args.date}/ACD/_sig/detailed_signal_analysis_report.md"
        s3_client.put_object(
            Bucket=args.bucket,
            Key=report_key,
            Body=detailed_report.encode('utf-8'),
            ContentType='text/markdown'
        )
        
        print(f"💾 Saved detailed report: s3://{args.bucket}/{report_key}")
            
    except Exception as e:
        print(f"❌ Error generating detailed report: {e}")
        sys.exit(1)
    
    # Save detailed data
    print(f"\n💾 Saving detailed analysis data...")
    
    detailed_data = {
        "date": args.date,
        "window": "canonical_1200_1300",
        "quality_analysis": quality_analysis,
        "detailed_correlations": detailed_correlations,
        "volatility_analysis": volatility_analysis,
        "summary_timestamp": datetime.now(timezone.utc).isoformat()
    }
    
    data_key = f"analysis/{args.date}/ACD/_sig/detailed_signal_analysis_data.json"
    s3_client.put_object(
        Bucket=args.bucket,
        Key=data_key,
        Body=json.dumps(detailed_data, indent=2),
        ContentType='application/json'
    )
    
    print(f"💾 Saved detailed data: s3://{args.bucket}/{data_key}")
    
    # Final summary
    print(f"\n📊 DETAILED ANALYSIS SUMMARY")
    print("="*60)
    
    total_issues = sum(len(analysis['data_quality_issues']) for analysis in quality_analysis.values())
    perfect_corrs = [pair for pair, data in detailed_correlations.items() if data['is_perfect_correlation']]
    
    print(f"Data quality issues: {total_issues}")
    print(f"Perfect correlations: {len(perfect_corrs)}")
    print(f"Venues analyzed: {len(quality_analysis)}")
    print(f"Correlation pairs: {len(detailed_correlations)}")
    
    if perfect_corrs or total_issues > 0:
        print(f"\n⚠️ DATA QUALITY CONCERNS DETECTED")
        print(f"   Perfect correlations: {len(perfect_corrs)}")
        print(f"   Data quality issues: {total_issues}")
        print(f"   Review detailed report for specific issues")
    else:
        print(f"\n✅ DATA QUALITY ACCEPTABLE")
        print(f"   No significant data quality issues detected")
    
    print(f"\n📁 Generated artifacts:")
    print(f"  Detailed report: s3://{args.bucket}/{report_key}")
    print(f"  Detailed data: s3://{args.bucket}/{data_key}")

if __name__ == "__main__":
    main()
