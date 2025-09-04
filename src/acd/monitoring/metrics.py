"""Metrics collection for ACD Monitor runs."""

import json
import logging
import time
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Union
import pandas as pd

logger = logging.getLogger(__name__)


@dataclass
class RunMetrics:
    """Core metrics for a single ACD Monitor run."""

    # VMM Performance Metrics
    spurious_regime_rate: float
    auroc: float
    f1: float
    structural_stability_median: float
    vmm_convergence_rate: float
    mean_iterations: float

    # Runtime Performance
    runtime_p50: float  # seconds
    runtime_p95: float  # seconds
    runtime_total: float  # seconds

    # Timestamping & Quality
    timestamp_success_rate: float
    quality_overall: float
    quality_profile_id: str
    schema_validation_pass_rate: float
    bundle_export_success_rate: float

    # Dataset & Configuration
    dataset_size: int
    thresholds_profile: str
    code_version: str
    seed: int

    # Metadata
    run_id: str
    timestamp: str
    pipeline_version: str

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return asdict(self)

    def to_json(self) -> str:
        """Convert to JSON string."""
        return json.dumps(self.to_dict(), indent=2)

    def to_parquet_row(self) -> Dict[str, Any]:
        """Convert to single row for Parquet logging."""
        data = self.to_dict()
        # Ensure all values are serializable
        for key, value in data.items():
            if isinstance(value, (float, int, str, bool)):
                continue
            data[key] = str(value)
        return data


class MetricsCollector:
    """Collects and stores metrics from ACD Monitor runs."""

    def __init__(self, output_dir: Path):
        """Initialize metrics collector.

        Args:
            output_dir: Directory to store metrics outputs
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # Ensure metrics subdirectories exist
        (self.output_dir / "artifacts" / "metrics").mkdir(parents=True, exist_ok=True)

        self.run_metrics: List[RunMetrics] = []
        self.current_run_start: Optional[float] = None

    def start_run(
        self,
        run_id: str,
        seed: int,
        dataset_size: int,
        thresholds_profile: str,
        pipeline_version: str = "1.0.0",
    ):
        """Start timing a new run."""
        self.current_run_start = time.time()
        self.current_run_id = run_id
        self.current_run_seed = seed
        self.current_run_dataset_size = dataset_size
        self.current_run_thresholds = thresholds_profile
        self.current_run_pipeline_version = pipeline_version

        logger.info(f"Started metrics collection for run {run_id}")

    def collect_vmm_metrics(self, vmm_results: Dict[str, Any]) -> None:
        """Collect VMM-specific metrics from results."""
        self.vmm_metrics = vmm_results

    def collect_runtime_metrics(self, window_runtimes: List[float], total_runtime: float) -> None:
        """Collect runtime performance metrics."""
        if not window_runtimes:
            self.runtime_metrics = {
                "runtime_p50": 0.0,
                "runtime_p95": 0.0,
                "runtime_total": total_runtime,
            }
            return

        sorted_runtimes = sorted(window_runtimes)
        n = len(sorted_runtimes)

        self.runtime_metrics = {
            "runtime_p50": sorted_runtimes[n // 2],
            "runtime_p95": sorted_runtimes[int(0.95 * n)],
            "runtime_total": total_runtime,
        }

    def collect_quality_metrics(self, quality_scores: Dict[str, float], profile_id: str) -> None:
        """Collect data quality metrics."""
        self.quality_metrics = {
            "quality_overall": quality_scores.get("overall", 0.0),
            "quality_profile_id": profile_id,
        }

    def collect_timestamp_metrics(self, success_rate: float) -> None:
        """Collect timestamping success metrics."""
        self.timestamp_metrics = {"timestamp_success_rate": success_rate}

    def collect_validation_metrics(
        self, schema_pass_rate: float, export_success_rate: float
    ) -> None:
        """Collect validation and export success metrics."""
        self.validation_metrics = {
            "schema_validation_pass_rate": schema_pass_rate,
            "bundle_export_success_rate": export_success_rate,
        }

    def finalize_run(self, code_version: str = "dev") -> RunMetrics:
        """Finalize the current run and create metrics."""
        if not hasattr(self, "current_run_start"):
            raise RuntimeError("No run in progress")

        # Calculate VMM metrics
        vmm_metrics = getattr(self, "vmm_metrics", {})
        runtime_metrics = getattr(self, "runtime_metrics", {})
        quality_metrics = getattr(self, "quality_metrics", {})
        timestamp_metrics = getattr(self, "timestamp_metrics", {})
        validation_metrics = getattr(self, "validation_metrics", {})

        metrics = RunMetrics(
            # VMM Performance
            spurious_regime_rate=vmm_metrics.get("spurious_regime_rate", 0.0),
            auroc=vmm_metrics.get("auroc", 0.0),
            f1=vmm_metrics.get("f1", 0.0),
            structural_stability_median=vmm_metrics.get("structural_stability_median", 0.0),
            vmm_convergence_rate=vmm_metrics.get("convergence_rate", 0.0),
            mean_iterations=vmm_metrics.get("mean_iterations", 0.0),
            # Runtime Performance
            runtime_p50=runtime_metrics.get("runtime_p50", 0.0),
            runtime_p95=runtime_metrics.get("runtime_p95", 0.0),
            runtime_total=runtime_metrics.get("runtime_total", 0.0),
            # Timestamping & Quality
            timestamp_success_rate=timestamp_metrics.get("timestamp_success_rate", 0.0),
            quality_overall=quality_metrics.get("quality_overall", 0.0),
            quality_profile_id=quality_metrics.get("quality_profile_id", "unknown"),
            schema_validation_pass_rate=validation_metrics.get("schema_validation_pass_rate", 0.0),
            bundle_export_success_rate=validation_metrics.get("bundle_export_success_rate", 0.0),
            # Dataset & Configuration
            dataset_size=self.current_run_dataset_size,
            thresholds_profile=self.current_run_thresholds,
            code_version=code_version,
            seed=self.current_run_seed,
            # Metadata
            run_id=self.current_run_id,
            timestamp=datetime.now().isoformat(),
            pipeline_version=self.current_run_pipeline_version,
        )

        # Store metrics
        self.run_metrics.append(metrics)

        # Clear current run state
        self.current_run_start = None
        delattr(self, "current_run_id")
        delattr(self, "current_run_seed")
        delattr(self, "current_run_dataset_size")
        delattr(self, "current_run_thresholds")
        delattr(self, "current_run_pipeline_version")

        # Clean up collected metrics
        for attr in [
            "vmm_metrics",
            "runtime_metrics",
            "quality_metrics",
            "timestamp_metrics",
            "validation_metrics",
        ]:
            if hasattr(self, attr):
                delattr(self, attr)

        logger.info(f"Finalized metrics for run {metrics.run_id}")
        return metrics

    def save_run_summary(self, metrics: RunMetrics) -> Path:
        """Save single run summary to JSON."""
        output_path = self.output_dir / "run_summary.json"
        with open(output_path, "w") as f:
            json.dump(metrics.to_dict(), f, indent=2)

        logger.info(f"Saved run summary to {output_path}")
        return output_path

    def append_to_run_log(self, metrics: RunMetrics) -> Path:
        """Append metrics to Parquet run log."""
        log_path = self.output_dir / "artifacts" / "metrics" / "run_log.parquet"

        # Convert to DataFrame row
        df_row = pd.DataFrame([metrics.to_parquet_row()])

        if log_path.exists():
            # Append to existing log
            existing_df = pd.read_parquet(log_path)
            updated_df = pd.concat([existing_df, df_row], ignore_index=True)
        else:
            # Create new log
            updated_df = df_row

        # Save updated log
        updated_df.to_parquet(log_path, index=False)

        logger.info(f"Appended metrics to run log: {log_path}")
        return log_path

    def get_recent_metrics(self, n_runs: int = 10) -> List[RunMetrics]:
        """Get metrics from the last n runs."""
        return self.run_metrics[-n_runs:] if self.run_metrics else []

    def get_metrics_trend(self, metric_name: str, n_runs: int = 7) -> List[float]:
        """Get trend for a specific metric over the last n runs."""
        recent = self.get_recent_metrics(n_runs)
        if not recent:
            return []

        return [getattr(metrics, metric_name, 0.0) for metrics in recent]
