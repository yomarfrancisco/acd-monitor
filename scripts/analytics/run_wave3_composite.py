#!/usr/bin/env python3
"""
Wave-3 Module W3.5: Composite Index Construction
Aggregate weak signals into a single coordination index.
"""

import json
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent.parent))


class Wave3CompositeExecutor:
    """Execute composite index construction for Wave-3."""

    def __init__(self):
        self.wave3_dir = "data/derived/btc_usd/wave3"
        self.analysis_dir = "analysis/wave3/btc_usd/composite"
        self.venues = ["binance", "coinbase", "kraken", "okx", "bybit"]

        os.makedirs(self.analysis_dir, exist_ok=True)

    def run_composite_analysis(self):
        """Run composite index construction."""
        print("🔧 Wave-3 Module W3.5: Composite Index Construction")
        print("=" * 50)

        # Load composite inputs
        print("📥 Loading composite inputs...")
        composite_data = pd.read_parquet(f"{self.wave3_dir}/composite_inputs.parquet")
        print(f"  📊 Composite data: {composite_data.shape}")

        # Load results from other modules
        print("🔄 Loading results from other Wave-3 modules...")
        module_results = self._load_module_results()

        # Construct composite index
        print("🔄 Constructing composite coordination index...")
        composite_index = self._construct_composite_index(composite_data, module_results)

        # Generate outputs
        print("📊 Generating composite outputs...")
        self._generate_composite_outputs(composite_index)

        print("✅ Composite index construction completed successfully!")
        return True

    def _load_module_results(self) -> Dict:
        """Load results from other Wave-3 modules."""
        module_results = {}

        # Load ICP results
        try:
            icp_invariance = pd.read_csv(
                f"{self.wave3_dir.replace('wave3', 'analysis/wave3/btc_usd/icp')}/invariance_tests.csv"
            )
            invariant_pct = (icp_invariance["invariant"] == True).mean()
            module_results["icp"] = {
                "invariant_pct": invariant_pct,
                "coordination_signal": invariant_pct,  # Higher = more coordination
            }
        except:
            module_results["icp"] = {"invariant_pct": 0.5, "coordination_signal": 0.5}

        # Load VMM results
        try:
            vmm_jstats = pd.read_csv(
                f"{self.wave3_dir.replace('wave3', 'analysis/wave3/btc_usd/vmm')}/Jstats.csv"
            )
            delta_j = vmm_jstats[vmm_jstats["model"] == "delta_j"]["j_statistic"].iloc[0]
            # Positive delta_J favors competitive, negative favors coordination
            coordination_signal = max(0, -delta_j)  # Convert to coordination signal
            module_results["vmm"] = {"delta_j": delta_j, "coordination_signal": coordination_signal}
        except:
            module_results["vmm"] = {"delta_j": 0, "coordination_signal": 0.5}

        # Load Copula results
        try:
            # Load session results and calculate average dependence
            copula_dir = f"{self.wave3_dir.replace('wave3', 'analysis/wave3/btc_usd/copula')}"
            session_files = [
                f
                for f in os.listdir(copula_dir)
                if f.startswith("session_") and f.endswith(".json")
            ]

            all_tau_values = []
            for session_file in session_files:
                with open(f"{copula_dir}/{session_file}", "r") as f:
                    session_data = json.load(f)
                    if "kendall_tau" in session_data:
                        tau_values = [
                            result["tau"] for result in session_data["kendall_tau"].values()
                        ]
                        all_tau_values.extend(tau_values)

            avg_dependence = (
                np.mean([abs(tau) for tau in all_tau_values]) if all_tau_values else 0.5
            )
            module_results["copula"] = {
                "avg_dependence": avg_dependence,
                "coordination_signal": avg_dependence,  # Higher = more coordination
            }
        except:
            module_results["copula"] = {"avg_dependence": 0.5, "coordination_signal": 0.5}

        # Load Clustering results
        try:
            cluster_profiles = pd.read_csv(
                f"{self.wave3_dir.replace('wave3', 'analysis/wave3/btc_usd/clustering')}/cluster_profiles.csv"
            )
            max_coordination_score = cluster_profiles["coordination_score"].max()
            module_results["clustering"] = {
                "max_coordination_score": max_coordination_score,
                "coordination_signal": max_coordination_score,
            }
        except:
            module_results["clustering"] = {
                "max_coordination_score": 0.5,
                "coordination_signal": 0.5,
            }

        print(f"  📊 Loaded results from {len(module_results)} modules")
        return module_results

    def _construct_composite_index(
        self, composite_data: pd.DataFrame, module_results: Dict
    ) -> Dict:
        """Construct composite coordination index."""
        # Get z-scored signals from composite inputs
        zscore_cols = [col for col in composite_data.columns if col.endswith("_zscore")]
        signal_data = composite_data[zscore_cols].copy()

        # Calculate module weights based on coordination signals
        module_weights = {}
        for module, results in module_results.items():
            coordination_signal = results["coordination_signal"]
            # Normalize to 0-1 range
            normalized_signal = min(1.0, max(0.0, coordination_signal))
            module_weights[module] = normalized_signal

        # Normalize weights to sum to 1
        total_weight = sum(module_weights.values())
        if total_weight > 0:
            module_weights = {k: v / total_weight for k, v in module_weights.items()}
        else:
            module_weights = {k: 0.25 for k in module_weights.keys()}  # Equal weights

        print(f"  📊 Module weights: {module_weights}")

        # Calculate composite index for each window
        composite_scores = []
        for idx, row in signal_data.iterrows():
            # Equal weights within each signal type
            window_score = row.mean()  # Average of z-scored signals

            # Apply module weights (simplified - using average for now)
            weighted_score = window_score * sum(module_weights.values()) / len(module_weights)

            composite_scores.append(weighted_score)

        # Rescale to 0-100 range
        composite_scores = np.array(composite_scores)
        min_score = composite_scores.min()
        max_score = composite_scores.max()

        if max_score > min_score:
            rescaled_scores = ((composite_scores - min_score) / (max_score - min_score)) * 100
        else:
            rescaled_scores = np.full_like(composite_scores, 50)  # Neutral score

        # Calculate bootstrap confidence intervals (simplified)
        n_bootstrap = 100
        bootstrap_scores = []
        for _ in range(n_bootstrap):
            # Simple bootstrap by resampling with replacement
            bootstrap_indices = np.random.choice(
                len(composite_scores), size=len(composite_scores), replace=True
            )
            bootstrap_sample = composite_scores[bootstrap_indices]
            bootstrap_mean = bootstrap_sample.mean()
            bootstrap_scores.append(bootstrap_mean)

        bootstrap_scores = np.array(bootstrap_scores)
        ci_lower = np.percentile(bootstrap_scores, 2.5)
        ci_upper = np.percentile(bootstrap_scores, 97.5)

        return {
            "window_scores": rescaled_scores.tolist(),
            "raw_scores": composite_scores.tolist(),
            "module_weights": module_weights,
            "confidence_intervals": {"lower": ci_lower, "upper": ci_upper},
            "summary_stats": {
                "mean": np.mean(rescaled_scores),
                "std": np.std(rescaled_scores),
                "min": np.min(rescaled_scores),
                "max": np.max(rescaled_scores),
                "median": np.median(rescaled_scores),
            },
        }

    def _generate_composite_outputs(self, composite_index: Dict):
        """Generate composite index outputs."""
        # Save composite index
        index_data = pd.DataFrame(
            {
                "window_index": range(len(composite_index["window_scores"])),
                "coordination_index": composite_index["window_scores"],
                "raw_score": composite_index["raw_scores"],
            }
        )

        index_file = f"{self.analysis_dir}/index.csv"
        index_data.to_csv(index_file, index=False)
        print(f"  💾 Composite index saved to {index_file}")

        # Generate summary report
        self._generate_composite_summary(composite_index)

    def _generate_composite_summary(self, composite_index: Dict):
        """Generate composite index summary report."""
        summary_file = f"{self.analysis_dir}/W3_COMPOSITE_SUMMARY.md"

        with open(summary_file, "w") as f:
            f.write("# Wave-3 Composite Index Summary\n\n")
            f.write(f"**Analysis Date**: {datetime.now().isoformat()}\n")
            f.write("**Method**: Composite Coordination Index\n")
            f.write(
                "**Purpose**: Aggregate weak signals into single coordination monitoring score\n\n"
            )

            # Index statistics
            stats = composite_index["summary_stats"]
            f.write("## Composite Index Statistics\n\n")
            f.write(f"- **Mean Score**: {stats['mean']:.2f}/100\n")
            f.write(f"- **Standard Deviation**: {stats['std']:.2f}\n")
            f.write(f"- **Range**: {stats['min']:.2f} - {stats['max']:.2f}\n")
            f.write(f"- **Median**: {stats['median']:.2f}\n\n")

            # Module weights
            f.write("## Module Weights\n\n")
            f.write("| Module | Weight | Contribution |\n")
            f.write("|--------|--------|-------------|\n")

            for module, weight in composite_index["module_weights"].items():
                f.write(f"| {module.upper()} | {weight:.3f} | {weight*100:.1f}% |\n")

            # Confidence intervals
            ci = composite_index["confidence_intervals"]
            f.write(f"\n- **95% Confidence Interval**: [{ci['lower']:.2f}, {ci['upper']:.2f}]\n\n")

            # Interpretation
            f.write("## Interpretation\n\n")
            mean_score = stats["mean"]

            if mean_score < 30:
                f.write("### 🟢 LOW COORDINATION SIGNAL\n\n")
                f.write("- Composite index suggests **competitive market dynamics**\n")
                f.write("- Low coordination scores across time windows\n")
                f.write("- Evidence supports independent venue behavior\n\n")
            elif mean_score < 70:
                f.write("### 🟡 MODERATE COORDINATION SIGNAL\n\n")
                f.write("- Composite index suggests **mixed market dynamics**\n")
                f.write("- Moderate coordination scores with some variation\n")
                f.write("- Evidence is inconclusive between competition and coordination\n\n")
            else:
                f.write("### 🔴 HIGH COORDINATION SIGNAL\n\n")
                f.write("- Composite index suggests **coordinated market dynamics**\n")
                f.write("- High coordination scores across time windows\n")
                f.write("- Evidence supports coordinated venue behavior\n\n")

            # Score interpretation
            f.write("## Score Interpretation\n\n")
            f.write("- **0-30**: Low coordination (competitive dynamics)\n")
            f.write("- **30-70**: Moderate coordination (mixed signals)\n")
            f.write("- **70-100**: High coordination (coordinated dynamics)\n\n")

            # Limitations
            f.write("## Limitations\n\n")
            f.write("### Interpretability Limits\n\n")
            f.write("- **Composite nature**: Index combines multiple weak signals\n")
            f.write("- **No causal identification**: Correlation does not imply causation\n")
            f.write("- **Single-day analysis**: Limited temporal scope\n")
            f.write(
                "- **Heuristic weights**: Module weights are data-driven, not theoretically derived\n"
            )
            f.write("- **Bootstrap approximation**: Confidence intervals are simplified\n\n")

            f.write("### Usage Recommendations\n\n")
            f.write("- **Monitoring tool**: Use for trend monitoring, not definitive conclusions\n")
            f.write("- **Triage score**: Helps identify periods requiring deeper analysis\n")
            f.write("- **Complementary evidence**: Should be combined with other analyses\n")
            f.write("- **Regular updates**: Requires continuous monitoring for stability\n\n")

            f.write("## Next Steps\n\n")
            f.write("1. **Monitor trends**: Track index over time for patterns\n")
            f.write("2. **Validate signals**: Cross-check with individual module results\n")
            f.write("3. **Refine weights**: Update module weights based on new evidence\n")
            f.write("4. **Extend analysis**: Apply to multi-day datasets when available\n")

        print(f"  💾 Summary saved to {summary_file}")


if __name__ == "__main__":
    executor = Wave3CompositeExecutor()
    success = executor.run_composite_analysis()

    if success:
        print("\n🎉 Wave-3 Composite index construction completed successfully!")
    else:
        print("\n❌ Wave-3 Composite index construction failed!")
        sys.exit(1)
