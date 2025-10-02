"""Health check system for ACD Monitor runs."""

import enum
import logging
from dataclasses import dataclass
from typing import Dict, List, Optional

import yaml

from .metrics import RunMetrics

logger = logging.getLogger(__name__)


class MonitoringMode(enum.Enum):
    """Monitoring mode for threshold adjustments."""

    STRICT = "strict"
    BALANCED = "balanced"
    PERMISSIVE = "permissive"


class HealthStatus(enum.Enum):
    """Health status classification."""

    PASS = "PASS"
    WARN = "WARN"
    FAIL = "FAIL"


@dataclass
class HealthGate:
    """Individual health check gate."""

    name: str
    status: HealthStatus
    value: float
    threshold: float
    message: str
    details: Optional[str] = None


@dataclass
class HealthCheckResult:
    """Result of a health check run."""

    overall_status: HealthStatus
    gates: List[HealthGate]
    summary: str
    recommendations: List[str]

    @property
    def exit_code(self) -> int:
        """Return exit code for CI integration."""
        if self.overall_status == HealthStatus.PASS:
            return 0
        elif self.overall_status == HealthStatus.WARN:
            return 1
        else:  # FAIL
            return 2


class HealthChecker:
    """Performs health checks on ACD Monitor runs."""

    def __init__(self, config_path: Optional[str] = None):
        """Initialize health checker with configuration.

        Args:
            config_path: Path to YAML configuration file
        """
        self.config = self._load_config(config_path)
        self.mode = MonitoringMode(self.config.get("monitoring_mode", "balanced"))

        # Load thresholds based on mode
        self.thresholds = self._get_thresholds_for_mode()

        logger.info(f"Initialized health checker in {self.mode.value} mode")

    def _load_config(self, config_path: Optional[str]) -> Dict:
        """Load configuration from YAML file or use defaults."""
        if config_path:
            try:
                with open(config_path, "r") as f:
                    return yaml.safe_load(f)
            except Exception as e:
                logger.warning(f"Failed to load config from {config_path}: {e}")

        # Default configuration
        return {
            "monitoring_mode": "balanced",
            "thresholds": {
                "strict": {
                    "spurious_rate_warn_offset": 0.01,
                    "spurious_rate_fail_offset": 0.02,
                    "convergence_warn": 0.75,
                    "convergence_fail": 0.55,
                    "stability_warn": 0.55,
                    "stability_fail": 0.40,
                    "runtime_warn": 2.5,
                    "runtime_fail": 6.0,
                    "timestamp_warn": 0.985,
                    "timestamp_fail": 0.975,
                    "quality_warn_offset": 0.08,
                    "quality_fail_offset": 0.15,
                    "schema_warn": 0.99,
                    "schema_fail": 0.96,
                    "export_warn": 0.99,
                    "export_fail": 0.975,
                },
                "balanced": {
                    "spurious_rate_warn_offset": 0.015,
                    "spurious_rate_fail_offset": 0.025,
                    "convergence_warn": 0.70,
                    "convergence_fail": 0.50,
                    "stability_warn": 0.50,
                    "stability_fail": 0.35,
                    "runtime_warn": 3.0,
                    "runtime_fail": 7.0,
                    "timestamp_warn": 0.98,
                    "timestamp_fail": 0.97,
                    "quality_warn_offset": 0.10,
                    "quality_fail_offset": 0.20,
                    "schema_warn": 0.98,
                    "schema_fail": 0.95,
                    "export_warn": 0.985,
                    "export_fail": 0.97,
                },
                "permissive": {
                    "spurious_rate_warn_offset": 0.02,
                    "spurious_rate_fail_offset": 0.03,
                    "convergence_warn": 0.65,
                    "convergence_fail": 0.45,
                    "stability_warn": 0.45,
                    "stability_fail": 0.30,
                    "runtime_warn": 3.5,
                    "runtime_fail": 8.0,
                    "timestamp_warn": 0.975,
                    "timestamp_fail": 0.965,
                    "quality_warn_offset": 0.12,
                    "quality_fail_offset": 0.25,
                    "schema_warn": 0.97,
                    "schema_fail": 0.94,
                    "export_warn": 0.98,
                    "export_fail": 0.965,
                },
            },
        }

    def _get_thresholds_for_mode(self) -> Dict:
        """Get thresholds for the current monitoring mode."""
        return self.config["thresholds"][self.mode.value]

    def check_health(self, metrics: RunMetrics, adaptive_threshold: float) -> HealthCheckResult:
        """Perform comprehensive health check on run metrics.

        Args:
            metrics: Run metrics to check
            adaptive_threshold: Adaptive threshold for spurious rate

        Returns:
            Health check result with PASS/WARN/FAIL classification
        """
        gates = []

        # 1. Spurious Regime Rate Check
        spurious_gate = self._check_spurious_rate(metrics.spurious_regime_rate, adaptive_threshold)
        gates.append(spurious_gate)

        # 2. VMM Convergence Rate Check
        convergence_gate = self._check_convergence_rate(metrics.vmm_convergence_rate)
        gates.append(convergence_gate)

        # 3. Structural Stability Check
        stability_gate = self._check_structural_stability(metrics.structural_stability_median)
        gates.append(stability_gate)

        # 4. Runtime Performance Check
        runtime_gate = self._check_runtime_performance(metrics.runtime_p95)
        gates.append(runtime_gate)

        # 5. Timestamp Success Rate Check
        timestamp_gate = self._check_timestamp_success(metrics.timestamp_success_rate)
        gates.append(timestamp_gate)

        # 6. Quality Score Check
        quality_gate = self._check_quality_score(
            metrics.quality_overall, metrics.quality_profile_id
        )
        gates.append(quality_gate)

        # 7. Schema Validation Check
        schema_gate = self._check_schema_validation(metrics.schema_validation_pass_rate)
        gates.append(schema_gate)

        # 8. Export Success Check
        export_gate = self._check_export_success(metrics.bundle_export_success_rate)
        gates.append(export_gate)

        # Determine overall status
        overall_status = self._determine_overall_status(gates)

        # Generate summary and recommendations
        summary = self._generate_summary(overall_status, gates)
        recommendations = self._generate_recommendations(gates)

        result = HealthCheckResult(
            overall_status=overall_status,
            gates=gates,
            summary=summary,
            recommendations=recommendations,
        )

        logger.info(f"Health check completed: {overall_status.value}")
        return result

    def _check_spurious_rate(self, spurious_rate: float, adaptive_threshold: float) -> HealthGate:
        """Check spurious regime rate against adaptive threshold."""
        warn_offset = self.thresholds["spurious_rate_warn_offset"]
        self.thresholds["spurious_rate_fail_offset"]

        if spurious_rate <= adaptive_threshold:
            status = HealthStatus.PASS
            message = f"Spurious rate {spurious_rate:.3f} within threshold {adaptive_threshold:.3f}"
        elif spurious_rate <= adaptive_threshold + warn_offset:
            status = HealthStatus.WARN
            message = (
                f"Spurious rate {spurious_rate:.3f} above threshold {adaptive_threshold:.3f} (WARN)"
            )
        else:
            status = HealthStatus.FAIL
            message = (
                f"Spurious rate {spurious_rate:.3f} above threshold {adaptive_threshold:.3f} (FAIL)"
            )

        return HealthGate(
            name="Spurious Regime Rate",
            status=status,
            value=spurious_rate,
            threshold=adaptive_threshold,
            message=message,
        )

    def _check_convergence_rate(self, convergence_rate: float) -> HealthGate:
        """Check VMM convergence rate."""
        warn_threshold = self.thresholds["convergence_warn"]
        fail_threshold = self.thresholds["convergence_fail"]

        if convergence_rate >= warn_threshold:
            status = HealthStatus.PASS
            message = f"Convergence rate {convergence_rate:.1%} meets target"
        elif convergence_rate >= fail_threshold:
            status = HealthStatus.WARN
            message = f"Convergence rate {convergence_rate:.1%} below target {warn_threshold:.1%}"
        else:
            status = HealthStatus.FAIL
            message = f"Convergence rate {convergence_rate:.1%} critically low"

        return HealthGate(
            name="VMM Convergence Rate",
            status=status,
            value=convergence_rate,
            threshold=warn_threshold,
            message=message,
        )

    def _check_structural_stability(self, stability_median: float) -> HealthGate:
        """Check structural stability median."""
        warn_threshold = self.thresholds["stability_warn"]
        fail_threshold = self.thresholds["stability_fail"]

        if stability_median >= warn_threshold:
            status = HealthStatus.PASS
            message = f"Structural stability {stability_median:.3f} meets target"
        elif stability_median >= fail_threshold:
            status = HealthStatus.WARN
            message = (
                f"Structural stability {stability_median:.3f} below target {warn_threshold:.3f}"
            )
        else:
            status = HealthStatus.FAIL
            message = f"Structural stability {stability_median:.3f} critically low"

        return HealthGate(
            name="Structural Stability",
            status=status,
            value=stability_median,
            threshold=warn_threshold,
            message=message,
        )

    def _check_runtime_performance(self, runtime_p95: float) -> HealthGate:
        """Check runtime performance (95th percentile)."""
        warn_threshold = self.thresholds["runtime_warn"]
        fail_threshold = self.thresholds["runtime_fail"]

        if runtime_p95 <= warn_threshold:
            status = HealthStatus.PASS
            message = f"Runtime p95 {runtime_p95:.2f}s within target"
        elif runtime_p95 <= fail_threshold:
            status = HealthStatus.WARN
            message = f"Runtime p95 {runtime_p95:.2f}s above target {warn_threshold}s"
        else:
            status = HealthStatus.FAIL
            message = f"Runtime p95 {runtime_p95:.2f}s critically high"

        return HealthGate(
            name="Runtime Performance (p95)",
            status=status,
            value=runtime_p95,
            threshold=warn_threshold,
            message=message,
        )

    def _check_timestamp_success(self, success_rate: float) -> HealthGate:
        """Check timestamp success rate."""
        warn_threshold = self.thresholds["timestamp_warn"]
        fail_threshold = self.thresholds["timestamp_fail"]

        if success_rate >= warn_threshold:
            status = HealthStatus.PASS
            message = f"Timestamp success rate {success_rate:.1%} meets target"
        elif success_rate >= fail_threshold:
            status = HealthStatus.WARN
            message = f"Timestamp success rate {success_rate:.1%} below target {warn_threshold:.1%}"
        else:
            status = HealthStatus.FAIL
            message = f"Timestamp success rate {success_rate:.1%} critically low"

        return HealthGate(
            name="Timestamp Success Rate",
            status=status,
            value=success_rate,
            threshold=warn_threshold,
            message=message,
        )

    def _check_quality_score(self, quality_score: float, profile_id: str) -> HealthGate:
        """Check quality score against profile minimum."""
        # Get profile minimum from quality profiles
        profile_min = self._get_profile_minimum(profile_id)
        warn_offset = self.thresholds["quality_warn_offset"]
        self.thresholds["quality_fail_offset"]

        if quality_score >= profile_min:
            status = HealthStatus.PASS
            message = f"Quality score {quality_score:.3f} meets profile minimum {profile_min:.3f}"
        elif quality_score >= profile_min - warn_offset:
            status = HealthStatus.WARN
            message = (
                f"Quality score {quality_score:.3f} below profile minimum {profile_min:.3f} (WARN)"
            )
        else:
            status = HealthStatus.FAIL
            message = (
                f"Quality score {quality_score:.3f} below profile minimum {profile_min:.3f} (FAIL)"
            )

        return HealthGate(
            name="Data Quality Score",
            status=status,
            value=quality_score,
            threshold=profile_min,
            message=message,
        )

    def _check_schema_validation(self, pass_rate: float) -> HealthGate:
        """Check schema validation pass rate."""
        warn_threshold = self.thresholds["schema_warn"]
        fail_threshold = self.thresholds["schema_fail"]

        if pass_rate >= warn_threshold:
            status = HealthStatus.PASS
            message = f"Schema validation pass rate {pass_rate:.1%} meets target"
        elif pass_rate >= fail_threshold:
            status = HealthStatus.WARN
            message = (
                f"Schema validation pass rate {pass_rate:.1%} below target {warn_threshold:.1%}"
            )
        else:
            status = HealthStatus.FAIL
            message = f"Schema validation pass rate {pass_rate:.1%} critically low"

        return HealthGate(
            name="Schema Validation",
            status=status,
            value=pass_rate,
            threshold=warn_threshold,
            message=message,
        )

    def _check_export_success(self, success_rate: float) -> HealthGate:
        """Check bundle export success rate."""
        warn_threshold = self.thresholds["export_warn"]
        fail_threshold = self.thresholds["export_fail"]

        if success_rate >= warn_threshold:
            status = HealthStatus.PASS
            message = f"Export success rate {success_rate:.1%} meets target"
        elif success_rate >= fail_threshold:
            status = HealthStatus.WARN
            message = f"Export success rate {success_rate:.1%} below target {warn_threshold:.1%}"
        else:
            status = HealthStatus.FAIL
            message = f"Export success rate {success_rate:.1%} critically low"

        return HealthGate(
            name="Bundle Export Success",
            status=status,
            value=success_rate,
            threshold=warn_threshold,
            message=message,
        )

    def _get_profile_minimum(self, profile_id: str) -> float:
        """Get minimum quality score for a profile."""
        # Default profile minimums (should match quality_profiles.py)
        profile_minimums = {
            "CDS_live": 0.7,
            "Bond_daily": 0.65,
            "Regulatory_disclosure": 0.6,
            "Market_data": 0.75,
            "Analyst_feed": 0.7,
        }
        return profile_minimums.get(profile_id, 0.7)

    def _determine_overall_status(self, gates: List[HealthGate]) -> HealthStatus:
        """Determine overall health status from individual gates."""
        if any(gate.status == HealthStatus.FAIL for gate in gates):
            return HealthStatus.FAIL
        elif any(gate.status == HealthStatus.WARN for gate in gates):
            return HealthStatus.WARN
        else:
            return HealthStatus.PASS

    def _generate_summary(self, overall_status: HealthStatus, gates: List[HealthGate]) -> str:
        """Generate summary of health check results."""
        total_gates = len(gates)
        pass_count = sum(1 for gate in gates if gate.status == HealthStatus.PASS)
        warn_count = sum(1 for gate in gates if gate.status == HealthStatus.WARN)
        fail_count = sum(1 for gate in gates if gate.status == HealthStatus.FAIL)

        summary = f"Health Check: {overall_status.value} "
        summary += f"({pass_count}/{total_gates} PASS, {warn_count} WARN, {fail_count} FAIL)"

        if overall_status == HealthStatus.FAIL:
            summary += " - Critical issues detected"
        elif overall_status == HealthStatus.WARN:
            summary += " - Performance degradation detected"
        else:
            summary += " - All systems operational"

        return summary

    def _generate_recommendations(self, gates: List[HealthGate]) -> List[str]:
        """Generate actionable recommendations based on health check results."""
        recommendations = []

        for gate in gates:
            if gate.status == HealthStatus.FAIL:
                if "Spurious Regime Rate" in gate.name:
                    recommendations.append("Investigate data quality and VMM parameter tuning")
                elif "Convergence Rate" in gate.name:
                    recommendations.append(
                        "Review VMM convergence criteria and numerical stability"
                    )
                elif "Structural Stability" in gate.name:
                    recommendations.append("Check data preprocessing and feature engineering")
                elif "Runtime" in gate.name:
                    recommendations.append(
                        "Optimize VMM implementation and consider parallelization"
                    )
                elif "Timestamp" in gate.name:
                    recommendations.append(
                        "Check TSA service availability and network connectivity"
                    )
                elif "Quality" in gate.name:
                    recommendations.append("Review data source quality and validation rules")
                elif "Schema" in gate.name:
                    recommendations.append("Validate data schema and field mappings")
                elif "Export" in gate.name:
                    recommendations.append("Check file permissions and disk space")

            elif gate.status == HealthStatus.WARN:
                if "Runtime" in gate.name:
                    recommendations.append("Monitor runtime trends and consider optimization")
                elif "Quality" in gate.name:
                    recommendations.append("Review quality thresholds and data source standards")

        if not recommendations:
            recommendations.append("Continue monitoring - no immediate action required")

        return recommendations

    def print_health_table(self, result: HealthCheckResult) -> None:
        """Print a compact health check table."""
        print(f"\n{'='*80}")
        print(f"ACD Monitor Health Check - {result.overall_status.value}")
        print(f"{'='*80}")
        print(f"{'Gate':<25} {'Status':<8} {'Value':<12} {'Threshold':<12} {'Details'}")
        print(f"{'-'*25} {'-'*8} {'-'*12} {'-'*12} {'-'*40}")

        for gate in result.gates:
            status_icon = (
                "✅"
                if gate.status == HealthStatus.PASS
                else "⚠️" if gate.status == HealthStatus.WARN else "❌"
            )
            print(
                f"{gate.name:<25} {status_icon} {gate.status.value:<6} {gate.value:<12.3f} {gate.threshold:<12.3f} {gate.message}"
            )

        print(f"\n{result.summary}")

        if result.recommendations:
            print(f"\nRecommendations:")
            for i, rec in enumerate(result.recommendations, 1):
                print(f"  {i}. {rec}")

        print(f"\nExit Code: {result.exit_code}")
        print(f"{'='*80}")
