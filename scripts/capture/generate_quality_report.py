#!/usr/bin/env python3
"""
Generate BTC vs ETH quality report for the latest 24h
"""

import json
import os
import boto3
import pandas as pd
from datetime import datetime, timedelta
from pathlib import Path

BUCKET = os.getenv("ACD_S3_BUCKET", "acd-monitor-snapshots")
PREFIX = os.getenv("ACD_S3_PREFIX", "snapshots")
SYMBOLS = ["BTC-USD", "ETH-USD"]
VENUES = ["binance", "coinbase", "kraken", "okx", "bybit"]

s3 = boto3.client("s3")

def get_windows_last_24h():
    """Get all windows from the last 24 hours."""
    windows = {}
    
    for symbol in SYMBOLS:
        try:
            response = s3.list_objects_v2(
                Bucket=BUCKET,
                Prefix=f"{PREFIX}/{symbol}/"
            )
            
            symbol_windows = []
            for obj in response.get("Contents", []):
                if obj["Key"].endswith("OVERLAP.json"):
                    # Extract timestamp
                    key_parts = obj["Key"].split("/")
                    if len(key_parts) >= 4:
                        date_part = key_parts[-3]
                        time_part = key_parts[-2]
                        
                        # Handle both date formats
                        try:
                            if "-" in date_part:
                                # Format: 2025-09-28_0100-0130
                                # Split time part into start and end
                                start_time, end_time = time_part.split("-")
                                window_time = datetime.strptime(f"{date_part}_{start_time}", "%Y-%m-%d_%H%M")
                            else:
                                # Format: 20250928_0100-0130
                                start_time, end_time = time_part.split("-")
                                window_time = datetime.strptime(f"{date_part}_{start_time}", "%Y%m%d_%H%M")
                        except:
                            continue
                        
                        # Check if within last 7 days
                        if window_time >= datetime.utcnow() - timedelta(days=7):
                            symbol_windows.append({
                                "key": obj["Key"].replace("/OVERLAP.json", ""),
                                "timestamp": window_time,
                                "size": obj["Size"]
                            })
            
            # Sort by timestamp
            symbol_windows.sort(key=lambda x: x["timestamp"])
            windows[symbol] = symbol_windows
            
        except Exception as e:
            print(f"Error getting windows for {symbol}: {e}")
            windows[symbol] = []
    
    return windows

def analyze_window(base_key):
    """Analyze a single window for quality metrics."""
    if not base_key:
        return None
    
    try:
        # Get OVERLAP.json
        overlap_key = f"{base_key}/OVERLAP.json"
        overlap_response = s3.get_object(Bucket=BUCKET, Key=overlap_key)
        overlap_data = json.loads(overlap_response["Body"].read())
        venues = overlap_data.get("venues", [])
        
        # Get coverage data if available
        coverage_data = None
        try:
            coverage_key = f"{base_key}/meta/coverage.json"
            coverage_response = s3.get_object(Bucket=BUCKET, Key=coverage_key)
            coverage_data = json.loads(coverage_response["Body"].read())
        except:
            pass
        
        # Check venue presence and data quality
        venue_analysis = {}
        total_rows = 0
        total_duplicates = 0
        
        for venue in venues:
            try:
                # List parquet files for this venue
                response = s3.list_objects_v2(
                    Bucket=BUCKET,
                    Prefix=f"{base_key}/ticks/{venue}/"
                )
                parquet_files = [obj["Key"] for obj in response.get("Contents", []) if obj["Key"].endswith(".parquet")]
                
                if parquet_files:
                    # Analyze first parquet file
                    parquet_key = parquet_files[0]
                    parquet_uri = f"s3://{BUCKET}/{parquet_key}"
                    
                    try:
                        df = pd.read_parquet(parquet_uri, storage_options={"anon": False})
                        
                        venue_analysis[venue] = {
                            "present": True,
                            "rows": len(df),
                            "columns": list(df.columns),
                            "duplicates": int(df["ts_exchange"].duplicated().sum()) if "ts_exchange" in df.columns else 0,
                            "file_size_mb": response["Contents"][0]["Size"] / (1024 * 1024)
                        }
                        
                        total_rows += len(df)
                        total_duplicates += venue_analysis[venue]["duplicates"]
                        
                    except Exception as e:
                        venue_analysis[venue] = {
                            "present": True,
                            "error": str(e),
                            "rows": 0,
                            "duplicates": 0
                        }
                else:
                    venue_analysis[venue] = {
                        "present": False,
                        "rows": 0,
                        "duplicates": 0
                    }
                    
            except Exception as e:
                venue_analysis[venue] = {
                    "present": False,
                    "error": str(e),
                    "rows": 0,
                    "duplicates": 0
                }
        
        # Calculate overall metrics
        venues_present = len([v for v in venue_analysis.values() if v.get("present", False)])
        duplicate_rate = (total_duplicates / total_rows * 100) if total_rows > 0 else 0
        
        return {
            "venues_present": venues_present,
            "total_venues": len(venues),
            "venue_analysis": venue_analysis,
            "total_rows": total_rows,
            "total_duplicates": total_duplicates,
            "duplicate_rate": duplicate_rate,
            "coverage_data": coverage_data
        }
        
    except Exception as e:
        print(f"Error analyzing window {base_key}: {e}")
        return None

def generate_report():
    """Generate the quality report."""
    print("📊 Generating BTC vs ETH Quality Report (Last 7 days)")
    print("=" * 60)
    
    # Get windows from last 24h
    windows = get_windows_last_24h()
    
    report = {
        "timestamp": datetime.utcnow().isoformat(),
        "period": "last_7_days",
        "symbols": {}
    }
    
    for symbol in SYMBOLS:
        print(f"\n🔍 Analyzing {symbol}...")
        
        symbol_windows = windows[symbol]
        print(f"  Found {len(symbol_windows)} windows")
        
        if not symbol_windows:
            report["symbols"][symbol] = {
                "windows": 0,
                "quality_rate": 0,
                "issues": ["No windows found in last 24h"]
            }
            continue
        
        # Analyze each window
        window_analyses = []
        for window in symbol_windows:
            analysis = analyze_window(window["key"])
            if analysis:
                window_analyses.append({
                    "window": window["key"],
                    "timestamp": window["timestamp"].isoformat(),
                    **analysis
                })
        
        # Calculate summary metrics
        if window_analyses:
            avg_venues = sum(w["venues_present"] for w in window_analyses) / len(window_analyses)
            avg_duplicates = sum(w["duplicate_rate"] for w in window_analyses) / len(window_analyses)
            quality_windows = len([w for w in window_analyses if w["venues_present"] >= 3 and w["duplicate_rate"] <= 0.1])
            quality_rate = (quality_windows / len(window_analyses)) * 100
            
            report["symbols"][symbol] = {
                "windows": len(window_analyses),
                "quality_rate": quality_rate,
                "avg_venues_present": avg_venues,
                "avg_duplicate_rate": avg_duplicates,
                "quality_windows": quality_windows,
                "window_details": window_analyses
            }
            
            print(f"  Quality Rate: {quality_rate:.1f}%")
            print(f"  Avg Venues: {avg_venues:.1f}/5")
            print(f"  Avg Duplicates: {avg_duplicates:.2f}%")
        else:
            report["symbols"][symbol] = {
                "windows": 0,
                "quality_rate": 0,
                "issues": ["No analyzable windows found"]
            }
    
    # Save report
    report_file = "reports/btc_eth_quality_report.json"
    os.makedirs(os.path.dirname(report_file), exist_ok=True)
    
    with open(report_file, "w") as f:
        json.dump(report, f, indent=2, default=str)
    
    print(f"\n📄 Report saved to {report_file}")
    
    # Print summary
    print(f"\n📈 SUMMARY:")
    for symbol in SYMBOLS:
        data = report["symbols"][symbol]
        print(f"  {symbol}: {data['windows']} windows, {data['quality_rate']:.1f}% quality")
    
    return report

if __name__ == "__main__":
    generate_report()
