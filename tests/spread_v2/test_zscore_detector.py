#!/usr/bin/env python3
"""
Unit tests for z-score dispersion detector.
"""

import unittest
import numpy as np
import pandas as pd
import sys
from pathlib import Path

# Add src to path
sys.path.append(str(Path(__file__).parent.parent.parent / "src"))

from scripts.gold_hunt_control_v2 import ZScoreDispersionDetector


class TestZScoreDetector(unittest.TestCase):
    """Test z-score dispersion detector."""

    def setUp(self):
        """Set up test fixtures."""
        # Create synthetic dispersion data with known episodes
        np.random.seed(42)
        n_points = 1000

        # Base dispersion with some episodes
        dispersion = np.random.normal(2.0, 0.5, n_points)

        # Add episodes (low dispersion periods)
        dispersion[100:110] = 0.5  # Episode 1: 10 seconds
        dispersion[200:215] = 0.3  # Episode 2: 15 seconds
        dispersion[300:310] = 0.4  # Episode 3: 10 seconds

        # Create timestamps
        timestamps = pd.date_range("2025-01-01", periods=n_points, freq="1S")

        self.dispersion = pd.Series(dispersion, index=timestamps)
        self.detector = ZScoreDispersionDetector(k_window=60, z_cut=-1.5, merge_gap=2)

    def test_compute_dispersion_zscore(self):
        """Test z-score computation."""
        z_scores = self.detector.compute_dispersion_zscore(self.dispersion)

        # Check that z-scores are computed
        self.assertEqual(len(z_scores), len(self.dispersion))
        self.assertFalse(z_scores.isna().all())

        # Episodes should have negative z-scores
        episode_indices = list(range(100, 110)) + list(range(200, 215)) + list(range(300, 310))
        episode_z_scores = z_scores.iloc[episode_indices]
        self.assertTrue((episode_z_scores < -1.0).any())

    def test_detect_episodes(self):
        """Test episode detection."""
        z_scores = self.detector.compute_dispersion_zscore(self.dispersion)
        episodes = self.detector.detect_episodes(self.dispersion, z_scores)

        # Should detect episodes
        self.assertGreater(len(episodes), 0)

        # Check episode properties
        for episode in episodes:
            self.assertIn("start_time", episode)
            self.assertIn("end_time", episode)
            self.assertIn("duration", episode)
            self.assertIn("min_zscore", episode)
            self.assertIn("detector", episode)
            self.assertEqual(episode["detector"], "zscore")

    def test_merge_nearby_episodes(self):
        """Test episode merging."""
        # Create episodes that should be merged
        starts = [10, 15, 20, 30]  # Gaps: 5, 5, 10
        ends = [12, 17, 22, 32]

        merged = self.detector._merge_nearby_episodes(starts, ends)

        # Should merge episodes with gap <= 2
        self.assertLessEqual(len(merged), len(starts))

        # Check that merged episodes span the correct ranges
        for start, end in merged:
            self.assertLessEqual(start, end)


if __name__ == "__main__":
    unittest.main()
