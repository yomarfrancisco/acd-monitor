"""
Performance benchmarks for ACD Engine

Tests runtime and memory usage for synthetic data analysis
to catch performance regressions.
"""

import pytest
import numpy as np
import pandas as pd
import time
import psutil
import os
from src.acd.analytics.integrated_engine import IntegratedACDEngine, IntegratedConfig
from src.acd.icp.engine import ICPConfig
from src.acd.vmm.engine import VMMConfig
from src.acd.vmm.crypto_moments import CryptoMomentConfig
from src.acd.data.synthetic_crypto import SyntheticCryptoGenerator, CryptoMarketConfig


class TestPerformance:
    """Performance benchmark tests"""

    @pytest.fixture
    def integrated_engine(self):
        """Create integrated ACD engine for testing"""
        icp_config = ICPConfig()
        vmm_config = VMMConfig()
        crypto_config = CryptoMomentConfig()
        integrated_config = IntegratedConfig(icp_config, vmm_config, crypto_config)
        return IntegratedACDEngine(integrated_config)

    @pytest.fixture
    def competitive_data(self):
        """Generate competitive synthetic data"""
        np.random.seed(42)
        config = CryptoMarketConfig(n_timepoints=2000, n_exchanges=4)
        generator = SyntheticCryptoGenerator(config)
        return generator.generate_competitive_scenario()

    @pytest.fixture
    def coordinated_data(self):
        """Generate coordinated synthetic data"""
        np.random.seed(42)
        config = CryptoMarketConfig(n_timepoints=2000, n_exchanges=4)
        generator = SyntheticCryptoGenerator(config)
        return generator.generate_coordinated_scenario()

    def get_memory_usage(self):
        """Get current memory usage in MB"""
        process = psutil.Process(os.getpid())
        return process.memory_info().rss / 1024 / 1024  # Convert to MB

    def test_competitive_performance(self, integrated_engine, competitive_data):
        """Benchmark competitive scenario analysis"""
        price_columns = ["Exchange_0", "Exchange_1", "Exchange_2", "Exchange_3"]

        # Measure memory before
        memory_before = self.get_memory_usage()

        # Measure runtime
        start_time = time.time()
        result = integrated_engine.analyze_coordination_risk(competitive_data, price_columns)
        end_time = time.time()

        # Measure memory after
        memory_after = self.get_memory_usage()

        # Calculate metrics
        runtime = end_time - start_time
        memory_used = memory_after - memory_before
        peak_memory = memory_after

        # Performance assertions (soft ceilings to catch regressions)
        assert runtime < 60.0, f"Competitive analysis took too long: {runtime:.2f}s (limit: 60s)"
        assert (
            memory_used < 500.0
        ), f"Competitive analysis used too much memory: {memory_used:.1f}MB (limit: 500MB)"
        assert (
            peak_memory < 1000.0
        ), f"Peak memory usage too high: {peak_memory:.1f}MB (limit: 1000MB)"

        # Verify result is valid
        assert result.risk_classification in ["LOW", "AMBER", "RED"], "Invalid risk classification"
        assert 0.0 <= result.composite_risk_score <= 100.0, "Invalid composite score"

        print(f"Competitive Performance:")
        print(f"  Runtime: {runtime:.2f}s")
        print(f"  Memory used: {memory_used:.1f}MB")
        print(f"  Peak memory: {peak_memory:.1f}MB")
        print(f"  Risk classification: {result.risk_classification}")
        print(f"  Composite score: {result.composite_risk_score:.2f}")

    def test_coordinated_performance(self, integrated_engine, coordinated_data):
        """Benchmark coordinated scenario analysis"""
        price_columns = ["Exchange_0", "Exchange_1", "Exchange_2", "Exchange_3"]

        # Measure memory before
        memory_before = self.get_memory_usage()

        # Measure runtime
        start_time = time.time()
        result = integrated_engine.analyze_coordination_risk(coordinated_data, price_columns)
        end_time = time.time()

        # Measure memory after
        memory_after = self.get_memory_usage()

        # Calculate metrics
        runtime = end_time - start_time
        memory_used = memory_after - memory_before
        peak_memory = memory_after

        # Performance assertions (soft ceilings to catch regressions)
        assert runtime < 60.0, f"Coordinated analysis took too long: {runtime:.2f}s (limit: 60s)"
        assert (
            memory_used < 500.0
        ), f"Coordinated analysis used too much memory: {memory_used:.1f}MB (limit: 500MB)"
        assert (
            peak_memory < 1000.0
        ), f"Peak memory usage too high: {peak_memory:.1f}MB (limit: 1000MB)"

        # Verify result is valid
        assert result.risk_classification in ["LOW", "AMBER", "RED"], "Invalid risk classification"
        assert 0.0 <= result.composite_risk_score <= 100.0, "Invalid composite score"

        print(f"Coordinated Performance:")
        print(f"  Runtime: {runtime:.2f}s")
        print(f"  Memory used: {memory_used:.1f}MB")
        print(f"  Peak memory: {peak_memory:.1f}MB")
        print(f"  Risk classification: {result.risk_classification}")
        print(f"  Composite score: {result.composite_risk_score:.2f}")

    def test_both_scenarios_performance(
        self, integrated_engine, competitive_data, coordinated_data
    ):
        """Benchmark both scenarios together"""
        price_columns = ["Exchange_0", "Exchange_1", "Exchange_2", "Exchange_3"]

        # Measure memory before
        memory_before = self.get_memory_usage()

        # Measure runtime for both scenarios
        start_time = time.time()

        competitive_result = integrated_engine.analyze_coordination_risk(
            competitive_data, price_columns
        )
        coordinated_result = integrated_engine.analyze_coordination_risk(
            coordinated_data, price_columns
        )

        end_time = time.time()

        # Measure memory after
        memory_after = self.get_memory_usage()

        # Calculate metrics
        runtime = end_time - start_time
        memory_used = memory_after - memory_before
        peak_memory = memory_after

        # Performance assertions (soft ceilings to catch regressions)
        assert runtime < 120.0, f"Both scenarios took too long: {runtime:.2f}s (limit: 120s)"
        assert (
            memory_used < 800.0
        ), f"Both scenarios used too much memory: {memory_used:.1f}MB (limit: 800MB)"
        assert (
            peak_memory < 1500.0
        ), f"Peak memory usage too high: {peak_memory:.1f}MB (limit: 1500MB)"

        # Verify results are valid and different
        assert (
            competitive_result.risk_classification != coordinated_result.risk_classification
        ), "Scenarios should have different classifications"
        assert (
            competitive_result.composite_risk_score != coordinated_result.composite_risk_score
        ), "Scenarios should have different scores"

        print(f"Both Scenarios Performance:")
        print(f"  Total runtime: {runtime:.2f}s")
        print(f"  Total memory used: {memory_used:.1f}MB")
        print(f"  Peak memory: {peak_memory:.1f}MB")
        print(
            f"  Competitive: {competitive_result.composite_risk_score:.2f} → {competitive_result.risk_classification}"
        )
        print(
            f"  Coordinated: {coordinated_result.composite_risk_score:.2f} → {coordinated_result.risk_classification}"
        )

    def test_memory_efficiency(self, integrated_engine, competitive_data):
        """Test memory efficiency over multiple runs"""
        price_columns = ["Exchange_0", "Exchange_1", "Exchange_2", "Exchange_3"]

        # Run multiple analyses to check for memory leaks
        memory_usage = []

        for i in range(5):
            memory_before = self.get_memory_usage()
            result = integrated_engine.analyze_coordination_risk(competitive_data, price_columns)
            memory_after = self.get_memory_usage()

            memory_used = memory_after - memory_before
            memory_usage.append(memory_used)

            # Verify result is valid
            assert result.risk_classification in [
                "LOW",
                "AMBER",
                "RED",
            ], f"Invalid classification in run {i+1}"

        # Check for memory leaks (memory usage should not increase significantly)
        memory_variance = np.var(memory_usage)
        assert (
            memory_variance < 5000.0
        ), f"Memory usage variance too high: {memory_variance:.1f}MB² (possible memory leak)"

        print(f"Memory Efficiency Test:")
        print(f"  Memory usage per run: {memory_usage}")
        print(f"  Memory variance: {memory_variance:.1f}MB²")
        print(f"  Average memory per run: {np.mean(memory_usage):.1f}MB")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
