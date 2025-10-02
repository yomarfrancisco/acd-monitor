#!/usr/bin/env python3
"""
Wave-1 Analysis & Scoring for Competitive Behavior Detection

Read-only analysis of Wave-1 variables to detect coordination risk patterns.
No data mutation - only reads artifacts and produces scorecards.
"""

import json
import hashlib
import os
import sys
import io
from datetime import datetime, timezone
from typing import Dict, List, Any, Tuple
import pandas as pd
import boto3
import numpy as np

# =============================================================================
# SCORING THRESHOLDS (Constants)
# =============================================================================

# Variance Ratio (VR = var_1s/var_5s)
VR_GREEN_MIN, VR_GREEN_MAX = 0.7, 1.3
VR_AMBER_MIN_LOW, VR_AMBER_MAX_LOW = 0.6, 0.7
VR_AMBER_MIN_HIGH, VR_AMBER_MAX_HIGH = 1.3, 1.5
# Red: <0.6 or >1.5

# Autocorrelation (AR1)
AR1_GREEN_MAX = 0.2
AR1_AMBER_MAX = 0.4
# Red: >0.4

# Cross-correlation (venue pairs)
XCORR_GREEN_MAX = 0.7
XCORR_AMBER_MAX = 0.85
# Red: >0.85

# Rolling volatility/spread convergence
ROLLING_VOL_CORR_THRESHOLD = 0.85
SPREAD_STD_THRESHOLD = 0.001  # Small threshold for tight spreads

# PCA (if present)
PCA_FIRST_COMPONENT_THRESHOLD = 0.8

# =============================================================================
# CONFIGURATION
# =============================================================================

S3_BUCKET = "acd-monitor-snapshots"
ANALYSIS_PREFIX = "analysis/20251001/wave1"
REPORT_PREFIX = "analysis/20251001/wave1_report"
SYMBOLS = ["btc_usd", "eth_usd"]
ARTIFACTS = ["variance_ratios", "autocorr", "xcorr", "rolling", "pca"]

s3 = boto3.client('s3')

# =============================================================================
# UTILITY FUNCTIONS
# =============================================================================

def read_parquet_s3(key: str) -> pd.DataFrame:
    """Read Parquet file from S3."""
    try:
        response = s3.get_object(Bucket=S3_BUCKET, Key=key)
        return pd.read_parquet(io.BytesIO(response['Body'].read()))
    except Exception as e:
        raise Exception(f"Failed to read {key}: {e}")

def get_artifact_hash(key: str) -> str:
    """Get SHA256 hash of S3 object."""
    try:
        response = s3.get_object(Bucket=S3_BUCKET, Key=key)
        content = response['Body'].read()
        return hashlib.sha256(content).hexdigest()
    except Exception as e:
        raise Exception(f"Failed to get hash for {key}: {e}")

def severity_to_int(severity: str) -> int:
    """Convert severity to integer for max comparison."""
    return {"GREEN": 0, "AMBER": 1, "RED": 2}[severity]

def int_to_severity(severity_int: int) -> str:
    """Convert integer back to severity string."""
    return {0: "GREEN", 1: "AMBER", 2: "RED"}[severity_int]

# =============================================================================
# SCORING FUNCTIONS
# =============================================================================

def score_variance_ratio(vr: float) -> str:
    """Score variance ratio."""
    if VR_GREEN_MIN <= vr <= VR_GREEN_MAX:
        return "GREEN"
    elif (VR_AMBER_MIN_LOW <= vr <= VR_AMBER_MAX_LOW) or (VR_AMBER_MIN_HIGH <= vr <= VR_AMBER_MAX_HIGH):
        return "AMBER"
    else:
        return "RED"

def score_autocorrelation(ar1: float) -> str:
    """Score autocorrelation (absolute value)."""
    abs_ar1 = abs(ar1)
    if abs_ar1 <= AR1_GREEN_MAX:
        return "GREEN"
    elif abs_ar1 <= AR1_AMBER_MAX:
        return "AMBER"
    else:
        return "RED"

def score_cross_correlation(xcorr: float) -> str:
    """Score cross-correlation."""
    abs_xcorr = abs(xcorr)
    if abs_xcorr <= XCORR_GREEN_MAX:
        return "GREEN"
    elif abs_xcorr <= XCORR_AMBER_MAX:
        return "AMBER"
    else:
        return "RED"

def check_rolling_volatility_convergence(df: pd.DataFrame) -> bool:
    """Check for rolling volatility convergence flag."""
    if len(df) == 0:
        return False
    
    # Check if rolling vol correlations > threshold and spread std is small
    vol_corr_cols = [col for col in df.columns if 'vol' in col.lower() and 'corr' in col.lower()]
    spread_std_cols = [col for col in df.columns if 'spread' in col.lower() and 'std' in col.lower()]
    
    if vol_corr_cols and spread_std_cols:
        max_vol_corr = df[vol_corr_cols].max().max() if len(vol_corr_cols) > 0 else 0
        median_spread_std = df[spread_std_cols].median().median() if len(spread_std_cols) > 0 else float('inf')
        
        return max_vol_corr > ROLLING_VOL_CORR_THRESHOLD and median_spread_std <= SPREAD_STD_THRESHOLD
    
    return False

def check_pca_dominance(df: pd.DataFrame) -> bool:
    """Check if PCA shows first component dominance."""
    if len(df) == 0 or 'explained_variance_ratio' not in df.columns:
        return False
    
    # Check if any venue has first component > threshold
    return df['explained_variance_ratio'].max() > PCA_FIRST_COMPONENT_THRESHOLD

# =============================================================================
# MAIN ANALYSIS
# =============================================================================

def analyze_symbol(symbol: str) -> Dict[str, Any]:
    """Analyze a single symbol and return scorecard."""
    print(f"📊 Analyzing {symbol}...")
    
    # Load artifacts
    artifacts = {}
    artifact_hashes = {}
    
    for artifact in ARTIFACTS:
        key = f"{ANALYSIS_PREFIX}/{symbol}/{artifact}.parquet"
        
        # Check if artifact exists
        try:
            s3.head_object(Bucket=S3_BUCKET, Key=key)
        except:
            if artifact == "pca":
                print(f"  ℹ️ {artifact} absent (optional)")
                continue
            else:
                raise Exception(f"Missing required artifact: {key}")
        
        # Load and validate
        df = read_parquet_s3(key)
        if len(df) == 0:
            raise Exception(f"Empty artifact: {key}")
        
        artifacts[artifact] = df
        artifact_hashes[artifact] = get_artifact_hash(key)
        print(f"  ✅ {artifact}: {len(df)} rows")
    
    # Initialize scorecard
    scorecard = {
        "symbol": symbol,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "per_venue_metrics": {},
        "pairwise_metrics": {},
        "flags": {},
        "overall_rating": "GREEN",
        "artifact_hashes": artifact_hashes
    }
    
    # Analyze variance ratios
    if "variance_ratios" in artifacts:
        vr_df = artifacts["variance_ratios"]
        venue_scores = {}
        for _, row in vr_df.iterrows():
            venue = row['venue']
            vr = row['vr_ratio']
            score = score_variance_ratio(vr)
            venue_scores[venue] = {"vr": vr, "score": score}
        
        scorecard["per_venue_metrics"]["variance_ratios"] = venue_scores
    
    # Analyze autocorrelation
    if "autocorr" in artifacts:
        ac_df = artifacts["autocorr"]
        venue_scores = {}
        for _, row in ac_df.iterrows():
            venue = row['venue']
            ar1 = row['ar1_coef']
            score = score_autocorrelation(ar1)
            venue_scores[venue] = {"ar1": ar1, "score": score}
        
        scorecard["per_venue_metrics"]["autocorrelation"] = venue_scores
    
    # Analyze cross-correlation
    if "xcorr" in artifacts:
        xcorr_df = artifacts["xcorr"]
        pair_scores = {}
        xcorr_values = []
        
        for _, row in xcorr_df.iterrows():
            pair = f"{row['venue1']}-{row['venue2']}"
            xcorr = row['cross_corr']
            score = score_cross_correlation(xcorr)
            pair_scores[pair] = {"xcorr": xcorr, "score": score}
            xcorr_values.append(abs(xcorr))
        
        scorecard["pairwise_metrics"] = pair_scores
        
        # Calculate p75 for summary
        if xcorr_values:
            xcorr_p75 = np.percentile(xcorr_values, 75)
            scorecard["xcorr_p75"] = xcorr_p75
            scorecard["xcorr_p75_score"] = score_cross_correlation(xcorr_p75)
    
    # Check rolling volatility convergence
    if "rolling" in artifacts:
        rolling_df = artifacts["rolling"]
        convergence_flag = check_rolling_volatility_convergence(rolling_df)
        scorecard["flags"]["rolling_vol_convergence"] = convergence_flag
    
    # Check PCA dominance
    if "pca" in artifacts:
        pca_df = artifacts["pca"]
        dominance_flag = check_pca_dominance(pca_df)
        scorecard["flags"]["pca_dominance"] = dominance_flag
    
    # Calculate overall rating (max severity)
    all_scores = []
    
    # Collect venue scores
    for venue_metrics in scorecard["per_venue_metrics"].values():
        for venue_data in venue_metrics.values():
            if "score" in venue_data:
                all_scores.append(severity_to_int(venue_data["score"]))
    
    # Collect pairwise scores
    for pair_data in scorecard["pairwise_metrics"].values():
        if "score" in pair_data:
            all_scores.append(severity_to_int(pair_data["score"]))
    
    # Check flags (flags are binary, so they contribute RED if true)
    for flag_name, flag_value in scorecard["flags"].items():
        if flag_value:
            all_scores.append(2)  # RED
    
    if all_scores:
        max_severity = max(all_scores)
        scorecard["overall_rating"] = int_to_severity(max_severity)
    
    return scorecard

def create_pairwise_detail(scorecards: List[Dict[str, Any]]) -> pd.DataFrame:
    """Create pairwise cross-correlation detail CSV."""
    rows = []
    
    for scorecard in scorecards:
        symbol = scorecard["symbol"]
        for pair, data in scorecard["pairwise_metrics"].items():
            venue1, venue2 = pair.split("-")
            rows.append({
                "symbol": symbol,
                "venue1": venue1,
                "venue2": venue2,
                "cross_corr": data["xcorr"],
                "score": data["score"]
            })
    
    return pd.DataFrame(rows)

def create_per_venue_metrics(scorecards: List[Dict[str, Any]]) -> pd.DataFrame:
    """Create per-venue metrics CSV."""
    rows = []
    
    for scorecard in scorecards:
        symbol = scorecard["symbol"]
        
        # Variance ratios
        if "variance_ratios" in scorecard["per_venue_metrics"]:
            for venue, data in scorecard["per_venue_metrics"]["variance_ratios"].items():
                rows.append({
                    "symbol": symbol,
                    "venue": venue,
                    "metric": "variance_ratio",
                    "value": data["vr"],
                    "score": data["score"]
                })
        
        # Autocorrelation
        if "autocorrelation" in scorecard["per_venue_metrics"]:
            for venue, data in scorecard["per_venue_metrics"]["autocorrelation"].items():
                rows.append({
                    "symbol": symbol,
                    "venue": venue,
                    "metric": "autocorr_ar1",
                    "value": data["ar1"],
                    "score": data["score"]
                })
    
    return pd.DataFrame(rows)

def main():
    """Main analysis function."""
    print("🔍 Wave-1 Analysis & Scoring for 20251001")
    print("=" * 50)
    
    # Analyze each symbol
    scorecards = []
    all_artifact_hashes = {}
    
    for symbol in SYMBOLS:
        try:
            scorecard = analyze_symbol(symbol)
            scorecards.append(scorecard)
            all_artifact_hashes.update(scorecard["artifact_hashes"])
        except Exception as e:
            print(f"❌ Failed to analyze {symbol}: {e}")
            sys.exit(1)
    
    # Create detailed outputs
    pairwise_detail = create_pairwise_detail(scorecards)
    per_venue_metrics = create_per_venue_metrics(scorecards)
    
    # Create manifest
    manifest = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "stage": "G",
        "date": "20251001",
        "wave1_analysis": True,
        "thresholds": {
            "variance_ratio": {"green": [VR_GREEN_MIN, VR_GREEN_MAX], "amber": [VR_AMBER_MIN_LOW, VR_AMBER_MAX_LOW, VR_AMBER_MIN_HIGH, VR_AMBER_MAX_HIGH]},
            "autocorr": {"green_max": AR1_GREEN_MAX, "amber_max": AR1_AMBER_MAX},
            "cross_corr": {"green_max": XCORR_GREEN_MAX, "amber_max": XCORR_AMBER_MAX},
            "rolling_vol": {"corr_threshold": ROLLING_VOL_CORR_THRESHOLD, "spread_std_threshold": SPREAD_STD_THRESHOLD},
            "pca": {"first_component_threshold": PCA_FIRST_COMPONENT_THRESHOLD}
        },
        "artifact_hashes": all_artifact_hashes,
        "symbols": [sc["symbol"] for sc in scorecards],
        "overall_ratings": {sc["symbol"]: sc["overall_rating"] for sc in scorecards}
    }
    
    # Write outputs to S3
    print("\n💾 Writing outputs to S3...")
    
    # Save scorecards
    for scorecard in scorecards:
        symbol = scorecard["symbol"]
        key = f"{REPORT_PREFIX}/{symbol}_scorecard.json"
        s3.put_object(
            Bucket=S3_BUCKET,
            Key=key,
            Body=json.dumps(scorecard, indent=2)
        )
        print(f"  ✅ {key}")
    
    # Save detailed CSVs
    pairwise_key = f"{REPORT_PREFIX}/pairwise_xcorr_detail.csv"
    s3.put_object(
        Bucket=S3_BUCKET,
        Key=pairwise_key,
        Body=pairwise_detail.to_csv(index=False)
    )
    print(f"  ✅ {pairwise_key}")
    
    per_venue_key = f"{REPORT_PREFIX}/per_venue_metrics.csv"
    s3.put_object(
        Bucket=S3_BUCKET,
        Key=per_venue_key,
        Body=per_venue_metrics.to_csv(index=False)
    )
    print(f"  ✅ {per_venue_key}")
    
    # Save manifest
    manifest_key = f"{REPORT_PREFIX}/manifest.json"
    s3.put_object(
        Bucket=S3_BUCKET,
        Key=manifest_key,
        Body=json.dumps(manifest, indent=2)
    )
    print(f"  ✅ {manifest_key}")
    
    # Save README
    readme_content = f"""Wave-1 Analysis Report for 20251001
Generated: {datetime.now(timezone.utc).isoformat()}

This report contains competitive behavior analysis results for BTC-USD and ETH-USD
using Wave-1 variables computed from canonical data.

Files:
- btc_usd_scorecard.json: BTC-USD detailed scorecard
- eth_usd_scorecard.json: ETH-USD detailed scorecard  
- pairwise_xcorr_detail.csv: Cross-correlation details by venue pair
- per_venue_metrics.csv: Per-venue variance ratios and autocorrelation
- manifest.json: Analysis metadata and artifact hashes

Scoring Thresholds:
- Variance Ratio: Green 0.7-1.3, Amber 0.6-0.7/1.3-1.5, Red <0.6/>1.5
- Autocorrelation: Green ≤0.2, Amber 0.2-0.4, Red >0.4
- Cross-correlation: Green ≤0.7, Amber 0.7-0.85, Red >0.85
- Rolling Vol Convergence: Vol corr >0.85 AND spread std ≤0.001
- PCA Dominance: First component >0.8

Overall Ratings: {', '.join([f"{sc['symbol']}={sc['overall_rating']}" for sc in scorecards])}
"""
    
    readme_key = f"{REPORT_PREFIX}/README.txt"
    s3.put_object(
        Bucket=S3_BUCKET,
        Key=readme_key,
        Body=readme_content
    )
    print(f"  ✅ {readme_key}")
    
    # Print validation summary
    print("\n📊 VALIDATION SUMMARY:")
    print("=" * 30)
    
    for scorecard in scorecards:
        symbol = scorecard["symbol"]
        rating = scorecard["overall_rating"]
        
        # Get key metrics for summary
        vr_summary = []
        ar1_summary = []
        xcorr_summary = []
        
        if "variance_ratios" in scorecard["per_venue_metrics"]:
            for venue, data in scorecard["per_venue_metrics"]["variance_ratios"].items():
                vr_summary.append(f"{venue}={data['vr']:.2f}")
        
        if "autocorrelation" in scorecard["per_venue_metrics"]:
            for venue, data in scorecard["per_venue_metrics"]["autocorrelation"].items():
                ar1_summary.append(f"{data['ar1']:.2f}")
        
        if "xcorr_p75" in scorecard:
            xcorr_summary.append(f"p75={scorecard['xcorr_p75']:.2f}")
        
        print(f"{symbol.upper()}: VR {', '.join(vr_summary)} | AR1 max={max(ar1_summary) if ar1_summary else 'N/A'} | xcorr {', '.join(xcorr_summary)} → {rating}")
    
    print(f"\n✅ Wave-1 analysis complete. Results saved to s3://{S3_BUCKET}/{REPORT_PREFIX}/")

if __name__ == "__main__":
    main()

