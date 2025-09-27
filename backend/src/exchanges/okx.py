from datetime import datetime, timezone

import aiohttp

OKX_BARS = {"1m": "1m", "5m": "5m", "15m": "15m", "30m": "30m", "1h": "1H", "4h": "4H", "1d": "1D"}


def _iso(ms: str) -> str:
    return datetime.fromtimestamp(int(ms) / 1000, tz=timezone.utc).isoformat()


async def fetch_ohlcv(
    session: aiohttp.ClientSession, inst_id: str, tf: str, proxy_base: str | None
):
    bar = OKX_BARS.get(tf, "5m")
    base = proxy_base or ""
    url = (
        f"{base}/okx/candles?instId={inst_id}&bar={bar}&limit=288"
        if base
        else f"https://www.okx.com/api/v5/market/candles?instId={inst_id}&bar={bar}&limit=288"
    )
    async with session.get(url) as r:
        j = await r.json()
        data = j.get("data", [])
        # OKX candles: [ts, o, h, l, c, vol, volCcy, ...]
        ohlcv = [
            [_iso(c[0]), float(c[1]), float(c[2]), float(c[3]), float(c[4]), float(c[5])]
            for c in reversed(data)
        ]
        return ohlcv


async def fetch_ticker(session: aiohttp.ClientSession, inst_id: str, proxy_base: str | None):
    base = proxy_base or ""
    url = (
        f"{base}/okx/ticker?instId={inst_id}"
        if base
        else f"https://www.okx.com/api/v5/market/ticker?instId={inst_id}"
    )
    async with session.get(url) as r:
        j = await r.json()
        d = (j.get("data") or [{}])[0]
        bid = float(d.get("bidPx", 0) or 0)
        ask = float(d.get("askPx", 0) or 0)
        mid = (bid + ask) / 2 if bid and ask else 0
        return {"bid": bid, "ask": ask, "mid": mid, "ts": datetime.now(timezone.utc).isoformat()}
