#!/usr/bin/env python3
"""
Phase 1 Implementation Test Script

Tests the core ICP and VMM engines with crypto-specific moment conditions
on synthetic data to validate Phase 1 deliverables.
"""

import os
import sys

sys.path.append(os.path.join(os.path.dirname(__file__), "..", "src"))

from datetime import datetime

import numpy as np
import pandas as pd

from acd.analytics.integrated_engine import IntegratedACDEngine, IntegratedConfig
from acd.data.synthetic_crypto import CryptoMarketConfig, SyntheticCryptoGenerator
from acd.icp.engine import ICPConfig, ICPEngine
from acd.vmm.crypto_moments import CryptoMomentCalculator, CryptoMomentConfig
from acd.vmm.engine import VMMConfig, VMMEngine


def test_phase1_implementation():
    """Test Phase 1 implementation"""

    print("=" * 60)
    print("PHASE 1 IMPLEMENTATION TEST")
    print("=" * 60)

    # Generate synthetic data
    print("\n1. Generating synthetic crypto data...")
    config = CryptoMarketConfig(n_timepoints=2000, n_exchanges=4)
    generator = SyntheticCryptoGenerator(config)

    competitive_data = generator.generate_competitive_scenario()
    coordinated_data = generator.generate_coordinated_scenario()

    print(f"   ✓ Generated competitive data: {competitive_data.shape}")
    print(f"   ✓ Generated coordinated data: {coordinated_data.shape}")

    # Get price columns
    price_cols = [col for col in competitive_data.columns if col.startswith("Exchange_")]
    print(f"   ✓ Price columns: {price_cols}")

    # Test ICP Engine
    print("\n2. Testing ICP Engine...")
    icp_config = ICPConfig(significance_level=0.05, power_threshold=0.8, min_samples_per_env=100)
    icp_engine = ICPEngine(icp_config)

    # Test on competitive data
    icp_result_competitive = icp_engine.analyze_invariance(competitive_data, price_cols)
    print(f"   ✓ Competitive ICP - Reject H0: {icp_result_competitive.reject_h0}")
    print(f"   ✓ Competitive ICP - P-value: {icp_result_competitive.p_value:.4f}")
    print(f"   ✓ Competitive ICP - Effect size: {icp_result_competitive.effect_size:.4f}")
    print(f"   ✓ Competitive ICP - Power: {icp_result_competitive.power:.4f}")

    # Test on coordinated data
    icp_result_coordinated = icp_engine.analyze_invariance(coordinated_data, price_cols)
    print(f"   ✓ Coordinated ICP - Reject H0: {icp_result_coordinated.reject_h0}")
    print(f"   ✓ Coordinated ICP - P-value: {icp_result_coordinated.p_value:.4f}")
    print(f"   ✓ Coordinated ICP - Effect size: {icp_result_coordinated.effect_size:.4f}")
    print(f"   ✓ Coordinated ICP - Power: {icp_result_coordinated.power:.4f}")

    # Test Enhanced ICP with statistical rigor
    print("\n2b. Testing Enhanced ICP with Statistical Rigor...")

    # Test enhanced ICP on competitive data
    enhanced_icp_competitive = icp_engine.analyze_invariance_enhanced(competitive_data, price_cols)
    print(f"   ✓ Enhanced ICP Competitive - Reject H0: {enhanced_icp_competitive.reject_h0}")
    print(f"   ✓ Enhanced ICP Competitive - P-value: {enhanced_icp_competitive.p_value:.4f}")
    print(
        f"   ✓ Enhanced ICP Competitive - FDR adjusted p-value: {enhanced_icp_competitive.fdr_adjusted_p_value:.4f}"
    )
    print(
        f"   ✓ Enhanced ICP Competitive - Effect size: {enhanced_icp_competitive.effect_size:.4f}"
    )
    print(
        f"   ✓ Enhanced ICP Competitive - Statistical power: {enhanced_icp_competitive.statistical_power:.4f}"
    )
    print(
        f"   ✓ Enhanced ICP Competitive - Required sample size: {enhanced_icp_competitive.required_sample_size}"
    )
    print(
        f"   ✓ Enhanced ICP Competitive - FDR controlled: {enhanced_icp_competitive.fdr_controlled}"
    )

    # Test enhanced ICP on coordinated data
    enhanced_icp_coordinated = icp_engine.analyze_invariance_enhanced(coordinated_data, price_cols)
    print(f"   ✓ Enhanced ICP Coordinated - Reject H0: {enhanced_icp_coordinated.reject_h0}")
    print(f"   ✓ Enhanced ICP Coordinated - P-value: {enhanced_icp_coordinated.p_value:.4f}")
    print(
        f"   ✓ Enhanced ICP Coordinated - FDR adjusted p-value: {enhanced_icp_coordinated.fdr_adjusted_p_value:.4f}"
    )
    print(
        f"   ✓ Enhanced ICP Coordinated - Effect size: {enhanced_icp_coordinated.effect_size:.4f}"
    )
    print(
        f"   ✓ Enhanced ICP Coordinated - Statistical power: {enhanced_icp_coordinated.statistical_power:.4f}"
    )
    print(
        f"   ✓ Enhanced ICP Coordinated - Required sample size: {enhanced_icp_coordinated.required_sample_size}"
    )
    print(
        f"   ✓ Enhanced ICP Coordinated - FDR controlled: {enhanced_icp_coordinated.fdr_controlled}"
    )

    # Test Crypto Moments
    print("\n3. Testing Crypto Moments...")
    crypto_config = CryptoMomentConfig(max_lag=5, mirroring_window=3, spread_floor_threshold=0.0001)
    crypto_calculator = CryptoMomentCalculator(crypto_config)

    # Test on competitive data
    moments_competitive = crypto_calculator.calculate_moments(competitive_data, price_cols)
    summary_competitive = crypto_calculator.get_moment_summary(moments_competitive)
    print(f"   ✓ Competitive - Max lead-lag beta: {summary_competitive['max_lead_lag_beta']:.4f}")
    print(
        f"   ✓ Competitive - Max mirroring ratio: {summary_competitive['max_mirroring_ratio']:.4f}"
    )
    print(
        f"   ✓ Competitive - Avg spread frequency: {summary_competitive['avg_spread_frequency']:.4f}"
    )

    # Test on coordinated data
    moments_coordinated = crypto_calculator.calculate_moments(coordinated_data, price_cols)
    summary_coordinated = crypto_calculator.get_moment_summary(moments_coordinated)
    print(f"   ✓ Coordinated - Max lead-lag beta: {summary_coordinated['max_lead_lag_beta']:.4f}")
    print(
        f"   ✓ Coordinated - Max mirroring ratio: {summary_coordinated['max_mirroring_ratio']:.4f}"
    )
    print(
        f"   ✓ Coordinated - Avg spread frequency: {summary_coordinated['avg_spread_frequency']:.4f}"
    )

    # Test Integrated Engine
    print("\n4. Testing Integrated Engine...")
    integrated_config = IntegratedConfig(
        icp_config=icp_config,
        vmm_config=VMMConfig(),  # Use default VMM config
        crypto_moments_config=crypto_config,
    )
    integrated_engine = IntegratedACDEngine(integrated_config)

    # Test on competitive data
    result_competitive = integrated_engine.analyze_coordination_risk(competitive_data, price_cols)
    print(f"   ✓ Competitive - Risk classification: {result_competitive.risk_classification}")
    print(f"   ✓ Competitive - Composite score: {result_competitive.composite_risk_score:.2f}")
    print(f"   ✓ Competitive - Confidence: {result_competitive.confidence_level:.2f}")

    # Test on coordinated data
    result_coordinated = integrated_engine.analyze_coordination_risk(coordinated_data, price_cols)
    print(f"   ✓ Coordinated - Risk classification: {result_coordinated.risk_classification}")
    print(f"   ✓ Coordinated - Composite score: {result_coordinated.composite_risk_score:.2f}")
    print(f"   ✓ Coordinated - Confidence: {result_coordinated.confidence_level:.2f}")

    # Test distinction capability
    print("\n5. Testing Competitive vs Coordinated Distinction...")
    distinction_achieved = (
        result_coordinated.composite_risk_score > result_competitive.composite_risk_score
    )
    print(f"   ✓ Distinction achieved: {distinction_achieved}")
    print(
        f"   ✓ Score difference: {result_coordinated.composite_risk_score - result_competitive.composite_risk_score:.2f}"
    )

    # Test diagnostic report
    print("\n6. Testing Diagnostic Report Generation...")
    report = integrated_engine.generate_diagnostic_report(result_coordinated)
    print(f"   ✓ Report generated with {len(report)} sections")
    print(f"   ✓ Summary includes: {list(report['summary'].keys())}")
    print(f"   ✓ Recommendations: {len(report['recommendations'])} items")

    # Phase 1 Success Criteria Check
    print("\n" + "=" * 60)
    print("PHASE 1 SUCCESS CRITERIA CHECK")
    print("=" * 60)

    success_criteria = {
        "ICP functional": icp_result_competitive.p_value is not None
        and icp_result_coordinated.p_value is not None,
        "VMM functional": result_competitive.vmm_result is not None
        and result_coordinated.vmm_result is not None,
        "Crypto moments functional": moments_competitive is not None
        and moments_coordinated is not None,
        "Risk classification fixed": result_competitive.risk_classification
        in ["LOW", "AMBER", "RED"],
        "Distinction achieved": distinction_achieved,
        "Diagnostic outputs": report is not None and len(report) > 0,
    }

    all_passed = True
    for criterion, passed in success_criteria.items():
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"   {status} {criterion}")
        if not passed:
            all_passed = False

    print("\n" + "=" * 60)
    if all_passed:
        print("🎉 PHASE 1 IMPLEMENTATION SUCCESSFUL!")
        print("All success criteria met. Ready for Phase 2.")
    else:
        print("❌ PHASE 1 IMPLEMENTATION NEEDS WORK")
        print("Some success criteria not met. Review and fix issues.")
    print("=" * 60)

    return all_passed


if __name__ == "__main__":
    try:
        success = test_phase1_implementation()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)
