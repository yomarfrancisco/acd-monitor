"""
ACD Data Ingestion Module

Handles ingestion of market data from multiple sources:
- Client feeds (real-time trading data)
- Independent feeds (market data providers)
- Regulatory feeds (official market data)
"""

import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

import pandas as pd

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class DataIngestionError(Exception):
    """Custom exception for data ingestion errors"""


class DataIngestionConfig:
    """Configuration for data ingestion"""

    def __init__(
        self,
        max_file_size_mb: int = 100,
        supported_formats: List[str] = None,
        validation_strict: bool = True,
        cache_enabled: bool = True,
        cache_ttl_hours: int = 24,
    ):
        # Validate parameters
        if max_file_size_mb <= 0:
            raise ValueError("max_file_size_mb must be positive")
        if cache_ttl_hours <= 0:
            raise ValueError("cache_ttl_hours must be positive")

        self.max_file_size_mb = max_file_size_mb
        self.supported_formats = supported_formats or ["csv", "parquet", "json"]
        self.validation_strict = validation_strict
        self.cache_enabled = cache_enabled
        self.cache_ttl_hours = cache_ttl_hours


class DataIngestion:
    """Main data ingestion class for ACD platform"""

    def __init__(self, config: DataIngestionConfig):
        """Initialize data ingestion with configuration"""
        self.config = config
        self.ingestion_stats = {
            "total_files": 0,
            "successful_ingestions": 0,
            "failed_ingestions": 0,
            "total_records": 0,
            "last_ingestion": None,
        }

    def ingest_file(
        self, file_path: Union[str, Path], source_type: str, schema_override: Optional[Dict] = None
    ) -> pd.DataFrame:
        """
        Ingest data file with validation and preprocessing

        Args:
            file_path: Path to data file
            source_type: Type of data source ('client', 'independent', 'regulatory')
            schema_override: Optional schema override for validation

        Returns:
            Ingested and validated DataFrame
        """
        file_path = Path(file_path)

        try:
            # Validate file
            self._validate_file(file_path)

            # Determine file format and ingest
            file_format = self._detect_format(file_path)
            raw_data = self._read_file(file_path, file_format)

            # Validate and preprocess data
            validated_data = self._validate_data(raw_data, source_type, schema_override)

            # Update ingestion statistics
            self._update_stats(file_path, validated_data, success=True)

            logger.info(f"Successfully ingested {file_path} ({len(validated_data)} records)")
            return validated_data

        except Exception as e:
            self._update_stats(file_path, None, success=False)
            logger.error(f"Failed to ingest {file_path}: {e}")
            raise DataIngestionError(f"Ingestion failed: {e}")

    def _validate_file(self, file_path: Path) -> None:
        """Validate file before ingestion"""
        if not file_path.exists():
            raise DataIngestionError(f"File not found: {file_path}")

        if not file_path.is_file():
            raise DataIngestionError(f"Path is not a file: {file_path}")

        # Check file size
        file_size_mb = file_path.stat().st_size / (1024 * 1024)
        if file_size_mb > self.config.max_file_size_mb:
            raise DataIngestionError(
                f"File size {file_size_mb:.1f}MB exceeds limit {self.config.max_file_size_mb}MB"
            )

        # Check file format
        file_extension = file_path.suffix.lower().lstrip(".")
        if file_extension not in self.config.supported_formats:
            raise DataIngestionError(
                f"Unsupported file format: {file_extension}. "
                f"Supported: {self.config.supported_formats}"
            )

    def _detect_format(self, file_path: Path) -> str:
        """Detect file format from extension"""
        extension = file_path.suffix.lower().lstrip(".")

        if extension == "csv":
            return "csv"
        elif extension == "parquet":
            return "parquet"
        elif extension == "json":
            return "json"
        else:
            # Try to infer from content
            return self._infer_format_from_content(file_path)

    def _infer_format_from_content(self, file_path: Path) -> str:
        """Infer file format from file content"""
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                first_line = f.readline().strip()

                if first_line.startswith("{") or first_line.startswith("["):
                    return "json"
                elif "," in first_line or ";" in first_line:
                    return "csv"
                else:
                    return "csv"  # Default fallback
        except Exception:
            return "csv"  # Default fallback

    def _read_file(self, file_path: Path, file_format: str) -> pd.DataFrame:
        """Read file based on detected format"""
        try:
            if file_format == "csv":
                # Try different CSV dialects
                try:
                    return pd.read_csv(file_path)
                except Exception:
                    # Try with different separators
                    return pd.read_csv(file_path, sep=";")

            elif file_format == "parquet":
                return pd.read_parquet(file_path)

            elif file_format == "json":
                return pd.read_json(file_path)

            else:
                raise DataIngestionError(f"Unsupported format: {file_format}")

        except Exception as e:
            raise DataIngestionError(f"Failed to read {file_format} file: {e}")

    def _validate_data(
        self, data: pd.DataFrame, source_type: str, schema_override: Optional[Dict]
    ) -> pd.DataFrame:
        """Validate and preprocess ingested data"""
        if data.empty:
            raise DataIngestionError("Data file is empty")

        # Apply source-specific validation
        if source_type == "client":
            validated_data = self._validate_client_data(data)
        elif source_type == "independent":
            validated_data = self._validate_independent_data(data)
        elif source_type == "regulatory":
            validated_data = self._validate_regulatory_data(data)
        else:
            raise DataIngestionError(f"Unknown source type: {source_type}")

        # Apply schema override if provided
        if schema_override:
            validated_data = self._apply_schema_override(validated_data, schema_override)

        # Standard preprocessing
        validated_data = self._standard_preprocessing(validated_data)

        return validated_data

    def _validate_client_data(self, data: pd.DataFrame) -> pd.DataFrame:
        """Validate client trading data"""
        required_columns = ["timestamp", "price", "volume", "symbol"]

        # Check required columns
        missing_columns = [col for col in required_columns if col not in data.columns]
        if missing_columns:
            raise DataIngestionError(f"Missing required columns for client data: {missing_columns}")

        # Ensure timestamp column exists and is datetime
        if "timestamp" in data.columns:
            data["timestamp"] = pd.to_datetime(data["timestamp"])

        # Validate numeric columns
        numeric_columns = ["price", "volume"]
        for col in numeric_columns:
            if col in data.columns:
                data[col] = pd.to_numeric(data[col], errors="coerce")

        return data

    def _validate_independent_data(self, data: pd.DataFrame) -> pd.DataFrame:
        """Validate independent market data"""
        # Independent feeds may have different schemas
        # Focus on common market data patterns

        # Ensure at least one price column exists
        price_columns = [col for col in data.columns if "price" in col.lower()]
        if not price_columns:
            raise DataIngestionError("No price columns found in independent data")

        # Convert timestamp if present
        if "timestamp" in data.columns:
            data["timestamp"] = pd.to_datetime(data["timestamp"])

        return data

    def _validate_regulatory_data(self, data: pd.DataFrame) -> pd.DataFrame:
        """Validate regulatory market data"""
        # Regulatory data should have strict validation

        # Check for regulatory identifiers
        regulatory_columns = ["timestamp", "market_id", "instrument_id"]
        missing_columns = [col for col in regulatory_columns if col not in data.columns]
        if missing_columns:
            raise DataIngestionError(f"Missing required regulatory columns: {missing_columns}")

        # Ensure timestamp is properly formatted
        if "timestamp" in data.columns:
            data["timestamp"] = pd.to_datetime(data["timestamp"])

        # Validate regulatory identifiers
        if "market_id" in data.columns:
            if data["market_id"].isna().any():
                raise DataIngestionError("Regulatory data contains missing market IDs")

        return data

    def _apply_schema_override(self, data: pd.DataFrame, schema_override: Dict) -> pd.DataFrame:
        """Apply custom schema override"""
        try:
            # Rename columns if specified
            if "column_mapping" in schema_override:
                data = data.rename(columns=schema_override["column_mapping"])

            # Select specific columns if specified
            if "columns" in schema_override:
                data = data[schema_override["columns"]]

            # Apply data type conversions if specified
            if "dtypes" in schema_override:
                for col, dtype in schema_override["dtypes"].items():
                    if col in data.columns:
                        data[col] = data[col].astype(dtype)

            return data

        except Exception as e:
            raise DataIngestionError(f"Schema override failed: {e}")

    def _standard_preprocessing(self, data: pd.DataFrame) -> pd.DataFrame:
        """Apply standard preprocessing to all data"""
        # Remove completely empty rows
        data = data.dropna(how="all")

        # Sort by timestamp if present
        if "timestamp" in data.columns:
            data = data.sort_values("timestamp")

        # Reset index
        data = data.reset_index(drop=True)

        return data

    def _update_stats(self, file_path: Path, data: Optional[pd.DataFrame], success: bool) -> None:
        """Update ingestion statistics"""
        self.ingestion_stats["total_files"] += 1

        if success:
            self.ingestion_stats["successful_ingestions"] += 1
            if data is not None:
                self.ingestion_stats["total_records"] += len(data)
        else:
            self.ingestion_stats["failed_ingestions"] += 1

        self.ingestion_stats["last_ingestion"] = datetime.now(timezone.utc)

    def get_ingestion_stats(self) -> Dict[str, Any]:
        """Get current ingestion statistics"""
        stats = self.ingestion_stats.copy()

        # Calculate success rate
        if stats["total_files"] > 0:
            stats["success_rate"] = stats["successful_ingestions"] / stats["total_files"]
        else:
            stats["success_rate"] = 0.0

        return stats

    def ingest_directory(
        self, directory_path: Union[str, Path], source_type: str, file_pattern: str = "*.*"
    ) -> List[pd.DataFrame]:
        """
        Ingest all files in a directory matching the pattern

        Args:
            directory_path: Directory containing data files
            source_type: Type of data source
            file_pattern: File pattern to match (e.g., "*.csv")

        Returns:
            List of ingested DataFrames
        """
        directory_path = Path(directory_path)

        if not directory_path.exists() or not directory_path.is_dir():
            raise DataIngestionError(f"Directory not found: {directory_path}")

        # Find matching files
        matching_files = list(directory_path.glob(file_pattern))

        if not matching_files:
            logger.warning(f"No files found matching pattern '{file_pattern}' in {directory_path}")
            return []

        # Ingest each file
        ingested_data = []
        for file_path in matching_files:
            try:
                data = self.ingest_file(file_path, source_type)
                ingested_data.append(data)
            except Exception as e:
                logger.error(f"Failed to ingest {file_path}: {e}")
                continue

        logger.info(f"Ingested {len(ingested_data)} files from {directory_path}")
        return ingested_data


def create_ingestion_config(
    max_file_size_mb: int = 100, validation_strict: bool = True, cache_enabled: bool = True
) -> DataIngestionConfig:
    """Create a standard ingestion configuration"""
    return DataIngestionConfig(
        max_file_size_mb=max_file_size_mb,
        validation_strict=validation_strict,
        cache_enabled=cache_enabled,
    )


def ingest_market_data(
    file_path: Union[str, Path],
    source_type: str = "independent",
    config: Optional[DataIngestionConfig] = None,
) -> pd.DataFrame:
    """
    Convenience function for ingesting market data

    Args:
        file_path: Path to data file
        source_type: Type of data source
        config: Optional configuration override

    Returns:
        Ingested and validated DataFrame
    """
    if config is None:
        config = create_ingestion_config()

    ingestion = DataIngestion(config)
    return ingestion.ingest_file(file_path, source_type)
