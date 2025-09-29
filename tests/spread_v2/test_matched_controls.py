#!/usr/bin/env python3
"""
Unit tests for matched control sampling.
"""

import unittest
import numpy as np
import pandas as pd
import sys
from pathlib import Path

# Add src to path
sys.path.append(str(Path(__file__).parent.parent.parent / "src"))

from scripts.gold_hunt_control_v2 import MatchedControlSampler, EpisodeControlAnalyzer


class TestMatchedControls(unittest.TestCase):
    """Test matched control sampling."""
    
    def setUp(self):
        """Set up test fixtures."""
        np.random.seed(42)
        
        # Create synthetic mid prices data
        n_points = 1000
        timestamps = pd.date_range('2025-01-01', periods=n_points, freq='1S')
        
        # Generate correlated price data
        base_price = 45000
        price_data = {}
        for venue in ['binance', 'coinbase', 'kraken', 'okx', 'bybit']:
            # Add some correlation but with venue-specific noise
            noise = np.random.normal(0, 10, n_points)
            prices = base_price + np.cumsum(noise) + np.random.normal(0, 5, n_points)
            price_data[venue] = prices
        
        self.mid_prices_df = pd.DataFrame(price_data, index=timestamps)
        self.sampler = MatchedControlSampler(n_controls=50, random_state=42)
        self.analyzer = EpisodeControlAnalyzer(n_bootstrap=100, random_state=42)
    
    def test_extract_features(self):
        """Test feature extraction."""
        features = self.sampler.extract_features(self.mid_prices_df)
        
        # Check feature columns
        expected_cols = ['time_idx', 't_in_window', 'vol30s', 'volrate']
        for col in expected_cols:
            self.assertIn(col, features.columns)
        
        # Check feature ranges
        self.assertTrue((features['t_in_window'] >= 0).all())
        self.assertTrue((features['t_in_window'] <= 1).all())
        self.assertTrue((features['vol30s'] >= 0).all())
    
    def test_sample_controls_exclusion(self):
        """Test that controls exclude episode region."""
        features = self.sampler.extract_features(self.mid_prices_df)
        
        # Test episode in middle of data
        episode_start = 400
        episode_end = 410
        episode_features = features.iloc[episode_start]
        
        control_indices = self.sampler.sample_controls(
            episode_features, features, episode_start, episode_end
        )
        
        # Should find controls
        self.assertGreater(len(control_indices), 0)
        
        # Controls should not overlap with episode region
        exclusion_buffer = 10  # seconds
        excluded_start = max(0, episode_start - exclusion_buffer)
        excluded_end = min(len(features), episode_end + exclusion_buffer)
        
        for control_idx in control_indices:
            self.assertFalse(excluded_start <= control_idx < excluded_end)
    
    def test_bootstrap_determinism(self):
        """Test that bootstrap is deterministic with fixed seed."""
        # Create simple test data
        episode_data = pd.DataFrame({
            'dispersion_zscore': [-2.0, -1.8, -1.9],
            'volume_rate': [100, 120, 110],
            'realized_vol': [0.5, 0.6, 0.55]
        })
        
        control_data = pd.DataFrame({
            'dispersion_zscore': [0.5, 0.3, 0.4, 0.6, 0.2],
            'volume_rate': [80, 90, 85, 95, 75],
            'realized_vol': [0.3, 0.4, 0.35, 0.45, 0.25]
        })
        
        # Run bootstrap multiple times with same seed
        results1 = self.analyzer.compare_episode_controls(episode_data, control_data)
        results2 = self.analyzer.compare_episode_controls(episode_data, control_data)
        
        # Results should be identical
        self.assertEqual(results1['p_value'], results2['p_value'])
        self.assertEqual(results1['cohens_d'], results2['cohens_d'])
    
    def test_control_sampling_determinism(self):
        """Test that control sampling is deterministic."""
        features = self.sampler.extract_features(self.mid_prices_df)
        episode_features = features.iloc[100]
        
        # Sample controls twice with same seed
        controls1 = self.sampler.sample_controls(
            episode_features, features, 100, 110
        )
        controls2 = self.sampler.sample_controls(
            episode_features, features, 100, 110
        )
        
        # Should get same results
        self.assertEqual(controls1, controls2)


if __name__ == '__main__':
    unittest.main()
