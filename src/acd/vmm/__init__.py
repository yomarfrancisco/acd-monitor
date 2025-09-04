"""
VMM - Variational Method of Moments
Continuous monitoring engine for coordination detection
"""

from .engine import VMMConfig, VMMOutput, VMMState, run_vmm
from .profiles import get_default_config

__all__ = ["run_vmm", "VMMConfig", "VMMState", "VMMOutput", "get_default_config"]
