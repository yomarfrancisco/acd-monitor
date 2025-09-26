"""
Real-time overlap orchestrator for ACD analysis.
Continuously captures data from all 5 venues and monitors for strict overlap windows.
"""

import asyncio
import websockets
import aiohttp
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import json
import logging
import os
import time
from typing import Dict, List, Optional, Tuple
import sys
from pathlib import Path

logger = logging.getLogger(__name__)


class OverlapOrchestrator:
    """Real-time capture orchestrator with strict overlap monitoring."""

    def __init__(self, pair: str = "BTC-USD", export_dir: str = "exports"):
        self.pair = pair
        self.export_dir = export_dir
        self.venues = ["binance", "coinbase", "kraken", "okx", "bybit"]
        self.capture_start = datetime.now()
        self.capture_duration = timedelta(hours=3)
        self.capture_end = self.capture_start + self.capture_duration

        # Message tracking per venue
        self.venue_stats = {
            venue: {"messages": 0, "last_heartbeat": None, "lag_ms": 0} for venue in self.venues
        }

        # Clock state
        self.clock_offset_ms = None
        self._record_clock_state()

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
        """Emit heartbeats every 5 seconds."""
        while datetime.now() < self.capture_end:
            await asyncio.sleep(5)

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

    async def _overlap_monitor(self):
        """Monitor for strict overlap windows."""
        while datetime.now() < self.capture_end:
            await asyncio.sleep(30)  # Check every 30 seconds

            try:
                # Import overlap finder
                sys.path.append("src")
                from acdlib.io.overlap import find_real_overlap_rolling

                # Check for overlap
                result = find_real_overlap_rolling(
                    self.venues,
                    self.pair,
                    freq="1s",
                    max_gap_s=1,
                    min_minutes=[30, 20, 10],
                    quorum=4,
                )

                if result:
                    start, end, venues_used, policy = result

                    # Write overlap.json
                    overlap_data = {
                        "startUTC": start.isoformat(),
                        "endUTC": end.isoformat(),
                        "minutes": (end - start).total_seconds() / 60,
                        "venues": venues_used,
                        "excluded": [v for v in self.venues if v not in venues_used],
                        "policy": policy,
                    }

                    with open(f"{self.export_dir}/overlap.json", "w") as f:
                        json.dump(overlap_data, f, indent=2)

                    logger.info(f"Overlap found: {policy} with {len(venues_used)} venues")
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
    parser.add_argument("--export-dir", default="exports", help="Export directory")
    parser.add_argument("--verbose", action="store_true", help="Verbose logging")

    args = parser.parse_args()

    # Setup logging
    logging.basicConfig(
        level=logging.INFO if args.verbose else logging.WARNING,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    orchestrator = OverlapOrchestrator(args.pair, args.export_dir)
    overlap_found = await orchestrator.run()

    if overlap_found:
        print("Overlap found - ready for analysis")
        sys.exit(0)
    else:
        print("No overlap found - insufficient data")
        sys.exit(2)


if __name__ == "__main__":
    asyncio.run(main())
