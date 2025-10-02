# file: writer/parsers/venues.py
from decimal import Decimal
from typing import Any, Dict, List, Optional, Tuple

def _to_float(x: Any) -> Optional[float]:
    try:
        return float(x)
    except Exception:
        try:
            return float(Decimal(str(x)))
        except Exception:
            return None

def _detect_epoch_seconds(ts: Any) -> Optional[float]:
    try:
        ts = int(float(ts))
    except Exception:
        return None
    # heuristics: s / ms / µs
    if ts > 9_999_999_999_999:   # µs
        return ts / 1_000_000.0
    if ts > 9_999_999_999:       # ms
        return ts / 1_000.0
    return float(ts)             # s

# ---------- BYBIT (v5 trade / book-ticker) ----------
def parse_bybit(msg: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    Supports Bybit v5 'publicTrade' and 'tickers' messages.
    Returns normalized tick dict or None if not applicable.
    """
    topic = msg.get("topic") or msg.get("arg", {}).get("topic")
    data = msg.get("data") or msg.get("data", [])

    # publicTrade: data is list of trades dicts
    if topic and "publicTrade" in topic and isinstance(data, list):
        # pick the last trade
        t = data[-1]
        # time keys vary: ts/ T / tradeTime/ time
        ts = t.get("ts") or t.get("T") or t.get("time") or t.get("tradeTime") or t.get("timestamp")
        px = _to_float(t.get("p") or t.get("price"))
        sz = _to_float(t.get("v") or t.get("qty") or t.get("size"))
        if ts is None or px is None:
            return None
        return {
            "venue": "bybit",
            "ts_exchange": _detect_epoch_seconds(ts),
            "last_px": px,
            "trade_sz": sz,
            "best_bid": None, "best_ask": None, "bid_sz": None, "ask_sz": None
        }

    # tickers (best bid/ask)
    if topic and ("tickers" in topic or "bookticker" in topic):
        # Bybit tickers shape: data is dict
        d = data if isinstance(data, dict) else (data[-1] if data else {})
        ts = d.get("ts") or d.get("timestamp") or d.get("T")
        bid = _to_float(d.get("bid1Price") or d.get("bidPrice") or d.get("b"))
        ask = _to_float(d.get("ask1Price") or d.get("askPrice") or d.get("a"))
        if ts is None or (bid is None and ask is None):
            return None
        return {
            "venue": "bybit",
            "ts_exchange": _detect_epoch_seconds(ts),
            "last_px": None,
            "best_bid": bid, "best_ask": ask,
            "bid_sz": _to_float(d.get("bid1Size") or d.get("B")), 
            "ask_sz": _to_float(d.get("ask1Size") or d.get("A")),
            "trade_sz": None
        }
    return None

# ---------- KRAKEN (trades channel) ----------
def parse_kraken(msg: Any) -> Optional[Dict[str, Any]]:
    """
    Kraken trades are arrays:
    [ channelId, [ [price, volume, time, side, orderType, misc], ... ], "XBT/USD", "trade" ]
    """
    if not isinstance(msg, list) or len(msg) < 4:
        return None
    if not (isinstance(msg[1], list) and msg[-1] == "trade"):
        return None

    pair = msg[2]
    trades = msg[1]
    if not trades:
        return None
    price_str, vol_str, time_str, *_ = trades[-1]
    px = _to_float(price_str)
    sz = _to_float(vol_str)
    # Kraken time is seconds with decimals (string)
    ts = _detect_epoch_seconds(float(time_str))
    if px is None or ts is None:
        return None
    return {
        "venue": "kraken",
        "symbol_alias": "BTC-USD" if pair.upper() in ("XBT/USD","XBTUSD") else None,
        "ts_exchange": ts,
        "last_px": px,
        "trade_sz": sz,
        "best_bid": None, "best_ask": None, "bid_sz": None, "ask_sz": None
    }

