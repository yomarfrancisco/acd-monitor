"""
Diagnostic Layers Integration

Combines VMM, ICP, lead-lag, and mirroring validation layers into unified diagnostics.
"""

import logging
from pathlib import Path
from typing import Any, Dict

import pandas as pd

from ..data.synthetic_crypto import CryptoMarketConfig
from ..icp.engine import ICPConfig, ICPEngine
from ..validation.lead_lag import LeadLagValidator
from ..validation.mirroring import MirroringValidator
from ..vmm.crypto_moments import CryptoMomentCalculator, CryptoMomentConfig
from ..vmm.engine import VMMConfig, VMMEngine
from ..vmm.scalers import GlobalMomentScaler

logger = logging.getLogger(__name__)


class DiagnosticLayersAnalyzer:
    """Integrates all diagnostic layers for comprehensive analysis"""

    def __init__(self, base_config: CryptoMarketConfig):
        self.base_config = base_config
        self.layer_results = {}

    def run_diagnostic_layers(
        self, competitive_data: pd.DataFrame, coordinated_data: pd.DataFrame, seed: int = 42
    ) -> Dict[str, Any]:
        """
        Run all diagnostic layers on both scenarios

        Args:
            competitive_data: Competitive scenario data
            coordinated_data: Coordinated scenario data
            seed: Random seed for reproducibility

        Returns:
            Dictionary with results from all layers
        """
        logger.info("Running comprehensive diagnostic layers analysis")

        price_columns = [col for col in competitive_data.columns if col.startswith("Exchange_")]

        # Initialize analyzers
        global_scaler = GlobalMomentScaler(method="minmax")
        crypto_config = CryptoMomentConfig()
        crypto_calculator = CryptoMomentCalculator(crypto_config, global_scaler)
        vmm_config = VMMConfig()
        vmm_engine = VMMEngine(vmm_config, crypto_calculator)

        icp_config = ICPConfig()
        icp_engine = ICPEngine(icp_config)

        lead_lag_analyzer = LeadLagValidator()
        mirroring_analyzer = MirroringValidator()

        # Run VMM analysis
        logger.info("Running VMM analysis")
        competitive_vmm = vmm_engine.run_vmm(
            competitive_data, price_columns, environment_column="volatility_regime", seed=seed
        )
        coordinated_vmm = vmm_engine.run_vmm(
            coordinated_data, price_columns, environment_column="volatility_regime", seed=seed
        )

        # Run ICP analysis
        logger.info("Running ICP analysis")
        competitive_icp = icp_engine.run_icp(
            competitive_data, price_columns, environment_column="volatility_regime"
        )
        coordinated_icp = icp_engine.run_icp(
            coordinated_data, price_columns, environment_column="volatility_regime"
        )

        # Run lead-lag analysis
        logger.info("Running lead-lag analysis")
        competitive_lead_lag = lead_lag_analyzer.analyze_lead_lag(competitive_data, price_columns)
        coordinated_lead_lag = lead_lag_analyzer.analyze_lead_lag(coordinated_data, price_columns)

        # Run mirroring analysis
        logger.info("Running mirroring analysis")
        competitive_mirroring = mirroring_analyzer.analyze_mirroring(
            competitive_data, price_columns
        )
        coordinated_mirroring = mirroring_analyzer.analyze_mirroring(
            coordinated_data, price_columns
        )

        # Compile results
        self.layer_results = {
            "vmm": {
                "competitive": {
                    "J": competitive_vmm.over_identification_stat,
                    "p": competitive_vmm.over_identification_p_value,
                    "stability": competitive_vmm.structural_stability,
                },
                "coordinated": {
                    "J": coordinated_vmm.over_identification_stat,
                    "p": coordinated_vmm.over_identification_p_value,
                    "stability": coordinated_vmm.structural_stability,
                },
            },
            "icp": {
                "competitive": {
                    "p": competitive_icp.invariance_p_value,
                    "power": competitive_icp.power,
                    "reject": competitive_icp.invariance_p_value < 0.05,
                },
                "coordinated": {
                    "p": coordinated_icp.invariance_p_value,
                    "power": coordinated_icp.power,
                    "reject": coordinated_icp.invariance_p_value < 0.05,
                },
            },
            "lead_lag": {
                "competitive": {
                    "persistence": getattr(competitive_lead_lag, "persistence", 0.0),
                    "switching_entropy": getattr(competitive_lead_lag, "switching_entropy", 1.0),
                    "significant_windows": getattr(
                        competitive_lead_lag, "significant_windows", 0.0
                    ),
                },
                "coordinated": {
                    "persistence": getattr(coordinated_lead_lag, "persistence", 0.0),
                    "switching_entropy": getattr(coordinated_lead_lag, "switching_entropy", 1.0),
                    "significant_windows": getattr(
                        coordinated_lead_lag, "significant_windows", 0.0
                    ),
                },
            },
            "mirroring": {
                "competitive": {
                    "median_ratio": getattr(competitive_mirroring, "median_ratio", 0.0),
                    "high_mirroring_fraction": getattr(
                        competitive_mirroring, "high_mirroring_fraction", 0.0
                    ),
                    "cosine_similarity": getattr(competitive_mirroring, "cosine_similarity", 0.0),
                },
                "coordinated": {
                    "median_ratio": getattr(coordinated_mirroring, "median_ratio", 0.0),
                    "high_mirroring_fraction": getattr(
                        coordinated_mirroring, "high_mirroring_fraction", 0.0
                    ),
                    "cosine_similarity": getattr(coordinated_mirroring, "cosine_similarity", 0.0),
                },
            },
        }

        return self.layer_results

    def calculate_consistency_score(self) -> float:
        """
        Calculate consistency score (0-1) based on expected directional relationships

        Returns:
            Consistency score where 1.0 indicates perfect consistency with expected patterns
        """
        if not self.layer_results:
            return 0.0

        consistency_checks = []

        # VMM: coordinated should have higher J and lower p
        vmm_comp = self.layer_results["vmm"]["competitive"]
        vmm_coord = self.layer_results["vmm"]["coordinated"]

        vmm_j_consistent = vmm_coord["J"] > vmm_comp["J"]
        vmm_p_consistent = vmm_coord["p"] < vmm_comp["p"]
        consistency_checks.extend([vmm_j_consistent, vmm_p_consistent])

        # ICP: coordinated should reject invariance (lower p)
        icp_comp = self.layer_results["icp"]["competitive"]
        icp_coord = self.layer_results["icp"]["coordinated"]

        icp_p_consistent = icp_coord["p"] < icp_comp["p"]
        consistency_checks.append(icp_p_consistent)

        # Lead-lag: coordinated should have higher persistence and lower switching entropy
        ll_comp = self.layer_results["lead_lag"]["competitive"]
        ll_coord = self.layer_results["lead_lag"]["coordinated"]

        ll_persistence_consistent = ll_coord["persistence"] > ll_comp["persistence"]
        ll_entropy_consistent = ll_coord["switching_entropy"] < ll_comp["switching_entropy"]
        consistency_checks.extend([ll_persistence_consistent, ll_entropy_consistent])

        # Mirroring: coordinated should have higher mirroring ratios
        mir_comp = self.layer_results["mirroring"]["competitive"]
        mir_coord = self.layer_results["mirroring"]["coordinated"]

        mir_ratio_consistent = mir_coord["median_ratio"] > mir_comp["median_ratio"]
        mir_fraction_consistent = (
            mir_coord["high_mirroring_fraction"] > mir_comp["high_mirroring_fraction"]
        )
        consistency_checks.extend([mir_ratio_consistent, mir_fraction_consistent])

        # Calculate overall consistency score
        consistency_score = sum(consistency_checks) / len(consistency_checks)

        return consistency_score

    def apply_bh_fdr_correction(self, alpha: float = 0.05) -> Dict[str, float]:
        """
        Apply Benjamini-Hochberg FDR correction to p-values

        Args:
            alpha: Significance level

        Returns:
            Dictionary with corrected q-values
        """
        if not self.layer_results:
            return {}

        # Collect all p-values
        p_values = []
        layer_names = []

        # VMM p-values
        p_values.extend(
            [
                self.layer_results["vmm"]["competitive"]["p"],
                self.layer_results["vmm"]["coordinated"]["p"],
            ]
        )
        layer_names.extend(["vmm_competitive", "vmm_coordinated"])

        # ICP p-values
        p_values.extend(
            [
                self.layer_results["icp"]["competitive"]["p"],
                self.layer_results["icp"]["coordinated"]["p"],
            ]
        )
        layer_names.extend(["icp_competitive", "icp_coordinated"])

        # Apply BH correction
        from scipy.stats import false_discovery_control

        q_values = false_discovery_control(p_values, alpha=alpha)

        # Create result dictionary
        bh_results = {}
        for i, layer_name in enumerate(layer_names):
            bh_results[layer_name] = {
                "p_value": p_values[i],
                "q_value": q_values[i],
                "significant": q_values[i] < alpha,
            }

        return bh_results

    def save_report(self, output_path: str) -> None:
        """Save comprehensive diagnostic layers report"""
        if not self.layer_results:
            logger.warning("No results to save")
            return

        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)

        # Calculate consistency score
        consistency_score = self.calculate_consistency_score()

        # Apply BH FDR correction
        bh_results = self.apply_bh_fdr_correction()

        # Generate report
        report = f"""# Diagnostic Layers Analysis Report

## Summary
- **Consistency Score**: {consistency_score:.3f} (0-1 scale, higher is better)
- **Expected Pattern**: Coordinated scenarios should show higher J, lower p, higher persistence, lower entropy, higher mirroring

## Layer Results

### VMM (Variational Method of Moments)
| Scenario | J-statistic | p-value | Stability | BH q-value | Significant |
|----------|-------------|---------|-----------|------------|-------------|
| Competitive | {self.layer_results['vmm']['competitive']['J']:.3f} | {self.layer_results['vmm']['competitive']['p']:.3f} | {self.layer_results['vmm']['competitive']['stability']:.3f} | {bh_results.get('vmm_competitive', {}).get('q_value', 'N/A'):.3f} | {'✅' if bh_results.get('vmm_competitive', {}).get('significant', False) else '❌'} |
| Coordinated | {self.layer_results['vmm']['coordinated']['J']:.3f} | {self.layer_results['vmm']['coordinated']['p']:.3f} | {self.layer_results['vmm']['coordinated']['stability']:.3f} | {bh_results.get('vmm_coordinated', {}).get('q_value', 'N/A'):.3f} | {'✅' if bh_results.get('vmm_coordinated', {}).get('significant', False) else '❌'} |

**Alternative Explanations**: High J-statistics may indicate structural breaks, regime changes, or model misspecification rather than coordination.

### ICP (Invariant Causal Prediction)
| Scenario | p-value | Power | Reject H0 | BH q-value | Significant |
|----------|---------|-------|-----------|------------|-------------|
| Competitive | {self.layer_results['icp']['competitive']['p']:.3f} | {self.layer_results['icp']['competitive']['power']:.3f} | {'✅' if self.layer_results['icp']['competitive']['reject'] else '❌'} | {bh_results.get('icp_competitive', {}).get('q_value', 'N/A'):.3f} | {'✅' if bh_results.get('icp_competitive', {}).get('significant', False) else '❌'} |
| Coordinated | {self.layer_results['icp']['coordinated']['p']:.3f} | {self.layer_results['icp']['coordinated']['power']:.3f} | {'✅' if self.layer_results['icp']['coordinated']['reject'] else '❌'} | {bh_results.get('icp_coordinated', {}).get('q_value', 'N/A'):.3f} | {'✅' if bh_results.get('icp_coordinated', {}).get('significant', False) else '❌'} |

**Alternative Explanations**: Invariance rejection may be due to market structure changes, regulatory events, or technological disruptions.

### Lead-Lag Analysis
| Scenario | Persistence | Switching Entropy | Significant Windows | Expected Direction |
|----------|-------------|-------------------|-------------------|-------------------|
| Competitive | {self.layer_results['lead_lag']['competitive']['persistence']:.3f} | {self.layer_results['lead_lag']['competitive']['switching_entropy']:.3f} | {self.layer_results['lead_lag']['competitive']['significant_windows']:.3f} | Baseline |
| Coordinated | {self.layer_results['lead_lag']['coordinated']['persistence']:.3f} | {self.layer_results['lead_lag']['coordinated']['switching_entropy']:.3f} | {self.layer_results['lead_lag']['coordinated']['significant_windows']:.3f} | ↑ Persistence, ↓ Entropy |

**Alternative Explanations**: Persistent lead-lag patterns may reflect information flow, latency differences, or market maker strategies.

### Mirroring Analysis
| Scenario | Median Ratio | High Mirroring % | Cosine Similarity | Expected Direction |
|----------|--------------|------------------|-------------------|-------------------|
| Competitive | {self.layer_results['mirroring']['competitive']['median_ratio']:.3f} | {self.layer_results['mirroring']['competitive']['high_mirroring_fraction']:.3f} | {self.layer_results['mirroring']['competitive']['cosine_similarity']:.3f} | Baseline |
| Coordinated | {self.layer_results['mirroring']['coordinated']['median_ratio']:.3f} | {self.layer_results['mirroring']['coordinated']['high_mirroring_fraction']:.3f} | {self.layer_results['mirroring']['coordinated']['cosine_similarity']:.3f} | ↑ Ratios |

**Alternative Explanations**: High mirroring may result from common market data feeds, similar algorithms, or competitive responses.

## Consistency Analysis
- **Overall Consistency Score**: {consistency_score:.3f}/1.0
- **Interpretation**: {'High consistency with expected coordination patterns' if consistency_score > 0.7 else 'Moderate consistency' if consistency_score > 0.5 else 'Low consistency with expected patterns'}

## Recommendations
- {'✅ Strong evidence of coordination patterns' if consistency_score > 0.7 else '⚠️ Mixed evidence, investigate alternative explanations' if consistency_score > 0.5 else '❌ Weak evidence, likely competitive behavior'}
- Consider additional validation layers (HMM, information flow) for stronger evidence
- Review alternative explanations for each significant signal
"""

        with open(output_file, "w") as f:
            f.write(report)

        logger.info(f"Diagnostic layers report saved to {output_file}")
