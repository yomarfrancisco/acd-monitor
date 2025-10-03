"""
Smoke test for Wave 4 tick-level operations.
Tests imports and basic functionality with 1-minute subset.
"""
import pytest
import pandas as pd
import numpy as np
from pathlib import Path
import sys
import os

# Add scripts to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "scripts" / "wave4_tick_optimized"))

def test_imports():
    """Test that all modules can be imported."""
    try:
        from lib_sync import analyze_large_trade_sync
        from lib_ofi import analyze_ofi_spikes
        from lib_impact import analyze_impact_spillovers
        assert True
    except ImportError as e:
        pytest.fail(f"Import failed: {e}")

def test_create_sample_data():
    """Create sample tick data for testing."""
    # Create 1-minute sample data
    timestamps = pd.date_range('2025-09-25T00:00:00', periods=100, freq='100ms')
    
    sample_data = pd.DataFrame({
        'time_exchange': timestamps,
        'price': 100000 + np.random.randn(100) * 100,
        'base_amount': np.random.exponential(0.1, 100),
        'guid': [f"guid_{i}" for i in range(100)],
        'taker_side': np.random.choice(['BUY', 'SELL'], 100)
    })
    
    # Add time bins
    sample_data['ts_ns'] = sample_data['time_exchange'].astype('int64')
    sample_data['bin50'] = sample_data['ts_ns'] // 50_000_000
    sample_data['bin100'] = sample_data['ts_ns'] // 100_000_000
    
    return sample_data

def test_sync_analysis():
    """Test large trade synchronization analysis."""
    from lib_sync import analyze_large_trade_sync
    
    # Create sample data
    data1 = test_create_sample_data()
    data2 = test_create_sample_data()
    
    # Run analysis
    result = analyze_large_trade_sync(data1, data2, "TEST1", "TEST2")
    
    # Check result structure
    assert "venue1" in result
    assert "venue2" in result
    assert "status" in result
    assert result["venue1"] == "TEST1"
    assert result["venue2"] == "TEST2"

def test_ofi_analysis():
    """Test OFI spike analysis."""
    from lib_ofi import analyze_ofi_spikes
    
    # Create sample data
    data1 = test_create_sample_data()
    data2 = test_create_sample_data()
    
    # Run analysis
    result = analyze_ofi_spikes(data1, data2, "TEST1", "TEST2")
    
    # Check result structure
    assert "venue1" in result
    assert "venue2" in result
    assert "status" in result
    assert result["venue1"] == "TEST1"
    assert result["venue2"] == "TEST2"

def test_impact_analysis():
    """Test impact spillovers analysis."""
    from lib_impact import analyze_impact_spillovers
    
    # Create sample data
    data1 = test_create_sample_data()
    data2 = test_create_sample_data()
    
    # Run analysis
    result = analyze_impact_spillovers(data1, data2, "TEST1", "TEST2")
    
    # Check result structure
    assert "venue1" in result
    assert "venue2" in result
    assert "status" in result
    assert result["venue1"] == "TEST1"
    assert result["venue2"] == "TEST2"

def test_time_binning():
    """Test time binning functionality."""
    data = test_create_sample_data()
    
    # Check that bins are created
    assert 'bin50' in data.columns
    assert 'bin100' in data.columns
    
    # Check that bins are integers
    assert data['bin50'].dtype == 'int64'
    assert data['bin100'].dtype == 'int64'
    
    # Check that bins are reasonable
    assert data['bin50'].min() >= 0
    assert data['bin100'].min() >= 0

def test_data_aggregation():
    """Test data aggregation by bins."""
    data = test_create_sample_data()
    
    # Aggregate by 50ms bins
    agg_data = data.groupby('bin50').agg({
        'base_amount': 'sum',
        'price': 'last',
        'time_exchange': 'last'
    }).reset_index()
    
    # Check aggregation
    assert len(agg_data) <= len(data)
    assert 'base_amount' in agg_data.columns
    assert 'price' in agg_data.columns

if __name__ == "__main__":
    # Run smoke tests
    test_imports()
    test_sync_analysis()
    test_ofi_analysis()
    test_impact_analysis()
    test_time_binning()
    test_data_aggregation()
    print("✅ All smoke tests passed")
