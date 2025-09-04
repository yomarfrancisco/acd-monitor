"""Demo pipeline for ACD Monitor.

This module provides end-to-end demonstration of the ACD Monitor pipeline
using mock data and golden datasets for real-world readiness validation.
"""

from .ingestion import MockDataIngestion
from .pipeline import DemoPipeline
from .visualization import DemoVisualization

__all__ = ["MockDataIngestion", "DemoPipeline", "DemoVisualization"]
