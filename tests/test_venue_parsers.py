# tests/test_venue_parsers.py
import pytest
from writer.parsers.venues import parse_bybit, parse_kraken


def test_bybit_public_trade():
    msg = {
        "topic": "publicTrade.btcusdt",
        "data": [{"T": 1759392000123, "p": "110250.1", "v": "0.002"}],
    }
    out = parse_bybit(msg)
    assert out["venue"] == "bybit" and out["last_px"] == 110250.1 and out["ts_exchange"] > 1.7e9


def test_bybit_tickers():
    msg = {
        "topic": "tickers.btcusdt",
        "data": {
            "ts": 1759392000123,
            "bid1Price": "110200.5",
            "ask1Price": "110300.5",
            "bid1Size": "1.5",
            "ask1Size": "2.0",
        },
    }
    out = parse_bybit(msg)
    assert out["venue"] == "bybit" and out["best_bid"] == 110200.5 and out["best_ask"] == 110300.5


def test_kraken_trade_array():
    msg = [42, [["110900.2", "0.001", "1759392000.123", "b", "l", ""]], "XBT/USD", "trade"]
    out = parse_kraken(msg)
    assert (
        out["venue"] == "kraken" and out["last_px"] == 110900.2 and out["symbol_alias"] == "BTC-USD"
    )


def test_kraken_xbtusd_alias():
    msg = [42, [["110900.2", "0.001", "1759392000.123", "b", "l", ""]], "XBTUSD", "trade"]
    out = parse_kraken(msg)
    assert out["venue"] == "kraken" and out["symbol_alias"] == "BTC-USD"


def test_bybit_invalid_message():
    msg = {"invalid": "message"}
    out = parse_bybit(msg)
    assert out is None


def test_kraken_invalid_message():
    msg = ["not", "a", "trade", "message"]
    out = parse_kraken(msg)
    assert out is None
