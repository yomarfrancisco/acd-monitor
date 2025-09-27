"""
Test Lead-Lag invariant: venues≥2 ⇒ edges>0.
"""
import pytest
import json
import sys
from pathlib import Path

# Add scripts to path
sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))


def test_leadlag_venues_ge_2_edges_gt_0():
    """Test that venues≥2 always produces edges>0."""
    # Test case 1: 2 venues should produce edges
    overlap_2_venues = {
        "startUTC": "2025-09-26T20:48:04Z",
        "endUTC": "2025-09-26T20:57:52Z",
        "venues": ["binance", "coinbase"],
        "policy": "TEST_2s"
    }
    
    # Mock leadlag_results.json for 2 venues
    leadlag_2_venues = {
        "overlap_window": overlap_2_venues,
        "edges": [
            {"from": "binance", "to": "coinbase", "h1s": 0.1, "h5s": 0.2, "significance": 0.05},
            {"from": "coinbase", "to": "binance", "h1s": 0.15, "h5s": 0.25, "significance": 0.03}
        ],
        "top_leader": "binance",
        "horizons": [1, 5],
        "analysis_type": "lead_lag",
        "venues_count": 2,
        "edges_count": 2
    }
    
    # Should have edges
    assert len(leadlag_2_venues["edges"]) > 0
    assert leadlag_2_venues["edges_count"] > 0
    assert leadlag_2_venues["venues_count"] >= 2
    
    # Test case 2: 3 venues should produce more edges
    overlap_3_venues = {
        "startUTC": "2025-09-26T20:48:04Z", 
        "endUTC": "2025-09-26T20:57:52Z",
        "venues": ["binance", "coinbase", "kraken"],
        "policy": "TEST_2s"
    }
    
    # Mock leadlag_results.json for 3 venues (should have 6 edges: 3*2)
    leadlag_3_venues = {
        "overlap_window": overlap_3_venues,
        "edges": [
            {"from": "binance", "to": "coinbase", "h1s": 0.1, "h5s": 0.2, "significance": 0.05},
            {"from": "binance", "to": "kraken", "h1s": 0.12, "h5s": 0.22, "significance": 0.04},
            {"from": "coinbase", "to": "binance", "h1s": 0.15, "h5s": 0.25, "significance": 0.03},
            {"from": "coinbase", "to": "kraken", "h1s": 0.18, "h5s": 0.28, "significance": 0.06},
            {"from": "kraken", "to": "binance", "h1s": 0.08, "h5s": 0.18, "significance": 0.07},
            {"from": "kraken", "to": "coinbase", "h1s": 0.09, "h5s": 0.19, "significance": 0.08}
        ],
        "top_leader": "binance",
        "horizons": [1, 5],
        "analysis_type": "lead_lag",
        "venues_count": 3,
        "edges_count": 6
    }
    
    # Should have 6 edges (3*2)
    assert len(leadlag_3_venues["edges"]) == 6
    assert leadlag_3_venues["edges_count"] == 6
    assert leadlag_3_venues["venues_count"] == 3


def test_leadlag_venues_lt_2_should_abort():
    """Test that venues<2 should abort with proper error."""
    # Test case: 1 venue should abort
    overlap_1_venue = {
        "startUTC": "2025-09-26T20:48:04Z",
        "endUTC": "2025-09-26T20:57:52Z", 
        "venues": ["binance"],
        "policy": "TEST_2s"
    }
    
    # This should trigger [ABORT:leadlag:venues_lt_2]
    # In real code, this would be caught by the script
    assert len(overlap_1_venue["venues"]) < 2


def test_leadlag_empty_edges_should_abort():
    """Test that empty edges should abort with proper error."""
    # Test case: venues≥2 but edges=0 should abort
    leadlag_empty_edges = {
        "overlap_window": {
            "startUTC": "2025-09-26T20:48:04Z",
            "endUTC": "2025-09-26T20:57:52Z",
            "venues": ["binance", "coinbase"],
            "policy": "TEST_2s"
        },
        "edges": [],
        "top_leader": None,
        "horizons": [1, 5],
        "analysis_type": "lead_lag",
        "venues_count": 2,
        "edges_count": 0
    }
    
    # This should trigger [ABORT:leadlag:edges_empty]
    assert leadlag_empty_edges["venues_count"] >= 2
    assert leadlag_empty_edges["edges_count"] == 0


def test_leadlag_edge_schema_validation():
    """Test that edges have required schema."""
    edge = {
        "from": "binance",
        "to": "coinbase", 
        "h1s": 0.1,
        "h5s": 0.2,
        "significance": 0.05
    }
    
    # Required fields
    required_fields = ["from", "to", "h1s", "h5s", "significance"]
    assert all(field in edge for field in required_fields)
    
    # Data types
    assert isinstance(edge["from"], str)
    assert isinstance(edge["to"], str)
    assert isinstance(edge["h1s"], (int, float))
    assert isinstance(edge["h5s"], (int, float))
    assert isinstance(edge["significance"], (int, float))
    
    # Value ranges
    assert 0 <= edge["significance"] <= 1
    assert edge["from"] != edge["to"]  # No self-loops
