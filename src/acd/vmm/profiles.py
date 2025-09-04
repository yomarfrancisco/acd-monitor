"""
VMM Configuration Profiles
Default settings and acceptance profile tie-ins
"""

import os
from dataclasses import dataclass
from typing import Any, Dict

import yaml


@dataclass
class VMMConfig:
    """Configuration for VMM continuous monitoring"""

    # Window and processing
    window: str = "30D"  # Rolling window size
    step_initial: float = 0.05  # Initial learning rate
    step_decay: float = 0.001  # Learning rate decay parameter
    max_iters: int = 200  # Maximum iterations per window
    tol: float = 1e-5  # Convergence tolerance

    # Output flags
    emit_regime_confidence: bool = True
    emit_structural_stability: bool = True
    emit_environment_quality: bool = True
    emit_dynamic_validation: bool = True

    # Convergence settings
    convergence_window: int = 5  # Successive iterations for convergence check
    early_stop_plateau: bool = True
    divergence_guard: bool = True

    # Variational family settings
    use_low_rank_covariance: bool = False  # Start with mean-field, allow expansion
    min_data_points: int = 2000  # Minimum data for warm-up

    # Acceptance profile
    profile_name: str = "vmm_primary"


def get_default_config() -> VMMConfig:
    """Get default VMM configuration"""
    return VMMConfig()


def load_config_from_yaml(config_path: str) -> VMMConfig:
    """Load VMM configuration from YAML file"""
    if not os.path.exists(config_path):
        return get_default_config()

    with open(config_path, "r") as f:
        config_data = yaml.safe_load(f)

    vmm_config = config_data.get("vmm_monitoring", {})

    return VMMConfig(
        window=vmm_config.get("window", "30D"),
        step_initial=vmm_config.get("step_initial", 0.05),
        step_decay=vmm_config.get("step_decay", 0.001),
        max_iters=vmm_config.get("max_iters", 200),
        tol=vmm_config.get("tol", 1e-5),
        emit_regime_confidence=vmm_config.get("emit_regime_confidence", True),
        emit_structural_stability=vmm_config.get("emit_structural_stability", True),
        emit_environment_quality=vmm_config.get("emit_environment_quality", True),
        emit_dynamic_validation=vmm_config.get("emit_dynamic_validation", True),
        convergence_window=vmm_config.get("convergence_window", 5),
        early_stop_plateau=vmm_config.get("early_stop_plateau", True),
        divergence_guard=vmm_config.get("divergence_guard", True),
        use_low_rank_covariance=vmm_config.get("use_low_rank_covariance", False),
        min_data_points=vmm_config.get("min_data_points", 2000),
        profile_name=vmm_config.get("profile_name", "vmm_primary"),
    )


def get_acceptance_profile(profile_name: str = "vmm_primary") -> Dict[str, Any]:
    """Get acceptance criteria for VMM profiles"""

    profiles = {
        "vmm_primary": {
            "spurious_regime_rate": 0.05,  # ≤ 5% on competitive golden set
            "reproducibility_drift": 0.03,  # |Δstructural_stability| ≤ 0.03
            "regime_source": "vmm",  # Default regime source for risk scoring
            "convergence_tolerance": 1e-5,
            "max_iterations": 200,
        },
        "hmm_research": {
            "spurious_regime_rate": 0.10,  # Higher tolerance for research
            "reproducibility_drift": 0.05,
            "regime_source": "hmm",  # Use HMM for research comparators
            "convergence_tolerance": 1e-4,
            "max_iterations": 100,
        },
    }

    return profiles.get(profile_name, profiles["vmm_primary"])
