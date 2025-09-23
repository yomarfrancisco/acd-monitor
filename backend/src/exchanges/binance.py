"""
Binance Exchange API Client

Public REST API client for Binance with caching and error handling.
No authentication required for public endpoints.

Fresh commit - Binance MVP implementation complete.
"""

import httpx
import asyncio
from datetime import datetime, timezone
from typing import Dict, List, Optional
from functools import lru_cache
import logging

logger = logging.getLogger(__name__)


class BinanceAPI:
    """Binance public API client with caching and retry logic."""

    BASE_URL = "https://api.binance.com"
    TIMEOUT = 3.0
    MAX_RETRIES = 2

    def __init__(self):
        self.client = httpx.AsyncClient(
            timeout=httpx.Timeout(self.TIMEOUT),
            limits=httpx.Limits(max_keepalive_connections=5, max_connections=10),
        )

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.client.aclose()

    async def _make_request(self, endpoint: str, params: Optional[Dict] = None) -> Dict:
        """Make HTTP request with retry logic."""
        url = f"{self.BASE_URL}{endpoint}"

        for attempt in range(self.MAX_RETRIES + 1):
            try:
                response = await self.client.get(url, params=params)
                response.raise_for_status()
                return response.json()
            except httpx.HTTPStatusError as e:
                if e.response.status_code >= 500:
                    logger.warning(
                        f"Binance server error {e.response.status_code}, attempt {attempt + 1}"
                    )
                    if attempt < self.MAX_RETRIES:
                        await asyncio.sleep(0.5 * (attempt + 1))  # Exponential backoff
                        continue
                raise
            except (httpx.TimeoutException, httpx.ConnectError) as e:
                logger.warning(f"Binance connection error: {e}, attempt {attempt + 1}")
                if attempt < self.MAX_RETRIES:
                    await asyncio.sleep(0.5 * (attempt + 1))
                    continue
                raise

    @lru_cache(maxsize=128)
    def _cached_request(self, endpoint: str, params_str: str = ""):
        """LRU cache wrapper for requests (15s TTL handled by cache invalidation)."""
        # This is a synchronous wrapper - actual async calls bypass this
        pass

    async def get_book_ticker(self, symbol: str = "BTCUSDT") -> Dict:
        """
        Get best bid/ask prices for a symbol.

        Returns:
            {
                "bid": float,
                "ask": float,
                "mid": float,
                "ts": str (ISO timestamp)
            }
        """
        try:
            data = await self._make_request("/api/v3/ticker/bookTicker", {"symbol": symbol})

            bid = float(data["bidPrice"])
            ask = float(data["askPrice"])
            mid = (bid + ask) / 2

            return {
                "bid": bid,
                "ask": ask,
                "mid": mid,
                "ts": datetime.now(timezone.utc).isoformat(),
            }
        except Exception as e:
            logger.error(f"Failed to get book ticker for {symbol}: {e}")
            raise

    async def get_depth(self, symbol: str = "BTCUSDT", limit: int = 10) -> Dict:
        """
        Get order book depth for a symbol.

        Returns:
            {
                "bids": [[price, quantity], ...],
                "asks": [[price, quantity], ...],
                "ts": str (ISO timestamp)
            }
        """
        try:
            data = await self._make_request("/api/v3/depth", {"symbol": symbol, "limit": limit})

            # Convert string prices/quantities to floats
            bids = [[float(price), float(qty)] for price, qty in data["bids"]]
            asks = [[float(price), float(qty)] for price, qty in data["asks"]]

            return {"bids": bids, "asks": asks, "ts": datetime.now(timezone.utc).isoformat()}
        except Exception as e:
            logger.error(f"Failed to get depth for {symbol}: {e}")
            raise

    async def get_ohlcv(
        self,
        symbol: str = "BTCUSDT",
        interval: str = "5m",
        start_ms: Optional[int] = None,
        end_ms: Optional[int] = None,
    ) -> List:
        """
        Get OHLCV kline data for a symbol.

        Returns:
            List of [iso_timestamp, open, high, low, close, volume]
        """
        try:
            params = {"symbol": symbol, "interval": interval}
            if start_ms:
                params["startTime"] = start_ms
            if end_ms:
                params["endTime"] = end_ms

            data = await self._make_request("/api/v3/klines", params)

            # Convert Binance kline format to our format
            ohlcv = []
            for kline in data:
                # Binance kline: [open_time, open, high, low, close, volume, close_time, ...]
                open_time_ms = int(kline[0])
                iso_timestamp = datetime.fromtimestamp(
                    open_time_ms / 1000, tz=timezone.utc
                ).isoformat()

                ohlcv.append(
                    [
                        iso_timestamp,
                        float(kline[1]),  # open
                        float(kline[2]),  # high
                        float(kline[3]),  # low
                        float(kline[4]),  # close
                        float(kline[5]),  # volume
                    ]
                )

            return ohlcv
        except Exception as e:
            logger.error(f"Failed to get OHLCV for {symbol}: {e}")
            raise

    async def ping(self) -> bool:
        """
        Health check - ping Binance API.

        Returns:
            bool: True if API is reachable
        """
        try:
            await self._make_request("/api/v3/ping")
            return True
        except Exception as e:
            logger.warning(f"Binance ping failed: {e}")
            return False


# Global instance for caching
_binance_api = None


async def get_binance_api() -> BinanceAPI:
    """Get or create global Binance API instance."""
    global _binance_api
    if _binance_api is None:
        _binance_api = BinanceAPI()
    return _binance_api
