import aiohttp
from datetime import datetime, timezone

# Kraken intervals are minutes. Pair for BTC/USDT is "XBTUSDT".
KR_INTERVALS = {"1m": 1, "5m": 5, "15m": 15, "30m": 30, "1h": 60, "4h": 240, "1d": 1440}


def _iso(ts_sec: float) -> str:
    return datetime.fromtimestamp(ts_sec, tz=timezone.utc).isoformat()


async def fetch_ohlcv(session: aiohttp.ClientSession, pair: str, tf: str, proxy_base: str | None):
    interval = KR_INTERVALS.get(tf, 5)
    base = proxy_base or ""
    url = (
        f"{base}/kraken/OHLC?pair={pair}&interval={interval}"
        if base
        else f"https://api.kraken.com/0/public/OHLC?pair={pair}&interval={interval}"
    )
    async with session.get(url) as r:
        j = await r.json()
        if j.get("error"):
            raise RuntimeError(f"kraken_api_error:{j['error']}")
        data = list(j["result"].values())[0]  # first key is pair
        # [ time, open, high, low, close, vwap, volume, count ]
        ohlcv = [
            [_iso(c[0]), float(c[1]), float(c[2]), float(c[3]), float(c[4]), float(c[6])]
            for c in data
        ]
        return ohlcv


async def fetch_ticker(session: aiohttp.ClientSession, pair: str, proxy_base: str | None):
    base = proxy_base or ""
    url = (
        f"{base}/kraken/Ticker?pair={pair}"
        if base
        else f"https://api.kraken.com/0/public/Ticker?pair={pair}"
    )
    async with session.get(url) as r:
        j = await r.json()
        if j.get("error"):
            raise RuntimeError(f"kraken_api_error:{j['error']}")
        d = list(j["result"].values())[0]
        bid = float(d["b"][0])
        ask = float(d["a"][0])
        mid = (bid + ask) / 2
        return {"bid": bid, "ask": ask, "mid": mid, "ts": datetime.now(timezone.utc).isoformat()}
