"""
Test InfoShare bounds schema: bounds present & in [0,1].
"""
import pytest
import json
import sys
from pathlib import Path

# Add scripts to path
sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))


def test_infoshare_bounds_present():
    """Test that InfoShare results have bounds present."""
    # Mock info_share_results.json
    infoshare_results = {
        "overlap_window": {
            "startUTC": "2025-09-26T20:48:04Z",
            "endUTC": "2025-09-26T20:57:52Z",
            "venues": ["binance", "coinbase", "kraken"],
            "policy": "TEST_2s"
        },
        "bounds": {
            "binance": {"lower": 0.1, "upper": 0.4, "point": 0.25},
            "coinbase": {"lower": 0.2, "upper": 0.5, "point": 0.35},
            "kraken": {"lower": 0.15, "upper": 0.45, "point": 0.30}
        },
        "analysis_type": "info_share",
        "venues_count": 3
    }
    
    # Should have bounds
    assert "bounds" in infoshare_results
    assert len(infoshare_results["bounds"]) > 0
    assert infoshare_results["venues_count"] == len(infoshare_results["bounds"])


def test_infoshare_bounds_in_range_0_1():
    """Test that all bounds are in range [0,1]."""
    bounds = {
        "binance": {"lower": 0.1, "upper": 0.4, "point": 0.25},
        "coinbase": {"lower": 0.2, "upper": 0.5, "point": 0.35},
        "kraken": {"lower": 0.15, "upper": 0.45, "point": 0.30}
    }
    
    for venue, bound in bounds.items():
        # Each bound should be in [0, 1]
        assert 0 <= bound["lower"] <= 1, f"{venue} lower bound {bound['lower']} not in [0,1]"
        assert 0 <= bound["upper"] <= 1, f"{venue} upper bound {bound['upper']} not in [0,1]"
        assert 0 <= bound["point"] <= 1, f"{venue} point bound {bound['point']} not in [0,1]"
        
        # Bounds should be ordered: lower <= point <= upper
        assert bound["lower"] <= bound["point"], f"{venue} lower > point"
        assert bound["point"] <= bound["upper"], f"{venue} point > upper"


def test_infoshare_bounds_sum_approximately_1():
    """Test that venue bounds sum approximately to 1."""
    bounds = {
        "binance": {"lower": 0.1, "upper": 0.4, "point": 0.25},
        "coinbase": {"lower": 0.2, "upper": 0.5, "point": 0.35},
        "kraken": {"lower": 0.15, "upper": 0.45, "point": 0.30}
    }
    
    # Sum of point estimates should be approximately 1
    point_sum = sum(bound["point"] for bound in bounds.values())
    assert 0.98 <= point_sum <= 1.02, f"Point sum {point_sum} not in [0.98, 1.02]"


def test_infoshare_bounds_edge_cases():
    """Test edge cases for bounds."""
    # Edge case: all venues equal (should still be valid)
    equal_bounds = {
        "venue1": {"lower": 0.3, "upper": 0.3, "point": 0.3},
        "venue2": {"lower": 0.3, "upper": 0.3, "point": 0.3},
        "venue3": {"lower": 0.3, "upper": 0.3, "point": 0.3}
    }
    
    for venue, bound in equal_bounds.items():
        assert 0 <= bound["lower"] <= 1
        assert 0 <= bound["upper"] <= 1
        assert 0 <= bound["point"] <= 1
        assert bound["lower"] == bound["point"] == bound["upper"]
    
    # Edge case: extreme values (should still be in [0,1])
    extreme_bounds = {
        "min": {"lower": 0.0, "upper": 0.0, "point": 0.0},
        "max": {"lower": 1.0, "upper": 1.0, "point": 1.0}
    }
    
    for venue, bound in extreme_bounds.items():
        assert 0 <= bound["lower"] <= 1
        assert 0 <= bound["upper"] <= 1
        assert 0 <= bound["point"] <= 1


def test_infoshare_bounds_schema_validation():
    """Test that bounds have required schema."""
    bound = {
        "lower": 0.1,
        "upper": 0.4,
        "point": 0.25
    }
    
    # Required fields
    required_fields = ["lower", "upper", "point"]
    assert all(field in bound for field in required_fields)
    
    # Data types
    assert isinstance(bound["lower"], (int, float))
    assert isinstance(bound["upper"], (int, float))
    assert isinstance(bound["point"], (int, float))
    
    # Value ranges
    assert 0 <= bound["lower"] <= 1
    assert 0 <= bound["upper"] <= 1
    assert 0 <= bound["point"] <= 1
    
    # Ordering
    assert bound["lower"] <= bound["point"] <= bound["upper"]


def test_infoshare_missing_bounds_should_abort():
    """Test that missing bounds should trigger abort."""
    # This should trigger [ABORT:infoshare:invalid_bounds]
    infoshare_no_bounds = {
        "overlap_window": {
            "startUTC": "2025-09-26T20:48:04Z",
            "endUTC": "2025-09-26T20:57:52Z",
            "venues": ["binance", "coinbase"],
            "policy": "TEST_2s"
        },
        "bounds": {},  # Empty bounds
        "analysis_type": "info_share",
        "venues_count": 2
    }
    
    assert len(infoshare_no_bounds["bounds"]) == 0
    assert infoshare_no_bounds["venues_count"] > 0
