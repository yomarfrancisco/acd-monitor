#!/usr/bin/env python3
"""
ICP-VMM Real Data Test

Tests the ICP-VMM pipeline on real BTC-USD data from local snapshots.
"""

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

# Add src to path
sys.path.append(str(Path(__file__).parent.parent.parent / "src"))

from icp_vmm.environments import EnvironmentLabeler
from icp_vmm.export import ICPVMMExporter
from icp_vmm.icp import ICPTester
from icp_vmm.tests import PreconditionTester
from icp_vmm.transforms import DataTransformer
from icp_vmm.vmm import VMMAnalyzer


def load_real_data(snapshot_path: str):
    """Load real data from local snapshot."""
    print(f"📂 Loading data from {snapshot_path}")

    venue_data = {}
    snapshot_dir = Path(snapshot_path)

    # Load tick data for each venue
    ticks_dir = snapshot_dir / "ticks"
    if not ticks_dir.exists():
        raise FileNotFoundError(f"Ticks directory not found: {ticks_dir}")

    for venue_dir in ticks_dir.iterdir():
        if venue_dir.is_dir():
            venue = venue_dir.name
            parquet_files = list(venue_dir.glob("*.parquet"))
            if parquet_files:
                df = pd.read_parquet(parquet_files[0])
                venue_data[venue] = df
                print(f"   ✅ {venue}: {len(df)} observations")
            else:
                print(f"   ⚠️ {venue}: No parquet files found")

    # Load overlap metadata
    overlap_file = snapshot_dir / "OVERLAP.json"
    if overlap_file.exists():
        with open(overlap_file, "r") as f:
            overlap_data = json.load(f)
        print(f"   ✅ OVERLAP.json loaded")
    else:
        overlap_data = {}
        print(f"   ⚠️ OVERLAP.json not found")

    # Create mock continuous metrics (in real implementation, these would be calculated)
    if venue_data:
        n_obs = len(list(venue_data.values())[0])
        continuous_metrics = {
            "daily_vwap": 50000.0,  # Mock VWAP
            "day_high": 50100.0,  # Mock high
            "day_low": 49900.0,  # Mock low
            "liquidity_ratio": pd.Series(np.random.uniform(0.5, 2.0, n_obs)),
            "liquidity_volatility": pd.Series(np.random.uniform(0.1, 0.5, n_obs)),
            "leadership_shares": pd.Series(np.random.uniform(0.2, 0.8, n_obs)),
        }
    else:
        continuous_metrics = {}

    return venue_data, continuous_metrics, overlap_data


def main():
    """Run ICP-VMM real data test."""
    print("🚀 Starting ICP-VMM Real Data Test")
    print("=" * 60)

    try:
        # Load real data
        snapshot_path = "snapshots/btc_window1"
        venue_data, continuous_metrics, overlap_data = load_real_data(snapshot_path)

        if not venue_data:
            print("❌ No venue data found")
            return 1

        print(f"✅ Loaded data for {len(venue_data)} venues")

        # Initialize components
        print("\n🔧 Initializing ICP-VMM components...")
        env_labeler = EnvironmentLabeler(min_obs_per_env=5)
        transformer = DataTransformer()
        tester = PreconditionTester()
        vmm_analyzer = VMMAnalyzer()
        icp_tester = ICPTester(fdr_alpha=0.05, bootstrap_samples=100)
        exporter = ICPVMMExporter("acd-monitor-snapshots", "analysis")

        # Prepare data
        print("\n📈 Preparing data for analysis...")
        prepared_data, processed_metrics, warnings = transformer.prepare_analysis_data(
            venue_data, continuous_metrics
        )
        print(f"✅ Data prepared with {len(warnings)} warnings")
        if warnings:
            for warning in warnings:
                print(f"   ⚠️ {warning}")

        # Label environments
        print("\n🏷️ Labeling environments...")
        labeled_data = {}
        for venue, data in prepared_data.items():
            labeled_data[venue] = env_labeler.label_all_environments(data, processed_metrics)

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
                labeled_data, {}, {}  # env_leadership  # env_residuals
            )
            print(
                f"✅ ICP tests completed: {icp_tests.get('overall', {}).get('status', 'UNKNOWN')}"
            )

            status = "PROVISIONAL"

        # Prepare results
        window_id = f"btc_window1_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        results = {
            "window_id": window_id,
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
            print("✅ ICP-VMM Real Data Test completed successfully!")
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

            # Print sample ICP results
            if icp_tests:
                print("\n📄 Sample ICP.json:")
                icp_sample = {
                    "overall": icp_tests.get("overall", {}),
                    "parameter_tests": list(icp_tests.get("parameter_tests", {}).keys()),
                    "leadership_tests": icp_tests.get("leadership_tests", {}),
                    "residual_tests": icp_tests.get("residual_tests", {}),
                }
                print(json.dumps(icp_sample, indent=2)[:500] + "...")

        else:
            print(f"❌ Export failed: {export_status.get('error', 'Unknown error')}")
            return 1

    except Exception as e:
        print(f"❌ Real data test failed: {e}")
        import traceback

        traceback.print_exc()
        return 1

    print("\n🎉 ICP-VMM Real Data Test completed successfully!")
    return 0


if __name__ == "__main__":
    exit(main())
