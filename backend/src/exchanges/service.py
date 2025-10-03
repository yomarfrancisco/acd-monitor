"""
Exchange Service

Thin service layer for aggregating exchange data.
"""

import asyncio
import logging
import os
from datetime import datetime, timedelta, timezone
from typing import Dict

import aiohttp

from . import bybit, kraken, okx
from .binance import get_binance_api

logger = logging.getLogger(__name__)


class ExchangeService:
    """Service for fetching and aggregating exchange data."""

    def __init__(self):
        pass

    async def fetch_overview(self, symbol: str = "BTCUSDT", tf: str = "5m") -> Dict:
        """
        Fetch overview data for a symbol from Binance.

        Args:
            symbol: Trading symbol (e.g., "BTCUSDT")
            tf: Timeframe (e.g., "5m")

        Returns:
            {
                "venue": "binance",
                "symbol": "BTCUSDT",
                "asOf": "2024-01-01T00:00:00Z",
                "ticker": {"bid": 50000.0, "ask": 50001.0, "mid": 50000.5},
                "ohlcv": [[iso, o, h, l, c, v], ...]
            }
        """
        try:
            logger.info(f"🔍 fetch_overview called: symbol={symbol}, tf={tf}")
            api = await get_binance_api()

            # Fetch ticker and OHLCV data concurrently
            logger.info(f"📡 Starting concurrent fetch for {symbol}")
            ticker_task = api.get_book_ticker(symbol)

            # Get last 24 hours of 5m bars
            end_time = datetime.now(timezone.utc)
            start_time = end_time - timedelta(hours=24)
            start_ms = int(start_time.timestamp() * 1000)
            end_ms = int(end_time.timestamp() * 1000)

            logger.info(f"⏰ Time range: {start_time.isoformat()} to {end_time.isoformat()}")
            logger.info(f"⏰ MS range: {start_ms} to {end_ms}")

            ohlcv_task = api.get_ohlcv(symbol, tf, start_ms, end_ms)

            # Wait for both requests
            logger.info("⏳ Waiting for ticker and OHLCV data...")
            ticker_data, ohlcv_data = await asyncio.gather(ticker_task, ohlcv_task)

            logger.info(f"✅ Ticker data received: {ticker_data}")
            logger.info(f"✅ OHLCV data received: {len(ohlcv_data)} bars")

            if ohlcv_data:
                logger.info(f"📊 First OHLCV bar: {ohlcv_data[0]}")
                logger.info(f"📊 Last OHLCV bar: {ohlcv_data[-1]}")
            else:
                logger.warning("⚠️ OHLCV data is empty!")

            result = {
                "venue": "binance",
                "symbol": symbol,
                "asOf": datetime.now(timezone.utc).isoformat(),
                "ticker": ticker_data,
                "ohlcv": ohlcv_data,
            }

            logger.info(f"🎯 Returning overview with {len(ohlcv_data)} OHLCV bars")
            return result

        except ValueError as ve:
            # Handle specific Binance errors
            error_msg = str(ve)
            if error_msg == "binance_no_ohlcv":
                logger.error(f"No OHLCV data available for {symbol}")
                raise ValueError("binance_no_ohlcv")
            elif error_msg == "binance_invalid_symbol":
                logger.error(f"Invalid symbol {symbol}")
                raise ValueError("binance_invalid_symbol")
            else:
                logger.error(f"Binance error for {symbol}: {error_msg}")
                raise ve
        except Exception as e:
            logger.error(f"Failed to fetch overview for {symbol}: {e}")
            raise

    async def fetch_depth(self, symbol: str = "BTCUSDT", limit: int = 10) -> Dict:
        """
        Fetch order book depth for a symbol.

        Args:
            symbol: Trading symbol
            limit: Number of price levels to fetch

        Returns:
            {
                "venue": "binance",
                "symbol": "BTCUSDT",
                "asOf": "2024-01-01T00:00:00Z",
                "depth": {"bids": [[price, qty], ...], "asks": [[price, qty], ...]}
            }
        """
        try:
            api = await get_binance_api()
            depth_data = await api.get_depth(symbol, limit)

            return {
                "venue": "binance",
                "symbol": symbol,
                "asOf": datetime.now(timezone.utc).isoformat(),
                "depth": {"bids": depth_data["bids"], "asks": depth_data["asks"]},
            }

        except Exception as e:
            logger.error(f"Failed to fetch depth for {symbol}: {e}")
            raise

    async def fetch_overview_multi(
        self, venue: str, symbol: str = "BTCUSDT", tf: str = "5m"
    ) -> Dict:
        """
        Fetch overview data for a symbol from any supported exchange.

        Args:
            venue: Exchange name ("kraken", "okx", "bybit")
            symbol: Trading symbol (e.g., "BTCUSDT")
            tf: Timeframe (e.g., "5m")

        Returns:
            Unified exchange overview format
        """
        try:
            proxy_base = os.getenv("CRYPTO_PROXY_BASE")
            logger.info(
                f"🔍 fetch_overview_multi: venue={venue}, symbol={symbol}, "
                f"tf={tf}, proxy={proxy_base}"
            )

            async with aiohttp.ClientSession() as session:
                if venue == "kraken":
                    # Map BTCUSDT -> XBTUSDT for Kraken
                    pair = symbol.replace("BTC", "XBT") if symbol.startswith("BTC") else symbol
                    ticker_data, ohlcv_data = await asyncio.gather(
                        kraken.fetch_ticker(session, pair, proxy_base),
                        kraken.fetch_ohlcv(session, pair, tf, proxy_base),
                    )
                elif venue == "okx":
                    # Map BTCUSDT -> BTC-USDT for OKX
                    inst_id = symbol.replace("USDT", "-USDT").replace("USD", "-USD")
                    ticker_data, ohlcv_data = await asyncio.gather(
                        okx.fetch_ticker(session, inst_id, proxy_base),
                        okx.fetch_ohlcv(session, inst_id, tf, proxy_base),
                    )
                elif venue == "bybit":
                    # Bybit uses same symbol format
                    ticker_data, ohlcv_data = await asyncio.gather(
                        bybit.fetch_ticker(session, symbol, proxy_base),
                        bybit.fetch_ohlcv(session, symbol, tf, proxy_base),
                    )
                else:
                    raise ValueError(f"Unsupported venue: {venue}")

                result = {
                    "venue": venue,
                    "symbol": symbol,
                    "asOf": datetime.now(timezone.utc).isoformat(),
                    "ticker": ticker_data,
                    "ohlcv": ohlcv_data,
                }

                logger.info(
                    f"✅ {venue} overview: {len(ohlcv_data)} bars, "
                    f"mid=${ticker_data.get('mid', 0):.2f}"
                )
                return result

        except Exception as e:
            logger.error(f"Failed to fetch {venue} overview for {symbol}: {e}")
            raise

    async def ping_binance(self) -> bool:
        """
        Health check for Binance API.

        Returns:
            bool: True if Binance is reachable
        """
        try:
            api = await get_binance_api()
            return await api.ping()
        except Exception as e:
            logger.warning(f"Binance health check failed: {e}")
            return False


# Global service instance
_exchange_service = None


def get_exchange_service() -> ExchangeService:
    """Get or create global exchange service instance."""
    global _exchange_service
    if _exchange_service is None:
        _exchange_service = ExchangeService()
    return _exchange_service
