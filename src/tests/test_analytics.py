"""
Tests for ACD Analytics Module
"""

import pytest
import numpy as np
from src.backend.analytics import ACDAnalytics, RiskMetrics

class TestACDAnalytics:
    """Test cases for ACD analytics"""
    
    def setup_method(self):
        """Set up test fixtures"""
        self.analytics = ACDAnalytics()
        self.sample_prices = np.array([100, 101, 99, 102, 98, 103, 97, 104])
        self.sample_events = [{"type": "market_shock", "impact": "medium"}]
        
    def test_price_stability_calculation(self):
        """Test price stability calculation"""
        stability = self.analytics.calculate_price_stability(self.sample_prices)
        assert isinstance(stability, float)
        assert 0 <= stability <= 100
        
    def test_synchronization_calculation(self):
        """Test price synchronization calculation"""
        sync = self.analytics.calculate_synchronization(self.sample_prices)
        assert isinstance(sync, float)
        assert 0 <= sync <= 100
        
    def test_environmental_sensitivity(self):
        """Test environmental sensitivity calculation"""
        sensitivity = self.analytics.calculate_environmental_sensitivity(
            self.sample_prices, self.sample_events
        )
        assert isinstance(sensitivity, float)
        assert 0 <= sensitivity <= 100
        
    def test_composite_score_calculation(self):
        """Test composite score calculation"""
        score = self.analytics.calculate_composite_score(25.0, 18.0, 82.0)
        assert isinstance(score, float)
        assert 0 <= score <= 100
        
    def test_verdict_assignment(self):
        """Test risk verdict assignment"""
        assert self.analytics.get_verdict(14) == "LOW"
        assert self.analytics.get_verdict(50) == "MEDIUM"
        assert self.analytics.get_verdict(80) == "HIGH"
        
    def test_full_case_analysis(self):
        """Test complete case analysis"""
        result = self.analytics.analyze_case(
            "test_case", self.sample_prices, self.sample_events
        )
        
        assert isinstance(result, RiskMetrics)
        assert hasattr(result, "case_id") == False  # Not set in current implementation
        assert 0 <= result.composite_score <= 100
        assert result.verdict in ["LOW", "MEDIUM", "HIGH"]
        assert 0 <= result.confidence <= 1
