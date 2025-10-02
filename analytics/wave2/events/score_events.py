#!/usr/bin/env python3
"""
Score Event Studies for Stage I1 - Wave-2
"""

import json
import os
import sys
import io
import hashlib
from datetime import datetime, timezone
from typing import Dict, List, Any
import pandas as pd
import numpy as np
import boto3

S3_BUCKET = "acd-monitor-snapshots"
DATE = "20251001"

s3 = boto3.client('s3')

def read_parquet_s3(key: str) -> pd.DataFrame:
    """Read Parquet file from S3."""
    try:
        response = s3.get_object(Bucket=S3_BUCKET, Key=key)
        return pd.read_parquet(io.BytesIO(response['Body'].read()))
    except Exception as e:
        raise Exception(f"Failed to read {key}: {e}")

def score_event_suspicion(events_df: pd.DataFrame) -> pd.DataFrame:
    """Score suspicion levels for event studies."""
    
    # Default thresholds (as specified in requirements)
    THRESHOLDS = {
        "invariance_car_300s": 0.02,  # |car_300s| < 0.02
        "invariance_d_vol": 0.05,     # |d_vol| < 0.05  
        "invariance_d_spread": 0.5,   # |d_spread| < 0.5bp (estimated from mid)
        "overreaction_car_60s": 0.5,  # |car_60s| > 0.5σ(pre) - simplified to 0.5
    }
    
    # Filter to successful events only
    successful_df = events_df[events_df['status'] == 'success'].copy()
    
    if len(successful_df) == 0:
        print("⚠️ No successful events to score")
        return events_df
    
    # Compute suspicion flags
    successful_df['invariance_flag'] = (
        (np.abs(successful_df['car_300s']) < THRESHOLDS['invariance_car_300s']) &
        (np.abs(successful_df['d_vol']) < THRESHOLDS['invariance_d_vol']) &
        (np.abs(successful_df['d_spread']) < THRESHOLDS['invariance_d_spread'])
    )
    
    successful_df['overreaction_flag'] = (
        np.abs(successful_df['car_60s']) > THRESHOLDS['overreaction_car_60s']
    )
    
    # Overall suspicion score (0-2 scale)
    successful_df['suspicion_score'] = (
        successful_df['invariance_flag'].astype(int) + 
        successful_df['overreaction_flag'].astype(int)
    )
    
    # Merge back with original dataframe
    result_df = events_df.copy()
    for col in ['invariance_flag', 'overreaction_flag', 'suspicion_score']:
        if col in successful_df.columns:
            result_df[col] = result_df['status'].map(
                successful_df.set_index(['symbol', 'venue', 'event_type'])[col].to_dict()
            ).fillna(False if col.endswith('_flag') else 0)
    
    return result_df

def create_scorecard(events_df: pd.DataFrame) -> Dict[str, Any]:
    """Create comprehensive scorecard for event studies."""
    
    successful_df = events_df[events_df['status'] == 'success']
    
    if len(successful_df) == 0:
        return {
            "summary": "No successful events to analyze",
            "total_combinations": 0,
            "successful_combinations": 0,
            "suspicion_flags": {},
            "top_suspicious": [],
            "venue_summary": {},
            "event_type_summary": {}
        }
    
    # Overall statistics
    total_combinations = len(events_df)
    successful_combinations = len(successful_df)
    
    # Suspicion flags
    suspicion_flags = {
        "invariance_count": int(successful_df['invariance_flag'].sum()) if 'invariance_flag' in successful_df.columns else 0,
        "overreaction_count": int(successful_df['overreaction_flag'].sum()) if 'overreaction_flag' in successful_df.columns else 0,
        "high_suspicion_count": int((successful_df['suspicion_score'] >= 2).sum()) if 'suspicion_score' in successful_df.columns else 0
    }
    
    # Top suspicious combinations
    if 'suspicion_score' in successful_df.columns:
        top_suspicious = successful_df.nlargest(5, 'suspicion_score')[
            ['venue', 'event_type', 'suspicion_score', 'car_300s', 'd_vol', 'd_spread']
        ].to_dict('records')
    else:
        top_suspicious = []
    
    # Venue summary
    venue_summary = {}
    for venue in successful_df['venue'].unique():
        venue_data = successful_df[successful_df['venue'] == venue]
        venue_summary[venue] = {
            "combinations": int(len(venue_data)),
            "avg_car_300s": float(venue_data['car_300s'].mean()),
            "avg_d_vol": float(venue_data['d_vol'].mean()),
            "avg_d_spread": float(venue_data['d_spread'].mean()),
            "invariance_rate": float(venue_data['invariance_flag'].mean()) if 'invariance_flag' in venue_data.columns else 0.0,
            "overreaction_rate": float(venue_data['overreaction_flag'].mean()) if 'overreaction_flag' in venue_data.columns else 0.0
        }
    
    # Event type summary
    event_type_summary = {}
    for event_type in successful_df['event_type'].unique():
        event_data = successful_df[successful_df['event_type'] == event_type]
        event_type_summary[event_type] = {
            "combinations": int(len(event_data)),
            "avg_car_300s": float(event_data['car_300s'].mean()),
            "avg_d_vol": float(event_data['d_vol'].mean()),
            "avg_d_spread": float(event_data['d_spread'].mean()),
            "invariance_rate": float(event_data['invariance_flag'].mean()) if 'invariance_flag' in event_data.columns else 0.0,
            "overreaction_rate": float(event_data['overreaction_flag'].mean()) if 'overreaction_flag' in event_data.columns else 0.0
        }
    
    return {
        "summary": f"Analyzed {successful_combinations}/{total_combinations} successful combinations",
        "total_combinations": total_combinations,
        "successful_combinations": successful_combinations,
        "suspicion_flags": suspicion_flags,
        "top_suspicious": top_suspicious,
        "venue_summary": venue_summary,
        "event_type_summary": event_type_summary,
        "thresholds_used": {
            "invariance_car_300s": 0.02,
            "invariance_d_vol": 0.05,
            "invariance_d_spread": 0.5,
            "overreaction_car_60s": 0.5
        }
    }

def save_scorecard(symbol: str, scorecard: Dict[str, Any]) -> str:
    """Save scorecard to S3."""
    symbol_lower = symbol.lower().replace('-', '_')
    key = f"analysis/{DATE}/wave2/events/{symbol_lower}/_checks/scorecard.json"
    
    # Check if file exists
    try:
        s3.head_object(Bucket=S3_BUCKET, Key=key)
        print(f"  ⚠️ Scorecard exists: {key} - reusing")
        return key
    except:
        pass
    
    # Save scorecard
    s3.put_object(
        Bucket=S3_BUCKET,
        Key=key,
        Body=json.dumps(scorecard, indent=2)
    )
    
    print(f"  ✅ Saved scorecard: {key}")
    return key

def create_readme(symbol: str, scorecard: Dict[str, Any]) -> str:
    """Create README for event studies."""
    symbol_lower = symbol.lower().replace('-', '_')
    key = f"analysis/{DATE}/wave2/events/{symbol_lower}/_checks/EVENTS_README.txt"
    
    # Check if file exists
    try:
        s3.head_object(Bucket=S3_BUCKET, Key=key)
        print(f"  ⚠️ README exists: {key} - reusing")
        return key
    except:
        pass
    
    # Create README content
    readme_content = f"""Event Studies Analysis for {symbol} - {DATE}

SUMMARY
=======
{scorecard['summary']}

SUSPICION FLAGS
===============
- Invariance events: {scorecard['suspicion_flags']['invariance_count']}
- Over-reaction events: {scorecard['suspicion_flags']['overreaction_count']}
- High suspicion (score ≥ 2): {scorecard['suspicion_flags']['high_suspicion_count']}

THRESHOLDS USED
===============
- Invariance CAR(300s): |car_300s| < {scorecard['thresholds_used']['invariance_car_300s']}
- Invariance ΔVol: |d_vol| < {scorecard['thresholds_used']['invariance_d_vol']}
- Invariance ΔSpread: |d_spread| < {scorecard['thresholds_used']['invariance_d_spread']}
- Over-reaction CAR(60s): |car_60s| > {scorecard['thresholds_used']['overreaction_car_60s']}

VENUE SUMMARY
=============
"""
    
    for venue, stats in scorecard['venue_summary'].items():
        readme_content += f"""
{venue.upper()}:
  Combinations: {stats['combinations']}
  Avg CAR(300s): {stats['avg_car_300s']:.4f}
  Avg ΔVol: {stats['avg_d_vol']:.4f}
  Avg ΔSpread: {stats['avg_d_spread']:.4f}
  Invariance Rate: {stats['invariance_rate']:.2%}
  Over-reaction Rate: {stats['overreaction_rate']:.2%}
"""
    
    readme_content += f"""
EVENT TYPE SUMMARY
==================
"""
    
    for event_type, stats in scorecard['event_type_summary'].items():
        readme_content += f"""
{event_type.upper()}:
  Combinations: {stats['combinations']}
  Avg CAR(300s): {stats['avg_car_300s']:.4f}
  Avg ΔVol: {stats['avg_d_vol']:.4f}
  Avg ΔSpread: {stats['avg_d_spread']:.4f}
  Invariance Rate: {stats['invariance_rate']:.2%}
  Over-reaction Rate: {stats['overreaction_rate']:.2%}
"""
    
    if scorecard['top_suspicious']:
        readme_content += f"""
TOP SUSPICIOUS COMBINATIONS
===========================
"""
        for i, item in enumerate(scorecard['top_suspicious'], 1):
            readme_content += f"""
{i}. {item['venue']}-{item['event_type']} (score: {item['suspicion_score']})
   CAR(300s): {item['car_300s']:.4f}
   ΔVol: {item['d_vol']:.4f}
   ΔSpread: {item['d_spread']:.4f}
"""
    
    readme_content += f"""

INTERPRETATION
=============
- Invariance: Venues show minimal reaction to exogenous shocks
- Over-reaction: Venues show excessive reaction to shocks
- High suspicion: Both invariance and over-reaction patterns

Generated: {datetime.now(timezone.utc).isoformat()}
"""
    
    # Save README
    s3.put_object(
        Bucket=S3_BUCKET,
        Key=key,
        Body=readme_content
    )
    
    print(f"  ✅ Saved README: {key}")
    return key

def main():
    """Main function."""
    print("📊 Scoring Event Studies for Stage I1...")
    
    symbols = ["BTC-USD", "ETH-USD"]
    results = {}
    
    for symbol in symbols:
        try:
            print(f"\n📊 Processing {symbol}...")
            
            # Load events data
            symbol_lower = symbol.lower().replace('-', '_')
            events_key = f"analysis/{DATE}/wave2/events/{symbol_lower}/events.parquet"
            
            try:
                events_df = read_parquet_s3(events_key)
                print(f"  ✅ Loaded {len(events_df)} event combinations")
            except Exception as e:
                print(f"  ⚠️ No events data for {symbol}: {e}")
                continue
            
            # Score suspicion
            scored_df = score_event_suspicion(events_df)
            
            # Create scorecard
            scorecard = create_scorecard(scored_df)
            
            # Save outputs
            scorecard_key = save_scorecard(symbol, scorecard)
            readme_key = create_readme(symbol, scorecard)
            
            results[symbol] = {
                "status": "success",
                "scorecard_key": scorecard_key,
                "readme_key": readme_key,
                "summary": scorecard['summary']
            }
            
        except Exception as e:
            print(f"  ❌ Failed {symbol}: {e}")
            results[symbol] = {"status": "failed", "error": str(e)}
    
    # Print summary
    print(f"\n📊 Event Studies Scoring Summary:")
    for symbol, result in results.items():
        if result.get("status") == "success":
            print(f"  {symbol}: ✅ {result.get('summary')}")
        else:
            print(f"  {symbol}: ❌ {result.get('error')}")

if __name__ == "__main__":
    main()
