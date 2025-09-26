"""
Real-time overlap orchestrator for ACD analysis.
Continuously captures data from all 5 venues and monitors for strict overlap windows.
"""

import asyncio
import websockets
import aiohttp
import pandas as pd
from datetime import datetime, timedelta
import json
import logging
import os
import time
import subprocess
import signal
import shutil
from typing import List, Dict, Optional
import sys
from pathlib import Path
import csv

logger = logging.getLogger(__name__)


class OverlapOrchestrator:
    """Real-time capture orchestrator with strict overlap monitoring."""

    def __init__(
        self,
        pair: str = "BTC-USD",
        export_dir: str = "exports",
        freq: str = "1s",
        quorum: int = 4,
        min_minutes: List[int] = [30, 20, 10],
        policy_order: List[str] = ["BEST4_30m", "BEST4_20m", "BEST4_10m", "ALL5_10m"],
        max_gap_s: float = 1.0,
        heartbeat_interval: int = 5,
        check_interval: int = 30,
        micro_gap_stitch: bool = False,
    ):
        self.pair = pair
        self.export_dir = export_dir
        self.freq = freq
        self.quorum = quorum
        self.min_minutes = min_minutes
        self.policy_order = policy_order
        self.max_gap_s = max_gap_s
        self.heartbeat_interval = heartbeat_interval
        self.check_interval = check_interval
        self.micro_gap_stitch = micro_gap_stitch

        self.venues = ["binance", "coinbase", "kraken", "okx", "bybit"]
        self.capture_start = datetime.now()
        self.capture_duration = timedelta(hours=3)
        self.capture_end = self.capture_start + self.capture_duration

        # Message tracking per venue
        self.venue_stats = {
            venue: {
                "messages": 0,
                "last_heartbeat": None,
                "lag_ms": 0,
                "last_tick_exchange_ts": None,
                "last_tick_local_ts": None,
                "gaps_last_30s": 0,
                "skewed": False,
            }
            for venue in self.venues
        }

        # Clock state
        self.clock_offset_ms = None
        self.last_clock_check = None
        self._record_clock_state()

        # Status tracking
        self.overlap_status_dir = Path(export_dir) / "overlap"
        self.overlap_status_dir.mkdir(parents=True, exist_ok=True)

        # PID file for restart safety
        self.pid_file = self.overlap_status_dir / "orchestrator.pid"
        self._check_pid_file()

        # Status files
        self.status_file = self.overlap_status_dir / "OVERLAP_STATUS.json"
        self.log_file = self.overlap_status_dir / "OVERLAP_STATUS.log"
        self.heartbeat_file = self.overlap_status_dir / "HEARTBEAT.csv"
        self.clock_file = self.overlap_status_dir / "CLOCK_CHECK.json"

        # Initialize heartbeat CSV
        self._init_heartbeat_csv()

        # Setup signal handlers
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)

        # Ensure export directory exists
        os.makedirs(export_dir, exist_ok=True)

    def _record_clock_state(self):
        """Record system clock state on startup."""
        try:
            # Simple NTP offset estimation (in production, use proper NTP client)
            import subprocess

            result = subprocess.run(["ntpq", "-p"], capture_output=True, text=True, timeout=5)
            if result.returncode == 0:
                # Parse NTP offset if available
                lines = result.stdout.split("\n")
                for line in lines:
                    if "*" in line:  # System peer
                        parts = line.split()
                        if len(parts) > 7:
                            try:
                                self.clock_offset_ms = float(parts[7]) * 1000  # Convert to ms
                                break
                            except (ValueError, IndexError):
                                pass
        except Exception:
            pass  # NTP not available, use system time

        clock_info = {"source": "system", "offset_ms": self.clock_offset_ms}
        print(f"[CLOCK:ntp] {json.dumps(clock_info)}")
        logger.info(f"Clock state recorded: {clock_info}")

    def _check_pid_file(self):
        """Check if orchestrator is already running."""
        if self.pid_file.exists():
            try:
                with open(self.pid_file, "r") as f:
                    pid = int(f.read().strip())
                # Check if process is still running
                try:
                    os.kill(pid, 0)  # Signal 0 just checks if process exists
                    logger.error(
                        f"[ABORT:already_running] Orchestrator already running with PID {pid}"
                    )
                    print(
                        f'[ABORT:already_running] {{"pid":{pid},'
                        f'"reason":"orchestrator already running"}}'
                    )
                    sys.exit(1)
                except OSError:
                    # Process doesn't exist, remove stale PID file
                    self.pid_file.unlink()
            except (ValueError, FileNotFoundError):
                # Invalid PID file, remove it
                self.pid_file.unlink()

        # Write our PID
        with open(self.pid_file, "w") as f:
            f.write(str(os.getpid()))

    def _init_heartbeat_csv(self):
        """Initialize heartbeat CSV file with headers."""
        if not self.heartbeat_file.exists():
            with open(self.heartbeat_file, "w", newline="") as f:
                writer = csv.writer(f)
                writer.writerow(
                    [
                        "ts",
                        "venue",
                        "msgs_last_30s",
                        "last_tick_exchange_ts",
                        "last_tick_local_ts",
                        "lag_ms",
                        "gaps_last_30s",
                    ]
                )

    def _signal_handler(self, signum, frame):
        """Handle shutdown signals gracefully."""
        logger.info(f"Received signal {signum}, shutting down gracefully...")
        self._cleanup()
        sys.exit(0)

    def _cleanup(self):
        """Clean up resources on shutdown."""
        try:
            # Flush final status
            self._write_status()
            # Remove PID file
            if self.pid_file.exists():
                self.pid_file.unlink()
            logger.info("Cleanup completed")
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")

    def _write_status(self):
        """Write current status to OVERLAP_STATUS.json."""
        try:
            # Calculate best window from current data
            best_window = self._calculate_best_window()

            # Categorize venues
            venues_ready = []
            venues_gappy = []
            venues_idle = []

            for venue, stats in self.venue_stats.items():
                if stats["messages"] > 0:
                    if stats["gaps_last_30s"] == 0:
                        venues_ready.append(venue)
                    else:
                        venues_gappy.append(venue)
                else:
                    venues_idle.append(venue)

            status = {
                "policy_checked": self.policy_order,
                "best_window": best_window,
                "venues_ready": venues_ready,
                "venues_gappy": venues_gappy,
                "venues_idle": venues_idle,
                "last_check_utc": datetime.now().isoformat(),
                "capture_uptime_sec": (datetime.now() - self.capture_start).total_seconds(),
                "micro_gap_stitch": self.micro_gap_stitch,
            }

            with open(self.status_file, "w") as f:
                json.dump(status, f, indent=2)

        except Exception as e:
            logger.error(f"Error writing status: {e}")

    def _calculate_best_window(self) -> Optional[Dict]:
        """Calculate the best available window from current data."""
        try:
            # This is a simplified version - in practice, you'd load recent data
            # and calculate actual overlap windows
            return {"start": None, "end": None, "minutes": 0, "venues": [], "gaps_ok": False}
        except Exception:
            return None

    def _write_heartbeat(self):
        """Write heartbeat data to CSV."""
        try:
            current_time = datetime.now().isoformat()

            with open(self.heartbeat_file, "a", newline="") as f:
                writer = csv.writer(f)
                for venue, stats in self.venue_stats.items():
                    writer.writerow(
                        [
                            current_time,
                            venue,
                            stats["messages"],
                            stats["last_tick_exchange_ts"],
                            stats["last_tick_local_ts"],
                            stats["lag_ms"],
                            stats["gaps_last_30s"],
                        ]
                    )
        except Exception as e:
            logger.error(f"Error writing heartbeat: {e}")

    def _check_clock_skew(self):
        """Check for clock skew and update venue status."""
        try:
            current_time = datetime.now()

            # Only check every 5 minutes
            if (
                self.last_clock_check is None
                or (current_time - self.last_clock_check).total_seconds() >= 300
            ):

                clock_data = {
                    "timestamp": current_time.isoformat(),
                    "ntp_offset_ms": self.clock_offset_ms,
                    "venue_skew": {},
                }

                # Check each venue for skew
                for venue, stats in self.venue_stats.items():
                    if stats["last_tick_exchange_ts"] and stats["last_tick_local_ts"]:
                        # Calculate drift between exchange and local timestamps
                        drift_ms = abs(stats["last_tick_exchange_ts"] - stats["last_tick_local_ts"])
                        is_skewed = drift_ms > 2000  # 2 second threshold

                        clock_data["venue_skew"][venue] = {
                            "drift_ms": drift_ms,
                            "skewed": is_skewed,
                        }

                        stats["skewed"] = is_skewed

                with open(self.clock_file, "w") as f:
                    json.dump(clock_data, f, indent=2)

                self.last_clock_check = current_time

        except Exception as e:
            logger.error(f"Error checking clock skew: {e}")

    def _log_overlap_event(self, event_type: str, data: Dict):
        """Log overlap events to the status log file."""
        try:
            log_entry = {"timestamp": datetime.now().isoformat(), "event": event_type, "data": data}

            with open(self.log_file, "a") as f:
                f.write(f"[OVERLAP:{event_type}] {json.dumps(log_entry)}\n")

        except Exception as e:
            logger.error(f"Error logging overlap event: {e}")

    def _pin_overlap_window(self, overlap_data: Dict) -> str:
        """Pin an overlap window and create snapshot."""
        try:
            # Create run directory with ISO timestamps
            start_iso = overlap_data["startUTC"].replace(":", "").replace("-", "")
            end_iso = overlap_data["endUTC"].replace(":", "").replace("-", "")
            run_dir = Path(self.export_dir) / "real_data_runs" / f"{start_iso}__{end_iso}"
            run_dir.mkdir(parents=True, exist_ok=True)

            # Write overlap.json to run directory
            overlap_file = run_dir / "OVERLAP.json"
            with open(overlap_file, "w") as f:
                json.dump(overlap_data, f, indent=2)

            # Create snapshot of parquet files
            snapshot_dir = run_dir / "ticks"
            snapshot_dir.mkdir(exist_ok=True)

            # Copy relevant parquet files for each venue
            for venue in overlap_data["venues"]:
                venue_snapshot_dir = snapshot_dir / venue
                venue_snapshot_dir.mkdir(exist_ok=True)

                # Copy parquet files that intersect the window
                self._copy_venue_snapshot(venue, overlap_data, venue_snapshot_dir)

            # Generate gap report
            gap_report = self._generate_gap_report(overlap_data, snapshot_dir)
            gap_report_file = run_dir / "GAP_REPORT.json"
            with open(gap_report_file, "w") as f:
                json.dump(gap_report, f, indent=2)

            # Create run manifest
            manifest = self._create_run_manifest(overlap_data, run_dir, gap_report)
            manifest_file = run_dir / "MANIFEST.json"
            with open(manifest_file, "w") as f:
                json.dump(manifest, f, indent=2)

            logger.info(f"Overlap window pinned to {run_dir}")
            return str(run_dir)

        except Exception as e:
            logger.error(f"Error pinning overlap window: {e}")
            raise

    def _copy_venue_snapshot(self, venue: str, overlap_data: Dict, snapshot_dir: Path):
        """Copy parquet files for a venue that intersect the overlap window."""
        try:
            source_dir = Path("data/ticks") / venue / self.pair / self.freq

            if not source_dir.exists():
                logger.warning(f"No data directory for {venue}: {source_dir}")
                return

            # Parse overlap window
            start_dt = datetime.fromisoformat(overlap_data["startUTC"])
            end_dt = datetime.fromisoformat(overlap_data["endUTC"])

            # Find and copy relevant parquet files
            for date_dir in source_dir.iterdir():
                if not date_dir.is_dir():
                    continue

                for hour_dir in date_dir.iterdir():
                    if not hour_dir.is_dir():
                        continue

                    for parquet_file in hour_dir.glob("*.parquet"):
                        # Check if file intersects the window
                        if self._file_intersects_window(parquet_file, start_dt, end_dt):
                            # Copy file to snapshot
                            dest_file = snapshot_dir / parquet_file.name
                            shutil.copy2(parquet_file, dest_file)

        except Exception as e:
            logger.error(f"Error copying venue snapshot for {venue}: {e}")

    def _file_intersects_window(
        self, parquet_file: Path, start_dt: datetime, end_dt: datetime
    ) -> bool:
        """Check if a parquet file intersects the overlap window."""
        try:
            # Read a small sample to check timestamp range
            df = pd.read_parquet(parquet_file, nrows=10)
            if len(df) == 0:
                return False

            # Convert timestamps
            df["timestamp"] = pd.to_datetime(df["ts_local"], unit="ms")
            file_start = df["timestamp"].min()
            file_end = df["timestamp"].max()

            # Check intersection
            return not (file_end < start_dt or file_start > end_dt)

        except Exception:
            return False

    def _generate_gap_report(self, overlap_data: Dict, snapshot_dir: Path) -> Dict:
        """Generate detailed gap report for the overlap window."""
        try:
            gap_report = {
                "overlap_window": overlap_data,
                "venues": {},
                "stitches": {} if self.micro_gap_stitch else None,
                "policy_violations": [],
            }

            start_dt = datetime.fromisoformat(overlap_data["startUTC"])
            end_dt = datetime.fromisoformat(overlap_data["endUTC"])
            # window_seconds = (end_dt - start_dt).total_seconds()
            # Not used in current implementation

            for venue in overlap_data["venues"]:
                venue_dir = snapshot_dir / venue
                if not venue_dir.exists():
                    continue

                venue_gaps = self._analyze_venue_gaps(venue, venue_dir, start_dt, end_dt)
                gap_report["venues"][venue] = venue_gaps

                # Check for policy violations
                if venue_gaps["max_consecutive_gap"] > self.max_gap_s:
                    gap_report["policy_violations"].append(
                        {
                            "venue": venue,
                            "max_consecutive_gap": venue_gaps["max_consecutive_gap"],
                            "threshold": self.max_gap_s,
                        }
                    )

            return gap_report

        except Exception as e:
            logger.error(f"Error generating gap report: {e}")
            return {"error": str(e)}

    def _analyze_venue_gaps(
        self, venue: str, venue_dir: Path, start_dt: datetime, end_dt: datetime
    ) -> Dict:
        """Analyze gaps for a specific venue in the overlap window."""
        try:
            # Load all parquet files for the venue
            all_data = []
            for parquet_file in venue_dir.glob("*.parquet"):
                try:
                    df = pd.read_parquet(parquet_file)
                    if len(df) > 0:
                        df["timestamp"] = pd.to_datetime(df["ts_local"], unit="ms")
                        # Filter to overlap window
                        mask = (df["timestamp"] >= start_dt) & (df["timestamp"] <= end_dt)
                        window_data = df[mask]
                        if len(window_data) > 0:
                            all_data.append(window_data)
                except Exception as e:
                    logger.warning(f"Error reading {parquet_file}: {e}")
                    continue

            if not all_data:
                return {
                    "total_seconds": 0,
                    "missing_seconds": 0,
                    "max_consecutive_gap": 0,
                    "gap_ratio": 1.0,
                    "first_missing": None,
                    "last_missing": None,
                }

            # Combine all data
            combined_df = pd.concat(all_data, ignore_index=True)
            combined_df = combined_df.sort_values("timestamp")

            # Calculate gaps
            time_diffs = combined_df["timestamp"].diff().dt.total_seconds()
            gaps = time_diffs[time_diffs > self.max_gap_s]

            window_seconds = (end_dt - start_dt).total_seconds()
            missing_seconds = gaps.sum() if len(gaps) > 0 else 0
            max_consecutive_gap = gaps.max() if len(gaps) > 0 else 0

            return {
                "total_seconds": window_seconds,
                "missing_seconds": missing_seconds,
                "max_consecutive_gap": max_consecutive_gap,
                "gap_ratio": missing_seconds / window_seconds if window_seconds > 0 else 0,
                "first_missing": gaps.index[0] if len(gaps) > 0 else None,
                "last_missing": gaps.index[-1] if len(gaps) > 0 else None,
            }

        except Exception as e:
            logger.error(f"Error analyzing gaps for {venue}: {e}")
            return {"error": str(e)}

    def _create_run_manifest(self, overlap_data: Dict, run_dir: Path, gap_report: Dict) -> Dict:
        """Create run manifest with provenance information."""
        try:
            # Get git commit hash
            try:
                commit_hash = subprocess.check_output(
                    ["git", "rev-parse", "HEAD"], text=True
                ).strip()
            except Exception:
                commit_hash = "unknown"

            manifest = {
                "run_id": run_dir.name,
                "created_at": datetime.now().isoformat(),
                "git_commit": commit_hash,
                "overlap_policy": overlap_data["policy"],
                "overlap_window": {
                    "start": overlap_data["startUTC"],
                    "end": overlap_data["endUTC"],
                    "minutes": overlap_data["minutes"],
                    "venues": overlap_data["venues"],
                    "excluded": overlap_data.get("excluded", []),
                },
                "data_sources": {
                    venue: str(run_dir / "ticks" / venue) for venue in overlap_data["venues"]
                },
                "gap_report": gap_report,
                "micro_gap_stitch": self.micro_gap_stitch,
                "seeds": {"numpy": 42, "random": 42},
                "orchestrator_config": {
                    "pair": self.pair,
                    "freq": self.freq,
                    "quorum": self.quorum,
                    "max_gap_s": self.max_gap_s,
                    "min_minutes": self.min_minutes,
                    "policy_order": self.policy_order,
                },
            }

            return manifest

        except Exception as e:
            logger.error(f"Error creating run manifest: {e}")
            return {"error": str(e)}

    async def _capture_binance(self, session: aiohttp.ClientSession):
        """Capture data from Binance WebSocket."""
        venue = "binance"
        url = "wss://stream.binance.com:9443/ws/btcusdt@ticker"

        try:
            async with websockets.connect(url) as websocket:
                logger.info(f"Connected to {venue} WebSocket")

                while datetime.now() < self.capture_end:
                    try:
                        message = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                        data = json.loads(message)

                        # Extract tick data
                        ts_exchange = int(data.get("E", 0))  # Event time
                        ts_local = int(time.time() * 1000)  # Local timestamp
                        best_bid = float(data.get("b", 0))  # Best bid
                        best_ask = float(data.get("a", 0))  # Best ask
                        mid = (best_bid + best_ask) / 2 if best_bid and best_ask else 0
                        last_trade_px = float(data.get("c", 0))  # Last price
                        last_trade_qty = float(data.get("Q", 0))  # Last quantity

                        # Persist tick
                        await self._persist_tick(
                            venue,
                            self.pair,
                            ts_exchange,
                            ts_local,
                            best_bid,
                            best_ask,
                            mid,
                            last_trade_px,
                            last_trade_qty,
                            "ticker",
                        )

                        self.venue_stats[venue]["messages"] += 1
                        self.venue_stats[venue]["last_tick_exchange_ts"] = ts_exchange
                        self.venue_stats[venue]["last_tick_local_ts"] = ts_local

                    except asyncio.TimeoutError:
                        continue
                    except Exception as e:
                        logger.error(f"Error processing {venue} message: {e}")
                        continue

        except Exception as e:
            logger.error(f"Failed to connect to {venue}: {e}")

    async def _capture_coinbase(self, session: aiohttp.ClientSession):
        """Capture data from Coinbase WebSocket."""
        venue = "coinbase"
        url = "wss://ws-feed.exchange.coinbase.com"

        try:
            async with websockets.connect(url) as websocket:
                # Subscribe to ticker channel
                subscribe_msg = {
                    "type": "subscribe",
                    "product_ids": ["BTC-USD"],
                    "channels": ["ticker"],
                }
                await websocket.send(json.dumps(subscribe_msg))
                logger.info(f"Connected to {venue} WebSocket")

                while datetime.now() < self.capture_end:
                    try:
                        message = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                        data = json.loads(message)

                        if data.get("type") == "ticker":
                            ts_exchange = pd.to_datetime(data.get("time")).timestamp() * 1000
                            ts_local = int(time.time() * 1000)
                            best_bid = float(data.get("best_bid", 0))
                            best_ask = float(data.get("best_ask", 0))
                            mid = (best_bid + best_ask) / 2 if best_bid and best_ask else 0
                            last_trade_px = float(data.get("price", 0))
                            last_trade_qty = float(data.get("last_size", 0))

                            await self._persist_tick(
                                venue,
                                self.pair,
                                ts_exchange,
                                ts_local,
                                best_bid,
                                best_ask,
                                mid,
                                last_trade_px,
                                last_trade_qty,
                                "ticker",
                            )

                            self.venue_stats[venue]["messages"] += 1

                    except asyncio.TimeoutError:
                        continue
                    except Exception as e:
                        logger.error(f"Error processing {venue} message: {e}")
                        continue

        except Exception as e:
            logger.error(f"Failed to connect to {venue}: {e}")

    async def _capture_kraken(self, session: aiohttp.ClientSession):
        """Capture data from Kraken WebSocket."""
        venue = "kraken"
        url = "wss://ws.kraken.com/"

        try:
            async with websockets.connect(url) as websocket:
                # Subscribe to ticker
                subscribe_msg = {
                    "event": "subscribe",
                    "pair": ["XBT/USD"],
                    "subscription": {"name": "ticker"},
                }
                await websocket.send(json.dumps(subscribe_msg))
                logger.info(f"Connected to {venue} WebSocket")

                while datetime.now() < self.capture_end:
                    try:
                        message = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                        data = json.loads(message)

                        if isinstance(data, list) and len(data) > 1:
                            ticker_data = data[1]
                            if isinstance(ticker_data, dict) and "b" in ticker_data:
                                ts_exchange = int(
                                    time.time() * 1000
                                )  # Kraken doesn't provide event time
                                ts_local = int(time.time() * 1000)
                                best_bid = float(ticker_data.get("b", [0, 0])[0])
                                best_ask = float(ticker_data.get("a", [0, 0])[0])
                                mid = (best_bid + best_ask) / 2 if best_bid and best_ask else 0
                                last_trade_px = float(ticker_data.get("c", [0, 0])[0])
                                last_trade_qty = float(ticker_data.get("c", [0, 0])[1])

                                await self._persist_tick(
                                    venue,
                                    self.pair,
                                    ts_exchange,
                                    ts_local,
                                    best_bid,
                                    best_ask,
                                    mid,
                                    last_trade_px,
                                    last_trade_qty,
                                    "ticker",
                                )

                                self.venue_stats[venue]["messages"] += 1

                    except asyncio.TimeoutError:
                        continue
                    except Exception as e:
                        logger.error(f"Error processing {venue} message: {e}")
                        continue

        except Exception as e:
            logger.error(f"Failed to connect to {venue}: {e}")

    async def _capture_okx(self, session: aiohttp.ClientSession):
        """Capture data from OKX WebSocket."""
        venue = "okx"
        url = "wss://ws.okx.com:8443/ws/v5/public"

        try:
            async with websockets.connect(url) as websocket:
                # Subscribe to ticker
                subscribe_msg = {
                    "op": "subscribe",
                    "args": [{"channel": "tickers", "instId": "BTC-USDT"}],
                }
                await websocket.send(json.dumps(subscribe_msg))
                logger.info(f"Connected to {venue} WebSocket")

                while datetime.now() < self.capture_end:
                    try:
                        message = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                        data = json.loads(message)

                        if data.get("data"):
                            ticker_data = data["data"][0]
                            ts_exchange = int(ticker_data.get("ts", 0))
                            ts_local = int(time.time() * 1000)
                            best_bid = float(ticker_data.get("bidPx", 0))
                            best_ask = float(ticker_data.get("askPx", 0))
                            mid = (best_bid + best_ask) / 2 if best_bid and best_ask else 0
                            last_trade_px = float(ticker_data.get("last", 0))
                            last_trade_qty = float(ticker_data.get("lastSz", 0))

                            await self._persist_tick(
                                venue,
                                self.pair,
                                ts_exchange,
                                ts_local,
                                best_bid,
                                best_ask,
                                mid,
                                last_trade_px,
                                last_trade_qty,
                                "ticker",
                            )

                            self.venue_stats[venue]["messages"] += 1

                    except asyncio.TimeoutError:
                        continue
                    except Exception as e:
                        logger.error(f"Error processing {venue} message: {e}")
                        continue

        except Exception as e:
            logger.error(f"Failed to connect to {venue}: {e}")

    async def _capture_bybit(self, session: aiohttp.ClientSession):
        """Capture data from Bybit WebSocket."""
        venue = "bybit"
        url = "wss://stream.bybit.com/v5/public/spot"

        try:
            async with websockets.connect(url) as websocket:
                # Subscribe to ticker
                subscribe_msg = {"op": "subscribe", "args": ["tickers.BTCUSDT"]}
                await websocket.send(json.dumps(subscribe_msg))
                logger.info(f"Connected to {venue} WebSocket")

                while datetime.now() < self.capture_end:
                    try:
                        message = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                        data = json.loads(message)

                        if data.get("topic") == "tickers.BTCUSDT" and data.get("data"):
                            ticker_data = data["data"]
                            ts_exchange = int(ticker_data.get("ts", 0))
                            ts_local = int(time.time() * 1000)
                            best_bid = float(ticker_data.get("bid1Price", 0))
                            best_ask = float(ticker_data.get("ask1Price", 0))
                            mid = (best_bid + best_ask) / 2 if best_bid and best_ask else 0
                            last_trade_px = float(ticker_data.get("lastPrice", 0))
                            last_trade_qty = float(ticker_data.get("lastSize", 0))

                            await self._persist_tick(
                                venue,
                                self.pair,
                                ts_exchange,
                                ts_local,
                                best_bid,
                                best_ask,
                                mid,
                                last_trade_px,
                                last_trade_qty,
                                "ticker",
                            )

                            self.venue_stats[venue]["messages"] += 1

                    except asyncio.TimeoutError:
                        continue
                    except Exception as e:
                        logger.error(f"Error processing {venue} message: {e}")
                        continue

        except Exception as e:
            logger.error(f"Failed to connect to {venue}: {e}")

    async def _persist_tick(
        self,
        exchange: str,
        pair: str,
        ts_exchange: int,
        ts_local: int,
        best_bid: float,
        best_ask: float,
        mid: float,
        last_trade_px: float,
        last_trade_qty: float,
        event_type: str,
    ):
        """Persist normalized tick data to parquet partitions."""
        try:
            # Create directory structure: data/ticks/<exchange>/<pair>/1s/<YYYY-MM-DD>/<HH>/
            dt = datetime.fromtimestamp(ts_local / 1000)
            date_str = dt.strftime("%Y-%m-%d")
            hour_str = dt.strftime("%H")

            base_dir = Path("data/ticks") / exchange / pair / "1s" / date_str / hour_str
            base_dir.mkdir(parents=True, exist_ok=True)

            # Create tick row
            tick_data = {
                "exchange": exchange,
                "pair": pair,
                "ts_exchange": ts_exchange,
                "ts_local": ts_local,
                "best_bid": best_bid,
                "best_ask": best_ask,
                "mid": mid,
                "last_trade_px": last_trade_px,
                "last_trade_qty": last_trade_qty,
                "event_type": event_type,
            }

            # Append to parquet file (create new file every minute for efficiency)
            minute_str = dt.strftime("%M")
            file_path = base_dir / f"ticks_{minute_str}.parquet"

            df = pd.DataFrame([tick_data])
            if file_path.exists():
                existing_df = pd.read_parquet(file_path)
                df = pd.concat([existing_df, df], ignore_index=True)

            df.to_parquet(file_path, index=False)

        except Exception as e:
            logger.error(f"Error persisting tick for {exchange}: {e}")

    async def _heartbeat_monitor(self):
        """Emit heartbeats at configured interval."""
        while datetime.now() < self.capture_end:
            await asyncio.sleep(self.heartbeat_interval)

            for venue, stats in self.venue_stats.items():
                lag_ms = int(time.time() * 1000) - stats.get(
                    "last_timestamp", int(time.time() * 1000)
                )
                heartbeat = {
                    "venue": venue,
                    "ts_local": datetime.now().isoformat(),
                    "lag_ms": lag_ms,
                    "msgs": stats["messages"],
                }
                print(f"[CAPTURE:hb] {json.dumps(heartbeat)}")
                logger.info(f"Heartbeat for {venue}: {heartbeat}")

                # Write to CSV
                self._write_heartbeat()

                # Check clock skew
                self._check_clock_skew()

                # Write status
                self._write_status()

    async def _overlap_monitor(self):
        """Monitor for strict overlap windows."""
        while datetime.now() < self.capture_end:
            await asyncio.sleep(self.check_interval)

            try:
                # Import overlap finder
                sys.path.append("src")
                from acdlib.io.overlap import find_real_overlap_rolling

                # Check for overlap
                result = find_real_overlap_rolling(
                    self.venues,
                    self.pair,
                    freq=self.freq,
                    max_gap_s=self.max_gap_s,
                    min_minutes=self.min_minutes,
                    quorum=self.quorum,
                )

                if result:
                    start, end, venues_used, policy = result

                    # Create overlap data
                    overlap_data = {
                        "startUTC": start.isoformat(),
                        "endUTC": end.isoformat(),
                        "minutes": (end - start).total_seconds() / 60,
                        "venues": venues_used,
                        "excluded": [v for v in self.venues if v not in venues_used],
                        "policy": policy,
                    }

                    # Pin the overlap window and create snapshot
                    run_dir = self._pin_overlap_window(overlap_data)

                    # Log the found overlap
                    self._log_overlap_event("FOUND", overlap_data)
                    logger.info(f"Overlap found: {policy} with {len(venues_used)} venues")

                    # Trigger auto-analysis on the snapshot
                    await self._run_auto_analysis_on_snapshot(run_dir)
                    return True  # Signal to stop capture and run analysis

            except Exception as e:
                logger.error(f"Error in overlap monitoring: {e}")
                continue

        # No overlap found after 3 hours
        overlap_status = {
            "quorum": 4,
            "minutes_max": 0,
            "venues_ready": [],
            "venues_missing": self.venues,
        }

        with open(f"{self.export_dir}/overlap_status.json", "w") as f:
            json.dump(overlap_status, f, indent=2)

        print(f"[OVERLAP:INSUFFICIENT] {json.dumps(overlap_status)}")
        logger.error("No overlap found after 3 hours")
        return False

    async def _run_auto_analysis_on_snapshot(self, run_dir: str):
        """Run auto-analysis on the snapshot data."""
        logger.info(f"Starting auto-analysis on snapshot: {run_dir}")

        try:
            # Run the auto-analysis script on the snapshot
            cmd = [
                "python",
                "scripts/run_auto_microstructure.py",
                "--pair",
                self.pair,
                "--use-overlap-json",
                f"{run_dir}/OVERLAP.json",
                "--export-dir",
                f"{run_dir}/evidence",
                "--verbose",
            ]

            subprocess.run(cmd, capture_output=True, text=True, check=True)

            logger.info("Auto-analysis completed successfully")
            print(f"Auto-analysis completed - check {run_dir}/evidence/ for results")

        except subprocess.CalledProcessError as e:
            logger.error(f"Auto-analysis failed: {e}")
            logger.error(f"stdout: {e.stdout}")
            logger.error(f"stderr: {e.stderr}")
            # Log the abort
            self._log_overlap_event(
                "ABORT", {"reason": "auto_analysis_failed", "error": str(e), "run_dir": run_dir}
            )
            raise

    async def run(self):
        """Run the capture orchestrator."""
        logger.info(f"Starting overlap orchestrator for {self.pair}")
        logger.info(f"Capture window: {self.capture_start} to {self.capture_end}")

        async with aiohttp.ClientSession() as session:
            # Start all capture tasks
            tasks = [
                self._capture_binance(session),
                self._capture_coinbase(session),
                self._capture_kraken(session),
                self._capture_okx(session),
                self._capture_bybit(session),
                self._heartbeat_monitor(),
                self._overlap_monitor(),
            ]

            # Wait for overlap or timeout
            overlap_found = await asyncio.gather(*tasks, return_exceptions=True)

            # Check if overlap was found
            if any(isinstance(result, bool) and result for result in overlap_found):
                logger.info("Overlap found - stopping capture")
                return True
            else:
                logger.error("No overlap found - capture timeout")
                return False


async def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="ACD Overlap Orchestrator")
    parser.add_argument("--pair", default="BTC-USD", help="Trading pair")
    parser.add_argument("--freq", default="1s", help="Data frequency")
    parser.add_argument("--quorum", type=int, default=4, help="Minimum venues required")
    parser.add_argument(
        "--min-minutes", default="30,20,10", help="Minimum minutes (comma-separated)"
    )
    parser.add_argument(
        "--policy-order", default="BEST4_30m,BEST4_20m,BEST4_10m,ALL5_10m", help="Policy order"
    )
    parser.add_argument("--max-gap-s", type=float, default=1.0, help="Maximum gap in seconds")
    parser.add_argument("--export-dir", default="exports", help="Export directory")
    parser.add_argument("--heartbeat-s", type=int, default=5, help="Heartbeat interval in seconds")
    parser.add_argument(
        "--check-interval-s", type=int, default=30, help="Overlap check interval in seconds"
    )
    parser.add_argument(
        "--micro-gap-stitch", action="store_true", help="Enable micro-gap stitching"
    )
    parser.add_argument("--verbose", action="store_true", help="Verbose logging")

    args = parser.parse_args()

    # Setup logging
    logging.basicConfig(
        level=logging.INFO if args.verbose else logging.WARNING,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    # Parse min-minutes and policy-order
    min_minutes = [int(x) for x in args.min_minutes.split(",")]
    policy_order = args.policy_order.split(",")

    orchestrator = OverlapOrchestrator(
        pair=args.pair,
        export_dir=args.export_dir,
        freq=args.freq,
        quorum=args.quorum,
        min_minutes=min_minutes,
        policy_order=policy_order,
        max_gap_s=args.max_gap_s,
        heartbeat_interval=args.heartbeat_s,
        check_interval=args.check_interval_s,
        micro_gap_stitch=args.micro_gap_stitch,
    )
    overlap_found = await orchestrator.run()

    if overlap_found:
        print("Overlap found - ready for analysis")
        sys.exit(0)
    else:
        print("No overlap found - insufficient data")
        sys.exit(2)


if __name__ == "__main__":
    asyncio.run(main())
