"""Visualization and demo output for ACD Monitor demo pipeline."""

import json
import logging
from pathlib import Path
from typing import Dict, List, Optional, Any

import pandas as pd

logger = logging.getLogger(__name__)


class DemoVisualization:
    """Visualization and demo output generation for ACD Monitor."""

    def __init__(self, output_dir: str = "demo/outputs"):
        """Initialize demo visualization.

        Args:
            output_dir: Directory for demo outputs
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def create_calibration_report(
        self, vmm_results: List[Dict], quality_metrics: Dict[str, Dict]
    ) -> Dict[str, any]:
        """Create a comprehensive calibration report.

        Args:
            vmm_results: List of VMM analysis results
            quality_metrics: Data quality metrics by feed

        Returns:
            Calibration report dictionary
        """
        report = {
            "report_id": f"calibration_{pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')}",
            "timestamp": pd.Timestamp.now().isoformat(),
            "report_type": "demo_calibration",
            "summary": self._generate_calibration_summary(vmm_results, quality_metrics),
            "vmm_performance": self._analyze_vmm_performance(vmm_results),
            "data_quality_analysis": self._analyze_data_quality(quality_metrics),
            "recommendations": self._generate_calibration_recommendations(
                vmm_results, quality_metrics
            ),
        }

        return report

    def create_evidence_bundle_summary(self, evidence_bundles: List[Dict]) -> Dict[str, any]:
        """Create a summary of evidence bundles.

        Args:
            evidence_bundles: List of evidence bundle data

        Returns:
            Evidence bundle summary
        """
        summary = {
            "summary_id": f"evidence_summary_{pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')}",
            "timestamp": pd.Timestamp.now().isoformat(),
            "total_bundles": len(evidence_bundles),
            "bundle_details": [],
            "validation_summary": self._summarize_validation(evidence_bundles),
            "vmm_outputs_summary": self._summarize_vmm_outputs(evidence_bundles),
        }

        for bundle in evidence_bundles:
            summary["bundle_details"].append(
                {
                    "bundle_id": getattr(bundle, "bundle_id", "unknown"),
                    "creation_timestamp": getattr(bundle, "creation_timestamp", "unknown"),
                    "vmm_outputs": getattr(bundle, "vmm_outputs", {}),
                    "validation_status": getattr(bundle, "validation", False),
                }
            )

        return summary

    def generate_demo_dashboard_data(self, pipeline_results: Dict) -> Dict[str, any]:
        """Generate data for demo dashboard visualization.

        Args:
            pipeline_results: Complete pipeline execution results

        Returns:
            Dashboard data dictionary
        """
        dashboard_data = {
            "execution_metrics": {
                "total_time": pipeline_results.get("execution_time", 0),
                "phases_completed": 4,
                "success_rate": 1.0 if pipeline_results.get("success", False) else 0.0,
            },
            "data_flow": {
                "ingestion": {
                    "golden_datasets": len(
                        pipeline_results.get("ingestion_results", {}).get("golden_datasets", {})
                    ),
                    "mock_feeds": sum(
                        pipeline_results.get("ingestion_results", {}).get("mock_feeds", {}).values()
                    ),
                    "quality_metrics": len(
                        pipeline_results.get("ingestion_results", {}).get("quality_metrics", {})
                    ),
                },
                "processing": {
                    "vmm_windows": len(
                        pipeline_results.get("feature_engineering_results", {}).get(
                            "vmm_windows", []
                        )
                    ),
                    "evidence_bundles": len(pipeline_results.get("evidence_bundles", [])),
                    "calibration_reports": len(pipeline_results.get("calibration_reports", [])),
                },
                "output": {
                    "exported_files": len(
                        pipeline_results.get("export_results", {}).get("exported_bundles", [])
                    ),
                    "export_errors": len(
                        pipeline_results.get("export_results", {}).get("export_errors", [])
                    ),
                },
            },
            "performance_metrics": {
                "vmm_analysis": self._extract_vmm_performance_metrics(pipeline_results),
                "data_quality": self._extract_quality_metrics(pipeline_results),
                "pipeline_efficiency": self._calculate_pipeline_efficiency(pipeline_results),
            },
            "adaptive_thresholds": self._extract_threshold_information(pipeline_results),
            "timestamping": self._extract_timestamping_information(pipeline_results),
            "quality_profiles": self._extract_quality_profile_information(pipeline_results),
            "monitoring": self.generate_monitoring_dashboard(pipeline_results),
        }

        return dashboard_data

    def save_demo_outputs(self, outputs: Dict[str, any], output_type: str) -> str:
        """Save demo outputs to files.

        Args:
            outputs: Output data to save
            output_type: Type of output (calibration, evidence, dashboard)

        Returns:
            Path to saved file
        """
        timestamp = pd.Timestamp.now().strftime("%Y%m%d_%H%M%S")

        if output_type == "calibration":
            filename = f"calibration_report_{timestamp}.json"
        elif output_type == "evidence":
            filename = f"evidence_summary_{timestamp}.json"
        elif output_type == "dashboard":
            filename = f"demo_dashboard_{timestamp}.json"
        else:
            filename = f"demo_output_{timestamp}.json"

        output_path = self.output_dir / filename

        with open(output_path, "w") as f:
            json.dump(outputs, f, indent=2, default=str)

        logger.info(f"✅ Saved {output_type} output to {output_path}")
        return str(output_path)

    def _generate_calibration_summary(
        self, vmm_results: List[Dict], quality_metrics: Dict[str, Dict]
    ) -> Dict[str, any]:
        """Generate calibration summary statistics."""
        if not vmm_results:
            return {"error": "No VMM results available"}

        # Extract VMM metrics
        regime_confidences = [r.get("regime_confidence", 0) for r in vmm_results]
        structural_stabilities = [r.get("structural_stability", 0) for r in vmm_results]
        convergence_statuses = [r.get("convergence_status", "unknown") for r in vmm_results]

        # Calculate summary statistics
        summary = {
            "total_windows": len(vmm_results),
            "vmm_metrics": {
                "regime_confidence": {
                    "mean": sum(regime_confidences) / len(regime_confidences),
                    "min": min(regime_confidences),
                    "max": max(regime_confidences),
                    "std": pd.Series(regime_confidences).std(),
                },
                "structural_stability": {
                    "mean": sum(structural_stabilities) / len(structural_stabilities),
                    "min": min(structural_stabilities),
                    "max": max(structural_stabilities),
                    "std": pd.Series(structural_stabilities).std(),
                },
            },
            "convergence": {
                "converged": sum(1 for s in convergence_statuses if s == "converged"),
                "failed": sum(1 for s in convergence_statuses if s == "failed"),
                "convergence_rate": sum(1 for s in convergence_statuses if s == "converged")
                / len(convergence_statuses),
            },
        }

        return summary

    def _analyze_vmm_performance(self, vmm_results: List[Dict]) -> Dict[str, any]:
        """Analyze VMM performance across windows."""
        if not vmm_results:
            return {"error": "No VMM results available"}

        # Performance analysis
        performance = {
            "window_analysis": [],
            "overall_performance": {
                "successful_analyses": 0,
                "failed_analyses": 0,
                "average_regime_confidence": 0,
                "average_structural_stability": 0,
            },
        }

        successful_results = [r for r in vmm_results if r.get("convergence_status") == "converged"]

        if successful_results:
            performance["overall_performance"]["successful_analyses"] = len(successful_results)
            performance["overall_performance"]["average_regime_confidence"] = sum(
                r.get("regime_confidence", 0) for r in successful_results
            ) / len(successful_results)
            performance["overall_performance"]["average_structural_stability"] = sum(
                r.get("structural_stability", 0) for r in successful_results
            ) / len(successful_results)

        performance["overall_performance"]["failed_analyses"] = len(vmm_results) - len(
            successful_results
        )

        return performance

    def _analyze_data_quality(self, quality_metrics: Dict[str, Dict]) -> Dict[str, any]:
        """Analyze data quality across feeds."""
        if not quality_metrics:
            return {"error": "No quality metrics available"}

        # Aggregate quality scores
        all_scores = []
        for feed_name, metrics in quality_metrics.items():
            all_scores.append(metrics.get("overall", 0))

        analysis = {
            "total_feeds": len(quality_metrics),
            "quality_distribution": {
                "excellent": sum(1 for score in all_scores if score >= 0.9),
                "good": sum(1 for score in all_scores if 0.8 <= score < 0.9),
                "acceptable": sum(1 for score in all_scores if 0.7 <= score < 0.8),
                "poor": sum(1 for score in all_scores if score < 0.7),
            },
            "average_quality": sum(all_scores) / len(all_scores),
            "quality_by_feed": quality_metrics,
        }

        return analysis

    def _generate_calibration_recommendations(
        self, vmm_results: List[Dict], quality_metrics: Dict[str, Dict]
    ) -> List[str]:
        """Generate calibration recommendations based on results."""
        recommendations = []

        # VMM performance recommendations
        if vmm_results:
            convergence_rate = sum(
                1 for r in vmm_results if r.get("convergence_status") == "converged"
            ) / len(vmm_results)

            if convergence_rate < 0.8:
                recommendations.append(
                    "VMM convergence rate below 80% - consider adjusting tolerance or learning rate"
                )

            regime_confidences = [r.get("regime_confidence", 0) for r in vmm_results]
            if regime_confidences:
                avg_confidence = sum(regime_confidences) / len(regime_confidences)
                if avg_confidence < 0.5:
                    recommendations.append(
                        "Low average regime confidence - review feature engineering and data quality"
                    )

        # Data quality recommendations
        if quality_metrics:
            avg_quality = sum(m.get("overall", 0) for m in quality_metrics.values()) / len(
                quality_metrics
            )
            if avg_quality < 0.8:
                recommendations.append("Data quality below 80% - investigate data source issues")

        # General recommendations
        recommendations.extend(
            [
                "This is a demo calibration - real-world deployment requires actual market data",
                "VMM thresholds should be tuned based on specific market characteristics",
                "Regular recalibration is recommended as market conditions change",
            ]
        )

        return recommendations

    def _summarize_validation(self, evidence_bundles: List[Dict]) -> Dict[str, any]:
        """Summarize validation results across evidence bundles."""
        if not evidence_bundles:
            return {"error": "No evidence bundles available"}

        validation_summary = {
            "total_bundles": len(evidence_bundles),
            "valid_bundles": 0,
            "invalid_bundles": 0,
            "validation_errors": [],
        }

        for bundle in evidence_bundles:
            validation = getattr(bundle, "validation", False)
            if validation:
                validation_summary["valid_bundles"] += 1
            else:
                validation_summary["invalid_bundles"] += 1
                # For demo purposes, no specific errors to report
                validation_summary["validation_errors"].append("Demo validation")

        validation_summary["validation_rate"] = (
            validation_summary["valid_bundles"] / validation_summary["total_bundles"]
        )

        return validation_summary

    def _summarize_vmm_outputs(self, evidence_bundles: List) -> Dict[str, any]:
        """Summarize VMM outputs across evidence bundles."""
        if not evidence_bundles:
            return {"error": "No evidence bundles available"}

        # Handle both EvidenceBundle objects and dictionaries
        regime_confidences = []
        structural_stabilities = []

        for bundle in evidence_bundles:
            if hasattr(bundle, "vmm_outputs"):
                # EvidenceBundle object
                regime_confidences.append(getattr(bundle.vmm_outputs, "regime_confidence", 0))
                structural_stabilities.append(
                    getattr(bundle.vmm_outputs, "structural_stability", 0)
                )
            else:
                # Dictionary format (fallback)
                vmm_outputs = bundle.get("vmm_outputs", {})
                regime_confidences.append(vmm_outputs.get("regime_confidence", 0))
                structural_stabilities.append(vmm_outputs.get("structural_stability", 0))

        summary = {
            "total_bundles": len(evidence_bundles),
            "regime_confidence": {"values": regime_confidences, "mean": 0, "std": 0},
            "structural_stability": {"values": structural_stabilities, "mean": 0, "std": 0},
        }

        if summary["regime_confidence"]["values"]:
            summary["regime_confidence"]["mean"] = sum(
                summary["regime_confidence"]["values"]
            ) / len(summary["regime_confidence"]["values"])
            summary["regime_confidence"]["std"] = pd.Series(
                summary["regime_confidence"]["values"]
            ).std()

        if summary["structural_stability"]["values"]:
            summary["structural_stability"]["mean"] = sum(
                summary["structural_stability"]["values"]
            ) / len(summary["structural_stability"]["values"])
            summary["structural_stability"]["std"] = pd.Series(
                summary["structural_stability"]["values"]
            ).std()

        return summary

    def _extract_vmm_performance_metrics(self, pipeline_results: Dict) -> Dict[str, any]:
        """Extract VMM performance metrics from pipeline results."""
        feature_results = pipeline_results.get("feature_engineering_results", {})
        vmm_results = feature_results.get("vmm_results", [])

        if not vmm_results:
            return {"error": "No VMM results available"}

        metrics = {
            "total_windows": len(vmm_results),
            "convergence_rate": sum(
                1 for r in vmm_results if getattr(r, "convergence_status", "unknown") == "converged"
            )
            / len(vmm_results),
            "average_regime_confidence": sum(
                getattr(r, "regime_confidence", 0) for r in vmm_results
            )
            / len(vmm_results),
            "average_structural_stability": sum(
                getattr(r, "structural_stability", 0) for r in vmm_results
            )
            / len(vmm_results),
        }

        return metrics

    def _extract_quality_metrics(self, pipeline_results: Dict) -> Dict[str, any]:
        """Extract data quality metrics from pipeline results."""
        ingestion_results = pipeline_results.get("ingestion_results", {})
        quality_metrics = ingestion_results.get("quality_metrics", {})

        if not quality_metrics:
            return {"error": "No quality metrics available"}

        all_scores = [m.get("overall_score", 0) for m in quality_metrics.values()]

        metrics = {
            "total_feeds": len(quality_metrics),
            "average_quality": sum(all_scores) / len(all_scores),
            "quality_distribution": {
                "excellent": sum(1 for score in all_scores if score >= 0.9),
                "good": sum(1 for score in all_scores if 0.8 <= score < 0.9),
                "acceptable": sum(1 for score in all_scores if 0.7 <= score < 0.8),
                "poor": sum(1 for score in all_scores if score < 0.7),
            },
        }

        return metrics

    def _calculate_pipeline_efficiency(self, pipeline_results: Dict) -> Dict[str, any]:
        """Calculate pipeline efficiency metrics."""
        execution_time = pipeline_results.get("execution_time", 0)

        if execution_time == 0:
            return {"error": "No execution time available"}

        # Count outputs
        evidence_bundles = len(pipeline_results.get("evidence_bundles", []))
        calibration_reports = len(pipeline_results.get("calibration_reports", []))
        exported_files = len(pipeline_results.get("export_results", {}).get("exported_bundles", []))

        efficiency = {
            "execution_time_seconds": execution_time,
            "outputs_per_second": (
                (evidence_bundles + calibration_reports + exported_files) / execution_time
                if execution_time > 0
                else 0
            ),
            "evidence_bundles_per_second": (
                evidence_bundles / execution_time if execution_time > 0 else 0
            ),
            "calibration_reports_per_second": (
                calibration_reports / execution_time if execution_time > 0 else 0
            ),
            "total_outputs": evidence_bundles + calibration_reports + exported_files,
        }

        return efficiency

    def _extract_threshold_information(self, pipeline_results: Dict) -> Dict[str, Any]:
        """Extract adaptive threshold information from pipeline results."""
        evidence_bundles = pipeline_results.get("evidence_bundles", [])

        if not evidence_bundles:
            return {"error": "No evidence bundles available"}

        # Get threshold profile from first bundle (should be consistent across all)
        first_bundle = evidence_bundles[0]
        threshold_profile = getattr(first_bundle, "adaptive_threshold_profile", None)

        if not threshold_profile:
            return {"error": "No threshold profile found in evidence bundles"}

        # Extract key threshold information
        thresholds = {
            "framework_version": threshold_profile.get("framework_version", "unknown"),
            "small_dataset": {
                "max_size": threshold_profile.get("small_dataset", {}).get("max_size", 200),
                "threshold": threshold_profile.get("small_dataset", {}).get("threshold", 0.02),
                "description": threshold_profile.get("small_dataset", {}).get(
                    "description", "≤200 windows: ≤2%"
                ),
            },
            "medium_dataset": {
                "min_size": threshold_profile.get("medium_dataset", {}).get("min_size", 201),
                "max_size": threshold_profile.get("medium_dataset", {}).get("max_size", 800),
                "threshold": threshold_profile.get("medium_dataset", {}).get("threshold", 0.05),
                "description": threshold_profile.get("medium_dataset", {}).get(
                    "description", "201-800 windows: ≤5%"
                ),
            },
            "large_dataset": {
                "min_size": threshold_profile.get("large_dataset", {}).get("min_size", 801),
                "threshold": threshold_profile.get("large_dataset", {}).get("threshold", 0.08),
                "description": threshold_profile.get("large_dataset", {}).get(
                    "description", ">800 windows: ≤8%"
                ),
            },
            "continuous_scaling": threshold_profile.get("continuous_scaling", {}),
            "strict_mode": threshold_profile.get("strict_mode", True),
        }

        return thresholds

    def _extract_timestamping_information(self, pipeline_results: Dict) -> Dict[str, Any]:
        """Extract timestamping information from pipeline results."""
        evidence_bundles = pipeline_results.get("evidence_bundles", [])

        if not evidence_bundles:
            return {"error": "No evidence bundles available"}

        # Count timestamped bundles
        timestamped_bundles = sum(
            1 for b in evidence_bundles if getattr(b, "timestamp_chain", None) is not None
        )
        total_bundles = len(evidence_bundles)

        if timestamped_bundles == 0:
            return {"error": "No timestamped bundles found"}

        # Get timestamp information from first timestamped bundle
        timestamped_bundle = next(
            (b for b in evidence_bundles if getattr(b, "timestamp_chain", None) is not None), None
        )

        if not timestamped_bundle:
            return {"error": "No timestamped bundle found"}

        timestamp_chain = timestamped_bundle.timestamp_chain
        latest_response = (
            timestamp_chain.timestamp_responses[0] if timestamp_chain.timestamp_responses else None
        )

        if not latest_response:
            return {"error": "No timestamp response found"}

        timestamping_info = {
            "success_rate": timestamped_bundles / total_bundles,
            "total_bundles": total_bundles,
            "timestamped_bundles": timestamped_bundles,
            "latest_timestamp": latest_response.timestamp.isoformat(),
            "provider": latest_response.provider_name,
            "response_time_ms": latest_response.response_time_ms,
            "policy_oid": latest_response.policy_oid,
            "serial_number": latest_response.serial_number,
            "tsa_cert_digest": latest_response.tsa_cert_digest,
        }

        return timestamping_info

    def _extract_quality_profile_information(self, pipeline_results: Dict) -> Dict[str, Any]:
        """Extract quality profile information from pipeline results."""
        evidence_bundles = pipeline_results.get("evidence_bundles", [])

        if not evidence_bundles:
            return {"error": "No evidence bundles available"}

        # Get quality profile from first bundle
        first_bundle = evidence_bundles[0]
        quality_profile = getattr(first_bundle, "quality_profile", None)

        if not quality_profile:
            return {"error": "No quality profile found in evidence bundles"}

        profile_info = {
            "profile_name": quality_profile.source_type.value,
            "description": quality_profile.description,
            "rationale": quality_profile.rationale,
            "thresholds": {
                "overall_min": quality_profile.thresholds.overall_min,
                "timeliness_critical": quality_profile.thresholds.timeliness_critical,
                "timeliness_standard": quality_profile.thresholds.timeliness_standard,
                "completeness": quality_profile.thresholds.completeness,
                "consistency": quality_profile.thresholds.consistency,
                "accuracy": quality_profile.thresholds.accuracy,
            },
            "validation_rules": quality_profile.validation_rules,
            "metadata": quality_profile.metadata,
        }

        return profile_info

    def generate_monitoring_dashboard(self, pipeline_results: Dict) -> Dict[str, Any]:
        """Generate monitoring dashboard data."""
        monitoring_data = pipeline_results.get("monitoring", {})

        if not monitoring_data:
            return {"error": "No monitoring data available"}

        # Extract health check information
        health_check = monitoring_data.get("health_check", {})
        regression_detection = monitoring_data.get("regression_detection", {})

        # Get recent metrics trend (if available)
        recent_trends = {}
        try:
            metrics_file = Path(monitoring_data.get("metrics_file", ""))
            if metrics_file.exists():
                with open(metrics_file, "r") as f:
                    current_metrics = json.load(f)

                # Extract key metrics for trend analysis
                recent_trends = {
                    "spurious_regime_rate": current_metrics.get("spurious_regime_rate", 0.0),
                    "vmm_convergence_rate": current_metrics.get("vmm_convergence_rate", 0.0),
                    "structural_stability_median": current_metrics.get(
                        "structural_stability_median", 0.0
                    ),
                    "runtime_p95": current_metrics.get("runtime_p95", 0.0),
                    "timestamp_success_rate": current_metrics.get("timestamp_success_rate", 0.0),
                    "quality_overall": current_metrics.get("quality_overall", 0.0),
                }
        except Exception as e:
            logger.warning(f"Failed to extract recent trends: {e}")

        dashboard = {
            "top_line_status": health_check.get("overall_status", "UNKNOWN"),
            "health_check_summary": health_check.get("summary", "No health check data"),
            "exit_code": health_check.get("exit_code", -1),
            "regression_status": {
                "regressions_detected": regression_detection.get("regressions_detected", False),
                "regression_count": len(regression_detection.get("regression_notes", [])),
                "regression_notes": regression_detection.get("regression_notes", []),
            },
            "recent_metrics": recent_trends,
            "thresholds_applied": {
                "monitoring_mode": "balanced",  # Default mode
                "adaptive_threshold": 0.05,  # For 190-window golden dataset
                "regression_threshold": "20% change over 7 runs",
            },
            "recommendations": self._generate_monitoring_recommendations(
                health_check, regression_detection
            ),
            "generated_at": pd.Timestamp.now().isoformat(),
        }

        return dashboard

    def _generate_monitoring_recommendations(
        self, health_check: Dict, regression_detection: Dict
    ) -> List[str]:
        """Generate monitoring-specific recommendations."""
        recommendations = []

        # Health check recommendations
        if health_check.get("overall_status") == "FAIL":
            recommendations.append(
                "Immediate attention required - critical health check failures detected"
            )
        elif health_check.get("overall_status") == "WARN":
            recommendations.append(
                "Monitor performance trends - some health check warnings detected"
            )

        # Regression recommendations
        if regression_detection.get("regressions_detected", False):
            regression_count = len(regression_detection.get("regression_notes", []))
            recommendations.append(
                f"Investigate {regression_count} detected regressions in key metrics"
            )
            recommendations.append("Review recent code changes and data quality variations")

        # General monitoring recommendations
        if not recommendations:
            recommendations.append("Continue monitoring - no immediate action required")

        recommendations.append("Run health checks regularly to maintain system health")
        recommendations.append("Monitor regression trends over multiple runs")

        return recommendations
