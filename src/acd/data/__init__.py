"""
ACD Data Package

Data ingestion, quality assessment, and feature engineering for ACD analysis.
"""

from .features import (
    DataWindowing,
    FeatureEngineering,
    WindowConfig,
    WindowedData,
    create_window_config,
    create_windows,
)
from .ingest import (
    DataIngestion,
    DataIngestionConfig,
    DataIngestionError,
    create_ingestion_config,
    ingest_market_data,
)
from .quality import (
    DataQualityAssessment,
    DataQualityConfig,
    DataQualityError,
    DataQualityMetrics,
    assess_data_quality,
    create_quality_config,
)

__all__ = [
    # Ingestion
    "DataIngestion",
    "DataIngestionConfig",
    "DataIngestionError",
    "create_ingestion_config",
    "ingest_market_data",
    # Quality
    "DataQualityAssessment",
    "DataQualityConfig",
    "DataQualityError",
    "DataQualityMetrics",
    "create_quality_config",
    "assess_data_quality",
    # Features
    "DataWindowing",
    "FeatureEngineering",
    "WindowConfig",
    "WindowedData",
    "create_window_config",
    "create_windows",
]
