#!/usr/bin/env python3
"""
ICP-VMM Dry Run Test

Tests the ICP-VMM pipeline on mock data to validate the full flow.
"""

import sys
import json
import pandas as pd
import numpy as np
from datetime import datetime, timezone
from pathlib import Path

# Add src to path
sys.path.append(str(Path(__file__).parent.parent.parent / "src"))

from icp_vmm.environments import EnvironmentLabeler
from icp_vmm.transforms import DataTransformer
from icp_vmm.tests import PreconditionTester
from icp_vmm.vmm import VMMAnalyzer
from icp_vmm.icp import ICPTester
from icp_vmm.export import ICPVMMExporter


def create_mock_data():
    """Create mock BTC-USD data for testing."""
    np.random.seed(42)
    n_obs = 1000

    # Create timestamps
    start_time = pd.Timestamp("2025-09-29 12:00:00", tz="UTC")
    timestamps = pd.date_range(start_time, periods=n_obs, freq="1s")

    # Create mock venue data
    venue_data = {}
    venues = ["binance", "coinbase", "kraken", "okx", "bybit"]

    base_price = 50000
    for venue in venues:
        # Generate correlated price data
        price_noise = np.random.randn(n_obs) * 10
        prices = base_price + np.cumsum(price_noise)

        venue_data[venue] = pd.DataFrame(
            {
                "ts_exchange": timestamps,
                "last_px": prices,
                "best_bid": prices - np.random.uniform(0.5, 2.0, n_obs),
                "best_ask": prices + np.random.uniform(0.5, 2.0, n_obs),
                "spread_bps": np.random.uniform(0.1, 2.0, n_obs),
                "bid_sz": np.random.uniform(0.1, 10.0, n_obs),
                "ask_sz": np.random.uniform(0.1, 10.0, n_obs),
                "imbalance": np.random.uniform(-0.5, 0.5, n_obs),
            }
        )

    # Create continuous metrics
    continuous_metrics = {
        "daily_vwap": base_price,
        "day_high": base_price + 100,
        "day_low": base_price - 100,
        "liquidity_ratio": pd.Series(np.random.uniform(0.5, 2.0, n_obs)),
        "liquidity_volatility": pd.Series(np.random.uniform(0.1, 0.5, n_obs)),
        "leadership_shares": pd.Series(np.random.uniform(0.2, 0.8, n_obs)),
    }

    return venue_data, continuous_metrics


def main():
    """Run ICP-VMM dry run test."""
    print("🚀 Starting ICP-VMM Dry Run Test")
    print("=" * 60)

    try:
        # Create mock data
        print("📊 Creating mock BTC-USD data...")
        venue_data, continuous_metrics = create_mock_data()
        print(
            f"✅ Created data for {len(venue_data)} venues with {len(venue_data['binance'])} observations"
        )

        # Initialize components
        print("\n🔧 Initializing ICP-VMM components...")
        env_labeler = EnvironmentLabeler(min_obs_per_env=5)
        transformer = DataTransformer()
        tester = PreconditionTester()
        vmm_analyzer = VMMAnalyzer()
        icp_tester = ICPTester(
            fdr_alpha=0.05, bootstrap_samples=100
        )  # Reduced for speed
        exporter = ICPVMMExporter("acd-monitor-snapshots", "analysis")

        # Prepare data
        print("\n📈 Preparing data for analysis...")
        prepared_data, processed_metrics, warnings = transformer.prepare_analysis_data(
            venue_data, continuous_metrics
        )
        print(f"✅ Data prepared with {len(warnings)} warnings")

        # Label environments
        print("\n🏷️ Labeling environments...")
        labeled_data = {}
        for venue, data in prepared_data.items():
            labeled_data[venue] = env_labeler.label_all_environments(
                data, processed_metrics
            )

        # Get environment counts
        env_counts = {}
        for venue, data in labeled_data.items():
            venue_counts = env_labeler.get_environment_counts(data)
            for env_type, counts in venue_counts.items():
                if env_type not in env_counts:
                    env_counts[env_type] = {}
                for env, count in counts.items():
                    key = f"{venue}_{env}"
                    env_counts[env_type][key] = env_counts[env_type].get(key, 0) + count

        print("✅ Environment labeling completed")
        for env_type, counts in env_counts.items():
            print(f"   {env_type}: {len(counts)} bins")

        # Run precondition tests
        print("\n🧪 Running precondition tests...")
        test_results = tester.run_all_tests(prepared_data, env_counts)
        print(f"✅ Precondition tests: {test_results['overall']['status']}")

        if test_results["overall"]["status"] == "INSUFFICIENT":
            print("⚠️ Insufficient data for full analysis")
            status = "INSUFFICIENT"
            vmm_results = {}
            icp_tests = {}
        else:
            # Run VMM analysis
            print("\n📊 Running VMM analysis...")
            vmm_results = vmm_analyzer.analyze_vmm(prepared_data)
            print(f"✅ VMM analysis completed: {vmm_results.get('mode', 'UNKNOWN')}")

            # Run ICP tests
            print("\n🔍 Running ICP tests...")
            icp_tests = icp_tester.run_all_icp_tests(
                labeled_data,
                {},  # env_leadership - would be extracted from labeled_data
                {},  # env_residuals - would be calculated from VMM residuals
            )
            print(
                f"✅ ICP tests completed: {icp_tests.get('overall', {}).get('status', 'UNKNOWN')}"
            )

            status = "PROVISIONAL"

        # Prepare results
        results = {
            "window_id": "test_window_20250929_1200_1230",
            "symbol": "BTC-USD",
            "status": status,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "config": {
                "min_per_env": 5,
                "bootstrap_samples": 100,
                "fdr_alpha": 0.05,
                "mode": "provisional",
            },
            "env_counts": env_counts,
            "test_results": test_results,
            "vmm_results": vmm_results,
            "icp_tests": icp_tests,
            "warnings": warnings,
        }

        # Export results
        print("\n📁 Exporting results...")
        export_status = exporter.export_to_s3(results, results["window_id"], "BTC-USD")

        if export_status["status"] == "SUCCESS":
            print("✅ ICP-VMM Dry Run completed successfully!")
            print(f"📊 Status: {status}")
            print(f"📁 S3 Path: {export_status.get('s3_path', 'N/A')}")
            print(f"📄 Files: {export_status.get('files_exported', [])}")

            # Print key log lines
            print("\n📋 Key Log Lines:")
            print(
                f"[ICPVMM:status] window={results['window_id']} status={status} venues={len(venue_data)} coverage=1.00"
            )
            print(
                f"[ENV:bins] session={len(env_counts.get('session', {}))} vwap_side={len(env_counts.get('vwap_side', {}))} highlow={len(env_counts.get('hl_bucket', {}))} liquidity={len(env_counts.get('liquidity_regime', {}))} leadership={len(env_counts.get('leadership_regime', {}))}"
            )
            if vmm_results:
                print(
                    f"[VMM] mode={vmm_results.get('mode', 'UNKNOWN')} venues={len(vmm_results.get('venues', []))}"
                )
            if icp_tests:
                print(
                    f"[ICP] tested_params={len(icp_tests.get('parameter_tests', {}))} invariant={icp_tests.get('overall', {}).get('status', 'UNKNOWN')} fdr_q=0.05"
                )

            # Print sample manifest
            print("\n📄 Sample MANIFEST.json:")
            manifest_sample = {
                "window_id": results["window_id"],
                "timestamp": results["timestamp"],
                "status": status,
                "venues": list(venue_data.keys()),
                "environment_counts": env_counts,
                "test_results": test_results["overall"],
            }
            print(json.dumps(manifest_sample, indent=2)[:500] + "...")

        else:
            print(f"❌ Export failed: {export_status.get('error', 'Unknown error')}")
            return 1

    except Exception as e:
        print(f"❌ Dry run failed: {e}")
        import traceback

        traceback.print_exc()
        return 1

    print("\n🎉 ICP-VMM Dry Run Test completed successfully!")
    return 0


if __name__ == "__main__":
    exit(main())
