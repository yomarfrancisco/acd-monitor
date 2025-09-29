#!/usr/bin/env python3
"""
Test script for ACD Reporting v2 - Attribution Tables and Provenance-Tracked Outputs

This script tests the Reporting v2 functionality using the CMA Poster Frames case study.
"""

import sys
import os
from pathlib import Path

# Add src to path
sys.path.append(str(Path(__file__).parent.parent / "src"))

import json
import pandas as pd
import numpy as np
from datetime import datetime

from acd.analytics.report_v2 import ReportV2Generator, generate_regulatory_bundle
from acd.analytics.integrated_engine import IntegratedResult
from acd.icp.engine import ICPResult
from acd.vmm.engine import VMMOutput
from acd.vmm.crypto_moments import CryptoMoments
from acd.validation.lead_lag import LeadLagResult
from acd.validation.mirroring import MirroringResult
from acd.validation.hmm import HMMResult
from acd.validation.infoflow import InfoFlowResult


def create_mock_results():
    """Create mock results for testing"""

    # ICP Result
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

    # VMM Result
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

    # Crypto Moments
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

    # Integrated Result
    integrated_result = IntegratedResult(
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
            "High mirroring may reflect arbitrage constraints rather than coordination",
            "Lead-lag patterns may reflect natural market structure and information flow",
            "Spread floors may reflect liquidity constraints and inventory management",
        ],
        analysis_timestamp=pd.Timestamp.now(),
        data_quality_score=0.90,
    )

    # Validation Results
    lead_lag_result = LeadLagResult(
        lead_lag_betas={},
        granger_p_values={},
        persistence_scores={"BA": 0.8, "VS": 0.6, "EI": 0.7, "FR": 0.5},
        switching_entropy=0.3,
        significant_relationships=[("BA", "VS"), ("EI", "FR")],
        avg_granger_p=0.25,
        env_persistence={},
        env_entropy={},
        n_windows=50,
        n_exchanges=4,
        config=None,
    )

    mirroring_result = MirroringResult(
        cosine_similarities={},
        pearson_correlations={},
        depth_weighted_similarities={},
        significant_correlations=[("BA", "VS"), ("EI", "FR")],
        avg_cosine_similarity=0.65,
        avg_pearson_correlation=0.70,
        env_similarities={},
        env_correlations={},
        high_mirroring_pairs=[("BA", "VS"), ("EI", "FR")],
        mirroring_ratio=0.65,
        coordination_score=0.70,
        n_windows=50,
        n_exchanges=4,
        config=None,
    )

    hmm_result = HMMResult(
        state_sequence=np.array([0, 1, 2, 0, 1, 2, 0, 1]),
        state_probabilities=np.array([[0.8, 0.1, 0.1], [0.2, 0.6, 0.2], [0.1, 0.2, 0.7]]),
        transition_matrix=np.array([[0.7, 0.2, 0.1], [0.3, 0.5, 0.2], [0.2, 0.3, 0.5]]),
        emission_means=np.array([[1.0, 2.0], [1.5, 2.5], [2.0, 3.0]]),
        emission_covariances=np.array(
            [[[1.0, 0.0], [0.0, 1.0]], [[1.5, 0.0], [0.0, 1.5]], [[2.0, 0.0], [0.0, 2.0]]]
        ),
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
        significant_te_links=[("BA", "VS"), ("EI", "FR")],
        te_p_values={},
        avg_transfer_entropy=0.25,
        env_transfer_entropies={},
        env_centrality={},
        env_network_density={},
        information_hub_score=0.65,
        coordination_network_score=0.60,
        n_observations=100,
        n_exchanges=4,
        config=None,
    )

    validation_results = {
        "lead_lag": lead_lag_result,
        "mirroring": mirroring_result,
        "hmm": hmm_result,
        "infoflow": infoflow_result,
    }

    # Data Quality Metrics
    data_quality_metrics = {"completeness": 0.95, "consistency": 0.90, "sample_size_adequacy": 0.85}

    return integrated_result, validation_results, data_quality_metrics


def test_attribution_table_generation():
    """Test attribution table generation"""

    print("Testing Attribution Table Generation...")

    # Create mock results
    integrated_result, validation_results, data_quality_metrics = create_mock_results()

    # Initialize generator
    generator = ReportV2Generator(output_dir="artifacts/reports")

    # Generate attribution table
    attribution_table = generator.generate_attribution_table(
        integrated_result, validation_results, data_quality_metrics
    )

    print(f"✅ Attribution Table Generated:")
    print(f"   Total Risk Score: {attribution_table.total_risk_score:.1f}/100")
    print(f"   Risk Band: {attribution_table.risk_band}")
    print(f"   Confidence Level: {attribution_table.confidence_level:.1%}")
    print(f"   ICP Contribution: {attribution_table.icp_contribution:.1f}/100")
    print(f"   VMM Contribution: {attribution_table.vmm_contribution:.1f}/100")
    print(f"   Lead-Lag Driver: {attribution_table.lead_lag_driver:.1f}/100")
    print(f"   Mirroring Driver: {attribution_table.mirroring_driver:.1f}/100")
    print(f"   ICP p-value: {attribution_table.icp_p_value:.4f}")
    print(f"   Data Completeness: {attribution_table.data_completeness:.1%}")

    return attribution_table


def test_provenance_tracking():
    """Test provenance tracking"""

    print("\nTesting Provenance Tracking...")

    # Initialize generator
    generator = ReportV2Generator(output_dir="artifacts/reports")

    # Generate provenance info
    provenance = generator.generate_provenance_info(
        analysis_id="CMA_POSTER_FRAMES_TEST",
        data_file_paths=[
            "cases/cma_poster_frames/data/cma_data_seed_42.csv",
            "cases/cma_poster_frames/artifacts/cma_analysis_summary_seed_42.json",
        ],
        configs={
            "icp": {"significance_level": 0.05, "n_bootstrap": 1000},
            "vmm": {"max_iterations": 1000, "convergence_tolerance": 1e-6},
            "validation": {
                "lead_lag": {"window_size": 30, "max_lag": 5},
                "mirroring": {"window_size": 30, "similarity_threshold": 0.7},
                "hmm": {"n_states": 3, "window_size": 100},
                "infoflow": {"max_lag": 5, "n_bins": 10},
            },
        },
        result_file_paths={
            "icp": "artifacts/reports/icp_results.json",
            "vmm": "artifacts/reports/vmm_results.json",
            "validation": "artifacts/reports/validation_results.json",
            "integrated": "artifacts/reports/integrated_results.json",
        },
        seed=42,
    )

    print(f"✅ Provenance Info Generated:")
    print(f"   Analysis ID: {provenance.analysis_id}")
    print(f"   Version: {provenance.version}")
    print(f"   Timestamp: {provenance.timestamp}")
    print(f"   Seed: {provenance.seed}")
    print(f"   Data Files: {len(provenance.data_file_paths)}")
    print(f"   Result Files: {len(provenance.result_file_paths)}")
    print(f"   Content Hash: {provenance.content_hash[:16]}...")
    print(f"   Signature: {provenance.signature}")

    return provenance


def test_regulatory_bundle_generation():
    """Test regulatory bundle generation"""

    print("\nTesting Regulatory Bundle Generation...")

    # Create mock results
    integrated_result, validation_results, data_quality_metrics = create_mock_results()

    # Initialize generator
    generator = ReportV2Generator(output_dir="artifacts/reports")

    # Generate attribution table
    attribution_table = generator.generate_attribution_table(
        integrated_result, validation_results, data_quality_metrics
    )

    # Generate provenance
    provenance = generator.generate_provenance_info(
        analysis_id="CMA_POSTER_FRAMES_BUNDLE",
        data_file_paths=["cases/cma_poster_frames/data/cma_data_seed_42.csv"],
        configs={"icp": {"significance_level": 0.05}},
        result_file_paths={"icp": "artifacts/reports/icp_results.json"},
        seed=42,
    )

    # Generate regulatory bundle
    bundle = generator.generate_regulatory_bundle(
        integrated_result, validation_results, attribution_table, provenance, "CMA Poster Frames"
    )

    print(f"✅ Regulatory Bundle Generated:")
    print(f"   Bundle ID: {bundle.bundle_id}")
    print(f"   Created At: {bundle.created_at}")
    print(f"   Executive Summary Length: {len(bundle.executive_summary)} chars")
    print(f"   Key Findings: {len(bundle.key_findings)} findings")
    print(f"   Recommendations: {len(bundle.recommendations)} recommendations")
    print(f"   Alternative Explanations: {len(bundle.alternative_explanations)} explanations")
    print(f"   Audit Trail: {len(bundle.audit_trail)} entries")

    # Print executive summary
    print(f"\n📋 Executive Summary Preview:")
    print(
        bundle.executive_summary[:500] + "..."
        if len(bundle.executive_summary) > 500
        else bundle.executive_summary
    )

    return bundle


def test_bundle_saving():
    """Test bundle saving functionality"""

    print("\nTesting Bundle Saving...")

    # Create mock results
    integrated_result, validation_results, data_quality_metrics = create_mock_results()

    # Initialize generator
    generator = ReportV2Generator(output_dir="artifacts/reports")

    # Generate attribution table
    attribution_table = generator.generate_attribution_table(
        integrated_result, validation_results, data_quality_metrics
    )

    # Generate provenance
    provenance = generator.generate_provenance_info(
        analysis_id="CMA_POSTER_FRAMES_SAVE_TEST",
        data_file_paths=["cases/cma_poster_frames/data/cma_data_seed_42.csv"],
        configs={"icp": {"significance_level": 0.05}},
        result_file_paths={"icp": "artifacts/reports/icp_results.json"},
        seed=42,
    )

    # Generate regulatory bundle
    bundle = generator.generate_regulatory_bundle(
        integrated_result,
        validation_results,
        attribution_table,
        provenance,
        "CMA Poster Frames Save Test",
    )

    # Save bundle
    file_paths = generator.save_bundle(bundle, format="json")

    print(f"✅ Bundle Saved:")
    print(f"   JSON Bundle: {file_paths.get('json', 'N/A')}")
    print(f"   Attribution Table: {file_paths.get('attribution', 'N/A')}")
    print(f"   Provenance: {file_paths.get('provenance', 'N/A')}")

    # Verify files exist
    for file_type, file_path in file_paths.items():
        if Path(file_path).exists():
            print(f"   ✅ {file_type.title()} file exists: {file_path}")
        else:
            print(f"   ❌ {file_type.title()} file missing: {file_path}")

    return file_paths


def test_convenience_function():
    """Test the convenience function"""

    print("\nTesting Convenience Function...")

    # Create mock results
    integrated_result, validation_results, data_quality_metrics = create_mock_results()

    # Use convenience function
    bundle, file_paths = generate_regulatory_bundle(
        integrated_result=integrated_result,
        validation_results=validation_results,
        data_quality_metrics=data_quality_metrics,
        case_study_name="CMA Poster Frames Convenience Test",
        output_dir="artifacts/reports",
        seed=42,
    )

    print(f"✅ Convenience Function Test:")
    print(f"   Bundle ID: {bundle.bundle_id}")
    print(f"   File Paths: {len(file_paths)} files generated")
    print(f"   Risk Band: {bundle.attribution_table.risk_band}")
    print(f"   Total Risk Score: {bundle.attribution_table.total_risk_score:.1f}/100")

    return bundle, file_paths


def main():
    """Main test function"""

    print("🚀 ACD Reporting v2 - Attribution Tables and Provenance-Tracked Outputs")
    print("=" * 80)

    try:
        # Test attribution table generation
        attribution_table = test_attribution_table_generation()

        # Test provenance tracking
        provenance = test_provenance_tracking()

        # Test regulatory bundle generation
        bundle = test_regulatory_bundle_generation()

        # Test bundle saving
        file_paths = test_bundle_saving()

        # Test convenience function
        convenience_bundle, convenience_paths = test_convenience_function()

        print("\n" + "=" * 80)
        print("🎉 All Reporting v2 Tests Completed Successfully!")
        print("\n📊 Summary:")
        print(f"   ✅ Attribution Table Generation: Working")
        print(f"   ✅ Provenance Tracking: Working")
        print(f"   ✅ Regulatory Bundle Generation: Working")
        print(f"   ✅ Bundle Saving: Working")
        print(f"   ✅ Convenience Function: Working")

        print(f"\n📁 Generated Files:")
        for file_type, file_path in file_paths.items():
            print(f"   - {file_type.title()}: {file_path}")

        print(f"\n🔍 Key Metrics:")
        print(f"   - Risk Band: {bundle.attribution_table.risk_band}")
        print(f"   - Total Risk Score: {bundle.attribution_table.total_risk_score:.1f}/100")
        print(f"   - Confidence Level: {bundle.attribution_table.confidence_level:.1%}")
        print(f"   - ICP Contribution: {bundle.attribution_table.icp_contribution:.1f}/100")
        print(f"   - VMM Contribution: {bundle.attribution_table.vmm_contribution:.1f}/100")

        print(f"\n📋 Bundle Contents:")
        print(f"   - Executive Summary: {len(bundle.executive_summary)} chars")
        print(f"   - Key Findings: {len(bundle.key_findings)} findings")
        print(f"   - Recommendations: {len(bundle.recommendations)} recommendations")
        print(f"   - Alternative Explanations: {len(bundle.alternative_explanations)} explanations")
        print(f"   - Audit Trail: {len(bundle.audit_trail)} entries")

        return True

    except Exception as e:
        print(f"\n❌ Test Failed: {e}")
        import traceback

        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
