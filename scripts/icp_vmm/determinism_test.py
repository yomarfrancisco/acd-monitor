#!/usr/bin/env python3
"""
ICP-VMM Determinism Test

Runs export twice on same fixture and asserts identical manifestHash.
"""

import hashlib
import json
import shutil
import sys
import tempfile
from pathlib import Path
from typing import Any, Dict

# Add src to path
sys.path.append(str(Path(__file__).parent.parent.parent / "src"))

from icp_vmm.refined_export import RefinedICPVMMExporter


def create_test_fixture() -> Dict[str, Any]:
    """Create a test fixture for determinism testing."""
    return {
        "window_id": "test_determinism_20250930",
        "symbol": "BTC-USD",
        "status": "PROVISIONAL",
        "status_reason": "test fixture",
        "timestamp": "2025-09-30T00:00:00Z",
        "ts_start": "2025-09-30T00:00:00Z",
        "ts_end": "2025-09-30T00:30:00Z",
        "venues": ["binance", "coinbase", "kraken"],
        "observations": {"binance": 1000, "coinbase": 1000, "kraken": 1000},
        "coverage": {"binance": 1.0, "coinbase": 1.0, "kraken": 1.0},
        "schema_status": "complete",
        "missing_fields": [],
        "seed": 42,
        "fields_used": ["last_px", "best_bid", "best_ask"],
        "johansen_mode": "VAR_FEVD",
        "lags": 2,
        "rank": 0,
        "info_shares": {"binance": 0.33, "coinbase": 0.33, "kraken": 0.34},
        "fdr_q": 0.05,
        "tested_params": ["last_px", "best_bid"],
        "invariant_params": ["last_px"],
        "variant_params": ["best_bid"],
        "env_bins": {"session": ["europe"], "vwap_side": ["above", "below"]},
        "env_counts": {
            "session": {
                "binance_europe": 500,
                "coinbase_europe": 500,
                "kraken_europe": 500,
            },
            "vwap_side": {
                "binance_above": 250,
                "binance_below": 250,
                "coinbase_above": 250,
                "coinbase_below": 250,
                "kraken_above": 250,
                "kraken_below": 250,
            },
        },
        "min_bin_size": 5,
        "leadership_index": 0.1,
        "summary": "Test fixture for determinism",
        "vmm_results": {"mode": "VAR_FEVD"},
        "icp_tests": {"overall": {"status": "INVARIANT"}},
        "warnings": [],
        "git_sha": "test123",
        "data_hashes": {},
        "input_hashes": [],
        "output_hashes": [],
    }


def run_export(fixture: Dict[str, Any], output_dir: str) -> str:
    """Run export and return manifest hash."""
    # Use fixed timestamps in the fixture
    fixture["timestamp"] = "2025-09-30T00:00:00Z"
    fixture["ts_start"] = "2025-09-30T00:00:00Z"
    fixture["ts_end"] = "2025-09-30T00:30:00Z"

    exporter = RefinedICPVMMExporter()
    s3_inputs = [f"s3://test-bucket/input/{venue}.parquet" for venue in fixture["venues"]]

    result = exporter.export_refined_results(
        fixture, fixture["window_id"], "BTC-USD", s3_inputs, output_dir
    )

    if result["status"] != "SUCCESS":
        raise Exception(f"Export failed: {result.get('error', 'Unknown error')}")

    return result["manifest_hash"]


def test_determinism():
    """Test that two exports produce identical manifest hashes."""
    print("🧪 Testing ICP-VMM determinism...")

    fixture = create_test_fixture()

    # Create temporary directories
    with tempfile.TemporaryDirectory() as temp_dir:
        output_dir1 = Path(temp_dir) / "run1"
        output_dir2 = Path(temp_dir) / "run2"

        # Run export twice
        print("   Running first export...")
        hash1 = run_export(fixture, str(output_dir1))

        print("   Running second export...")
        hash2 = run_export(fixture, str(output_dir2))

        # Compare hashes
        if hash1 == hash2:
            print(f"✅ Determinism test passed: {hash1}")
            return True
        else:
            print(f"❌ Determinism test failed:")
            print(f"   Hash 1: {hash1}")
            print(f"   Hash 2: {hash2}")
            return False


def main():
    """Main test function."""
    if test_determinism():
        sys.exit(0)
    else:
        sys.exit(1)


if __name__ == "__main__":
    main()
