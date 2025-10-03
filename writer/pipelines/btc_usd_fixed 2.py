# file: writer/pipelines/btc_usd.py
import logging
import os
from datetime import datetime, timedelta, timezone
from statistics import median
from typing import Any, Dict, List, Optional

log = logging.getLogger(__name__)

# Configurable thresholds
PRICE_MIN_2025 = float(os.getenv("BTC_SANITY_MIN_2025", "80000"))
CROSS_FIELD_THRESHOLD = 0.90  # 90% pass rate

# Venue-specific field mapping
VENUE_LAST_PRICE_FIELD = {
    "binance": "last_px",  # adjust if actual payload uses e.g. "price"
    "coinbase": "last_px",
}


def detect_epoch_unit(ts_raw: int) -> float:
    """Detect timestamp unit and convert to seconds as float."""
    if ts_raw > 9e14:  # microseconds
        return ts_raw / 1_000_000.0
    if ts_raw > 9e11:  # milliseconds
        return ts_raw / 1_000.0
    return float(ts_raw)  # seconds


def _parse_window_label(window: str) -> tuple[int, int, int, int]:
    """Parse window label like '0200-0230' into (start_hour, start_min, end_hour, end_min)."""
    start, end = window.split("-")
    sh, sm = int(start[0:2]), int(start[2:4])
    eh, em = int(end[0:2]), int(end[2:4])
    return sh, sm, eh, em


def extract_last_price(payload: dict) -> Optional[float]:
    """Extract last price using venue-specific field mapping."""
    venue = payload.get("venue", "").lower()
    field = VENUE_LAST_PRICE_FIELD.get(venue, "last_px")
    val = payload.get(field)
    # Handle string types from some APIs
    return float(val) if val is not None else None


def normalize_tick(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Normalize tick data with validation."""
    # Symbol validation
    sym = payload.get("symbol")
    if sym != "BTC-USD":
        raise ValueError(f"Unexpected symbol: {sym}, expected BTC-USD")

    # Timestamp processing
    ts_raw = payload.get("ts_exchange")
    if ts_raw is None:
        raise ValueError("Missing ts_exchange field")

    ts_sec = detect_epoch_unit(ts_raw)

    # Price field extraction using venue-specific mapping
    last = extract_last_price(payload)
    bid = payload.get("best_bid")
    ask = payload.get("best_ask")

    # Fallback if trade price missing
    if last is None and bid is not None and ask is not None:
        last = (bid + ask) / 2.0
        log.warning("Using mid-price fallback", extra={"venue": payload.get("venue")})

    if last is None:
        raise ValueError("No price data available (last_px, best_bid, best_ask all missing)")

    return {
        "ts_verified": ts_sec,
        "last_px": last,
        "best_bid": bid,
        "best_ask": ask,
        "bid_sz": payload.get("bid_sz"),
        "ask_sz": payload.get("ask_sz"),
        "trade_sz": payload.get("trade_sz"),
        "venue": payload.get("venue"),
    }


def batch_contract(ticks: List[Dict[str, Any]], vdate_iso: str) -> None:
    """Validate batch against data contracts."""
    if not ticks:
        raise ValueError("Empty batch")

    # Extract prices for median check
    prices = [t["last_px"] for t in ticks if t["last_px"] is not None]
    if not prices:
        raise ValueError("No prices in batch")

    # Price sanity for 2025+ dates
    med = median(prices)
    if vdate_iso >= "2025-01-01" and med < PRICE_MIN_2025:
        raise ValueError(f"Sanity fail: median {med:.2f} < {PRICE_MIN_2025} for {vdate_iso}")

    # Cross-field consistency checks (only count evaluable rows)
    evaluated = 0
    ok = 0
    for t in ticks:
        last, bid, ask = t["last_px"], t["best_bid"], t["best_ask"]
        if None in (last, bid, ask):
            continue
        evaluated += 1
        spr = ask - bid
        mid = (ask + bid) / 2.0
        if (bid <= last <= ask) and (0 <= spr < 0.05 * mid):
            ok += 1

    if evaluated == 0:
        raise ValueError("Cross-field consistency: no evaluable rows")
    if (ok / evaluated) < CROSS_FIELD_THRESHOLD:
        raise ValueError(
            f"Cross-field consistency fail: {ok}/{evaluated} < {CROSS_FIELD_THRESHOLD:.0%}"
        )


def validate_timestamp_window(
    ts_verified_sec: float, folder_date_ymd: str, window: str, tolerance_minutes: int = 2
) -> None:
    """Validate timestamp falls within expected window with UTC timezone awareness."""
    folder_dt = datetime.strptime(folder_date_ymd, "%Y%m%d").replace(tzinfo=timezone.utc)
    sh, sm, eh, em = _parse_window_label(window)
    window_start = folder_dt.replace(hour=sh, minute=sm, second=0, microsecond=0)
    window_end = folder_dt.replace(hour=eh, minute=em, second=0, microsecond=0)
    ts_dt = datetime.fromtimestamp(ts_verified_sec, tz=timezone.utc)
    tol = timedelta(minutes=tolerance_minutes)
    if not (window_start - tol <= ts_dt <= window_end + tol):
        raise ValueError(
            f"Timestamp {ts_dt.isoformat()} outside window {window_start.isoformat()}–{window_end.isoformat()} (±{tolerance_minutes}m)"
        )
