#!/usr/bin/env python3
"""
Parquet Scan Test using PyArrow
Test streaming S3 parquet access without downloading.
"""

import json
import os
import sys
from pathlib import Path


def test_parquet_scan_pyarrow():
    """Test parquet scanning via PyArrow."""
    results = {
        "timestamp": "2025-09-30T18:35:00Z",
        "test_method": "pyarrow_s3fs",
        "success": False,
        "error": None,
        "row_count": None,
        "sample_data": None,
    }

    try:
        # Try to import required modules
        import pyarrow as pa
        import pyarrow.parquet as pq
        import s3fs

        # Create S3 filesystem
        fs = s3fs.S3FileSystem()

        # List some parquet files
        parquet_files = fs.glob(
            "acd-monitor-snapshots/snapshots/BTC-USD/*/*/ticks/*/part-*.parquet"
        )

        if not parquet_files:
            results["error"] = "No parquet files found"
            return results

        # Take first few files for testing
        test_files = parquet_files[:3]
        results["test_files"] = test_files

        # Read parquet files
        total_rows = 0
        sample_data = []

        for file_path in test_files:
            try:
                # Read parquet file
                table = pq.read_table(f"s3://{file_path}", filesystem=fs)
                total_rows += len(table)

                # Get sample data from first file
                if not sample_data:
                    sample_data = table.to_pandas().head(3).to_dict("records")

            except Exception as e:
                results["error"] = f"Error reading {file_path}: {str(e)}"
                return results

        results["row_count"] = total_rows
        results["sample_data"] = sample_data
        results["success"] = True

    except ImportError as e:
        results["error"] = f"Required modules not available: {str(e)}"
    except Exception as e:
        results["error"] = f"PyArrow scan failed: {str(e)}"
        results["error_type"] = type(e).__name__

    return results


if __name__ == "__main__":
    results = test_parquet_scan_pyarrow()
    print(json.dumps(results, indent=2))
