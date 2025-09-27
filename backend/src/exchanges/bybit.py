import aiohttp
from datetime import datetime, timezone


# Bybit v5: category=spot, interval in minutes as string: "5", "15", etc.
def _iso(ms: str) -> str:
    return datetime.fromtimestamp(int(ms) / 1000, tz=timezone.utc).isoformat()


async def fetch_ohlcv(session: aiohttp.ClientSession, symbol: str, tf: str, proxy_base: str | None):
    interval = {
        "1m": "1",
        "5m": "5",
        "15m": "15",
        "30m": "30",
        "1h": "60",
        "4h": "240",
        "1d": "D",
    }.get(tf, "5")
    base = proxy_base or ""
    if base:
        url = f"{base}/bybit/kline?category=spot&symbol={symbol}&interval={interval}&limit=288"
    else:
        url = (
            f"https://api.bybit.com/v5/market/kline?category=spot&symbol={symbol}"
            f"&interval={interval}&limit=288"
        )
    async with session.get(url) as r:
        j = await r.json()
        lst = (j.get("result") or {}).get("list") or []
        # Each item: [ start, open, high, low, close, volume, turnover ]
        ohlcv = [
            [_iso(c[0]), float(c[1]), float(c[2]), float(c[3]), float(c[4]), float(c[5])]
            for c in reversed(lst)
        ]
        return ohlcv


async def fetch_ticker(session: aiohttp.ClientSession, symbol: str, proxy_base: str | None):
    base = proxy_base or ""
    url = (
        f"{base}/bybit/tickers?category=spot&symbol={symbol}"
        if base
        else f"https://api.bybit.com/v5/market/tickers?category=spot&symbol={symbol}"
    )
    async with session.get(url) as r:
        j = await r.json()
        d = ((j.get("result") or {}).get("list") or [{}])[0]
        bid = float(d.get("bid1Price", 0) or 0)
        ask = float(d.get("ask1Price", 0) or 0)
        mid = (bid + ask) / 2 if bid and ask else 0
        return {"bid": bid, "ask": ask, "mid": mid, "ts": datetime.now(timezone.utc).isoformat()}
