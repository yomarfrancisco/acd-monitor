"""
Test resample functions for no NaN leakage and stable OHLC aggregation.
"""
import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import sys
from pathlib import Path

# Add scripts to path
sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from _analysis_utils import resample_minute, resample_second, ensure_time_mid_volume


def create_test_data():
    """Create test data for resampling."""
    dates = pd.date_range('2025-09-26 20:48:00', periods=10, freq='1S')
    data = {
        'time': dates,
        'mid': [50000 + i * 10 for i in range(10)],
        'volume': [1.0] * 10
    }
    return pd.DataFrame(data)


def test_resample_minute_no_nan_leakage():
    """Test that resample_minute produces no NaN leakage."""
    df = create_test_data()
    df = ensure_time_mid_volume(df)
    
    result = resample_minute(df)
    
    # Should have no NaN values
    assert not result.isna().any().any()
    
    # Should have expected columns
    expected_cols = ['time', 'open', 'high', 'low', 'close', 'mid']
    assert all(col in result.columns for col in expected_cols)
    
    # OHLC should be valid
    assert (result['high'] >= result['low']).all()
    assert (result['high'] >= result['open']).all()
    assert (result['high'] >= result['close']).all()
    assert (result['low'] <= result['open']).all()
    assert (result['low'] <= result['close']).all()


def test_resample_second_no_nan_leakage():
    """Test that resample_second produces no NaN leakage."""
    df = create_test_data()
    df = ensure_time_mid_volume(df)
    
    result = resample_second(df)
    
    # Should have no NaN values
    assert not result.isna().any().any()
    
    # Should have expected columns
    expected_cols = ['time', 'open', 'close', 'low', 'high', 'volume', 'mid']
    assert all(col in result.columns for col in expected_cols)
    
    # OHLC should be valid
    assert (result['high'] >= result['low']).all()
    assert (result['high'] >= result['open']).all()
    assert (result['high'] >= result['close']).all()
    assert (result['low'] <= result['open']).all()
    assert (result['low'] <= result['close']).all()


def test_resample_stable_ohlc_aggregation():
    """Test that OHLC aggregation is stable and deterministic."""
    # Create data with known pattern
    dates = pd.date_range('2025-09-26 20:48:00', periods=60, freq='1S')
    data = {
        'time': dates,
        'mid': [50000 + (i % 10) * 100 for i in range(60)],  # Repeating pattern
        'volume': [1.0] * 60
    }
    df = pd.DataFrame(data)
    df = ensure_time_mid_volume(df)
    
    # Resample multiple times - should be identical
    result1 = resample_minute(df)
    result2 = resample_minute(df)
    
    pd.testing.assert_frame_equal(result1, result2)
    
    # Mid should be average of OHLC
    for _, row in result1.iterrows():
        expected_mid = (row['open'] + row['high'] + row['low'] + row['close']) / 4
        assert abs(row['mid'] - expected_mid) < 1e-10


def test_resample_empty_dataframe():
    """Test resampling empty DataFrame."""
    empty_df = pd.DataFrame(columns=['time', 'mid', 'volume'])
    
    result_minute = resample_minute(empty_df)
    result_second = resample_second(empty_df)
    
    assert result_minute.empty
    assert result_second.empty


def test_resample_single_row():
    """Test resampling single row data."""
    single_row = pd.DataFrame({
        'time': [datetime(2025, 9, 26, 20, 48, 0)],
        'mid': [50000],
        'volume': [1.0]
    })
    single_row = ensure_time_mid_volume(single_row)
    
    result_minute = resample_minute(single_row)
    result_second = resample_second(single_row)
    
    # Should handle single row gracefully
    assert len(result_minute) <= 1
    assert len(result_second) <= 1
