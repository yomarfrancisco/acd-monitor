#!/usr/bin/env python3
"""
Phase 41K-HYPOTHESIS-TESTING: Causal Anomaly Detection & Regime Analysis
=======================================================================

Objective: Explore and quantify causal anomalies, regime-shift persistence, and 
potential coordination patterns using validated ICP + VMM outputs.

Guardrails:
- Read-only canonical + reports folders
- No new modeling or resampling — analysis only on validated metrics
- Write outputs exclusively to /data_v7/reports/hypothesis/
- Deterministic mode (seed = 42)
- Stop immediately if VALIDATION_OK != true
"""

import os
import sys
import json
import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime, timedelta
import traceback
import warnings
warnings.filterwarnings('ignore')

# Scientific computing imports
from scipy import stats
from scipy.spatial.distance import pdist, squareform
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import LinearRegression
import matplotlib.pyplot as plt
import seaborn as sns

# Configuration
BASE_DIR = Path(__file__).parent
CAUSALITY_DIR = BASE_DIR / 'data_v7' / 'reports' / 'causality'
VALIDATION_DIR = BASE_DIR / 'data_v7' / 'reports' / 'validation'
BEACONS_DIR = BASE_DIR / 'data_v7' / 'beacons'
HYPOTHESIS_DIR = BASE_DIR / 'data_v7' / 'reports' / 'hypothesis'

# Set deterministic seed
np.random.seed(42)

# Expected input files
ICP_VMM_METRICS_FILE = CAUSALITY_DIR / 'icp_vmm_metrics.json'
VALIDATION_SUMMARY_FILE = VALIDATION_DIR / 'validation_summary.json'
HOURLY_BEACONS_FILE = BEACONS_DIR / 'hourly_beacons.parquet'
VENUE_ALIGNED_FILE = BEACONS_DIR / 'venue_aligned.parquet'

# Venues
VENUES = ['BINANCE', 'BITGET', 'BYBITSPOT', 'COINBASE']

def setup_directories():
    """Create hypothesis output directory"""
    HYPOTHESIS_DIR.mkdir(parents=True, exist_ok=True)
    print(f"📁 Created hypothesis directory: {HYPOTHESIS_DIR}")

def log_message(message, log_file):
    """Log message to file and console"""
    timestamp = datetime.utcnow().isoformat()
    log_line = f"[{timestamp}] {message}"
    print(log_line)
    with open(log_file, 'a') as f:
        f.write(log_line + '\n')

def verify_validation_status():
    """Verify VALIDATION_OK=true before proceeding"""
    if not VALIDATION_SUMMARY_FILE.exists():
        raise RuntimeError("Validation summary file not found")
    
    with open(VALIDATION_SUMMARY_FILE, 'r') as f:
        validation_data = json.load(f)
    
    if not validation_data.get('VALIDATION_OK', False):
        raise RuntimeError("VALIDATION_OK=false - cannot proceed with hypothesis testing")
    
    print("✅ Validation status verified")
    return True

def load_validated_data():
    """Load validated ICP-VMM metrics and beacon data"""
    print("📊 Loading validated data...")
    
    # Load ICP-VMM metrics
    with open(ICP_VMM_METRICS_FILE, 'r') as f:
        metrics = json.load(f)
    
    # Load beacon data
    beacon_df = pd.read_parquet(HOURLY_BEACONS_FILE)
    venue_aligned_df = pd.read_parquet(VENUE_ALIGNED_FILE)
    
    print(f"  Loaded ICP-VMM metrics: {len(metrics)} categories")
    print(f"  Loaded beacon data: {len(beacon_df)} records")
    print(f"  Loaded venue-aligned data: {len(venue_aligned_df)} records")
    
    return metrics, beacon_df, venue_aligned_df

def causal_anomaly_detection(metrics, beacon_df, log_file):
    """Compute residual invariance scores and detect anomalies"""
    log_message("🔍 Starting causal anomaly detection...", log_file)
    
    try:
        # Extract ICP results
        icp_results = metrics.get('icp', {})
        variables = icp_results.get('variables', [])
        results = icp_results.get('results', {})
        
        log_message(f"  Analyzing {len(variables)} variables for causal anomalies", log_file)
        
        # Prepare data for anomaly detection
        icp_data = beacon_df[['timestamp', 'venue'] + variables].dropna()
        
        # Compute residual invariance scores per variable pair
        anomaly_scores = {}
        anomaly_timestamps = {}
        
        for target_var in variables:
            log_message(f"  Computing anomalies for {target_var}...", log_file)
            
            target_result = results.get(target_var, {})
            parents = target_result.get('invariant_parents', [])
            
            if not parents:
                continue
            
            # Compute residuals for each venue
            venue_residuals = {}
            
            for venue in VENUES:
                venue_data = icp_data[icp_data['venue'] == venue].copy()
                if len(venue_data) < 10:
                    continue
                
                # Prepare features
                X = venue_data[parents].values
                y = venue_data[target_var].values
                
                # Fit linear regression
                reg = LinearRegression().fit(X, y)
                y_pred = reg.predict(X)
                residuals = y - y_pred
                
                venue_residuals[venue] = {
                    'residuals': residuals,
                    'timestamps': venue_data['timestamp'].values,
                    'r2': reg.score(X, y)
                }
            
            # Compute anomaly scores (residual magnitude)
            for venue, data in venue_residuals.items():
                residuals = data['residuals']
                timestamps = data['timestamps']
                
                # Compute residual scores (absolute standardized residuals)
                residual_scores = np.abs(stats.zscore(residuals))
                
                # Identify anomalies (95th percentile threshold)
                threshold = np.percentile(residual_scores, 95)
                anomaly_mask = residual_scores > threshold
                
                anomaly_scores[f"{target_var}_{venue}"] = {
                    'scores': residual_scores,
                    'threshold': threshold,
                    'anomaly_count': np.sum(anomaly_mask),
                    'anomaly_rate': np.mean(anomaly_mask)
                }
                
                anomaly_timestamps[f"{target_var}_{venue}"] = {
                    'timestamps': timestamps[anomaly_mask],
                    'scores': residual_scores[anomaly_mask]
                }
        
        log_message(f"  ✅ Causal anomaly detection complete: {len(anomaly_scores)} variable-venue pairs analyzed", log_file)
        
        return {
            'anomaly_scores': anomaly_scores,
            'anomaly_timestamps': anomaly_timestamps,
            'variables': variables
        }
        
    except Exception as e:
        log_message(f"  ❌ Causal anomaly detection failed: {str(e)}", log_file)
        raise

def regime_persistence_analysis(metrics, log_file):
    """Analyze regime transition duration and frequency"""
    log_message("📈 Starting regime persistence analysis...", log_file)
    
    try:
        # Extract VMM results
        vmm_results = metrics.get('vmm', {})
        segments = vmm_results.get('invariant_segments', [])
        
        log_message(f"  Analyzing {len(segments)} regime segments", log_file)
        
        if not segments:
            log_message("  ⚠️ No VMM segments found", log_file)
            return {
                'total_segments': 0,
                'stable_segments': 0,
                'transitional_segments': 0,
                'avg_stable_duration': 0,
                'avg_transition_duration': 0,
                'stability_ratio': 0
            }
        
        # Analyze segment types and durations
        stable_segments = [s for s in segments if s.get('type') == 'stable']
        transitional_segments = [s for s in segments if s.get('type') == 'transition']
        
        # Compute duration statistics
        stable_durations = []
        transition_durations = []
        
        for s in stable_segments:
            length = s.get('length', 0)
            # Convert to numeric if it's a string
            if isinstance(length, str):
                try:
                    length = float(length)
                except (ValueError, TypeError):
                    length = 0
            stable_durations.append(length)
        
        for s in transitional_segments:
            length = s.get('length', 0)
            # Convert to numeric if it's a string
            if isinstance(length, str):
                try:
                    length = float(length)
                except (ValueError, TypeError):
                    length = 0
            transition_durations.append(length)
        
        avg_stable_duration = np.mean(stable_durations) if stable_durations else 0
        avg_transition_duration = np.mean(transition_durations) if transition_durations else 0
        
        # Compute stability ratio
        total_stable_hours = sum(stable_durations)
        total_transition_hours = sum(transition_durations)
        total_hours = total_stable_hours + total_transition_hours
        stability_ratio = total_stable_hours / total_hours if total_hours > 0 else 0
        
        # Analyze transition frequency
        transition_frequency = len(transitional_segments) / len(segments) if segments else 0
        
        log_message(f"  ✅ Regime analysis complete: {len(stable_segments)} stable, {len(transitional_segments)} transitional", log_file)
        
        return {
            'total_segments': len(segments),
            'stable_segments': len(stable_segments),
            'transitional_segments': len(transitional_segments),
            'avg_stable_duration': avg_stable_duration,
            'avg_transition_duration': avg_transition_duration,
            'stability_ratio': stability_ratio,
            'transition_frequency': transition_frequency,
            'total_stable_hours': total_stable_hours,
            'total_transition_hours': total_transition_hours
        }
        
    except Exception as e:
        log_message(f"  ❌ Regime persistence analysis failed: {str(e)}", log_file)
        raise

def cross_venue_comparisons(anomaly_results, log_file):
    """Compare causal stability across venues and detect synchronous anomalies"""
    log_message("🔗 Starting cross-venue comparisons...", log_file)
    
    try:
        anomaly_timestamps = anomaly_results['anomaly_timestamps']
        anomaly_scores = anomaly_results['anomaly_scores']
        variables = anomaly_results['variables']
        
        # Compute causal stability per venue
        venue_stability = {}
        for venue in VENUES:
            venue_anomalies = {}
            for var in variables:
                key = f"{var}_{venue}"
                if key in anomaly_scores:
                    venue_anomalies[var] = anomaly_scores[key]['anomaly_count']
            
            # Compute stability score (lower anomaly rate = higher stability)
            total_anomalies = sum(venue_anomalies.values())
            venue_stability[venue] = {
                'total_anomalies': total_anomalies,
                'variable_anomalies': venue_anomalies,
                'stability_score': 1.0 / (1.0 + total_anomalies)  # Higher score = more stable
            }
        
        # Detect synchronous anomalies (≥2 venues within ±1 hour)
        synchronous_anomalies = []
        
        # Group anomalies by variable
        for var in variables:
            var_anomalies = {}
            for venue in VENUES:
                key = f"{var}_{venue}"
                if key in anomaly_timestamps:
                    var_anomalies[venue] = anomaly_timestamps[key]['timestamps']
            
            # Find synchronous anomalies
            if len(var_anomalies) >= 2:
                for venue1, timestamps1 in var_anomalies.items():
                    for venue2, timestamps2 in var_anomalies.items():
                        if venue1 >= venue2:  # Avoid duplicates
                            continue
                        
                        # Check for timestamps within ±1 hour
                        for ts1 in timestamps1:
                            for ts2 in timestamps2:
                                if isinstance(ts1, str):
                                    ts1 = pd.to_datetime(ts1)
                                if isinstance(ts2, str):
                                    ts2 = pd.to_datetime(ts2)
                                
                                # Handle different timestamp types
                                if hasattr(ts1 - ts2, 'total_seconds'):
                                    time_diff = abs((ts1 - ts2).total_seconds() / 3600)  # hours
                                else:
                                    # For numpy timedelta64
                                    time_diff = abs((ts1 - ts2) / np.timedelta64(1, 'h'))  # hours
                                
                                if time_diff <= 1.0:
                                    synchronous_anomalies.append({
                                        'variable': var,
                                        'venue1': venue1,
                                        'venue2': venue2,
                                        'timestamp1': ts1,
                                        'timestamp2': ts2,
                                        'time_diff_hours': time_diff
                                    })
        
        log_message(f"  ✅ Cross-venue analysis complete: {len(synchronous_anomalies)} synchronous anomalies found", log_file)
        
        return {
            'venue_stability': venue_stability,
            'synchronous_anomalies': synchronous_anomalies,
            'most_stable_venue': max(venue_stability.keys(), key=lambda v: venue_stability[v]['stability_score']),
            'least_stable_venue': min(venue_stability.keys(), key=lambda v: venue_stability[v]['stability_score'])
        }
        
    except Exception as e:
        log_message(f"  ❌ Cross-venue comparisons failed: {str(e)}", log_file)
        raise

def generate_hypothesis_exports(anomaly_results, regime_results, venue_results, log_file):
    """Generate hypothesis summary, metrics, and visualizations"""
    log_message("📊 Generating hypothesis exports...", log_file)
    
    try:
        # Generate hypothesis summary
        summary_file = HYPOTHESIS_DIR / 'hypothesis_summary.txt'
        with open(summary_file, 'w') as f:
            f.write("Phase 41K-HYPOTHESIS-TESTING Summary\n")
            f.write("=" * 50 + "\n")
            f.write(f"Generated: {datetime.utcnow().isoformat()}Z\n\n")
            
            # Causal anomaly summary
            f.write("CAUSAL ANOMALY DETECTION:\n")
            f.write("-" * 30 + "\n")
            f.write(f"Variables analyzed: {len(anomaly_results['variables'])}\n")
            f.write(f"Variable-venue pairs: {len(anomaly_results['anomaly_scores'])}\n")
            
            # Top anomalies by rate
            anomaly_rates = []
            for key, data in anomaly_results['anomaly_scores'].items():
                anomaly_rates.append((key, data['anomaly_rate']))
            anomaly_rates.sort(key=lambda x: x[1], reverse=True)
            
            f.write(f"Top 5 anomaly rates:\n")
            for i, (key, rate) in enumerate(anomaly_rates[:5], 1):
                f.write(f"  {i}. {key}: {rate:.3f}\n")
            f.write("\n")
            
            # Regime persistence summary
            f.write("REGIME PERSISTENCE ANALYSIS:\n")
            f.write("-" * 35 + "\n")
            f.write(f"Total segments: {regime_results['total_segments']}\n")
            f.write(f"Stable segments: {regime_results['stable_segments']}\n")
            f.write(f"Transitional segments: {regime_results['transitional_segments']}\n")
            f.write(f"Average stable duration: {regime_results['avg_stable_duration']:.1f} hours\n")
            f.write(f"Average transition duration: {regime_results['avg_transition_duration']:.1f} hours\n")
            f.write(f"Stability ratio: {regime_results['stability_ratio']:.3f}\n\n")
            
            # Cross-venue summary
            f.write("CROSS-VENUE COMPARISONS:\n")
            f.write("-" * 30 + "\n")
            f.write(f"Synchronous anomalies: {len(venue_results['synchronous_anomalies'])}\n")
            f.write(f"Most stable venue: {venue_results['most_stable_venue']}\n")
            f.write(f"Least stable venue: {venue_results['least_stable_venue']}\n")
            
            # Venue stability scores
            f.write(f"Venue stability scores:\n")
            for venue, data in venue_results['venue_stability'].items():
                f.write(f"  {venue}: {data['stability_score']:.3f} ({data['total_anomalies']} anomalies)\n")
        
        # Generate structured metrics
        metrics = {
            'causal_anomalies': {
                'variables': anomaly_results['variables'],
                'anomaly_scores': {k: {
                    'threshold': float(v['threshold']),
                    'anomaly_count': int(v['anomaly_count']),
                    'anomaly_rate': float(v['anomaly_rate'])
                } for k, v in anomaly_results['anomaly_scores'].items()},
                'total_pairs': len(anomaly_results['anomaly_scores'])
            },
            'regime_persistence': regime_results,
            'cross_venue': {
                'venue_stability': {k: {
                    'total_anomalies': int(v['total_anomalies']),
                    'stability_score': float(v['stability_score'])
                } for k, v in venue_results['venue_stability'].items()},
                'synchronous_anomalies': len(venue_results['synchronous_anomalies']),
                'most_stable_venue': venue_results['most_stable_venue'],
                'least_stable_venue': venue_results['least_stable_venue']
            },
            'metadata': {
                'timestamp': datetime.utcnow().isoformat(),
                'seed': 42,
                'total_variables': len(anomaly_results['variables']),
                'total_venues': len(VENUES)
            }
        }
        
        metrics_file = HYPOTHESIS_DIR / 'hypothesis_metrics.json'
        with open(metrics_file, 'w') as f:
            json.dump(metrics, f, indent=2, default=str)
        
        # Generate anomaly heatmap
        generate_anomaly_heatmap(anomaly_results, log_file)
        
        log_message(f"  ✅ Hypothesis exports generated: {summary_file}", log_file)
        log_message(f"  ✅ Metrics saved: {metrics_file}", log_file)
        
        return True
        
    except Exception as e:
        log_message(f"  ❌ Hypothesis export generation failed: {str(e)}", log_file)
        raise

def generate_anomaly_heatmap(anomaly_results, log_file):
    """Generate heatmap of residual anomaly intensity by date/venue"""
    log_message("  📊 Generating anomaly heatmap...", log_file)
    
    try:
        # Prepare data for heatmap
        variables = anomaly_results['variables']
        anomaly_scores = anomaly_results['anomaly_scores']
        
        # Create matrix: variables x venues
        heatmap_data = []
        row_labels = []
        
        for var in variables:
            row = []
            for venue in VENUES:
                key = f"{var}_{venue}"
                if key in anomaly_scores:
                    row.append(anomaly_scores[key]['anomaly_rate'])
                else:
                    row.append(0.0)
            heatmap_data.append(row)
            row_labels.append(var)
        
        # Create heatmap
        plt.figure(figsize=(10, 8))
        heatmap_matrix = np.array(heatmap_data)
        
        sns.heatmap(heatmap_matrix, 
                   xticklabels=VENUES,
                   yticklabels=row_labels,
                   annot=True,
                   fmt='.3f',
                   cmap='Reds',
                   cbar_kws={'label': 'Anomaly Rate'})
        
        plt.title('Causal Anomaly Rates by Variable and Venue', fontsize=14, fontweight='bold')
        plt.xlabel('Venue', fontsize=12)
        plt.ylabel('Variable', fontsize=12)
        plt.tight_layout()
        
        # Save heatmap
        heatmap_file = HYPOTHESIS_DIR / 'hypothesis_heatmap.png'
        plt.savefig(heatmap_file, dpi=300, bbox_inches='tight')
        plt.close()
        
        log_message(f"    ✅ Anomaly heatmap saved: {heatmap_file}", log_file)
        
    except Exception as e:
        log_message(f"    ❌ Heatmap generation failed: {str(e)}", log_file)

def main():
    """Main execution function"""
    print("🚀 Phase 41K-HYPOTHESIS-TESTING: Causal Anomaly Detection & Regime Analysis")
    print("=" * 80)
    
    start_time = datetime.utcnow()
    
    # Setup
    setup_directories()
    log_file = HYPOTHESIS_DIR / 'hypothesis_log.txt'
    
    # Clear log file
    with open(log_file, 'w') as f:
        f.write(f"Phase 41K-HYPOTHESIS-TESTING Log\n")
        f.write(f"Started: {start_time.isoformat()}Z\n")
        f.write("=" * 50 + "\n\n")
    
    log_message("🔍 Starting hypothesis testing...", log_file)
    
    try:
        # Verify validation status
        verify_validation_status()
        
        # Load validated data
        metrics, beacon_df, venue_aligned_df = load_validated_data()
        
        # Run hypothesis tests
        anomaly_results = causal_anomaly_detection(metrics, beacon_df, log_file)
        regime_results = regime_persistence_analysis(metrics, log_file)
        venue_results = cross_venue_comparisons(anomaly_results, log_file)
        
        # Generate exports
        generate_hypothesis_exports(anomaly_results, regime_results, venue_results, log_file)
        
        # Final status
        end_time = datetime.utcnow()
        runtime = (end_time - start_time).total_seconds()
        
        log_message(f"✅ Hypothesis testing complete in {runtime:.1f} seconds", log_file)
        log_message("🎯 Final status: HYPOTHESIS_OK=true", log_file)
        
        print(f"\n🎯 HYPOTHESIS_OK=true")
        print(f"⏱️ Runtime: {runtime:.1f} seconds")
        print(f"📁 Reports: {HYPOTHESIS_DIR}")
        
        return 0
        
    except Exception as e:
        error_msg = f"❌ Unexpected error: {str(e)}\n{traceback.format_exc()}"
        log_message(error_msg, log_file)
        
        # Write error to summary
        summary_file = HYPOTHESIS_DIR / 'hypothesis_summary.txt'
        with open(summary_file, 'w') as f:
            f.write("Phase 41K-HYPOTHESIS-TESTING Summary\n")
            f.write("=" * 50 + "\n")
            f.write(f"Generated: {datetime.utcnow().isoformat()}Z\n")
            f.write("Overall Status: ❌ FAIL (Error)\n\n")
            f.write("ERROR:\n")
            f.write(str(e))
        
        # Write failed metrics
        metrics_file = HYPOTHESIS_DIR / 'hypothesis_metrics.json'
        with open(metrics_file, 'w') as f:
            json.dump({
                'HYPOTHESIS_OK': False,
                'error': str(e),
                'timestamp': datetime.utcnow().isoformat()
            }, f, indent=2)
        
        print(f"\n❌ HYPOTHESIS_OK=false (Error: {str(e)})")
        return 1

if __name__ == "__main__":
    sys.exit(main())
