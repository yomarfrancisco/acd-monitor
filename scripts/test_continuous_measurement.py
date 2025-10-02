#!/usr/bin/env python3
"""
Test Continuous Measurement System
"""

import subprocess
import sys
import json
import boto3
from datetime import datetime


def test_continuous_measurement():
    """Test the continuous measurement system with real S3 data"""

    # Test parameters
    symbol = "BTC-USD"
    date = "20250929"
    time_range = "1330-1400"
    output_path = f"continuous_metrics/{symbol}/{date}/{time_range}/metrics.json"

    print(f"Testing continuous measurement for {symbol} {date} {time_range}")

    # Run the measurement script
    cmd = [
        "python",
        "scripts/continuous_measurement.py",
        "--symbol",
        symbol,
        "--date",
        date,
        "--time-range",
        time_range,
        "--output-path",
        output_path,
    ]

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)

        if result.returncode == 0:
            print("✅ Continuous measurement completed successfully")
            print("Output:", result.stdout)

            # Verify S3 storage
            s3 = boto3.client("s3")
            try:
                response = s3.get_object(
                    Bucket="acd-monitor-snapshots", Key=output_path
                )
                data = json.loads(response["Body"].read())
                print(f"✅ Results stored in S3: {len(data)} keys")
                print(f"✅ Metrics for venues: {list(data.get('metrics', {}).keys())}")
                print(
                    f"✅ Cross-venue metrics: {list(data.get('cross_venue', {}).keys())}"
                )
                return True
            except Exception as e:
                print(f"❌ Failed to verify S3 storage: {e}")
                return False
        else:
            print(f"❌ Continuous measurement failed: {result.stderr}")
            return False

    except subprocess.TimeoutExpired:
        print("❌ Continuous measurement timed out")
        return False
    except Exception as e:
        print(f"❌ Test failed: {e}")
        return False


if __name__ == "__main__":
    success = test_continuous_measurement()
    sys.exit(0 if success else 1)
