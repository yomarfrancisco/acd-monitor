#!/usr/bin/env python3
"""
Parquet Scan Test using DuckDB/HTTPFS
Test streaming S3 parquet access without downloading.
"""

import os
import json
import sys
from pathlib import Path

def test_parquet_scan():
    """Test parquet scanning via DuckDB HTTPFS."""
    results = {
        "timestamp": "2025-09-30T18:35:00Z",
        "test_method": "duckdb_httpfs",
        "success": False,
        "error": None,
        "row_count": None,
        "sample_data": None
    }
    
    try:
        # Try to import duckdb
        import duckdb
        
        # Connect and install httpfs
        con = duckdb.connect()
        con.execute("INSTALL httpfs; LOAD httpfs;")
        
        # Set S3 region
        aws_region = os.getenv("AWS_REGION", "us-east-1")
        con.execute(f"SET s3_region='{aws_region}';")
        
        # Test query - count rows in parquet files
        query = """
        SELECT COUNT(*) AS n_rows
        FROM read_parquet('s3://acd-monitor-snapshots/snapshots/BTC-USD/*/*/ticks/*/part-*.parquet')
        """
        
        result = con.execute(query).fetchall()
        results["row_count"] = result[0][0]
        results["success"] = True
        
        # Try to get a small sample
        sample_query = """
        SELECT *
        FROM read_parquet('s3://acd-monitor-snapshots/snapshots/BTC-USD/*/*/ticks/*/part-*.parquet')
        LIMIT 5
        """
        
        sample_result = con.execute(sample_query).fetchall()
        results["sample_data"] = [list(row) for row in sample_result]
        
        con.close()
        
    except ImportError as e:
        results["error"] = f"duckdb not available: {str(e)}"
    except Exception as e:
        results["error"] = f"duckdb scan failed: {str(e)}"
        results["error_type"] = type(e).__name__
    
    return results

if __name__ == "__main__":
    results = test_parquet_scan()
    print(json.dumps(results, indent=2))
