"""
Tests for ACD Reporting v2 - Attribution Tables and Provenance-Tracked Outputs
"""

import json
import pytest
import pandas as pd
import numpy as np
from datetime import datetime
from pathlib import Path
from unittest.mock import Mock, patch, mock_open

from src.acd.analytics.report_v2 import (
    ReportV2Generator,
    AttributionTable,
    ProvenanceInfo,
    RegulatoryBundle,
    generate_regulatory_bundle,
)
from src.acd.icp.engine import ICPResult
from src.acd.vmm.engine import VMMOutput
from src.acd.vmm.crypto_moments import CryptoMoments
from src.acd.validation.lead_lag import LeadLagResult
from src.acd.validation.mirroring import MirroringResult
from src.acd.validation.hmm import HMMResult
from src.acd.validation.infoflow import InfoFlowResult
from src.acd.analytics.integrated_engine import IntegratedResult


class TestAttributionTable:
    """Test attribution table generation"""

    def test_attribution_table_creation(self):
        """Test basic attribution table creation"""

        attribution = AttributionTable(
            total_risk_score=75.5,
            risk_band="AMBER",
            confidence_level=0.85,
            icp_contribution=40.0,
            vmm_contribution=25.0,
            crypto_moments_contribution=15.0,
            validation_contribution=20.0,
            lead_lag_driver=60.0,
            mirroring_driver=45.0,
            regime_driver=30.0,
            infoflow_driver=25.0,
            icp_p_value=0.013,
            vmm_p_value=0.045,
            lead_lag_significance=0.75,
            mirroring_significance=0.65,
            data_completeness=0.95,
            data_consistency=0.90,
            sample_size_adequacy=0.85,
        )

        assert attribution.total_risk_score == 75.5
        assert attribution.risk_band == "AMBER"
        assert attribution.confidence_level == 0.85
        assert attribution.icp_contribution == 40.0
        assert attribution.lead_lag_driver == 60.0
        assert attribution.icp_p_value == 0.013


class TestProvenanceInfo:
    """Test provenance tracking"""

    def test_provenance_info_creation(self):
        """Test basic provenance info creation"""

        provenance = ProvenanceInfo(
            analysis_id="TEST_001",
            timestamp=datetime.now(),
            version="2.0.0",
            seed=42,
            data_file_paths=["data/test.csv"],
            config_files=["config/test.json"],
            icp_config={"significance_level": 0.05},
            vmm_config={"max_iterations": 1000},
            validation_configs={"lead_lag": {"window_size": 30}},
            result_file_paths={"icp": "results/icp.json"},
            intermediate_artifacts=["artifacts/temp.csv"],
            content_hash="abc123",
            signature="ACD_SIG_abc123",
        )

        assert provenance.analysis_id == "TEST_001"
        assert provenance.version == "2.0.0"
        assert provenance.seed == 42
        assert len(provenance.data_file_paths) == 1
        assert provenance.content_hash == "abc123"


class TestReportV2Generator:
    """Test ReportV2Generator functionality"""

    @pytest.fixture
    def generator(self):
        """Create ReportV2Generator instance"""
        return ReportV2Generator(output_dir="test_artifacts")

    @pytest.fixture
    def mock_integrated_result(self):
        """Create mock integrated result"""
        icp_result = ICPResult(
            test_statistic=2.5,
            p_value=0.013,
            reject_h0=True,
            effect_size=0.25,
            power=0.85,
            n_environments=3,
            environment_sizes={"env1": 100, "env2": 150, "env3": 120},
            confidence_interval=(0.15, 0.35),
            bootstrap_ci=(0.12, 0.38),
            r_squared=0.75,
            residual_normality=0.45,
            heteroscedasticity=0.32,
        )

        vmm_result = VMMOutput(
            convergence_status="converged",
            iterations=150,
            final_loss=0.05,
            beta_estimates=np.array([0.5, 0.3, 0.2]),
            sigma_estimates=np.array([0.1, 0.15, 0.2]),
            rho_estimates=np.array([0.3, 0.4, 0.5]),
            structural_stability=0.75,
            regime_confidence=0.80,
            over_identification_stat=12.5,
            over_identification_p_value=0.045,
        )

        crypto_moments = CryptoMoments(
            lead_lag_betas=np.array([0.6, 0.5, 0.4]),
            lead_lag_significance=np.array([0.8, 0.7, 0.6]),
            mirroring_ratios=np.array([0.7, 0.6, 0.5]),
            mirroring_consistency=np.array([0.8, 0.7, 0.6]),
            spread_floor_dwell_times=np.array([0.3, 0.4, 0.5]),
            spread_floor_frequency=np.array([0.2, 0.3, 0.4]),
            undercut_initiation_rate=np.array([0.2, 0.3, 0.4]),
            undercut_response_time=np.array([0.1, 0.2, 0.3]),
            mev_coordination_score=np.array([0.1, 0.2, 0.3]),
        )

        return IntegratedResult(
            icp_result=icp_result,
            vmm_result=vmm_result,
            crypto_moments=crypto_moments,
            composite_risk_score=75.5,
            risk_classification="AMBER",
            confidence_level=0.85,
            coordination_indicators={
                "environment_invariance": 1.0,
                "invariance_strength": 0.25,
                "structural_stability": 0.75,
                "regime_confidence": 0.80,
                "lead_lag_strength": 0.6,
                "mirroring_strength": 0.7,
            },
            alternative_explanations=[
                "High mirroring may reflect arbitrage constraints",
                "Lead-lag patterns may reflect natural market structure",
            ],
            analysis_timestamp=pd.Timestamp.now(),
            data_quality_score=0.90,
        )

    @pytest.fixture
    def mock_validation_results(self):
        """Create mock validation results"""

        lead_lag_result = LeadLagResult(
            lead_lag_betas={},
            granger_p_values={},
            persistence_scores={"Exchange_A": 0.8, "Exchange_B": 0.6},
            switching_entropy=0.3,
            significant_relationships=[],
            avg_granger_p=0.25,
            env_persistence={},
            env_entropy={},
            n_windows=50,
            n_exchanges=2,
            config=None,
        )

        mirroring_result = MirroringResult(
            cosine_similarities={},
            pearson_correlations={},
            depth_weighted_similarities={},
            significant_correlations=[],
            avg_cosine_similarity=0.65,
            avg_pearson_correlation=0.70,
            env_similarities={},
            env_correlations={},
            high_mirroring_pairs=[],
            mirroring_ratio=0.65,
            coordination_score=0.70,
            n_windows=50,
            n_exchanges=2,
            config=None,
        )

        hmm_result = HMMResult(
            state_sequence=np.array([0, 1, 2, 0, 1]),
            state_probabilities=np.array([[0.8, 0.1, 0.1], [0.2, 0.6, 0.2]]),
            transition_matrix=np.array([[0.7, 0.2, 0.1], [0.3, 0.5, 0.2]]),
            emission_means=np.array([[1.0, 2.0], [1.5, 2.5]]),
            emission_covariances=np.array([[[1.0, 0.0], [0.0, 1.0]], [[1.5, 0.0], [0.0, 1.5]]]),
            dwell_times={0: 5.0, 1: 3.0, 2: 2.0},
            state_frequencies={0: 0.5, 1: 0.3, 2: 0.2},
            regime_stability=0.75,
            env_dwell_times={},
            env_state_frequencies={},
            env_stability={},
            wide_spread_regime=2,
            lockstep_regime=0,
            coordination_regime_score=0.70,
            log_likelihood=-150.0,
            aic=320.0,
            bic=340.0,
            n_observations=100,
            n_features=2,
            config=None,
        )

        infoflow_result = InfoFlowResult(
            transfer_entropies={},
            directed_correlations={},
            network_centrality={},
            out_degree_concentration=0.6,
            eigenvector_centrality={},
            network_density=0.4,
            clustering_coefficient=0.3,
            significant_te_links=[],
            te_p_values={},
            avg_transfer_entropy=0.25,
            env_transfer_entropies={},
            env_centrality={},
            env_network_density={},
            information_hub_score=0.65,
            coordination_network_score=0.60,
            n_observations=100,
            n_exchanges=2,
            config=None,
        )

        return {
            "lead_lag": lead_lag_result,
            "mirroring": mirroring_result,
            "hmm": hmm_result,
            "infoflow": infoflow_result,
        }

    @pytest.fixture
    def mock_data_quality_metrics(self):
        """Create mock data quality metrics"""
        return {"completeness": 0.95, "consistency": 0.90, "sample_size_adequacy": 0.85}

    def test_generate_attribution_table(
        self, generator, mock_integrated_result, mock_validation_results, mock_data_quality_metrics
    ):
        """Test attribution table generation"""

        attribution_table = generator.generate_attribution_table(
            mock_integrated_result, mock_validation_results, mock_data_quality_metrics
        )

        assert isinstance(attribution_table, AttributionTable)
        assert attribution_table.total_risk_score == 75.5
        assert attribution_table.risk_band == "AMBER"
        assert attribution_table.confidence_level == 0.85
        assert attribution_table.icp_contribution > 0
        assert attribution_table.vmm_contribution > 0
        assert attribution_table.lead_lag_driver > 0
        assert attribution_table.mirroring_driver > 0
        assert attribution_table.icp_p_value == 0.013

    def test_generate_provenance_info(self, generator):
        """Test provenance info generation"""

        provenance = generator.generate_provenance_info(
            analysis_id="TEST_001",
            data_file_paths=["data/test.csv"],
            configs={"icp": {"significance_level": 0.05}},
            result_file_paths={"icp": "results/icp.json"},
            seed=42,
        )

        assert isinstance(provenance, ProvenanceInfo)
        assert provenance.analysis_id == "TEST_001"
        assert provenance.version == "2.0.0"
        assert provenance.seed == 42
        assert len(provenance.data_file_paths) == 1
        assert provenance.content_hash is not None
        assert provenance.signature is not None

    def test_generate_regulatory_bundle(
        self, generator, mock_integrated_result, mock_validation_results, mock_data_quality_metrics
    ):
        """Test regulatory bundle generation"""

        # Generate attribution table
        attribution_table = generator.generate_attribution_table(
            mock_integrated_result, mock_validation_results, mock_data_quality_metrics
        )

        # Generate provenance
        provenance = generator.generate_provenance_info(
            analysis_id="TEST_001",
            data_file_paths=["data/test.csv"],
            configs={"icp": {"significance_level": 0.05}},
            result_file_paths={"icp": "results/icp.json"},
            seed=42,
        )

        # Generate bundle
        bundle = generator.generate_regulatory_bundle(
            mock_integrated_result,
            mock_validation_results,
            attribution_table,
            provenance,
            "Test Case",
        )

        assert isinstance(bundle, RegulatoryBundle)
        assert bundle.bundle_id is not None
        assert bundle.executive_summary is not None
        assert len(bundle.key_findings) > 0
        assert len(bundle.recommendations) > 0
        assert bundle.methodology is not None
        assert bundle.attribution_table == attribution_table
        assert bundle.provenance == provenance

    def test_save_bundle(
        self, generator, mock_integrated_result, mock_validation_results, mock_data_quality_metrics
    ):
        """Test bundle saving functionality"""

        # Generate attribution table
        attribution_table = generator.generate_attribution_table(
            mock_integrated_result, mock_validation_results, mock_data_quality_metrics
        )

        # Generate provenance
        provenance = generator.generate_provenance_info(
            analysis_id="TEST_001",
            data_file_paths=["data/test.csv"],
            configs={"icp": {"significance_level": 0.05}},
            result_file_paths={"icp": "results/icp.json"},
            seed=42,
        )

        # Generate bundle
        bundle = generator.generate_regulatory_bundle(
            mock_integrated_result,
            mock_validation_results,
            attribution_table,
            provenance,
            "Test Case",
        )

        # Save bundle
        with patch("pathlib.Path.mkdir"), patch("builtins.open", mock_open()):
            file_paths = generator.save_bundle(bundle, format="json")

            assert "json" in file_paths
            assert "attribution" in file_paths
            assert "provenance" in file_paths
            assert all(isinstance(path, str) for path in file_paths.values())

    def test_icp_contribution_calculation(self, generator):
        """Test ICP contribution calculation"""

        # Test with rejection
        icp_result_reject = ICPResult(
            test_statistic=3.0,
            p_value=0.01,
            reject_h0=True,
            effect_size=0.3,
            power=0.9,
            n_environments=3,
            environment_sizes={"env1": 100, "env2": 150, "env3": 120},
            confidence_interval=(0.2, 0.4),
            bootstrap_ci=(0.18, 0.42),
            r_squared=0.80,
            residual_normality=0.50,
            heteroscedasticity=0.30,
        )

        contribution_reject = generator._calculate_icp_contribution(icp_result_reject)
        assert contribution_reject > 40.0  # Should be high due to rejection

        # Test without rejection
        icp_result_no_reject = ICPResult(
            test_statistic=0.5,
            p_value=0.5,
            reject_h0=False,
            effect_size=0.1,
            power=0.3,
            n_environments=3,
            environment_sizes={"env1": 100, "env2": 150, "env3": 120},
            confidence_interval=(0.05, 0.15),
            bootstrap_ci=(0.03, 0.17),
            r_squared=0.30,
            residual_normality=0.20,
            heteroscedasticity=0.10,
        )

        contribution_no_reject = generator._calculate_icp_contribution(icp_result_no_reject)
        assert contribution_no_reject == 5.0  # Should be low due to no rejection

    def test_vmm_contribution_calculation(self, generator):
        """Test VMM contribution calculation"""

        vmm_result = VMMOutput(
            convergence_status="converged",
            iterations=100,
            final_loss=0.03,
            beta_estimates=np.array([0.6, 0.4, 0.3]),
            sigma_estimates=np.array([0.08, 0.12, 0.18]),
            rho_estimates=np.array([0.4, 0.5, 0.6]),
            structural_stability=0.8,
            regime_confidence=0.9,
            over_identification_stat=10.0,
            over_identification_p_value=0.05,
        )

        contribution = generator._calculate_vmm_contribution(vmm_result)
        assert contribution > 0
        assert contribution <= 70.0  # Should be capped

    def test_crypto_contribution_calculation(self, generator):
        """Test crypto moments contribution calculation"""

        crypto_moments = CryptoMoments(
            lead_lag_betas=np.array([0.5, 0.4, 0.3]),
            lead_lag_significance=np.array([0.7, 0.6, 0.5]),
            mirroring_ratios=np.array([0.6, 0.5, 0.4]),
            mirroring_consistency=np.array([0.7, 0.6, 0.5]),
            spread_floor_dwell_times=np.array([0.2, 0.3, 0.4]),
            spread_floor_frequency=np.array([0.3, 0.4, 0.5]),
            undercut_initiation_rate=np.array([0.2, 0.3, 0.4]),
            undercut_response_time=np.array([0.1, 0.2, 0.3]),
            mev_coordination_score=np.array([0.1, 0.2, 0.3]),
        )

        contribution = generator._calculate_crypto_contribution(crypto_moments)
        assert contribution > 0
        assert contribution <= 50.0  # Should be capped

    def test_lead_lag_driver_calculation(self, generator, mock_validation_results):
        """Test lead-lag driver calculation"""

        lead_lag_result = mock_validation_results["lead_lag"]
        driver = generator._calculate_lead_lag_driver(lead_lag_result)

        assert driver > 0
        assert driver <= 100.0

    def test_mirroring_driver_calculation(self, generator, mock_validation_results):
        """Test mirroring driver calculation"""

        mirroring_result = mock_validation_results["mirroring"]
        driver = generator._calculate_mirroring_driver(mirroring_result)

        assert driver > 0
        assert driver <= 100.0

    def test_executive_summary_generation(
        self, generator, mock_integrated_result, mock_validation_results, mock_data_quality_metrics
    ):
        """Test executive summary generation"""

        attribution_table = generator.generate_attribution_table(
            mock_integrated_result, mock_validation_results, mock_data_quality_metrics
        )

        summary = generator._generate_executive_summary(
            mock_integrated_result, attribution_table, "Test Case"
        )

        assert isinstance(summary, str)
        assert "Test Case" in summary
        assert "AMBER" in summary
        assert "75.5" in summary
        assert "ICP Analysis" in summary

    def test_key_findings_generation(
        self, generator, mock_integrated_result, mock_validation_results, mock_data_quality_metrics
    ):
        """Test key findings generation"""

        attribution_table = generator.generate_attribution_table(
            mock_integrated_result, mock_validation_results, mock_data_quality_metrics
        )

        findings = generator._generate_key_findings(
            mock_integrated_result, mock_validation_results, attribution_table
        )

        assert isinstance(findings, list)
        assert len(findings) > 0
        assert any("icp" in finding.lower() for finding in findings)
        assert any("vmm" in finding.lower() for finding in findings)

    def test_recommendations_generation(
        self, generator, mock_integrated_result, mock_data_quality_metrics
    ):
        """Test recommendations generation"""

        attribution_table = AttributionTable(
            total_risk_score=75.5,
            risk_band="AMBER",
            confidence_level=0.85,
            icp_contribution=40.0,
            vmm_contribution=25.0,
            crypto_moments_contribution=15.0,
            validation_contribution=20.0,
            lead_lag_driver=60.0,
            mirroring_driver=45.0,
            regime_driver=30.0,
            infoflow_driver=25.0,
            icp_p_value=0.013,
            vmm_p_value=0.045,
            lead_lag_significance=0.75,
            mirroring_significance=0.65,
            data_completeness=0.95,
            data_consistency=0.90,
            sample_size_adequacy=0.85,
        )

        recommendations = generator._generate_recommendations(
            mock_integrated_result, attribution_table
        )

        assert isinstance(recommendations, list)
        assert len(recommendations) > 0
        assert any("ENHANCED MONITORING" in rec for rec in recommendations)


class TestGenerateRegulatoryBundle:
    """Test convenience function for bundle generation"""

    def test_generate_regulatory_bundle_function(self):
        """Test the convenience function"""

        # Create mock results
        icp_result = ICPResult(
            test_statistic=2.5,
            p_value=0.013,
            reject_h0=True,
            effect_size=0.25,
            power=0.85,
            n_environments=3,
            environment_sizes={"env1": 100, "env2": 150, "env3": 120},
            confidence_interval=(0.15, 0.35),
            bootstrap_ci=(0.12, 0.38),
            r_squared=0.75,
            residual_normality=0.45,
            heteroscedasticity=0.32,
        )

        vmm_result = VMMOutput(
            convergence_status="converged",
            iterations=150,
            final_loss=0.05,
            beta_estimates=np.array([0.5, 0.3, 0.2]),
            sigma_estimates=np.array([0.1, 0.15, 0.2]),
            rho_estimates=np.array([0.3, 0.4, 0.5]),
            structural_stability=0.75,
            regime_confidence=0.80,
            over_identification_stat=12.5,
            over_identification_p_value=0.045,
        )

        crypto_moments = CryptoMoments(
            lead_lag_betas=np.array([0.6, 0.5, 0.4]),
            lead_lag_significance=np.array([0.8, 0.7, 0.6]),
            mirroring_ratios=np.array([0.7, 0.6, 0.5]),
            mirroring_consistency=np.array([0.8, 0.7, 0.6]),
            spread_floor_dwell_times=np.array([0.3, 0.4, 0.5]),
            spread_floor_frequency=np.array([0.2, 0.3, 0.4]),
            undercut_initiation_rate=np.array([0.2, 0.3, 0.4]),
            undercut_response_time=np.array([0.1, 0.2, 0.3]),
            mev_coordination_score=np.array([0.1, 0.2, 0.3]),
        )

        integrated_result = IntegratedResult(
            icp_result=icp_result,
            vmm_result=vmm_result,
            crypto_moments=crypto_moments,
            composite_risk_score=75.5,
            risk_classification="AMBER",
            confidence_level=0.85,
            coordination_indicators={},
            alternative_explanations=[],
            analysis_timestamp=pd.Timestamp.now(),
            data_quality_score=0.90,
        )

        validation_results = {}
        data_quality_metrics = {
            "completeness": 0.95,
            "consistency": 0.90,
            "sample_size_adequacy": 0.85,
        }

        # Test the function
        with patch("pathlib.Path.mkdir"), patch("builtins.open", mock_open()):
            bundle, file_paths = generate_regulatory_bundle(
                integrated_result=integrated_result,
                validation_results=validation_results,
                data_quality_metrics=data_quality_metrics,
                case_study_name="Test Case",
                output_dir="test_artifacts",
                seed=42,
            )

            assert isinstance(bundle, RegulatoryBundle)
            assert isinstance(file_paths, dict)
            assert "json" in file_paths
            assert "attribution" in file_paths
            assert "provenance" in file_paths


class TestIntegration:
    """Integration tests for Reporting v2"""

    def test_end_to_end_bundle_generation(self):
        """Test end-to-end bundle generation"""

        # This would be a more comprehensive test with real data
        # For now, we'll test the basic structure

        generator = ReportV2Generator(output_dir="test_artifacts")

        # Create minimal mock data
        icp_result = ICPResult(
            test_statistic=2.5,
            p_value=0.013,
            reject_h0=True,
            effect_size=0.25,
            power=0.85,
            n_environments=3,
            environment_sizes={"env1": 100, "env2": 150, "env3": 120},
            confidence_interval=(0.15, 0.35),
            bootstrap_ci=(0.12, 0.38),
            r_squared=0.75,
            residual_normality=0.45,
            heteroscedasticity=0.32,
        )

        vmm_result = VMMOutput(
            convergence_status="converged",
            iterations=150,
            final_loss=0.05,
            beta_estimates=np.array([0.5, 0.3, 0.2]),
            sigma_estimates=np.array([0.1, 0.15, 0.2]),
            rho_estimates=np.array([0.3, 0.4, 0.5]),
            structural_stability=0.75,
            regime_confidence=0.80,
            over_identification_stat=12.5,
            over_identification_p_value=0.045,
        )

        crypto_moments = CryptoMoments(
            lead_lag_betas=np.array([0.6, 0.5, 0.4]),
            lead_lag_significance=np.array([0.8, 0.7, 0.6]),
            mirroring_ratios=np.array([0.7, 0.6, 0.5]),
            mirroring_consistency=np.array([0.8, 0.7, 0.6]),
            spread_floor_dwell_times=np.array([0.3, 0.4, 0.5]),
            spread_floor_frequency=np.array([0.2, 0.3, 0.4]),
            undercut_initiation_rate=np.array([0.2, 0.3, 0.4]),
            undercut_response_time=np.array([0.1, 0.2, 0.3]),
            mev_coordination_score=np.array([0.1, 0.2, 0.3]),
        )

        integrated_result = IntegratedResult(
            icp_result=icp_result,
            vmm_result=vmm_result,
            crypto_moments=crypto_moments,
            composite_risk_score=75.5,
            risk_classification="AMBER",
            confidence_level=0.85,
            coordination_indicators={},
            alternative_explanations=[],
            analysis_timestamp=pd.Timestamp.now(),
            data_quality_score=0.90,
        )

        validation_results = {}
        data_quality_metrics = {
            "completeness": 0.95,
            "consistency": 0.90,
            "sample_size_adequacy": 0.85,
        }

        # Generate attribution table
        attribution_table = generator.generate_attribution_table(
            integrated_result, validation_results, data_quality_metrics
        )

        # Generate provenance
        provenance = generator.generate_provenance_info(
            analysis_id="INTEGRATION_TEST",
            data_file_paths=["data/test.csv"],
            configs={"icp": {"significance_level": 0.05}},
            result_file_paths={"icp": "results/icp.json"},
            seed=42,
        )

        # Generate bundle
        bundle = generator.generate_regulatory_bundle(
            integrated_result, validation_results, attribution_table, provenance, "Integration Test"
        )

        # Verify bundle structure
        assert bundle.bundle_id is not None
        assert bundle.executive_summary is not None
        assert len(bundle.key_findings) > 0
        assert len(bundle.recommendations) > 0
        assert bundle.methodology is not None
        assert bundle.attribution_table is not None
        assert bundle.provenance is not None
        assert len(bundle.audit_trail) > 0

        # Verify attribution table
        assert attribution_table.total_risk_score == 75.5
        assert attribution_table.risk_band == "AMBER"
        assert attribution_table.confidence_level == 0.85

        # Verify provenance
        assert provenance.analysis_id == "INTEGRATION_TEST"
        assert provenance.version == "2.0.0"
        assert provenance.seed == 42


if __name__ == "__main__":
    pytest.main([__file__])
