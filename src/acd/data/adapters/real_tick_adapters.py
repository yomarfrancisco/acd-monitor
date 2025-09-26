"""
Real tick data adapters for cryptocurrency exchanges.

This module provides adapters for fetching real tick/trade data from:
- Binance
- Coinbase 
- Kraken
- OKX
- Bybit

Each adapter standardizes data to schema: [timestamp, price, volume, venue]
"""

import logging
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List
import requests
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)


class RealTickAdapter(ABC):
    """Abstract base class for real tick data adapters."""

    def __init__(self, venue: str, pair: str = "BTC-USD"):
        self.venue = venue
        self.pair = pair
        self.base_url = self._get_base_url()

    @abstractmethod
    def _get_base_url(self) -> str:
        """Get the base API URL for the venue."""
        pass

    @abstractmethod
    def _get_trades_endpoint(self) -> str:
        """Get the trades endpoint for the venue."""
        pass

    @abstractmethod
    def _parse_trade_data(self, raw_data: List[Dict]) -> pd.DataFrame:
        """Parse raw trade data into standardized DataFrame."""
        pass

    def fetch_trades(
        self, start_time: datetime, end_time: datetime, limit: int = 1000
    ) -> pd.DataFrame:
        """
        Fetch trades for the specified time range.

        Args:
            start_time: Start datetime (UTC)
            end_time: End datetime (UTC)
            limit: Maximum number of trades per request

        Returns:
            DataFrame with columns: [timestamp, price, volume, venue]
        """
        try:
            # Convert to venue-specific timestamp format
            start_ts = int(start_time.timestamp() * 1000)  # milliseconds
            end_ts = int(end_time.timestamp() * 1000)

            # Fetch data from venue API
            raw_data = self._fetch_raw_trades(start_ts, end_ts, limit)

            if not raw_data:
                logger.warning(f"No trade data found for {self.venue} {self.pair}")
                return pd.DataFrame(columns=["timestamp", "price", "volume", "venue"])

            # Parse and standardize
            df = self._parse_trade_data(raw_data)
            df["venue"] = self.venue

            logger.info(f"Fetched {len(df)} trades for {self.venue} {self.pair}")
            return df

        except Exception as e:
            logger.error(f"Error fetching trades from {self.venue}: {e}")
            return pd.DataFrame(columns=["timestamp", "price", "volume", "venue"])

    def _fetch_raw_trades(self, start_ts: int, end_ts: int, limit: int) -> List[Dict]:
        """Fetch raw trade data from venue API."""
        try:
            url = self._get_trades_endpoint()
            params = self._get_trades_params(start_ts, end_ts, limit)

            response = requests.get(url, params=params, timeout=30)
            response.raise_for_status()

            return response.json()

        except Exception as e:
            logger.error(f"API request failed for {self.venue}: {e}")
            return []

    @abstractmethod
    def _get_trades_params(self, start_ts: int, end_ts: int, limit: int) -> Dict:
        """Get API parameters for trades request."""
        pass


class BinanceTickAdapter(RealTickAdapter):
    """Binance tick data adapter."""

    def _get_base_url(self) -> str:
        return "https://api.binance.com"

    def _get_trades_endpoint(self) -> str:
        return f"{self.base_url}/api/v3/aggTrades"

    def _get_trades_params(self, start_ts: int, end_ts: int, limit: int) -> Dict:
        return {
            "symbol": "BTCUSDT",
            "startTime": start_ts,
            "endTime": end_ts,
            "limit": min(limit, 1000),
        }

    def _parse_trade_data(self, raw_data: List[Dict]) -> pd.DataFrame:
        """Parse Binance aggregate trades data."""
        trades = []
        for trade in raw_data:
            trades.append(
                {
                    "timestamp": pd.to_datetime(trade["T"], unit="ms"),
                    "price": float(trade["p"]),
                    "volume": float(trade["q"]),
                }
            )

        return pd.DataFrame(trades)


class CoinbaseTickAdapter(RealTickAdapter):
    """Coinbase tick data adapter."""

    def _get_base_url(self) -> str:
        return "https://api.exchange.coinbase.com"

    def _get_trades_endpoint(self) -> str:
        return f"{self.base_url}/products/BTC-USD/trades"

    def _get_trades_params(self, start_ts: int, end_ts: int, limit: int) -> Dict:
        return {"start": str(start_ts), "end": str(end_ts), "limit": min(limit, 1000)}

    def _parse_trade_data(self, raw_data: List[Dict]) -> pd.DataFrame:
        """Parse Coinbase trades data."""
        trades = []
        for trade in raw_data:
            trades.append(
                {
                    "timestamp": pd.to_datetime(trade["time"]),
                    "price": float(trade["price"]),
                    "volume": float(trade["size"]),
                }
            )

        return pd.DataFrame(trades)


class KrakenTickAdapter(RealTickAdapter):
    """Kraken tick data adapter."""

    def _get_base_url(self) -> str:
        return "https://api.kraken.com"

    def _get_trades_endpoint(self) -> str:
        return f"{self.base_url}/0/public/Trades"

    def _get_trades_params(self, start_ts: int, end_ts: int, limit: int) -> Dict:
        return {
            "pair": "XXBTZUSD",
            "since": start_ts // 1000,  # Kraken uses seconds
            "count": min(limit, 1000),
        }

    def _parse_trade_data(self, raw_data: List[Dict]) -> pd.DataFrame:
        """Parse Kraken trades data."""
        trades = []
        if "result" in raw_data and "XXBTZUSD" in raw_data["result"]:
            trade_list = raw_data["result"]["XXBTZUSD"]
            for trade in trade_list:
                trades.append(
                    {
                        "timestamp": pd.to_datetime(trade[2], unit="s"),
                        "price": float(trade[0]),
                        "volume": float(trade[1]),
                    }
                )

        return pd.DataFrame(trades)


class OKXTickAdapter(RealTickAdapter):
    """OKX tick data adapter."""

    def _get_base_url(self) -> str:
        return "https://www.okx.com"

    def _get_trades_endpoint(self) -> str:
        return f"{self.base_url}/api/v5/market/history-trades"

    def _get_trades_params(self, start_ts: int, end_ts: int, limit: int) -> Dict:
        return {
            "instId": "BTC-USDT",
            "before": str(end_ts),
            "after": str(start_ts),
            "limit": min(limit, 1000),
        }

    def _parse_trade_data(self, raw_data: List[Dict]) -> pd.DataFrame:
        """Parse OKX trades data."""
        trades = []
        if "data" in raw_data:
            for trade in raw_data["data"]:
                trades.append(
                    {
                        "timestamp": pd.to_datetime(trade["ts"], unit="ms"),
                        "price": float(trade["px"]),
                        "volume": float(trade["sz"]),
                    }
                )

        return pd.DataFrame(trades)


class BybitTickAdapter(RealTickAdapter):
    """Bybit tick data adapter."""

    def _get_base_url(self) -> str:
        return "https://api.bybit.com"

    def _get_trades_endpoint(self) -> str:
        return f"{self.base_url}/v5/market/recent-trade"

    def _get_trades_params(self, start_ts: int, end_ts: int, limit: int) -> Dict:
        return {"category": "spot", "symbol": "BTCUSDT", "limit": min(limit, 1000)}

    def _parse_trade_data(self, raw_data: List[Dict]) -> pd.DataFrame:
        """Parse Bybit trades data."""
        trades = []
        if "result" in raw_data and "list" in raw_data["result"]:
            for trade in raw_data["result"]["list"]:
                trades.append(
                    {
                        "timestamp": pd.to_datetime(trade["time"], unit="ms"),
                        "price": float(trade["price"]),
                        "volume": float(trade["size"]),
                    }
                )

        return pd.DataFrame(trades)


def create_tick_adapter(venue: str, pair: str = "BTC-USD") -> RealTickAdapter:
    """Factory function to create tick adapters."""
    adapters = {
        "binance": BinanceTickAdapter,
        "coinbase": CoinbaseTickAdapter,
        "kraken": KrakenTickAdapter,
        "okx": OKXTickAdapter,
        "bybit": BybitTickAdapter,
    }

    if venue.lower() not in adapters:
        raise ValueError(f"Unsupported venue: {venue}")

    return adapters[venue.lower()](venue, pair)


def fetch_real_tick_data(
    venues: List[str],
    pair: str,
    start_time: datetime,
    end_time: datetime,
    cache_dir: str = "data/cache",
) -> Dict[str, pd.DataFrame]:
    """
    Fetch real tick data for multiple venues.

    Args:
        venues: List of venue names
        pair: Trading pair (e.g., "BTC-USD")
        start_time: Start datetime (UTC)
        end_time: End datetime (UTC)
        cache_dir: Cache directory for storing data

    Returns:
        Dictionary mapping venue names to DataFrames
    """
    from acd.data.cache import DataCache

    cache = DataCache(cache_dir)
    venue_data = {}

    for venue in venues:
        try:
            logger.info(f"Fetching real tick data for {venue} {pair}")

            # Create adapter
            adapter = create_tick_adapter(venue, pair)

            # Fetch data
            df = adapter.fetch_trades(start_time, end_time)

            if len(df) > 0:
                # Cache the data
                cache.put(
                    venue=venue,
                    pair=pair,
                    frequency="1s",
                    df=df,
                    metadata={"source": "real_tick_data", "venue": venue},
                )

                venue_data[venue] = df
                logger.info(f"Successfully cached {len(df)} ticks for {venue}")
            else:
                logger.warning(f"No data retrieved for {venue}")

        except Exception as e:
            logger.error(f"Failed to fetch data for {venue}: {e}")
            continue

    return venue_data


if __name__ == "__main__":
    # Example usage
    venues = ["binance", "coinbase", "kraken", "okx", "bybit"]
    start_time = datetime.now() - timedelta(days=1)
    end_time = datetime.now()

    data = fetch_real_tick_data(venues, "BTC-USD", start_time, end_time)
    print(f"Fetched data for {len(data)} venues")
