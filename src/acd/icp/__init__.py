"""
ICP (Invariant Causal Prediction) Module

Implements Brief 55+ ICP methodology for detecting environment-invariant
vs. environment-sensitive pricing relationships.
"""

from .engine import ICPConfig, ICPEngine, ICPResult, run_icp_analysis

__all__ = ["ICPEngine", "ICPConfig", "ICPResult", "run_icp_analysis"]
