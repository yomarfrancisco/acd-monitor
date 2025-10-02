#!/usr/bin/env python3
"""
Data Quality Validation Script

This script validates parquet file integrity, timestamp formatting,
schema compliance, and venue completeness for captured windows.
"""

import argparse
import json
import logging
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import boto3
import pandas as pd
import pyarrow.parquet as pq

# Import custom JSON encoder
class PandasJSONEncoder(json.JSONEncoder):
    """Custom JSON encoder for pandas/numpy types."""

    def default(self, obj):
        if isinstance(obj, pd.Timestamp):
            return obj.isoformat()
        elif isinstance(obj, (pd.Int64Dtype, pd.Int32Dtype)):
            return int(obj)
        elif isinstance(obj, (pd.Float64Dtype, pd.Float32Dtype)):
            return float(obj)
        elif hasattr(obj, "isoformat"):  # datetime objects
            return obj.isoformat()
        return super().default(obj)


def setup_logging(verbose: bool = False):
    """Setup logging configuration."""
    level = logging.INFO if verbose else logging.WARNING
    logging.basicConfig(level=level, format="%(asctime)s - %(levelname)s - %(message)s")


def validate_parquet_file(s3_path: str, s3_client) -> Dict:
    """Validate a single parquet file for quality issues."""
    issues = []
    stats = {}
    
    try:
        # Read parquet file from S3 using boto3 directly
        # Download to temporary location first
        import tempfile
        with tempfile.NamedTemporaryFile(suffix='.parquet') as tmp_file:
            # Download from S3
            bucket_name = s3_path.split('/')[2]
            key = '/'.join(s3_path.split('/')[3:])
            s3_client.download_file(bucket_name, key, tmp_file.name)
            
            # Read parquet file
            df = pd.read_parquet(tmp_file.name)
        
        if df.empty:
            issues.append("Empty parquet file")
            return {"issues": issues, "stats": stats}
        
        # Basic stats
        stats["rows"] = len(df)
        stats["columns"] = list(df.columns)
        stats["file_size_mb"] = len(df.to_parquet()) / (1024 * 1024)
        
        # Check required columns
        required_columns = ["ts_exchange", "price", "size"]
        missing_columns = [col for col in required_columns if col not in df.columns]
        if missing_columns:
            issues.append(f"Missing required columns: {missing_columns}")
        
        # Validate timestamp format and monotonicity
        if "ts_exchange" in df.columns:
            try:
                # Check if timestamps are properly formatted
                timestamps = pd.to_datetime(df["ts_exchange"])
                stats["timestamp_range"] = {
                    "start": timestamps.min().isoformat(),
                    "end": timestamps.max().isoformat()
                }
                
                # Check monotonicity (should be mostly increasing)
                timestamp_diffs = timestamps.diff().dropna()
                negative_diffs = (timestamp_diffs < pd.Timedelta(0)).sum()
                if negative_diffs > len(timestamps) * 0.01:  # More than 1% negative
                    issues.append(f"Timestamp monotonicity issues: {negative_diffs} negative diffs")
                    
            except Exception as e:
                issues.append(f"Timestamp validation failed: {e}")
        
        # Validate price and size data
        if "price" in df.columns:
            price_stats = df["price"].describe()
            if price_stats["min"] <= 0:
                issues.append("Invalid price data: non-positive prices found")
            stats["price_range"] = {"min": price_stats["min"], "max": price_stats["max"]}
            
        if "size" in df.columns:
            size_stats = df["size"].describe()
            if size_stats["min"] < 0:
                issues.append("Invalid size data: negative sizes found")
            stats["size_range"] = {"min": size_stats["min"], "max": size_stats["max"]}
        
        # Check for duplicate timestamps (potential data quality issue)
        if "ts_exchange" in df.columns:
            duplicate_timestamps = df["ts_exchange"].duplicated().sum()
            if duplicate_timestamps > 0:
                issues.append(f"Duplicate timestamps found: {duplicate_timestamps}")
        
    except Exception as e:
        issues.append(f"Failed to read parquet file: {e}")
        
    return {"issues": issues, "stats": stats}


def validate_window_quality(
    symbol: str, date: str, time_range: str, bucket: str, prefix: str, s3_client
) -> Dict:
    """Validate data quality for a specific window."""
    window_path = f"{prefix}/{symbol}/{date}/{time_range}"
    
    validation_results = {
        "window": f"{symbol}/{date}/{time_range}",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "venues": {},
        "overall_issues": [],
        "summary": {}
    }
    
    try:
        # Expected venues
        expected_venues = ["binance", "coinbase", "kraken", "okx", "bybit"]
        
        # Check each venue
        for venue in expected_venues:
            venue_path = f"{window_path}/ticks/{venue}/part-0000.parquet"
            
            try:
                # Validate parquet file
                parquet_result = validate_parquet_file(f"s3://{bucket}/{venue_path}", s3_client)
                validation_results["venues"][venue] = parquet_result
                
                if parquet_result["issues"]:
                    validation_results["overall_issues"].extend([
                        f"{venue}: {issue}" for issue in parquet_result["issues"]
                    ])
                    
            except Exception as e:
                validation_results["venues"][venue] = {
                    "issues": [f"Failed to validate: {e}"],
                    "stats": {}
                }
                validation_results["overall_issues"].append(f"{venue}: Failed to validate - {e}")
        
        # Check venue completeness
        available_venues = [v for v, data in validation_results["venues"].items() 
                           if data.get("stats", {}).get("rows", 0) > 0]
        missing_venues = [v for v in expected_venues if v not in available_venues]
        
        if missing_venues:
            validation_results["overall_issues"].append(f"Missing venues: {missing_venues}")
        
        # Generate summary
        validation_results["summary"] = {
            "total_venues": len(expected_venues),
            "available_venues": len(available_venues),
            "missing_venues": len(missing_venues),
            "total_issues": len(validation_results["overall_issues"]),
            "quality_score": max(0, 100 - len(validation_results["overall_issues"]) * 10)
        }
        
    except Exception as e:
        validation_results["overall_issues"].append(f"Window validation failed: {e}")
        
    return validation_results


def validate_recent_windows(
    symbols: List[str], days_back: int, bucket: str, prefix: str
) -> Dict:
    """Validate data quality for recent windows."""
    s3_client = boto3.client("s3")
    
    all_results = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "symbols": {},
        "overall_summary": {}
    }
    
    for symbol in symbols:
        logging.info(f"Validating {symbol}...")
        
        symbol_results = {
            "windows": [],
            "summary": {}
        }
        
        try:
            # List recent windows for this symbol
            response = s3_client.list_objects_v2(
                Bucket=bucket, Prefix=f"{prefix}/{symbol}/", Delimiter="/"
            )
            
            windows = []
            for obj in response.get("CommonPrefixes", []):
                date_path = obj["Prefix"].split("/")[-2]
                if date_path:
                    # List time ranges for this date
                    date_response = s3_client.list_objects_v2(
                        Bucket=bucket,
                        Prefix=f"{prefix}/{symbol}/{date_path}/",
                        Delimiter="/",
                    )
                    
                    for time_obj in date_response.get("CommonPrefixes", []):
                        time_range = time_obj["Prefix"].split("/")[-2]
                        if time_range and "-" in time_range:
                            windows.append((date_path, time_range))
            
            # Validate recent windows (last N)
            recent_windows = sorted(windows)[-days_back*4:]  # ~4 windows per day
            
            for date, time_range in recent_windows:
                window_result = validate_window_quality(
                    symbol, date, time_range, bucket, prefix, s3_client
                )
                symbol_results["windows"].append(window_result)
            
            # Generate symbol summary
            total_windows = len(symbol_results["windows"])
            windows_with_issues = len([w for w in symbol_results["windows"] 
                                     if w["overall_issues"]])
            
            symbol_results["summary"] = {
                "total_windows": total_windows,
                "windows_with_issues": windows_with_issues,
                "quality_rate": (total_windows - windows_with_issues) / total_windows if total_windows > 0 else 0
            }
            
        except Exception as e:
            logging.error(f"Error validating {symbol}: {e}")
            symbol_results["summary"] = {"error": str(e)}
        
        all_results["symbols"][symbol] = symbol_results
    
    # Generate overall summary
    total_windows = sum(s.get("summary", {}).get("total_windows", 0) 
                       for s in all_results["symbols"].values())
    total_issues = sum(s.get("summary", {}).get("windows_with_issues", 0) 
                      for s in all_results["symbols"].values())
    
    all_results["overall_summary"] = {
        "total_windows": total_windows,
        "windows_with_issues": total_issues,
        "overall_quality_rate": (total_windows - total_issues) / total_windows if total_windows > 0 else 0
    }
    
    return all_results


def write_validation_report(results: Dict, output_path: str):
    """Write validation report to file."""
    try:
        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_file, "w") as f:
            json.dump(results, f, indent=2, cls=PandasJSONEncoder)
            
        logging.info(f"Validation report written to {output_file}")
        
    except Exception as e:
        logging.error(f"Error writing validation report: {e}")


def main():
    """Main function for data quality validation."""
    parser = argparse.ArgumentParser(description="Validate data quality for captured windows")
    parser.add_argument(
        "--symbols", default="BTC-USD,ETH-USD", help="Comma-separated list of symbols"
    )
    parser.add_argument(
        "--days-back", type=int, default=1, help="Number of days to look back"
    )
    parser.add_argument("--bucket", default="acd-monitor-snapshots", help="S3 bucket")
    parser.add_argument("--prefix", default="snapshots", help="S3 prefix")
    parser.add_argument(
        "--output", default="reports/data_quality_report.json", help="Output file path"
    )
    parser.add_argument("--verbose", action="store_true", help="Verbose logging")

    args = parser.parse_args()

    setup_logging(args.verbose)

    try:
        # Parse symbols
        symbols = [s.strip() for s in args.symbols.split(",")]

        # Validate recent windows
        results = validate_recent_windows(
            symbols, args.days_back, args.bucket, args.prefix
        )

        # Write report
        write_validation_report(results, args.output)

        # Print summary
        overall = results.get("overall_summary", {})
        print(f"\nData Quality Validation Summary:")
        print(f"  Total windows: {overall.get('total_windows', 0)}")
        print(f"  Windows with issues: {overall.get('windows_with_issues', 0)}")
        print(f"  Overall quality rate: {overall.get('overall_quality_rate', 0):.1%}")

        # Print per-symbol summary
        for symbol, data in results.get("symbols", {}).items():
            summary = data.get("summary", {})
            print(f"\n{symbol}:")
            print(f"  Windows: {summary.get('total_windows', 0)}")
            print(f"  Quality rate: {summary.get('quality_rate', 0):.1%}")

        sys.exit(0)

    except Exception as e:
        logging.error(f"Data quality validation failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
