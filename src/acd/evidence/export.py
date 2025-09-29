"""Evidence export module for ACD Monitor.

This module handles export of evidence bundles with RFC3161 timestamping
for regulatory compliance and reproducibility.
"""

import base64
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

import requests

from .bundle import EvidenceBundle


class RFC3161TimestampService:
    """RFC3161 timestamp service for evidence bundles."""

    def __init__(self, service_url: Optional[str] = None):
        """Initialize timestamp service.

        Args:
            service_url: URL of RFC3161 timestamp service. If None, uses default.
        """
        self.service_url = service_url or "https://freetsa.org/tsr"

    def get_timestamp(self, data: bytes) -> Dict[str, Any]:
        """Get RFC3161 timestamp for data.

        Args:
            data: Data to timestamp

        Returns:
            Timestamp response with token and timestamp
        """
        try:
            # Hash the data with SHA-256
            data_hash = hashlib.sha256(data).digest()

            # Encode hash in base64
            encoded_hash = base64.b64encode(data_hash).decode("ascii")

            # Request timestamp from service
            response = requests.get(
                f"{self.service_url}", params={"data": encoded_hash}, timeout=30
            )
            response.raise_for_status()

            # Parse timestamp response
            timestamp_data = response.json()

            return {
                "timestamp_token": timestamp_data.get("token"),
                "timestamp": timestamp_data.get("timestamp"),
                "service_url": self.service_url,
                "hash_algorithm": "SHA-256",
                "encoded_hash": encoded_hash,
            }

        except Exception as e:
            # Fallback to local timestamp if service unavailable
            return {
                "timestamp_token": None,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "service_url": "local_fallback",
                "hash_algorithm": "SHA-256",
                "encoded_hash": base64.b64encode(hashlib.sha256(data).digest()).decode("ascii"),
                "error": str(e),
            }


def export_evidence_bundle(
    bundle: EvidenceBundle,
    output_dir: Union[str, Path],
    include_timestamp: bool = True,
    timestamp_service: Optional[RFC3161TimestampService] = None,
) -> Dict[str, Any]:
    """Export evidence bundle with optional RFC3161 timestamping.

    Args:
        bundle: EvidenceBundle to export
        output_dir: Directory to save exported files
        include_timestamp: Whether to include RFC3161 timestamp
        timestamp_service: RFC3161 timestamp service instance

    Returns:
        Export metadata including file paths and timestamp information
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Generate export metadata
    export_metadata = {
        "export_timestamp": datetime.now(timezone.utc).isoformat(),
        "bundle_id": bundle.bundle_id,
        "market": bundle.market,
        "files_exported": [],
        "timestamp_info": None,
        "checksum_validation": {},
    }

    # Export bundle as JSON
    bundle_json_path = output_dir / f"{bundle.bundle_id}.json"
    bundle_json = bundle.to_json(bundle_json_path)
    export_metadata["files_exported"].append(str(bundle_json_path))

    # Export calibration artifacts
    calibration_dir = output_dir / "calibration"
    calibration_dir.mkdir(exist_ok=True)

    for artifact in bundle.calibration_artifacts:
        # Create market-specific subdirectory
        market_dir = calibration_dir / artifact.market
        market_dir.mkdir(exist_ok=True)

        # Create timestamp subdirectory (YYYYMM format)
        timestamp_str = artifact.timestamp[:7].replace("-", "")  # Extract YYYY-MM
        timestamp_dir = market_dir / timestamp_str
        timestamp_dir.mkdir(exist_ok=True)

        # Export artifact
        artifact_file = timestamp_dir / f"{artifact.method}_{bundle.bundle_id}.json"
        with open(artifact_file, "w") as f:
            json.dump(artifact.calibration_curve, f, indent=2)

        export_metadata["files_exported"].append(str(artifact_file))

    # Export data quality evidence
    quality_file = output_dir / f"{bundle.bundle_id}_quality.json"
    with open(quality_file, "w") as f:
        json.dump(bundle.data_quality.__dict__, f, indent=2)
    export_metadata["files_exported"].append(str(quality_file))

    # Export VMM configuration
    config_file = output_dir / f"{bundle.bundle_id}_config.json"
    with open(config_file, "w") as f:
        json.dump(bundle.vmm_config, f, indent=2)
    export_metadata["files_exported"].append(str(config_file))

    # Export validation metrics
    validation_file = output_dir / f"{bundle.bundle_id}_validation.json"
    validation_data = {
        "golden_dataset_validation": bundle.golden_dataset_validation,
        "reproducibility_metrics": bundle.reproducibility_metrics,
    }
    with open(validation_file, "w") as f:
        json.dump(validation_data, f, indent=2)
    export_metadata["files_exported"].append(str(validation_file))

    # Generate RFC3161 timestamp if requested
    if include_timestamp:
        timestamp_service = timestamp_service or RFC3161TimestampService()

        # Create timestamp for the entire bundle
        bundle_bytes = bundle_json.encode("utf-8")
        timestamp_info = timestamp_service.get_timestamp(bundle_bytes)

        # Save timestamp information
        timestamp_file = output_dir / f"{bundle.bundle_id}_timestamp.json"
        with open(timestamp_file, "w") as f:
            json.dump(timestamp_info, f, indent=2)

        export_metadata["files_exported"].append(str(timestamp_file))
        export_metadata["timestamp_info"] = timestamp_info

    # Validate checksums
    export_metadata["checksum_validation"] = {
        "bundle_checksum": bundle.checksum,
        "export_checksum": hashlib.sha256(bundle_json.encode()).hexdigest(),
        "checksum_match": bundle.checksum == hashlib.sha256(bundle_json.encode()).hexdigest(),
    }

    # Export metadata
    metadata_file = output_dir / f"{bundle.bundle_id}_export_metadata.json"
    with open(metadata_file, "w") as f:
        json.dump(export_metadata, f, indent=2)

    export_metadata["files_exported"].append(str(metadata_file))

    return export_metadata


def create_evidence_summary(
    bundles: List[EvidenceBundle], output_file: Union[str, Path]
) -> Dict[str, Any]:
    """Create summary of multiple evidence bundles.

    Args:
        bundles: List of EvidenceBundle instances
        output_file: Path to save summary

    Returns:
        Summary metadata
    """
    summary = {
        "summary_timestamp": datetime.now(timezone.utc).isoformat(),
        "total_bundles": len(bundles),
        "markets_covered": list(set(bundle.market for bundle in bundles)),
        "date_range": {
            "earliest": min(bundle.analysis_window_start for bundle in bundles),
            "latest": max(bundle.analysis_window_end for bundle in bundles),
        },
        "vmm_performance_summary": {
            "avg_regime_confidence": sum(bundle.vmm_outputs.regime_confidence for bundle in bundles)
            / len(bundles),
            "avg_structural_stability": sum(
                bundle.vmm_outputs.structural_stability for bundle in bundles
            )
            / len(bundles),
            "avg_runtime": sum(bundle.vmm_outputs.runtime_seconds for bundle in bundles)
            / len(bundles),
            "convergence_rate": sum(
                1 for bundle in bundles if bundle.vmm_outputs.convergence_status == "converged"
            )
            / len(bundles),
        },
        "data_quality_summary": {
            "avg_completeness": sum(bundle.data_quality.completeness_score for bundle in bundles)
            / len(bundles),
            "avg_accuracy": sum(bundle.data_quality.accuracy_score for bundle in bundles)
            / len(bundles),
            "avg_timeliness": sum(bundle.data_quality.timeliness_score for bundle in bundles)
            / len(bundles),
            "avg_consistency": sum(bundle.data_quality.consistency_score for bundle in bundles)
            / len(bundles),
            "avg_overall": sum(bundle.data_quality.overall_score for bundle in bundles)
            / len(bundles),
        },
        "calibration_summary": {
            "total_artifacts": sum(len(bundle.calibration_artifacts) for bundle in bundles),
            "methods_used": list(
                set(art.method for bundle in bundles for art in bundle.calibration_artifacts)
            ),
            "avg_spurious_rate": (
                sum(
                    sum(art.spurious_rate for art in bundle.calibration_artifacts)
                    for bundle in bundles
                )
                / sum(len(bundle.calibration_artifacts) for bundle in bundles)
                if any(len(bundle.calibration_artifacts) > 0 for bundle in bundles)
                else 0.0
            ),
        },
    }

    # Save summary
    output_file = Path(output_file)
    output_file.parent.mkdir(parents=True, exist_ok=True)
    with open(output_file, "w") as f:
        json.dump(summary, f, indent=2)

    return summary


def validate_exported_bundle(export_dir: Union[str, Path]) -> Dict[str, Any]:
    """Validate exported evidence bundle.

    Args:
        export_dir: Directory containing exported bundle files

    Returns:
        Validation results
    """
    export_dir = Path(export_dir)
    validation_results = {
        "validation_timestamp": datetime.now(timezone.utc).isoformat(),
        "export_dir": str(export_dir),
        "files_found": [],
        "validation_errors": [],
        "overall_valid": True,
    }

    try:
        # Find bundle JSON file
        bundle_files = list(export_dir.glob("*.json"))
        if not bundle_files:
            validation_results["validation_errors"].append(
                "No JSON files found in export directory"
            )
            validation_results["overall_valid"] = False
            return validation_results

        # Find main bundle file (not metadata or timestamp files)
        bundle_file = None
        for file in bundle_files:
            if not any(
                suffix in file.name
                for suffix in ["_metadata", "_timestamp", "_quality", "_config", "_validation"]
            ):
                bundle_file = file
                break

        if not bundle_file:
            validation_results["validation_errors"].append("No main bundle file found")
            validation_results["overall_valid"] = False
            return validation_results

        # Load and validate bundle
        with open(bundle_file, "r") as f:
            bundle_data = json.load(f)

        # Basic structure validation
        required_fields = ["bundle_id", "vmm_outputs", "calibration_artifacts", "data_quality"]
        for field in required_fields:
            if field not in bundle_data:
                validation_results["validation_errors"].append(f"Missing required field: {field}")
                validation_results["overall_valid"] = False

        # Record found files
        validation_results["files_found"] = [str(f) for f in bundle_files]

        # Validate checksum if present
        if "checksum" in bundle_data:
            # Recompute checksum
            bundle_copy = bundle_data.copy()
            bundle_copy.pop("checksum", None)
            computed_checksum = hashlib.sha256(
                json.dumps(bundle_copy, sort_keys=True, default=str).encode()
            ).hexdigest()

            if bundle_data["checksum"] != computed_checksum:
                validation_results["validation_errors"].append("Checksum validation failed")
                validation_results["overall_valid"] = False

    except Exception as e:
        validation_results["validation_errors"].append(f"Validation error: {str(e)}")
        validation_results["overall_valid"] = False

    return validation_results
