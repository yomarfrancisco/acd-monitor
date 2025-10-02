#!/usr/bin/env python3
"""
Smoke test for default behavior of spread v2 detector.
"""

import unittest
import subprocess
import sys
import json
import tempfile
from pathlib import Path

# Add src to path
sys.path.append(str(Path(__file__).parent.parent.parent / "src"))


class TestDefaultBehavior(unittest.TestCase):
    """Test default behavior and CLI help."""

    def test_cli_help_shows_percentile_default(self):
        """Test that CLI help shows percentile as default detector."""
        result = subprocess.run(
            [sys.executable, "scripts/gold_hunt_control_v2.py", "--help"],
            capture_output=True,
            text=True,
        )

        self.assertEqual(result.returncode, 0)
        self.assertIn("--detector {percentile,zscore}", result.stdout)
        self.assertIn("default: percentile", result.stdout)

    def test_empty_snapshot_skips_cleanly(self):
        """Test that empty snapshot skips cleanly without errors."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create empty snapshot directory
            snapshot_dir = Path(temp_dir) / "empty_snapshot"
            snapshot_dir.mkdir()

            # Create empty OVERLAP.json
            overlap_data = {
                "startUTC": "2025-01-01T00:00:00.000000+00:00",
                "endUTC": "2025-01-01T00:01:00.000000+00:00",
                "minutes": 1.0,
                "venues": ["binance", "coinbase"],
                "policy": "TEST",
                "coverage": 1.0,
                "granularity_sec": 1,
                "min_duration_min": 1,
                "all_venues": True,
                "stitch": False,
                "mode": "TEST",
                "granularity": "1s",
            }

            with open(snapshot_dir / "OVERLAP.json", "w") as f:
                json.dump(overlap_data, f)

            # Create empty ticks directory
            ticks_dir = snapshot_dir / "ticks"
            ticks_dir.mkdir()

            # Run with default percentile detector
            result = subprocess.run(
                [
                    sys.executable,
                    "scripts/gold_hunt_control_v2.py",
                    "--snapshot-dir",
                    str(snapshot_dir),
                    "--export-dir",
                    str(Path(temp_dir) / "output"),
                    "--verbose",
                ],
                capture_output=True,
                text=True,
            )

            # Should exit cleanly (not crash)
            self.assertIn("No tick data loaded from snapshot", result.stderr)
            self.assertEqual(result.returncode, 0)

    def test_no_demo_provenance_in_real_data(self):
        """Test that real data never produces demo provenance."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create minimal real snapshot
            snapshot_dir = Path(temp_dir) / "real_snapshot"
            snapshot_dir.mkdir()

            # Create OVERLAP.json for real data
            overlap_data = {
                "startUTC": "2025-01-01T00:00:00.000000+00:00",
                "endUTC": "2025-01-01T00:01:00.000000+00:00",
                "minutes": 1.0,
                "venues": ["binance"],
                "policy": "REAL",
                "coverage": 1.0,
                "granularity_sec": 1,
                "min_duration_min": 1,
                "all_venues": True,
                "stitch": False,
                "mode": "REAL",
                "granularity": "1s",
            }

            with open(snapshot_dir / "OVERLAP.json", "w") as f:
                json.dump(overlap_data, f)

            # Create minimal tick data
            import pandas as pd
            import numpy as np

            ticks_dir = (
                snapshot_dir
                / "ticks"
                / "binance"
                / "BTC-USD"
                / "1s"
                / "2025-01-01"
                / "00"
            )
            ticks_dir.mkdir(parents=True)

            # Create minimal tick data
            timestamps = pd.date_range("2025-01-01T00:00:00", periods=60, freq="1S")
            tick_data = pd.DataFrame(
                {
                    "exchange": "binance",
                    "pair": "BTC-USD",
                    "ts_exchange": timestamps,
                    "ts_local": timestamps,
                    "best_bid": 45000.0,
                    "best_ask": 45001.0,
                    "mid": 45000.5,
                    "last_trade_px": 45000.5,
                    "last_trade_qty": 0.001,
                    "event_type": "ticker",
                }
            )

            tick_data.to_parquet(ticks_dir / "ticks_00.parquet", index=False)

            # Run with default settings
            result = subprocess.run(
                [
                    sys.executable,
                    "scripts/gold_hunt_control_v2.py",
                    "--snapshot-dir",
                    str(snapshot_dir),
                    "--export-dir",
                    str(Path(temp_dir) / "output"),
                    "--verbose",
                ],
                capture_output=True,
                text=True,
            )

            # Check output files
            output_dir = Path(temp_dir) / "output"
            if (output_dir / "control_v2_results.json").exists():
                with open(output_dir / "control_v2_results.json", "r") as f:
                    results = json.load(f)

                # Should not have demo provenance
                if "provenance" in results:
                    self.assertNotEqual(results["provenance"], "DEMO")
                if "regulatory_grade" in results:
                    self.assertNotEqual(results["regulatory_grade"], False)


if __name__ == "__main__":
    unittest.main()
