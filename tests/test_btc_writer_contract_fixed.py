# tests/test_btc_writer_contract.py
import pytest
from datetime import datetime, timezone
from writer.pipelines.btc_usd import normalize_tick, batch_contract, validate_timestamp_window

def test_detects_bad_2025_median():
    """Test that low 2025 prices trigger sanity failure."""
    ticks = []
    for px in [50100.0] * 100:  # ~$50k prices
        ticks.append({
            "last_px": px, 
            "best_bid": px - 50, 
            "best_ask": px + 50
        })
    
    with pytest.raises(ValueError, match="Sanity fail"):
        batch_contract(ticks, "2025-09-28")

def test_accepts_good_2025_median():
    """Test that reasonable 2025 prices pass sanity."""
    ticks = []
    for px in [110_000.0] * 100:  # ~$110k prices
        ticks.append({
            "last_px": px, 
            "best_bid": px - 30, 
            "best_ask": px + 30
        })
    
    # Should not raise
    batch_contract(ticks, "2025-09-28")

def test_cross_field_consistency_pass():
    """Test that consistent price relationships pass."""
    ticks = []
    for px in [110_000.0] * 100:
        ticks.append({
            "last_px": px, 
            "best_bid": px - 30, 
            "best_ask": px + 30
        })
    
    # Should pass
    batch_contract(ticks, "2025-09-28")

def test_cross_field_consistency_fail():
    """Test that inconsistent price relationships fail."""
    ticks = []
    for px in [110_000.0] * 100:
        # Inconsistent: bid > last > ask
        ticks.append({
            "last_px": px, 
            "best_bid": px + 50,  # bid > last
            "best_ask": px - 50   # ask < last
        })
    
    with pytest.raises(ValueError, match="Cross-field consistency fail"):
        batch_contract(ticks, "2025-09-28")

def test_symbol_validation():
    """Test that only BTC-USD symbol is accepted."""
    payload = {
        "symbol": "BTC-USDT",  # Wrong symbol
        "ts_exchange": 1727481600,  # 2025-09-28 02:00:00
        "last_px": 110000.0,
        "best_bid": 109970.0,
        "best_ask": 110030.0,
        "venue": "binance"
    }
    
    with pytest.raises(ValueError, match="Unexpected symbol"):
        normalize_tick(payload)

def test_timestamp_window_validation():
    """Test timestamp window validation with UTC timezone."""
    # Valid timestamp within window (2025-09-28 02:00:00 UTC)
    ts_ok = datetime(2025, 9, 28, 2, 0, 0, tzinfo=timezone.utc).timestamp()
    validate_timestamp_window(ts_ok, "20250928", "0200-0230")  # should pass

    # Invalid timestamp outside window (2025-09-28 03:30:00 UTC)
    ts_bad = datetime(2025, 9, 28, 3, 30, 0, tzinfo=timezone.utc).timestamp()
    with pytest.raises(ValueError):
        validate_timestamp_window(ts_bad, "20250928", "0200-0230")

def test_venue_specific_price_extraction():
    """Test venue-specific price field extraction."""
    # Test binance
    payload_binance = {
        "symbol": "BTC-USD",
        "venue": "binance",
        "last_px": 110000.0,
        "best_bid": 109970.0,
        "best_ask": 110030.0,
        "ts_exchange": 1727481600
    }
    
    result = normalize_tick(payload_binance)
    assert result["last_px"] == 110000.0
    
    # Test coinbase
    payload_coinbase = {
        "symbol": "BTC-USD",
        "venue": "coinbase", 
        "last_px": 110000.0,
        "best_bid": 109970.0,
        "best_ask": 110030.0,
        "ts_exchange": 1727481600
    }
    
    result = normalize_tick(payload_coinbase)
    assert result["last_px"] == 110000.0

def test_mid_price_fallback():
    """Test mid-price fallback when last_px is missing."""
    payload = {
        "symbol": "BTC-USD",
        "venue": "binance",
        "last_px": None,  # Missing last price
        "best_bid": 109970.0,
        "best_ask": 110030.0,
        "ts_exchange": 1727481600
    }
    
    result = normalize_tick(payload)
    expected_mid = (109970.0 + 110030.0) / 2.0
    assert result["last_px"] == expected_mid

def test_no_evaluable_rows():
    """Test handling when no rows can be evaluated for cross-field consistency."""
    ticks = [
        {"last_px": None, "best_bid": None, "best_ask": None},
        {"last_px": None, "best_bid": None, "best_ask": None}
    ]
    
    with pytest.raises(ValueError, match="Cross-field consistency: no evaluable rows"):
        batch_contract(ticks, "2025-09-28")

