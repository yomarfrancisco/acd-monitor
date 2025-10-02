#!/usr/bin/env python3
"""ACD Monitor Demo Pipeline Runner.

This script runs the complete ACD Monitor pipeline end-to-end using mock data,
producing calibration reports and evidence bundles for demonstration purposes.

Usage:
    python scripts/run_demo_pipeline.py

Outputs:
    - Calibration reports in demo/outputs/
    - Evidence bundle files in demo/outputs/
    - Pipeline execution summary
"""

import logging
import sys
import time
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from acd.demo.pipeline import DemoPipeline
from acd.demo.visualization import DemoVisualization
from acd.vmm.adaptive_thresholds import AdaptiveThresholdManager


def setup_logging():
    """Setup logging for the demo pipeline."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[logging.StreamHandler(sys.stdout), logging.FileHandler("demo/demo_pipeline.log")],
    )


def main():
    """Run the complete ACD Monitor demo pipeline."""
    print("🚀 ACD Monitor Demo Pipeline")
    print("=" * 50)

    # Setup logging
    setup_logging()
    logger = logging.getLogger(__name__)

    # Create output directory
    output_dir = Path("demo/outputs")
    output_dir.mkdir(parents=True, exist_ok=True)

    try:
        # Initialize pipeline
        logger.info("Initializing demo pipeline...")
        pipeline = DemoPipeline(output_dir=str(output_dir))
        visualization = DemoVisualization(output_dir=str(output_dir))

        # Run full pipeline
        logger.info("Starting pipeline execution...")
        start_time = time.time()

        pipeline_results = pipeline.run_full_pipeline()

        execution_time = time.time() - start_time

        # Check success
        if not pipeline_results["success"]:
            logger.error("Pipeline execution failed!")
            print("❌ Pipeline failed!")
            for error in pipeline_results.get("errors", []):
                print(f"   Error: {error}")
            return 1

        # Generate outputs
        logger.info("Generating demo outputs...")

        # 1. Calibration report
        feature_results = pipeline_results.get("feature_engineering_results", {})
        vmm_results = feature_results.get("vmm_results", [])
        quality_metrics = pipeline_results.get("ingestion_results", {}).get("quality_metrics", {})

        calibration_report = visualization.create_calibration_report(vmm_results, quality_metrics)
        calibration_path = visualization.save_demo_outputs(calibration_report, "calibration")

        # 2. Evidence bundle summary
        evidence_bundles = pipeline_results.get("evidence_bundles", [])
        evidence_summary = visualization.create_evidence_bundle_summary(evidence_bundles)
        evidence_path = visualization.save_demo_outputs(evidence_summary, "evidence")

        # 3. Demo dashboard data
        dashboard_data = visualization.generate_demo_dashboard_data(pipeline_results)
        dashboard_path = visualization.save_demo_outputs(dashboard_data, "dashboard")

        # Display results
        print("\n✅ Demo Pipeline Complete!")
        print(f"⏱️  Execution Time: {execution_time:.2f}s")

        # Pipeline summary
        pipeline_summary = pipeline.generate_pipeline_summary(pipeline_results)
        print("\n" + pipeline_summary)

        # Output files
        print(f"\n📁 Output Files Generated:")
        print(f"   • Calibration Report: {calibration_path}")
        print(f"   • Evidence Summary: {evidence_path}")
        print(f"   • Demo Dashboard: {dashboard_path}")

        # Check Week 3-4 baseline compliance
        print(f"\n🔍 Week 3-4 Baseline Compliance:")
        baseline_check = check_baseline_compliance(pipeline_results)
        for check, status in baseline_check.items():
            status_icon = "✅" if status else "❌"
            print(f"   {status_icon} {check}")

        # Success message
        if all(baseline_check.values()):
            print(
                f"\n🎉 All baseline requirements met! Demo pipeline ready for real-world transition."
            )
        else:
            print(f"\n⚠️  Some baseline requirements not met. Review before real-world deployment.")

        return 0

    except Exception as e:
        logger.error(f"Demo pipeline failed with error: {e}")
        print(f"❌ Demo pipeline failed: {e}")
        return 1


def check_baseline_compliance(pipeline_results: dict) -> dict:
    """Check compliance with Week 3-4 baseline requirements using adaptive thresholds."""
    baseline_checks = {}

    try:
        # Initialize adaptive threshold manager
        threshold_manager = AdaptiveThresholdManager()

        # Check VMM performance (Week 3 baseline)
        feature_results = pipeline_results.get("feature_engineering_results", {})
        vmm_results = feature_results.get("vmm_results", [])

        if vmm_results:
            # Check spurious regime rate using adaptive thresholds
            regime_confidences = [getattr(r, "regime_confidence", 0) for r in vmm_results]
            high_confidence_count = sum(1 for conf in regime_confidences if conf > 0.67)
            spurious_rate = (
                high_confidence_count / len(regime_confidences) if regime_confidences else 0
            )

            # Apply adaptive threshold based on dataset size
            dataset_size = len(regime_confidences)
            threshold_validation = threshold_manager.validate_spurious_rate(
                dataset_size, spurious_rate
            )

            threshold_description = f"≤{threshold_validation['threshold_applied']:.1%} ({threshold_validation['dataset_category']} dataset)"
            baseline_checks[f"Spurious regime rate {threshold_description}"] = threshold_validation[
                "passes"
            ]

            # Check structural stability (should be ≥ 0.6)
            structural_stabilities = [getattr(r, "structural_stability", 0) for r in vmm_results]
            avg_stability = (
                sum(structural_stabilities) / len(structural_stabilities)
                if structural_stabilities
                else 0
            )
            baseline_checks["Structural stability ≥ 0.6"] = avg_stability >= 0.6

            # Check convergence rate (should be ≥ 80%)
            convergence_statuses = [getattr(r, "convergence_status", "failed") for r in vmm_results]
            convergence_rate = sum(1 for s in convergence_statuses if s == "converged") / len(
                convergence_statuses
            )
            baseline_checks["VMM convergence rate ≥ 80%"] = convergence_rate >= 0.8

        # Check data quality (Week 4 baseline)
        ingestion_results = pipeline_results.get("ingestion_results", {})
        quality_metrics = ingestion_results.get("quality_metrics", {})

        if quality_metrics:
            all_scores = [m.get("overall_score", 0) for m in quality_metrics.values()]
            avg_quality = sum(all_scores) / len(all_scores) if all_scores else 0
            baseline_checks["Data quality metrics ≥ 0.8"] = avg_quality >= 0.8

        # Check execution time (should be < 1 minute)
        execution_time = pipeline_results.get("execution_time", 0)
        baseline_checks["Pipeline execution < 1 minute"] = execution_time < 60

        # Check output generation
        evidence_bundles = pipeline_results.get("evidence_bundles", [])
        calibration_reports = pipeline_results.get("calibration_reports", [])
        baseline_checks["Evidence bundles generated"] = len(evidence_bundles) > 0
        baseline_checks["Calibration reports generated"] = len(calibration_reports) > 0

        # Check adaptive threshold framework (Week 5: New)
        if evidence_bundles:
            first_bundle = evidence_bundles[0]
            threshold_profile = getattr(first_bundle, "adaptive_threshold_profile", None)
            baseline_checks["Adaptive threshold profile included"] = threshold_profile is not None

            # Check timestamping success rate (Week 5 Phase 3: New)
            timestamped_bundles = sum(
                1 for b in evidence_bundles if getattr(b, "timestamp_chain", None) is not None
            )
            timestamp_success_rate = (
                timestamped_bundles / len(evidence_bundles) if evidence_bundles else 0
            )
            baseline_checks["Timestamp success rate ≥ 99%"] = timestamp_success_rate >= 0.99

            # Check quality profile inclusion (Week 5 Phase 3: New)
            quality_profile_included = getattr(first_bundle, "quality_profile", None) is not None
            baseline_checks["Quality profile included"] = quality_profile_included

            # Check quality score against profile minimum (Week 5 Phase 3: New)
            if quality_profile_included and hasattr(first_bundle, "data_quality"):
                quality_scores = {
                    "overall_score": getattr(first_bundle.data_quality, "overall_score", 0)
                }
                profile = first_bundle.quality_profile
                if hasattr(profile, "thresholds"):
                    min_score = profile.thresholds.overall_min
                    actual_score = quality_scores["overall_score"]
                    baseline_checks[f"Quality score ≥ {min_score}"] = actual_score >= min_score

    except Exception as e:
        # If any check fails, mark all as failed
        baseline_checks = {"Baseline compliance check": False, "Error": str(e)}

    return baseline_checks


if __name__ == "__main__":
    sys.exit(main())
