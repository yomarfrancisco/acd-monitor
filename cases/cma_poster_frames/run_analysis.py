"""
CMA Poster Frames Case Study - ACD Analysis Pipeline

This module runs the complete ACD analysis on the CMA Poster Frames dataset,
applying ICP, VMM, and validation layers to detect coordination patterns.
"""

import sys
from pathlib import Path
import pandas as pd
import numpy as np
import json
from datetime import datetime
from typing import Dict, Any, List

# Add src to path for imports
sys.path.append(str(Path(__file__).parent.parent.parent))

from src.acd.icp.engine import ICPEngine, ICPConfig
from src.acd.vmm.engine import VMMEngine, VMMConfig
from src.acd.vmm.crypto_moments import CryptoMomentCalculator, CryptoMomentConfig
from src.acd.analytics.integrated_engine import IntegratedACDEngine, IntegratedConfig
from src.acd.validation.lead_lag import LeadLagValidator, LeadLagConfig
from src.acd.validation.mirroring import MirroringValidator, MirroringConfig
from src.acd.validation.hmm import HMMValidator, HMMConfig
from src.acd.validation.infoflow import InfoFlowValidator, InfoFlowConfig


class CMAPosterFramesAnalyzer:
    """Analyze CMA Poster Frames data using ACD framework"""

    def __init__(self, seed: int = 42):
        self.seed = seed
        self.data = None
        self.results = {}

        # Initialize ACD engines
        self._initialize_engines()

    def _initialize_engines(self):
        """Initialize ACD analysis engines"""

        # ICP Configuration
        self.icp_config = ICPConfig(
            significance_level=0.05,
            n_bootstrap=1000,
            min_samples_per_env=20,
            environment_columns=["environment"],
        )
        self.icp_engine = ICPEngine(self.icp_config)

        # VMM Configuration
        self.vmm_config = VMMConfig(max_iterations=1000, convergence_tolerance=1e-6)
        self.crypto_config = CryptoMomentConfig(
            max_lag=10, lead_lag_threshold=0.1, mirroring_window=5, mirroring_threshold=0.8
        )
        self.crypto_calculator = CryptoMomentCalculator(self.crypto_config)
        self.vmm_engine = VMMEngine(self.vmm_config, self.crypto_calculator)

        # Validation Layer Configurations
        self.lead_lag_config = LeadLagConfig(window_size=30, max_lag=5, significance_level=0.05)
        self.lead_lag_validator = LeadLagValidator(self.lead_lag_config)

        self.mirroring_config = MirroringConfig(
            top_k_levels=5, similarity_threshold=0.7, window_size=30
        )
        self.mirroring_validator = MirroringValidator(self.mirroring_config)

        self.hmm_config = HMMConfig(n_states=3, window_size=100, max_iterations=100)
        self.hmm_validator = HMMValidator(self.hmm_config)

        self.infoflow_config = InfoFlowConfig(max_lag=5, n_bins=10, significance_level=0.05)
        self.infoflow_validator = InfoFlowValidator(self.infoflow_config)

        # Integrated Engine
        self.integrated_config = IntegratedConfig(
            icp_config=self.icp_config,
            vmm_config=self.vmm_config,
            crypto_moments_config=self.crypto_config,
            icp_weight=0.4,
            vmm_weight=0.4,
            crypto_moments_weight=0.2,
        )
        self.integrated_engine = IntegratedACDEngine(self.integrated_config)

    def load_data(self, data_path: Path) -> pd.DataFrame:
        """Load CMA Poster Frames dataset"""

        print(f"Loading CMA Poster Frames data from: {data_path}")

        # Load CSV data
        self.data = pd.read_csv(data_path)
        self.data["date"] = pd.to_datetime(self.data["date"])

        # Prepare data for ACD analysis
        self.data = self._prepare_data_for_acd()

        print(f"Loaded {len(self.data)} records")
        print(f"Date range: {self.data['date'].min()} to {self.data['date'].max()}")
        print(f"Airlines: {', '.join(self.data['airline'].unique())}")

        return self.data

    def _prepare_data_for_acd(self) -> pd.DataFrame:
        """Prepare data for ACD analysis"""

        df = self.data.copy()

        # Keep original format for ACD analysis
        # Add environment column for ACD
        df["environment"] = df["coordination_period"]

        # Add derived features
        df["volatility_regime"] = df["coordination_strength"].apply(
            lambda x: (
                "high_coordination"
                if x > 0.7
                else "medium_coordination" if x > 0.3 else "competitive"
            )
        )

        # Add market condition
        df["market_condition"] = df["market_event"].apply(
            lambda x: "event" if x != "normal" else "normal"
        )

        return df

    def run_icp_analysis(self) -> Dict[str, Any]:
        """Run ICP analysis on CMA data"""

        print("\nRunning ICP analysis...")

        # Create price matrix (airlines as columns, dates as rows)
        price_matrix = self.data.pivot(index="date", columns="airline", values="price")

        # Add environment columns
        env_data = (
            self.data.groupby("date")
            .agg(
                {"environment": "first", "coordination_strength": "first", "market_event": "first"}
            )
            .reset_index()
        )

        # Merge environment data
        icp_data = price_matrix.merge(env_data, left_index=True, right_on="date")

        # Prepare data for ICP
        price_columns = ["BA", "VS", "EI", "FR"]

        # Run ICP
        from src.acd.icp.engine import run_icp_analysis

        icp_result = run_icp_analysis(
            data=icp_data, price_columns=price_columns, config=self.icp_config
        )

        self.results["icp"] = icp_result

        print(f"ICP Analysis Complete:")
        print(f"  - Environments tested: {icp_result.n_environments}")
        print(f"  - Invariance rejected: {icp_result.reject_h0}")
        print(f"  - P-value: {icp_result.p_value}")

        return icp_result

    def run_vmm_analysis(self) -> Dict[str, Any]:
        """Run VMM analysis on CMA data"""

        print("\nRunning VMM analysis...")

        # Create price matrix (airlines as columns, dates as rows)
        price_matrix = self.data.pivot(index="date", columns="airline", values="price")

        # Add environment columns
        env_data = (
            self.data.groupby("date")
            .agg(
                {"environment": "first", "coordination_strength": "first", "market_event": "first"}
            )
            .reset_index()
        )

        # Merge environment data
        vmm_data = price_matrix.merge(env_data, left_index=True, right_on="date")

        # Prepare data for VMM
        price_columns = ["BA", "VS", "EI", "FR"]

        # Run VMM
        vmm_result = self.vmm_engine.run_vmm(
            data=vmm_data,
            price_columns=price_columns,
            environment_column="environment",
            seed=self.seed,
        )

        self.results["vmm"] = vmm_result

        print(f"VMM Analysis Complete:")
        print(f"  - J-statistic: {getattr(vmm_result, 'j_statistic', 'N/A')}")
        print(f"  - P-value: {getattr(vmm_result, 'p_value', 'N/A')}")
        print(f"  - Stability: {getattr(vmm_result, 'stability', 'N/A')}")

        return vmm_result

    def run_validation_layers(self) -> Dict[str, Any]:
        """Run validation layers on CMA data"""

        print("\nRunning validation layers...")

        # Create price matrix (airlines as columns, dates as rows)
        price_matrix = self.data.pivot(index="date", columns="airline", values="price")

        # Add environment columns
        env_data = (
            self.data.groupby("date")
            .agg(
                {"environment": "first", "coordination_strength": "first", "market_event": "first"}
            )
            .reset_index()
        )

        # Merge environment data
        validation_data = price_matrix.merge(env_data, left_index=True, right_on="date")

        validation_results = {}

        # Lead-lag analysis
        print("  - Lead-lag analysis...")
        lead_lag_result = self.lead_lag_validator.analyze_lead_lag(
            data=validation_data,
            price_columns=["BA", "VS", "EI", "FR"],
            environment_column="environment",
        )
        validation_results["lead_lag"] = lead_lag_result

        # Mirroring analysis
        print("  - Mirroring analysis...")
        mirroring_result = self.mirroring_validator.analyze_mirroring(
            data=validation_data,
            price_columns=["BA", "VS", "EI", "FR"],
            environment_column="environment",
        )
        validation_results["mirroring"] = mirroring_result

        # HMM analysis
        print("  - HMM analysis...")
        hmm_result = self.hmm_validator.analyze_hmm(
            data=validation_data,
            price_columns=["BA", "VS", "EI", "FR"],
            environment_column="environment",
        )
        validation_results["hmm"] = hmm_result

        # Information flow analysis
        print("  - Information flow analysis...")
        infoflow_result = self.infoflow_validator.analyze_infoflow(
            data=validation_data,
            price_columns=["BA", "VS", "EI", "FR"],
            environment_column="environment",
        )
        validation_results["infoflow"] = infoflow_result

        self.results["validation"] = validation_results

        print("Validation layers complete")
        return validation_results

    def run_integrated_analysis(self) -> Dict[str, Any]:
        """Run integrated ACD analysis"""

        print("\nRunning integrated ACD analysis...")

        # Create price matrix (airlines as columns, dates as rows)
        price_matrix = self.data.pivot(index="date", columns="airline", values="price")

        # Add environment columns
        env_data = (
            self.data.groupby("date")
            .agg(
                {"environment": "first", "coordination_strength": "first", "market_event": "first"}
            )
            .reset_index()
        )

        # Merge environment data
        integrated_data = price_matrix.merge(env_data, left_index=True, right_on="date")

        # Prepare data for integrated analysis
        price_columns = ["BA", "VS", "EI", "FR"]

        # Run integrated analysis
        from src.acd.analytics.integrated_engine import run_integrated_analysis

        integrated_result = run_integrated_analysis(
            data=integrated_data, price_columns=price_columns, config=self.integrated_config
        )

        self.results["integrated"] = integrated_result

        print(f"Integrated Analysis Complete:")
        print(f"  - Composite Score: {getattr(integrated_result, 'composite_score', 'N/A')}")
        print(f"  - Risk Band: {getattr(integrated_result, 'risk_band', 'N/A')}")
        print(
            f"  - Coordination Detected: {getattr(integrated_result, 'coordination_detected', 'N/A')}"
        )

        return integrated_result

    def generate_summary_report(self) -> Dict[str, Any]:
        """Generate summary report of all analyses"""

        print("\nGenerating summary report...")

        # Extract key metrics
        icp_result = self.results.get("icp", {})
        vmm_result = self.results.get("vmm", {})
        validation_results = self.results.get("validation", {})
        integrated_result = self.results.get("integrated", {})

        # Coordination period analysis
        coordination_analysis = self._analyze_coordination_periods()

        # Market event analysis
        event_analysis = self._analyze_market_events()

        summary = {
            "analysis_info": {
                "case_study": "CMA Poster Frames",
                "analysis_date": datetime.now().isoformat(),
                "seed": self.seed,
                "n_records": len(self.data),
                "date_range": {
                    "start": self.data["date"].min().isoformat(),
                    "end": self.data["date"].max().isoformat(),
                },
            },
            "icp_results": {
                "invariance_rejected": getattr(icp_result, "reject_h0", False),
                "p_value": getattr(icp_result, "p_value", None),
                "environments_tested": getattr(icp_result, "n_environments", 0),
                "power": getattr(icp_result, "power", None),
            },
            "vmm_results": {
                "j_statistic": getattr(vmm_result, "j_statistic", None),
                "p_value": getattr(vmm_result, "p_value", None),
                "stability": getattr(vmm_result, "stability", None),
                "convergence_achieved": getattr(vmm_result, "convergence_achieved", False),
            },
            "validation_results": {
                "lead_lag": {
                    "persistence_score": (
                        getattr(validation_results.get("lead_lag"), "persistence_score", None)
                        if validation_results.get("lead_lag")
                        else None
                    ),
                    "switching_entropy": (
                        getattr(validation_results.get("lead_lag"), "switching_entropy", None)
                        if validation_results.get("lead_lag")
                        else None
                    ),
                },
                "mirroring": {
                    "mirroring_ratio": (
                        getattr(validation_results.get("mirroring"), "mirroring_ratio", None)
                        if validation_results.get("mirroring")
                        else None
                    ),
                    "coordination_score": (
                        getattr(validation_results.get("mirroring"), "coordination_score", None)
                        if validation_results.get("mirroring")
                        else None
                    ),
                },
                "hmm": {
                    "n_states": (
                        getattr(validation_results.get("hmm"), "n_states", None)
                        if validation_results.get("hmm")
                        else None
                    ),
                    "dwell_times": (
                        getattr(validation_results.get("hmm"), "dwell_times", None)
                        if validation_results.get("hmm")
                        else None
                    ),
                },
                "infoflow": {
                    "transfer_entropy": (
                        getattr(validation_results.get("infoflow"), "transfer_entropy", None)
                        if validation_results.get("infoflow")
                        else None
                    ),
                    "network_concentration": (
                        getattr(validation_results.get("infoflow"), "network_concentration", None)
                        if validation_results.get("infoflow")
                        else None
                    ),
                },
            },
            "integrated_results": {
                "composite_score": getattr(integrated_result, "composite_score", None),
                "risk_band": getattr(integrated_result, "risk_band", None),
                "coordination_detected": getattr(integrated_result, "coordination_detected", None),
                "confidence_level": getattr(integrated_result, "confidence_level", None),
            },
            "coordination_analysis": coordination_analysis,
            "market_event_analysis": event_analysis,
            "key_findings": self._generate_key_findings(),
            "recommendations": self._generate_recommendations(),
        }

        self.results["summary"] = summary
        return summary

    def _analyze_coordination_periods(self) -> Dict[str, Any]:
        """Analyze coordination periods"""

        coordination_periods = self.data[self.data["coordination_strength"] > 0]

        if len(coordination_periods) == 0:
            return {"coordination_detected": False, "periods": []}

        periods = []
        for period in coordination_periods["coordination_period"].unique():
            period_data = coordination_periods[
                coordination_periods["coordination_period"] == period
            ]

            # Calculate average price and volatility from long format data
            avg_price = float(period_data["price"].mean())
            price_volatility = float(period_data["price"].std())

            periods.append(
                {
                    "period": period,
                    "start_date": period_data["date"].min().isoformat(),
                    "end_date": period_data["date"].max().isoformat(),
                    "strength": float(period_data["coordination_strength"].mean()),
                    "avg_price": avg_price,
                    "price_volatility": price_volatility,
                }
            )

        return {
            "coordination_detected": True,
            "n_periods": len(periods),
            "total_coordination_days": len(coordination_periods),
            "periods": periods,
        }

    def _analyze_market_events(self) -> Dict[str, Any]:
        """Analyze market events"""

        events = self.data[self.data["market_event"] != "normal"]

        if len(events) == 0:
            return {"events_detected": False, "events": []}

        event_analysis = []
        for event in events["market_event"].unique():
            event_data = events[events["market_event"] == event]

            # Calculate average price from long format data
            avg_price = float(event_data["price"].mean())
            normal_price = float(self.data[self.data["market_event"] == "normal"]["price"].mean())

            event_analysis.append(
                {
                    "event": event,
                    "start_date": event_data["date"].min().isoformat(),
                    "end_date": event_data["date"].max().isoformat(),
                    "impact": float(event_data["event_impact"].mean()),
                    "avg_price": avg_price,
                    "price_change": avg_price - normal_price,
                }
            )

        return {"events_detected": True, "n_events": len(event_analysis), "events": event_analysis}

    def _generate_key_findings(self) -> List[str]:
        """Generate key findings from analysis"""

        findings = []

        # ICP findings
        icp_result = self.results.get("icp")
        if getattr(icp_result, "reject_h0", False):
            findings.append(
                "ICP analysis rejected invariance hypothesis, indicating coordination patterns"
            )
        else:
            findings.append(
                "ICP analysis failed to reject invariance hypothesis, suggesting competitive behavior"
            )

        # VMM findings
        vmm_result = self.results.get("vmm")
        if getattr(vmm_result, "p_value", 1) < 0.05:
            findings.append(
                "VMM analysis detected structural instability, consistent with coordination"
            )
        else:
            findings.append(
                "VMM analysis found structural stability, consistent with competitive behavior"
            )

        # Validation findings
        validation_results = self.results.get("validation", {})
        lead_lag_result = validation_results.get("lead_lag")
        if getattr(lead_lag_result, "persistence_score", 0) > 0.7:
            findings.append("Lead-lag analysis detected persistent price leadership patterns")

        mirroring_result = validation_results.get("mirroring")
        if getattr(mirroring_result, "mirroring_ratio", 0) > 0.6:
            findings.append("Mirroring analysis detected high price similarity between airlines")

        # Coordination periods
        coordination_analysis = self.results.get("summary", {}).get("coordination_analysis", {})
        if coordination_analysis.get("coordination_detected", False):
            findings.append(
                f"Detected {coordination_analysis.get('n_periods', 0)} coordination periods"
            )

        return findings

    def _generate_recommendations(self) -> List[str]:
        """Generate recommendations based on analysis"""

        recommendations = []

        # Risk-based recommendations
        integrated_result = self.results.get("integrated")
        risk_band = getattr(integrated_result, "risk_band", "UNKNOWN")

        if risk_band == "RED":
            recommendations.append(
                "High coordination risk detected - recommend immediate regulatory investigation"
            )
        elif risk_band == "AMBER":
            recommendations.append(
                "Medium coordination risk detected - recommend enhanced monitoring"
            )
        else:
            recommendations.append("Low coordination risk - continue routine monitoring")

        # Methodology recommendations
        recommendations.append("Validate findings with additional data sources and time periods")
        recommendations.append("Consider alternative explanations for observed patterns")
        recommendations.append("Implement ongoing monitoring system for early detection")

        return recommendations

    def save_results(self, output_dir: Path):
        """Save analysis results"""

        output_dir.mkdir(parents=True, exist_ok=True)

        # Save summary report
        summary_path = output_dir / f"cma_poster_frames_analysis_summary_seed_{self.seed}.json"
        with open(summary_path, "w") as f:
            json.dump(self.results.get("summary", {}), f, indent=2, default=str)

        # Save detailed results
        results_path = output_dir / f"cma_poster_frames_analysis_results_seed_{self.seed}.json"
        with open(results_path, "w") as f:
            json.dump(self.results, f, indent=2, default=str)

        print(f"\nResults saved to:")
        print(f"  - Summary: {summary_path}")
        print(f"  - Detailed: {results_path}")

        return summary_path, results_path


def main():
    """Run CMA Poster Frames analysis"""

    # Configuration
    seed = 42
    data_dir = Path("cases/cma_poster_frames/data")
    results_dir = Path("cases/cma_poster_frames/artifacts")

    # Initialize analyzer
    analyzer = CMAPosterFramesAnalyzer(seed=seed)

    # Load data
    data_path = data_dir / f"cma_poster_frames_data_seed_{seed}.csv"
    if not data_path.exists():
        print(f"Data file not found: {data_path}")
        print("Please run prepare_data.py first to generate the dataset")
        return

    analyzer.load_data(data_path)

    # Run analyses
    analyzer.run_icp_analysis()
    analyzer.run_vmm_analysis()
    analyzer.run_validation_layers()
    analyzer.run_integrated_analysis()

    # Generate summary
    summary = analyzer.generate_summary_report()

    # Save results
    analyzer.save_results(results_dir)

    # Print summary
    print("\n" + "=" * 60)
    print("CMA POSTER FRAMES ANALYSIS SUMMARY")
    print("=" * 60)
    print(f"Case Study: {summary['analysis_info']['case_study']}")
    print(f"Analysis Date: {summary['analysis_info']['analysis_date']}")
    print(f"Records Analyzed: {summary['analysis_info']['n_records']:,}")
    print(
        f"Date Range: {summary['analysis_info']['date_range']['start']} to {summary['analysis_info']['date_range']['end']}"
    )
    print()
    print("KEY RESULTS:")
    print(f"  ICP Invariance Rejected: {summary['icp_results']['invariance_rejected']}")
    vmm_p_value = summary["vmm_results"]["p_value"]
    print(f"  VMM P-value: {vmm_p_value:.4f}" if vmm_p_value is not None else "  VMM P-value: N/A")

    composite_score = summary["integrated_results"]["composite_score"]
    print(
        f"  Composite Score: {composite_score:.2f}"
        if composite_score is not None
        else "  Composite Score: N/A"
    )

    risk_band = summary["integrated_results"]["risk_band"]
    print(f"  Risk Band: {risk_band}" if risk_band is not None else "  Risk Band: N/A")

    coordination_detected = summary["integrated_results"]["coordination_detected"]
    print(
        f"  Coordination Detected: {coordination_detected}"
        if coordination_detected is not None
        else "  Coordination Detected: N/A"
    )
    print()
    print("COORDINATION ANALYSIS:")
    coord_analysis = summary["coordination_analysis"]
    if coord_analysis["coordination_detected"]:
        print(f"  Coordination Periods: {coord_analysis['n_periods']}")
        print(f"  Total Coordination Days: {coord_analysis['total_coordination_days']}")
    else:
        print("  No coordination periods detected")
    print()
    print("KEY FINDINGS:")
    for finding in summary["key_findings"]:
        print(f"  - {finding}")
    print()
    print("RECOMMENDATIONS:")
    for rec in summary["recommendations"]:
        print(f"  - {rec}")
    print("=" * 60)

    return analyzer


if __name__ == "__main__":
    analyzer = main()
