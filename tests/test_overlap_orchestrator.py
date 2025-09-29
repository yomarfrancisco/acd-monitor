"""
Unit tests for the overlap orchestrator.
"""

import pytest
import json
import tempfile
from pathlib import Path
# from datetime import datetime  # Not used in current tests
from src.acd.capture.overlap_orchestrator import OverlapOrchestrator


def test_status_json_shape():
    """Test that status JSON has the correct shape."""
    with tempfile.TemporaryDirectory() as temp_dir:
        orchestrator = OverlapOrchestrator(
            pair="BTC-USD",
            export_dir=temp_dir,
            freq="1s",
            quorum=4,
            min_minutes=[30, 20, 10],
            policy_order=["BEST4_30m", "BEST4_20m", "BEST4_10m", "ALL5_10m"],
            max_gap_s=1.0,
            heartbeat_interval=5,
            check_interval=30,
            micro_gap_stitch=False,
        )

        # Write status
        orchestrator._write_status()

        # Check status file exists
        status_file = orchestrator.status_file
        assert status_file.exists()

        # Load and validate status JSON
        with open(status_file, "r") as f:
            status = json.load(f)

        # Check required fields
        required_fields = [
            "policy_checked",
            "best_window",
            "venues_ready",
            "venues_gappy",
            "venues_idle",
            "last_check_utc",
            "capture_uptime_sec",
            "micro_gap_stitch",
        ]

        for field in required_fields:
            assert field in status, f"Missing field: {field}"

        # Check data types
        assert isinstance(status["policy_checked"], list)
        assert isinstance(status["venues_ready"], list)
        assert isinstance(status["venues_gappy"], list)
        assert isinstance(status["venues_idle"], list)
        assert isinstance(status["capture_uptime_sec"], (int, float))
        assert isinstance(status["micro_gap_stitch"], bool)


def test_pin_snapshot_path_build():
    """Test that pin/snapshot paths are built correctly."""
    with tempfile.TemporaryDirectory() as temp_dir:
        orchestrator = OverlapOrchestrator(
            pair="BTC-USD",
            export_dir=temp_dir,
            freq="1s",
            quorum=4,
            min_minutes=[30, 20, 10],
            policy_order=["BEST4_30m", "BEST4_20m", "BEST4_10m", "ALL5_10m"],
            max_gap_s=1.0,
            heartbeat_interval=5,
            check_interval=30,
            micro_gap_stitch=False,
        )

        # Test overlap data
        overlap_data = {
            "startUTC": "2025-09-26T20:30:00",
            "endUTC": "2025-09-26T21:00:00",
            "minutes": 30.0,
            "venues": ["binance", "coinbase", "kraken", "okx"],
            "excluded": ["bybit"],
            "policy": "BEST4_30m",
        }

        # Pin overlap window
        run_dir = orchestrator._pin_overlap_window(overlap_data)

        # Check run directory structure
        run_path = Path(run_dir)
        assert run_path.exists()
        assert run_path.is_dir()

        # Check expected files exist
        expected_files = ["OVERLAP.json", "GAP_REPORT.json", "MANIFEST.json", "ticks"]

        for file_name in expected_files:
            file_path = run_path / file_name
            assert file_path.exists(), f"Missing file: {file_name}"

        # Check ticks directory structure
        ticks_dir = run_path / "ticks"
        assert ticks_dir.is_dir()

        # Check venue directories exist
        for venue in overlap_data["venues"]:
            venue_dir = ticks_dir / venue
            assert venue_dir.exists(), f"Missing venue directory: {venue}"
            assert venue_dir.is_dir()


def test_heartbeat_csv_initialization():
    """Test that heartbeat CSV is initialized correctly."""
    with tempfile.TemporaryDirectory() as temp_dir:
        orchestrator = OverlapOrchestrator(
            pair="BTC-USD",
            export_dir=temp_dir,
            freq="1s",
            quorum=4,
            min_minutes=[30, 20, 10],
            policy_order=["BEST4_30m", "BEST4_20m", "BEST4_10m", "ALL5_10m"],
            max_gap_s=1.0,
            heartbeat_interval=5,
            check_interval=30,
            micro_gap_stitch=False,
        )

        # Check heartbeat file exists
        heartbeat_file = orchestrator.heartbeat_file
        assert heartbeat_file.exists()

        # Check CSV headers
        with open(heartbeat_file, "r") as f:
            content = f.read()
            lines = content.strip().split("\n")

            # Should have header line
            assert len(lines) >= 1

            # Check header columns
            header = lines[0]
            expected_columns = [
                "ts",
                "venue",
                "msgs_last_30s",
                "last_tick_exchange_ts",
                "last_tick_local_ts",
                "lag_ms",
                "gaps_last_30s",
            ]

            for column in expected_columns:
                assert column in header, f"Missing column: {column}"


if __name__ == "__main__":
    pytest.main([__file__])
