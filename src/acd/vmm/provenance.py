"""
VMM Provenance Management

Handles persistence and reproducibility of VMM weight matrix estimation
and moment stabilization parameters.
"""

import json
import os
from pathlib import Path
from typing import Dict, Any, Optional
import numpy as np
import logging

logger = logging.getLogger(__name__)


class VMMProvenance:
    """Manages VMM provenance for reproducibility"""

    def __init__(self, artifacts_dir: str = "artifacts"):
        self.artifacts_dir = Path(artifacts_dir)
        self.vmm_dir = self.artifacts_dir / "vmm"
        self.vmm_dir.mkdir(parents=True, exist_ok=True)

    def save_provenance(self, seed: int, provenance_data: Dict[str, Any]) -> Path:
        """Save VMM provenance to JSON file"""

        seed_dir = self.vmm_dir / f"seed-{seed}"
        seed_dir.mkdir(exist_ok=True)

        provenance_file = seed_dir / "provenance.json"

        # Convert numpy arrays to lists for JSON serialization
        serializable_data = self._make_serializable(provenance_data)

        with open(provenance_file, "w") as f:
            json.dump(serializable_data, f, indent=2)

        logger.info(f"Saved VMM provenance to {provenance_file}")
        return provenance_file

    def load_provenance(self, seed: int) -> Optional[Dict[str, Any]]:
        """Load VMM provenance from JSON file"""

        provenance_file = self.vmm_dir / f"seed-{seed}" / "provenance.json"

        if not provenance_file.exists():
            return None

        with open(provenance_file, "r") as f:
            data = json.load(f)

        # Convert lists back to numpy arrays where appropriate
        return self._make_numpy_arrays(data)

    def provenance_exists(self, seed: int) -> bool:
        """Check if provenance exists for given seed"""
        provenance_file = self.vmm_dir / f"seed-{seed}" / "provenance.json"
        return provenance_file.exists()

    def _make_serializable(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Convert numpy arrays to lists for JSON serialization"""
        serializable = {}

        for key, value in data.items():
            if isinstance(value, np.ndarray):
                serializable[key] = value.tolist()
            elif isinstance(value, (np.int64, np.int32, np.int16, np.int8)):
                serializable[key] = int(value)
            elif isinstance(value, (np.float64, np.float32, np.float16)):
                serializable[key] = float(value)
            elif isinstance(value, dict):
                serializable[key] = self._make_serializable(value)
            else:
                serializable[key] = value

        return serializable

    def _make_numpy_arrays(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Convert lists back to numpy arrays where appropriate"""
        numpy_data = {}

        for key, value in data.items():
            if isinstance(value, list) and key in [
                "mu0",
                "sigma0",
                "q01",
                "q99",
                "valid_components",
                "W_diag",
            ]:
                numpy_data[key] = np.array(value)
            elif isinstance(value, dict):
                numpy_data[key] = self._make_numpy_arrays(value)
            else:
                numpy_data[key] = value

        return numpy_data


def create_provenance_data(
    mu0: np.ndarray,
    sigma0: np.ndarray,
    q01: np.ndarray,
    q99: np.ndarray,
    valid_components: np.ndarray,
    W: np.ndarray,
    N: int,
    k: int,
    lag: int,
    ridge_lambda: float,
    condition_number: float,
    seed: int,
) -> Dict[str, Any]:
    """Create provenance data dictionary"""

    return {
        "seed": seed,
        "timestamp": str(np.datetime64("now")),
        "moment_stabilization": {
            "mu0": mu0,
            "sigma0": sigma0,
            "q01": q01,
            "q99": q99,
            "valid_components": valid_components,
            "k_original": len(mu0),
            "k_reduced": np.sum(valid_components),
            "ewma_applied": False,  # Will be updated by caller if needed
            "ewma_alpha": None,
            "components_dropped": None,
        },
        "hac_estimation": {
            "N": N,
            "k": k,
            "lag": lag,
            "ridge_lambda": ridge_lambda,
            "condition_number": condition_number,
        },
        "weight_matrix": {
            "W_diag": np.diag(W),
            "W_shape": W.shape,
            "W_condition": np.linalg.cond(W),
        },
        "methodology": {
            "winsorization_percentiles": [1, 99],
            "variance_threshold": 1e-3,
            "eigenvalue_floor": 1e-6,
            "max_condition_number": 1e6,
        },
    }
