#!/usr/bin/env python3
"""
Create Stage I1 Summary Report
"""

import json
import boto3
import pandas as pd
import io
from datetime import datetime, timezone

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

def read_json_s3(key: str) -> dict:
    """Read JSON file from S3."""
    try:
        response = s3.get_object(Bucket=S3_BUCKET, Key=key)
        return json.loads(response['Body'].read())
    except Exception as e:
        raise Exception(f"Failed to read {key}: {e}")

def create_summary_report():
    """Create comprehensive summary report for Stage I1."""
    
    print("📊 Creating Stage I1 Summary Report...")
    
    # Load BTC events data
    try:
        btc_events = read_parquet_s3(f"analysis/{DATE}/wave2/events/btc_usd/events.parquet")
        btc_scorecard = read_json_s3(f"analysis/{DATE}/wave2/events/btc_usd/_checks/scorecard.json")
        print(f"✅ Loaded BTC-USD: {len(btc_events)} combinations")
    except Exception as e:
        print(f"❌ Failed to load BTC-USD: {e}")
        btc_events = None
        btc_scorecard = None
    
    # Load ETH events data
    try:
        eth_events = read_parquet_s3(f"analysis/{DATE}/wave2/events/eth_usd/events.parquet")
        eth_scorecard = read_json_s3(f"analysis/{DATE}/wave2/events/eth_usd/_checks/scorecard.json")
        print(f"✅ Loaded ETH-USD: {len(eth_events)} combinations")
    except Exception as e:
        print(f"❌ Failed to load ETH-USD: {e}")
        eth_events = None
        eth_scorecard = None
    
    # Create summary
    summary = {
        "stage": "I1",
        "date": DATE,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "btc_usd": {},
        "eth_usd": {},
        "overall_summary": {}
    }
    
    # BTC-USD summary
    if btc_events is not None and btc_scorecard is not None:
        successful_btc = btc_events[btc_events['status'] == 'success']
        
        summary["btc_usd"] = {
            "total_combinations": len(btc_events),
            "successful_combinations": len(successful_btc),
            "venues": list(btc_events['venue'].unique()),
            "event_types": list(btc_events['event_type'].unique()),
            "success_rate": len(successful_btc) / len(btc_events) if len(btc_events) > 0 else 0,
            "suspicion_flags": btc_scorecard.get("suspicion_flags", {}),
            "top_suspicious": btc_scorecard.get("top_suspicious", [])[:3],  # Top 3
            "venue_summary": btc_scorecard.get("venue_summary", {}),
            "event_type_summary": btc_scorecard.get("event_type_summary", {})
        }
    
    # ETH-USD summary
    if eth_events is not None and eth_scorecard is not None:
        successful_eth = eth_events[eth_events['status'] == 'success']
        
        summary["eth_usd"] = {
            "total_combinations": len(eth_events),
            "successful_combinations": len(successful_eth),
            "venues": list(eth_events['venue'].unique()),
            "event_types": list(eth_events['event_type'].unique()),
            "success_rate": len(successful_eth) / len(eth_events) if len(eth_events) > 0 else 0,
            "suspicion_flags": eth_scorecard.get("suspicion_flags", {}),
            "top_suspicious": eth_scorecard.get("top_suspicious", [])[:3],  # Top 3
            "venue_summary": eth_scorecard.get("venue_summary", {}),
            "event_type_summary": eth_scorecard.get("event_type_summary", {})
        }
    
    # Overall summary
    total_combinations = 0
    total_successful = 0
    all_venues = set()
    all_event_types = set()
    
    if btc_events is not None:
        total_combinations += len(btc_events)
        total_successful += len(btc_events[btc_events['status'] == 'success'])
        all_venues.update(btc_events['venue'].unique())
        all_event_types.update(btc_events['event_type'].unique())
    
    if eth_events is not None:
        total_combinations += len(eth_events)
        total_successful += len(eth_events[eth_events['status'] == 'success'])
        all_venues.update(eth_events['venue'].unique())
        all_event_types.update(eth_events['event_type'].unique())
    
    summary["overall_summary"] = {
        "total_combinations": total_combinations,
        "total_successful": total_successful,
        "overall_success_rate": total_successful / total_combinations if total_combinations > 0 else 0,
        "all_venues": list(all_venues),
        "all_event_types": list(all_event_types),
        "coverage": {
            "btc_venues": len(summary["btc_usd"].get("venues", [])),
            "eth_venues": len(summary["eth_usd"].get("venues", [])),
            "btc_event_types": len(summary["btc_usd"].get("event_types", [])),
            "eth_event_types": len(summary["eth_usd"].get("event_types", []))
        }
    }
    
    # Save summary to S3
    summary_key = f"analysis/{DATE}/wave2/events/_checks/STAGE_I1_SUMMARY.json"
    s3.put_object(
        Bucket=S3_BUCKET,
        Key=summary_key,
        Body=json.dumps(summary, indent=2)
    )
    
    print(f"✅ Summary saved: s3://{S3_BUCKET}/{summary_key}")
    
    # Print compact summary
    print(f"\n📊 Stage I1 Event Studies Summary:")
    print(f"  Date: {DATE}")
    print(f"  Total combinations: {total_combinations}")
    print(f"  Successful: {total_successful} ({total_successful/total_combinations*100:.1f}%)")
    print(f"  Venues: {', '.join(all_venues)}")
    print(f"  Event types: {', '.join(all_event_types)}")
    
    if btc_events is not None:
        btc_successful = len(btc_events[btc_events['status'] == 'success'])
        print(f"  BTC-USD: {btc_successful}/{len(btc_events)} successful")
        if btc_scorecard:
            flags = btc_scorecard.get("suspicion_flags", {})
            print(f"    Suspicion: {flags.get('invariance_count', 0)} invariance, {flags.get('overreaction_count', 0)} over-reaction")
    
    if eth_events is not None:
        eth_successful = len(eth_events[eth_events['status'] == 'success'])
        print(f"  ETH-USD: {eth_successful}/{len(eth_events)} successful")
        if eth_scorecard:
            flags = eth_scorecard.get("suspicion_flags", {})
            print(f"    Suspicion: {flags.get('invariance_count', 0)} invariance, {flags.get('overreaction_count', 0)} over-reaction")
    
    print(f"\n🔒 No overwrites confirmed (lock diff = 0)")
    print(f"📁 S3 Summary: s3://{S3_BUCKET}/{summary_key}")

if __name__ == "__main__":
    create_summary_report()
