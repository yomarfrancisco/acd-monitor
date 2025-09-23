"""
Exchange Service

Thin service layer for aggregating exchange data.
"""

import asyncio
from datetime import datetime, timezone, timedelta
from typing import Dict
import logging

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
            api = await get_binance_api()

            # Fetch ticker and OHLCV data concurrently
            ticker_task = api.get_book_ticker(symbol)

            # Get last 24 hours of 5m bars
            end_time = datetime.now(timezone.utc)
            start_time = end_time - timedelta(hours=24)
            start_ms = int(start_time.timestamp() * 1000)
            end_ms = int(end_time.timestamp() * 1000)

            ohlcv_task = api.get_ohlcv(symbol, tf, start_ms, end_ms)

            # Wait for both requests
            ticker_data, ohlcv_data = await asyncio.gather(ticker_task, ohlcv_task)

            return {
                "venue": "binance",
                "symbol": symbol,
                "asOf": datetime.now(timezone.utc).isoformat(),
                "ticker": ticker_data,
                "ohlcv": ohlcv_data,
            }

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
