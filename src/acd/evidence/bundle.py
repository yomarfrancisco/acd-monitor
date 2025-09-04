"""Evidence bundle for ACD Monitor analysis results.

This module defines the EvidenceBundle class that encapsulates all
evidence from VMM analysis, calibration, and validation processes.
"""

import json
import hashlib
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass, asdict

from ..vmm.types import VMMResult, VMMConfig


@dataclass
class CalibrationArtifact:
    """Calibration artifact from VMM calibration process."""

    market: str
    timestamp: str
    method: str  # 'isotonic', 'platt', 'post_adjustment'
    spurious_rate: float
    structural_stability: float
    calibration_curve: Dict[str, Any]
    validation_metrics: Dict[str, float]
    file_path: str


@dataclass
class VMMEvidence:
    """VMM analysis evidence including outputs and metadata."""

    regime_confidence: float
    structural_stability: float
    dynamic_validation_score: float
    elbo_convergence: float
    iteration_count: int
    runtime_seconds: float
    convergence_status: str
    numerical_stability: Dict[str, float]


@dataclass
class DataQualityEvidence:
    """Data quality assessment evidence."""

    completeness_score: float
    accuracy_score: float
    timeliness_score: float
    consistency_score: float
    overall_score: float
    quality_issues: List[str]
    validation_timestamp: str


@dataclass
class EvidenceBundle:
    """Complete evidence bundle for ACD Monitor analysis."""

    # Core identification
    bundle_id: str
    creation_timestamp: str
    analysis_window_start: str
    analysis_window_end: str
    market: str

    # VMM outputs (Week 4 requirement)
    vmm_outputs: VMMEvidence

    # Calibration artifacts (Week 4 requirement)
    calibration_artifacts: List[CalibrationArtifact]

    # Data quality evidence
    data_quality: DataQualityEvidence

    # Analysis configuration
    vmm_config: Dict[str, Any]
    data_sources: List[str]

    # Validation and reproducibility
    golden_dataset_validation: Dict[str, float]
    reproducibility_metrics: Dict[str, float]

    # Metadata
    analyst: str
    version: str
    checksum: str

    def __post_init__(self):
        """Validate and compute checksum after initialization."""
        if not self.bundle_id:
            self.bundle_id = self._generate_bundle_id()

        if not self.checksum:
            self.checksum = self._compute_checksum()

    def _generate_bundle_id(self) -> str:
        """Generate unique bundle ID."""
        timestamp = datetime.now().isoformat()
        market_hash = hashlib.md5(self.market.encode()).hexdigest()[:8]
        return f"evidence_{market_hash}_{timestamp[:10]}"

    def _compute_checksum(self) -> str:
        """Compute SHA-256 checksum of bundle content."""
        # Convert to dict and sort for deterministic hashing
        bundle_dict = asdict(self)
        bundle_dict.pop("checksum", None)  # Remove checksum before computing

        # Convert to sorted JSON string
        bundle_json = json.dumps(bundle_dict, sort_keys=True, default=str)
        return hashlib.sha256(bundle_json.encode()).hexdigest()

    def to_dict(self) -> Dict[str, Any]:
        """Convert bundle to dictionary."""
        return asdict(self)

    def to_json(self, file_path: Optional[Union[str, Path]] = None) -> str:
        """Convert bundle to JSON string and optionally save to file."""
        bundle_dict = self.to_dict()
        json_str = json.dumps(bundle_dict, indent=2, default=str)

        if file_path:
            file_path = Path(file_path)
            file_path.parent.mkdir(parents=True, exist_ok=True)
            file_path.write_text(json_str)

        return json_str

    def validate_schema(self) -> bool:
        """Validate bundle against schema requirements."""
        try:
            # Check required fields
            required_fields = [
                "bundle_id",
                "creation_timestamp",
                "market",
                "vmm_outputs",
                "calibration_artifacts",
                "data_quality",
            ]

            for field in required_fields:
                if not hasattr(self, field) or getattr(self, field) is None:
                    return False

            # Validate VMM outputs
            vmm_outputs = self.vmm_outputs
            if not (0.0 <= vmm_outputs.regime_confidence <= 1.0):
                return False
            if not (0.0 <= vmm_outputs.structural_stability <= 1.0):
                return False
            if not (0.0 <= vmm_outputs.dynamic_validation_score <= 1.0):
                return False

            # Validate data quality scores
            quality = self.data_quality
            for score_field in [
                "completeness_score",
                "accuracy_score",
                "timeliness_score",
                "consistency_score",
                "overall_score",
            ]:
                score = getattr(quality, score_field)
                if not (0.0 <= score <= 1.0):
                    return False

            # Validate calibration artifacts
            for artifact in self.calibration_artifacts:
                if not (0.0 <= artifact.spurious_rate <= 1.0):
                    return False
                if not (0.0 <= artifact.structural_stability <= 1.0):
                    return False

            return True

        except Exception:
            return False

    @classmethod
    def from_vmm_result(
        cls,
        vmm_result: VMMResult,
        vmm_config: VMMConfig,
        market: str,
        window_start: str,
        window_end: str,
        calibration_artifacts: List[CalibrationArtifact],
        data_quality: DataQualityEvidence,
        analyst: str = "Theo",
        **kwargs,
    ) -> "EvidenceBundle":
        """Create EvidenceBundle from VMM analysis result."""

        # Extract VMM outputs
        vmm_outputs = VMMEvidence(
            regime_confidence=vmm_result.regime_confidence,
            structural_stability=vmm_result.structural_stability,
            dynamic_validation_score=vmm_result.dynamic_validation_score,
            elbo_convergence=vmm_result.elbo_convergence,
            iteration_count=vmm_result.iterations,
            runtime_seconds=vmm_result.runtime,
            convergence_status=vmm_result.convergence_status,
            numerical_stability=vmm_result.numerical_stability,
        )

        # Create bundle
        return cls(
            bundle_id="",  # Will be auto-generated
            creation_timestamp=datetime.now().isoformat(),
            analysis_window_start=window_start,
            analysis_window_end=window_end,
            market=market,
            vmm_outputs=vmm_outputs,
            calibration_artifacts=calibration_artifacts,
            data_quality=data_quality,
            vmm_config=vmm_config.to_dict(),
            data_sources=kwargs.get("data_sources", []),
            golden_dataset_validation=kwargs.get("golden_dataset_validation", {}),
            reproducibility_metrics=kwargs.get("reproducibility_metrics", {}),
            analyst=analyst,
            version="1.0.0",
            checksum="",  # Will be auto-computed
        )

    def get_calibration_summary(self) -> Dict[str, Any]:
        """Get summary of calibration artifacts."""
        if not self.calibration_artifacts:
            return {}

        summary = {
            "total_artifacts": len(self.calibration_artifacts),
            "methods_used": list(set(art.method for art in self.calibration_artifacts)),
            "avg_spurious_rate": sum(art.spurious_rate for art in self.calibration_artifacts)
            / len(self.calibration_artifacts),
            "avg_structural_stability": sum(
                art.structural_stability for art in self.calibration_artifacts
            )
            / len(self.calibration_artifacts),
            "latest_calibration": max(art.timestamp for art in self.calibration_artifacts),
        }

        return summary
