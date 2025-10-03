#!/usr/bin/env python3
"""
Wash-Trading Screens Analysis
Implements multiple screens to detect potential wash trading patterns.
"""
import pandas as pd
import numpy as np
import json
import logging
import time
import argparse
from pathlib import Path
from typing import Dict, List, Tuple, Any
import sys
from scipy import stats
from scipy.stats import chi2, kstest
import warnings
warnings.filterwarnings('ignore')

class NumpyEncoder(json.JSONEncoder):
    """Custom JSON encoder for numpy types."""
    def default(self, obj):
        if isinstance(obj, np.integer):
            return int(obj)
        elif isinstance(obj, np.floating):
            return float(obj)
        elif isinstance(obj, np.ndarray):
            return obj.tolist()
        return super(NumpyEncoder, self).default(obj)

# Add util to path
sys.path.append(str(Path(__file__).parent.parent / "util"))
from diag import Heartbeat, enable_stackdump, log_progress

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger(__name__)

def load_tick_data(venue: str, date: str) -> pd.DataFrame:
    """Load raw tick data for wash analysis."""
    # Try different data formats
    data_paths = [
        Path(f"analysis/flatfiles_ticks/raw/D-{date}/E-{venue}/"),
        Path(f"analysis/flatfiles_ticks/raw/{venue}_{date}.parquet"),
        Path(f"analysis/flatfiles_ticks/wave4/optimized/venue={venue}_date={date}.parquet")
    ]
    
    for data_path in data_paths:
        if data_path.exists():
            if data_path.is_dir():
                # Look for CSV files in directory
                csv_files = list(data_path.glob("*.csv.gz"))
                if csv_files:
                    try:
                        df = pd.read_csv(csv_files[0], compression='gzip', sep=';')
                        logger.info(f"Loaded {len(df):,} ticks for {venue} from {csv_files[0]}")
                        return df
                    except Exception as e:
                        logger.warning(f"Failed to load {csv_files[0]}: {e}")
                        continue
            else:
                try:
                    if data_path.suffix == '.parquet':
                        df = pd.read_parquet(data_path)
                    else:
                        df = pd.read_csv(data_path)
                    logger.info(f"Loaded {len(df):,} ticks for {venue} from {data_path}")
                    return df
                except Exception as e:
                    logger.warning(f"Failed to load {data_path}: {e}")
                    continue
    
    logger.warning(f"No tick data found for {venue} on {date}")
    return pd.DataFrame()

def benford_test(series: pd.Series, test_name: str) -> Dict:
    """Benford's Law test for first digit distribution."""
    logger.info(f"Running Benford test on {test_name}")
    
    if len(series) == 0:
        return {"status": "NO_DATA", "chi2_stat": 0.0, "p_value": 1.0}
    
    # Get first digits
    first_digits = series.astype(str).str[0].astype(int)
    first_digits = first_digits[first_digits > 0]  # Remove zeros
    
    if len(first_digits) == 0:
        return {"status": "NO_VALID_DIGITS", "chi2_stat": 0.0, "p_value": 1.0}
    
    # Count frequencies
    observed = first_digits.value_counts().sort_index()
    observed = observed.reindex(range(1, 10), fill_value=0)
    
    # Expected frequencies (Benford's Law)
    n = len(first_digits)
    expected = np.array([n * np.log10(1 + 1/d) for d in range(1, 10)])
    
    # Chi-square test
    chi2_stat = np.sum((observed - expected)**2 / expected)
    p_value = 1 - chi2.cdf(chi2_stat, df=8)
    
    return {
        "status": "SUCCESS",
        "chi2_stat": float(chi2_stat),
        "p_value": float(p_value),
        "significant": bool(p_value < 0.05),
        "observed": observed.to_dict(),
        "expected": {str(i): float(expected[i-1]) for i in range(1, 10)},
        "n_samples": n
    }

def round_number_clustering(series: pd.Series, test_name: str) -> Dict:
    """Test for clustering around round numbers."""
    logger.info(f"Running round number clustering test on {test_name}")
    
    if len(series) == 0:
        return {"status": "NO_DATA", "z_score": 0.0, "p_value": 1.0}
    
    # Define round numbers
    round_numbers = [1, 5, 10, 50, 100, 500, 1000, 5000, 10000]
    
    # Count values at round numbers (within 1% tolerance)
    round_counts = {}
    total_count = len(series)
    
    for round_num in round_numbers:
        tolerance = round_num * 0.01
        count = np.sum(np.abs(series - round_num) <= tolerance)
        round_counts[round_num] = count
    
    # Calculate z-scores vs expected (assuming uniform distribution)
    z_scores = {}
    p_values = {}
    
    for round_num, count in round_counts.items():
        expected = total_count / len(round_numbers)  # Uniform expectation
        std_dev = np.sqrt(expected * (1 - 1/len(round_numbers)))
        z_score = (count - expected) / std_dev if std_dev > 0 else 0
        z_scores[round_num] = z_score
        p_values[round_num] = 2 * (1 - stats.norm.cdf(abs(z_score)))
    
    # Overall test
    max_z = max(abs(z) for z in z_scores.values())
    overall_p = 2 * (1 - stats.norm.cdf(max_z))
    
    return {
        "status": "SUCCESS",
        "round_counts": round_counts,
        "z_scores": z_scores,
        "p_values": p_values,
        "max_z_score": max_z,
        "overall_p_value": overall_p,
        "significant": bool(overall_p < 0.05),
        "total_samples": total_count
    }

def tail_fit_test(series: pd.Series, test_name: str) -> Dict:
    """Test for power-law tail distribution."""
    logger.info(f"Running tail fit test on {test_name}")
    
    if len(series) == 0:
        return {"status": "NO_DATA", "alpha": 0.0, "ks_stat": 0.0, "p_value": 1.0}
    
    # Remove zeros and negative values
    series_clean = series[series > 0]
    
    if len(series_clean) < 100:
        return {"status": "INSUFFICIENT_DATA", "alpha": 0.0, "ks_stat": 0.0, "p_value": 1.0}
    
    # Fit power-law to tail (top 10%)
    tail_threshold = series_clean.quantile(0.9)
    tail_data = series_clean[series_clean >= tail_threshold]
    
    if len(tail_data) < 10:
        return {"status": "INSUFFICIENT_TAIL", "alpha": 0.0, "ks_stat": 0.0, "p_value": 1.0}
    
    # Estimate alpha (power-law exponent)
    log_data = np.log(tail_data)
    alpha = 1 + len(tail_data) / np.sum(log_data - np.log(tail_data.min()))
    
    # Generate theoretical power-law distribution
    x_min = tail_data.min()
    theoretical = np.random.pareto(alpha - 1, size=len(tail_data)) * x_min
    
    # Kolmogorov-Smirnov test
    ks_stat, p_value = kstest(tail_data, lambda x: 1 - (x/x_min)**(-alpha + 1))
    
    return {
        "status": "SUCCESS",
        "alpha": float(alpha),
        "ks_stat": float(ks_stat),
        "p_value": float(p_value),
        "significant": bool(p_value < 0.05),
        "tail_size": len(tail_data),
        "tail_threshold": float(tail_threshold)
    }

def temporal_regularity_test(series: pd.Series, test_name: str) -> Dict:
    """Test for temporal regularity in trade timing."""
    logger.info(f"Running temporal regularity test on {test_name}")
    
    if len(series) < 100:
        return {"status": "INSUFFICIENT_DATA", "regularity_score": 0.0, "p_value": 1.0}
    
    # Convert to datetime if not already
    if not pd.api.types.is_datetime64_any_dtype(series):
        series = pd.to_datetime(series)
    
    # Compute inter-arrival times
    inter_arrivals = series.diff().dropna()
    
    if len(inter_arrivals) == 0:
        return {"status": "NO_INTER_ARRIVALS", "regularity_score": 0.0, "p_value": 1.0}
    
    # Look for regular patterns (e.g., trades every N seconds)
    inter_arrivals_seconds = inter_arrivals.dt.total_seconds()
    
    # Find common intervals
    common_intervals = [1, 5, 10, 30, 60, 300, 600]  # 1s, 5s, 10s, 30s, 1m, 5m, 10m
    
    regularity_scores = {}
    for interval in common_intervals:
        tolerance = interval * 0.1  # 10% tolerance
        matches = np.sum(np.abs(inter_arrivals_seconds - interval) <= tolerance)
        score = matches / len(inter_arrivals_seconds)
        regularity_scores[interval] = score
    
    # Overall regularity score
    max_score = max(regularity_scores.values())
    
    # Statistical test (simplified)
    # Compare against random inter-arrivals
    n_bootstrap = 1000
    random_scores = []
    
    for _ in range(n_bootstrap):
        random_intervals = np.random.exponential(inter_arrivals_seconds.mean(), size=len(inter_arrivals_seconds))
        random_matches = np.sum(np.abs(random_intervals - 60) <= 6)  # 60s ± 10%
        random_scores.append(random_matches / len(random_intervals))
    
    null_mean = np.mean(random_scores)
    null_std = np.std(random_scores)
    z_score = (max_score - null_mean) / null_std if null_std > 0 else 0
    p_value = 1 - stats.norm.cdf(z_score)
    
    return {
        "status": "SUCCESS",
        "regularity_scores": regularity_scores,
        "max_score": float(max_score),
        "z_score": float(z_score),
        "p_value": float(p_value),
        "significant": bool(p_value < 0.05),
        "n_intervals": len(inter_arrivals_seconds)
    }

def analyze_venue_wash_screens(venue: str, date: str) -> Dict:
    """Run all wash trading screens for a venue."""
    logger.info(f"Analyzing wash screens for {venue}")
    
    # Load tick data
    df = load_tick_data(venue, date)
    
    if df.empty:
        return {"status": "NO_DATA", "venue": venue, "date": date}
    
    results = {
        "venue": venue,
        "date": date,
        "total_ticks": len(df),
        "screens": {}
    }
    
    # Benford tests on volumes and notional values
    if 'base_amount' in df.columns:
        results["screens"]["benford_volume"] = benford_test(df['base_amount'], f"{venue}_volume")
    
    if 'price' in df.columns and 'base_amount' in df.columns:
        notional = df['price'] * df['base_amount']
        results["screens"]["benford_notional"] = benford_test(notional, f"{venue}_notional")
    
    # Round number clustering
    if 'base_amount' in df.columns:
        results["screens"]["round_clustering_volume"] = round_number_clustering(
            df['base_amount'], f"{venue}_volume"
        )
    
    if 'price' in df.columns:
        results["screens"]["round_clustering_price"] = round_number_clustering(
            df['price'], f"{venue}_price"
        )
    
    # Tail fit tests
    if 'base_amount' in df.columns:
        results["screens"]["tail_fit_volume"] = tail_fit_test(df['base_amount'], f"{venue}_volume")
    
    if 'price' in df.columns:
        results["screens"]["tail_fit_price"] = tail_fit_test(df['price'], f"{venue}_price")
    
    # Temporal regularity
    if 'time_exchange' in df.columns:
        results["screens"]["temporal_regularity"] = temporal_regularity_test(
            df['time_exchange'], f"{venue}_timing"
        )
    
    return results

def generate_wash_dashboard(results: Dict) -> str:
    """Generate wash trading dashboard."""
    
    report = "# Wash Trading Screens Dashboard\n\n"
    report += f"**Analysis Date**: {pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
    report += f"**Method**: Multi-screen wash trading detection\n\n"
    
    # Venue summary
    report += "## Venue Summary\n\n"
    report += "| Venue | Total Ticks | Screens Run | Significant |\n"
    report += "|-------|-------------|-------------|------------|\n"
    
    for venue, result in results.items():
        if result.get("status") == "NO_DATA":
            report += f"| {venue} | 0 | 0 | 0 |\n"
            continue
        
        total_ticks = result.get("total_ticks", 0)
        screens = result.get("screens", {})
        significant = sum(1 for screen in screens.values() if screen.get("significant", False))
        
        report += f"| {venue} | {total_ticks:,} | {len(screens)} | {significant} |\n"
    
    # Detailed results per venue
    for venue, result in results.items():
        if result.get("status") == "NO_DATA":
            continue
        
        report += f"\n## {venue} Results\n\n"
        
        screens = result.get("screens", {})
        for screen_name, screen_result in screens.items():
            report += f"### {screen_name}\n\n"
            
            if screen_result.get("status") == "SUCCESS":
                report += f"- **Status**: {screen_result['status']}\n"
                
                if "p_value" in screen_result:
                    report += f"- **P-Value**: {screen_result['p_value']:.3f}\n"
                    report += f"- **Significant**: {'✓' if screen_result.get('significant', False) else '✗'}\n"
                
                if "chi2_stat" in screen_result:
                    report += f"- **Chi-Square**: {screen_result['chi2_stat']:.3f}\n"
                
                if "z_score" in screen_result:
                    report += f"- **Z-Score**: {screen_result['z_score']:.3f}\n"
                
                if "alpha" in screen_result:
                    report += f"- **Power-Law Alpha**: {screen_result['alpha']:.3f}\n"
                
                if "max_score" in screen_result:
                    report += f"- **Max Regularity Score**: {screen_result['max_score']:.3f}\n"
            else:
                report += f"- **Status**: {screen_result.get('status', 'UNKNOWN')}\n"
            
            report += "\n"
    
    # Overall flags
    report += "## Wash Trading Flags\n\n"
    
    flagged_venues = []
    for venue, result in results.items():
        if result.get("status") == "NO_DATA":
            continue
        
        screens = result.get("screens", {})
        significant_screens = [name for name, screen in screens.items() 
                              if screen.get("significant", False)]
        
        if significant_screens:
            flagged_venues.append({
                "venue": venue,
                "flags": significant_screens,
                "flag_count": len(significant_screens)
            })
    
    if flagged_venues:
        report += "| Venue | Flag Count | Flags |\n"
        report += "|-------|------------|-------|\n"
        
        for venue_info in flagged_venues:
            flags_str = ", ".join(venue_info["flags"])
            report += f"| {venue_info['venue']} | {venue_info['flag_count']} | {flags_str} |\n"
    else:
        report += "No venues flagged for wash trading patterns.\n"
    
    return report

def main():
    """Main execution function."""
    parser = argparse.ArgumentParser(description="Wash Trading Screens Analysis")
    parser.add_argument("--date", default="20250925", help="Date to analyze")
    parser.add_argument("--venues", default="BINANCE,COINBASE,BYBITSPOT,BITGET", 
                       help="Comma-separated venues")
    parser.add_argument("--out", default="analysis/wash_screens", 
                       help="Output directory")
    
    args = parser.parse_args()
    
    # Setup diagnostics
    enable_stackdump()
    beat = Heartbeat("analysis/_diag/wash_screens_heartbeat.json", 
                    meta={"job": "wash-screens", "args": vars(args)})
    
    try:
        # Parse venues
        venues = [v.strip() for v in args.venues.split(",")]
        
        # Run wash screens for each venue
        results = {}
        for venue in venues:
            logger.info(f"Analyzing {venue}...")
            result = analyze_venue_wash_screens(venue, args.date)
            results[venue] = result
            log_progress(beat, f"analyzed_{venue}", venue_done=venue)
        
        # Save results
        output_dir = Path(args.out)
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Save individual venue results
        for venue, result in results.items():
            with open(output_dir / f"screens_{venue}_{args.date}.json", "w") as f:
                json.dump(result, f, indent=2, cls=NumpyEncoder)
        
        # Generate dashboard
        dashboard = generate_wash_dashboard(results)
        with open(output_dir / "wash_screen_dashboard.md", "w") as f:
            f.write(dashboard)
        
        # Save overall results
        with open(output_dir / "overall_results.json", "w") as f:
            json.dump(results, f, indent=2, cls=NumpyEncoder)
        
        logger.info(f"✅ SUCCESS: Wash screens analysis complete")
        logger.info(f"📊 Results saved to: {output_dir}")
        
        # Print summary
        print("\n" + "=" * 60)
        print("WASH TRADING SCREENS DASHBOARD")
        print("=" * 60)
        print(dashboard)
        
    except Exception as e:
        logger.error(f"❌ ERROR: {e}")
        log_progress(beat, "error", error=str(e))
        raise

if __name__ == "__main__":
    main()
