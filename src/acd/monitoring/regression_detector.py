"""Regression detection for ACD Monitor metrics."""

import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
import pandas as pd

from .metrics import RunMetrics

logger = logging.getLogger(__name__)


class RegressionDetector:
    """Detects regressions in ACD Monitor metrics."""

    def __init__(self, metrics_log_path: Path, regressions_dir: Path):
        """Initialize regression detector.

        Args:
            metrics_log_path: Path to metrics log Parquet file
            regressions_dir: Directory to store regression reports
        """
        self.metrics_log_path = Path(metrics_log_path)
        self.regressions_dir = Path(regressions_dir)
        self.regressions_dir.mkdir(parents=True, exist_ok=True)

        # Regression thresholds
        self.regression_threshold = 0.20  # 20% change threshold
        self.trend_window = 7  # Number of runs for trend analysis

        logger.info(f"Initialized regression detector with {self.trend_window}-run trend window")

    def detect_regressions(self, current_metrics: RunMetrics) -> Dict[str, Any]:
        """Detect regressions by comparing current metrics to historical trends.

        Args:
            current_metrics: Metrics from the current run

        Returns:
            Dictionary containing regression analysis results
        """
        if not self.metrics_log_path.exists():
            logger.info("No historical metrics available for regression detection")
            return {"regressions_detected": False, "regression_notes": [], "trend_analysis": {}}

        try:
            # Load historical metrics
            historical_df = pd.read_parquet(self.metrics_log_path)

            # Get recent metrics for trend analysis
            recent_metrics = self._get_recent_metrics(historical_df, self.trend_window)

            if len(recent_metrics) < 3:  # Need at least 3 runs for meaningful analysis
                logger.info("Insufficient historical data for regression detection")
                return {"regressions_detected": False, "regression_notes": [], "trend_analysis": {}}

            # Analyze each metric for regressions
            regression_notes = []
            trend_analysis = {}

            metrics_to_check = [
                "spurious_regime_rate",
                "vmm_convergence_rate",
                "structural_stability_median",
                "runtime_p95",
                "timestamp_success_rate",
                "quality_overall",
            ]

            for metric_name in metrics_to_check:
                if not hasattr(current_metrics, metric_name):
                    continue

                current_value = getattr(current_metrics, metric_name)
                trend_result = self._analyze_metric_trend(
                    recent_metrics, metric_name, current_value
                )

                trend_analysis[metric_name] = trend_result

                if trend_result["regression_detected"]:
                    regression_notes.append(trend_result["regression_note"])

            # Determine overall regression status
            regressions_detected = len(regression_notes) > 0

            # Log regressions if detected
            if regressions_detected:
                self._log_regressions(current_metrics, regression_notes, trend_analysis)

            return {
                "regressions_detected": regressions_detected,
                "regression_notes": regression_notes,
                "trend_analysis": trend_analysis,
            }

        except Exception as e:
            logger.error(f"Error in regression detection: {e}")
            return {
                "regressions_detected": False,
                "regression_notes": [f"Regression detection failed: {e}"],
                "trend_analysis": {},
            }

    def _get_recent_metrics(self, df: pd.DataFrame, n_runs: int) -> List[Dict]:
        """Get the most recent n runs from metrics log."""
        # Sort by timestamp and get recent runs
        df_sorted = df.sort_values("timestamp", ascending=False)
        recent_df = df_sorted.head(n_runs)

        # Convert to list of dictionaries
        recent_metrics = []
        for _, row in recent_df.iterrows():
            metrics_dict = {}
            for col in df.columns:
                value = row[col]
                # Convert numeric strings back to numbers
                try:
                    if isinstance(value, str) and value.replace(".", "").replace("-", "").isdigit():
                        metrics_dict[col] = float(value)
                    else:
                        metrics_dict[col] = value
                except:
                    metrics_dict[col] = value
            recent_metrics.append(metrics_dict)

        return recent_metrics

    def _analyze_metric_trend(
        self, recent_metrics: List[Dict], metric_name: str, current_value: float
    ) -> Dict[str, Any]:
        """Analyze trend for a specific metric.

        Args:
            recent_metrics: List of recent metric dictionaries
            metric_name: Name of metric to analyze
            current_value: Current value of the metric

        Returns:
            Dictionary containing trend analysis results
        """
        # Extract historical values for this metric
        historical_values = []
        for metrics in recent_metrics:
            if metric_name in metrics:
                value = metrics[metric_name]
                if isinstance(value, (int, float)):
                    historical_values.append(value)

        if len(historical_values) < 2:
            return {
                "regression_detected": False,
                "regression_note": None,
                "historical_count": len(historical_values),
                "insufficient_data": True,
            }

        # Calculate median of recent values
        historical_median = float(pd.Series(historical_values).median())

        # Calculate percentage change
        if historical_median != 0:
            percent_change = abs(current_value - historical_median) / abs(historical_median)
        else:
            percent_change = 0.0

        # Determine if this is a regression
        regression_detected = percent_change > self.regression_threshold

        # Generate regression note if applicable
        regression_note = None
        if regression_detected:
            direction = "increased" if current_value > historical_median else "decreased"
            regression_note = (
                f"{metric_name.replace('_', ' ').title()} {direction} by "
                f"{percent_change:.1%} (current: {current_value:.3f}, "
                f"7-run median: {historical_median:.3f})"
            )

        return {
            "regression_detected": regression_detected,
            "regression_note": regression_note,
            "current_value": current_value,
            "historical_median": historical_median,
            "percent_change": percent_change,
            "historical_count": len(historical_values),
            "insufficient_data": False,
        }

    def _log_regressions(
        self,
        current_metrics: RunMetrics,
        regression_notes: List[str],
        trend_analysis: Dict[str, Any],
    ) -> None:
        """Log detected regressions to file and achievements log."""
        timestamp = datetime.now()
        date_str = timestamp.strftime("%Y-%m-%d")

        # Create regression report
        regression_report = self._create_regression_report(
            current_metrics, regression_notes, trend_analysis, timestamp
        )

        # Save regression report
        report_path = self.regressions_dir / f"{date_str}.md"
        with open(report_path, "w") as f:
            f.write(regression_report)

        # Append to achievements log
        self._append_to_achievements_log(date_str, regression_notes)

        logger.warning(f"Regressions detected and logged to {report_path}")

    def _create_regression_report(
        self,
        current_metrics: RunMetrics,
        regression_notes: List[str],
        trend_analysis: Dict[str, Any],
        timestamp: datetime,
    ) -> str:
        """Create a markdown regression report."""
        report = f"""# ACD Monitor Regression Report - {timestamp.strftime('%Y-%m-%d %H:%M:%S')}

## Run Information
- **Run ID**: {current_metrics.run_id}
- **Dataset Size**: {current_metrics.dataset_size}
- **Thresholds Profile**: {current_metrics.thresholds_profile}
- **Code Version**: {current_metrics.code_version}

## Regressions Detected
"""

        if regression_notes:
            for i, note in enumerate(regression_notes, 1):
                report += f"{i}. {note}\n"
        else:
            report += "No regressions detected.\n"

        report += f"""
## Detailed Trend Analysis

### Metric Trends (7-run comparison)
"""

        for metric_name, analysis in trend_analysis.items():
            if analysis.get("insufficient_data", False):
                continue

            report += f"""
#### {metric_name.replace('_', ' ').title()}
- **Current Value**: {analysis['current_value']:.3f}
- **Historical Median**: {analysis['historical_median']:.3f}
- **Percent Change**: {analysis['percent_change']:.1%}
- **Regression Detected**: {'Yes' if analysis['regression_detected'] else 'No'}
"""

        report += f"""
## Recommendations
1. Review recent code changes that may have introduced regressions
2. Investigate data quality changes or threshold adjustments
3. Monitor subsequent runs to confirm trend reversal
4. Consider rolling back changes if regressions persist

## Context
This report was generated automatically by the ACD Monitor regression detection system.
Threshold for regression detection: {self.regression_threshold:.0%} change over {self.trend_window} runs.
"""

        return report

    def _append_to_achievements_log(self, date_str: str, regression_notes: List[str]) -> None:
        """Append regression information to achievements log."""
        achievements_log_path = Path("docs/achievements_log.md")

        if not achievements_log_path.exists():
            logger.warning("Achievements log not found, skipping regression log update")
            return

        try:
            # Read current achievements log
            with open(achievements_log_path, "r") as f:
                content = f.read()

            # Find Week 5 section and add regression note
            if "## Week 5" in content:
                regression_summary = f"\n- **{date_str}**: Regressions detected: {len(regression_notes)} metrics showing >20% change from 7-run median"

                # Insert after Week 5 header
                content = content.replace("## Week 5", f"## Week 5{regression_summary}")

                # Write updated content
                with open(achievements_log_path, "w") as f:
                    f.write(content)

                logger.info("Updated achievements log with regression information")

        except Exception as e:
            logger.error(f"Failed to update achievements log: {e}")

    def get_regression_summary(self) -> Dict[str, Any]:
        """Get summary of recent regressions."""
        if not self.regressions_dir.exists():
            return {"total_reports": 0, "recent_regressions": []}

        # Count total regression reports
        report_files = list(self.regressions_dir.glob("*.md"))
        total_reports = len(report_files)

        # Get recent regression reports (last 5)
        recent_reports = []
        for report_file in sorted(report_files, reverse=True)[:5]:
            try:
                with open(report_file, "r") as f:
                    content = f.read()

                # Extract date and run ID
                lines = content.split("\n")
                date_line = next(
                    (line for line in lines if line.startswith("# ACD Monitor Regression Report")),
                    "",
                )
                run_id_line = next((line for line in lines if line.startswith("- **Run ID**:")), "")

                date = date_line.split(" - ")[-1] if " - " in date_line else "Unknown"
                run_id = run_id_line.split("**: ")[-1] if "**: " in run_id_line else "Unknown"

                recent_reports.append({"date": date, "run_id": run_id, "file": report_file.name})
            except Exception as e:
                logger.warning(f"Failed to parse regression report {report_file}: {e}")

        return {"total_reports": total_reports, "recent_regressions": recent_reports}
