"""
Test inclusive_end_date function for off-by-one guard.
"""
import pytest
from datetime import datetime
import sys
from pathlib import Path

# Add scripts to path
sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from _analysis_utils import inclusive_end_date


def test_inclusive_end_date_basic():
    """Test basic inclusive end date conversion."""
    result = inclusive_end_date("2025-09-26")
    expected = datetime(2025, 9, 26, 23, 59, 59, 999999)
    assert result == expected


def test_inclusive_end_date_edge_cases():
    """Test edge cases for inclusive end date."""
    # Year boundary
    result = inclusive_end_date("2024-12-31")
    expected = datetime(2024, 12, 31, 23, 59, 59, 999999)
    assert result == expected
    
    # Leap year
    result = inclusive_end_date("2024-02-29")
    expected = datetime(2024, 2, 29, 23, 59, 59, 999999)
    assert result == expected


def test_inclusive_end_date_invalid_format():
    """Test invalid date format raises ValueError."""
    with pytest.raises(ValueError, match="Invalid date format"):
        inclusive_end_date("2025/09/26")
    
    with pytest.raises(ValueError, match="Invalid date format"):
        inclusive_end_date("not-a-date")


def test_inclusive_end_date_off_by_one_guard():
    """Test that inclusive end date prevents off-by-one errors."""
    # This should include the entire day
    start = datetime(2025, 9, 26, 0, 0, 0)
    end = inclusive_end_date("2025-09-26")
    
    # Should be 24 hours minus 1 microsecond
    duration = end - start
    assert duration.total_seconds() > 86399.9  # Just under 24 hours
    assert duration.total_seconds() < 86400.1  # Just over 24 hours
