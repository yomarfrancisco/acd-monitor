"""
ACD Data Ingestion Module

Handles ingestion of market data from multiple sources:
- Client feeds (real-time trading data)
- Independent analyst feeds (research and analysis)
- Regulatory disclosures (official market data)
- Market data providers (Bloomberg, Reuters, etc.)
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
        # Week 4 enhancements
        enable_analyst_feeds: bool = True,
        enable_regulatory_feeds: bool = True,
        enable_market_data_providers: bool = True,
        strict_quality_thresholds: bool = True,
        analyst_feed_validation: bool = True,
        regulatory_compliance_check: bool = True,
    ):
        # Validate parameters
        if max_file_size_mb <= 0:
            raise ValueError("max_file_size_mb must be positive")
        if cache_ttl_hours <= 0:
            raise ValueError("cache_ttl_hours must be positive")

        self.max_file_size_mb = max_file_size_mb
        self.supported_formats = supported_formats or ["csv", "parquet", "json", "xlsx"]
        self.validation_strict = validation_strict
        self.cache_enabled = cache_enabled
        self.cache_ttl_hours = cache_ttl_hours

        # Week 4 enhancements
        self.enable_analyst_feeds = enable_analyst_feeds
        self.enable_regulatory_feeds = enable_regulatory_feeds
        self.enable_market_data_providers = enable_market_data_providers
        self.strict_quality_thresholds = strict_quality_thresholds
        self.analyst_feed_validation = analyst_feed_validation
        self.regulatory_compliance_check = regulatory_compliance_check


class AnalystFeedValidator:
    """Validator for independent analyst feeds"""

    def __init__(self):
        self.required_fields = [
            "timestamp",
            "analyst_id",
            "analysis_type",
            "confidence_score",
            "methodology",
            "data_sources",
            "disclaimer",
        ]

        self.analysis_types = [
            "market_structure",
            "coordination_detection",
            "regime_analysis",
            "risk_assessment",
            "regulatory_insight",
        ]

    def validate_analyst_feed(
        self, data: pd.DataFrame, source_metadata: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Validate analyst feed data and metadata"""
        validation_results = {"is_valid": True, "errors": [], "warnings": [], "quality_score": 0.0}

        # Check required fields
        missing_fields = [field for field in self.required_fields if field not in data.columns]
        if missing_fields:
            validation_results["errors"].append(f"Missing required fields: {missing_fields}")
            validation_results["is_valid"] = False

        # Validate analysis type
        if "analysis_type" in data.columns:
            invalid_types = data[~data["analysis_type"].isin(self.analysis_types)][
                "analysis_type"
            ].unique()
            if len(invalid_types) > 0:
                validation_results["warnings"].append(f"Invalid analysis types: {invalid_types}")

        # Validate confidence scores
        if "confidence_score" in data.columns:
            invalid_scores = data[
                (data["confidence_score"] < 0.0) | (data["confidence_score"] > 1.0)
            ]["confidence_score"]
            if len(invalid_scores) > 0:
                validation_results["errors"].append(
                    f"Invalid confidence scores: {invalid_scores.tolist()}"
                )
                validation_results["is_valid"] = False

        # Validate metadata
        if not self._validate_metadata(source_metadata):
            validation_results["errors"].append("Invalid source metadata")
            validation_results["is_valid"] = False

        # Calculate quality score
        validation_results["quality_score"] = self._calculate_quality_score(
            data, validation_results
        )

        return validation_results

    def _validate_metadata(self, metadata: Dict[str, Any]) -> bool:
        """Validate source metadata"""
        required_metadata = ["analyst_credentials", "methodology_description", "data_freshness"]
        return all(field in metadata for field in required_metadata)

    def _calculate_quality_score(
        self, data: pd.DataFrame, validation_results: Dict[str, Any]
    ) -> float:
        """Calculate quality score based on validation results"""
        base_score = 1.0

        # Penalize errors
        base_score -= len(validation_results["errors"]) * 0.2

        # Penalize warnings
        base_score -= len(validation_results["warnings"]) * 0.05

        # Bonus for data completeness
        completeness = 1 - (data.isnull().sum().sum() / (data.shape[0] * data.shape[1]))
        base_score += completeness * 0.1

        return max(0.0, min(1.0, base_score))


class RegulatoryFeedValidator:
    """Validator for regulatory disclosure feeds"""

    def __init__(self):
        self.required_fields = [
            "timestamp",
            "disclosure_id",
            "entity_id",
            "disclosure_type",
            "regulatory_authority",
            "compliance_status",
            "effective_date",
        ]

        self.disclosure_types = [
            "market_abuse",
            "insider_trading",
            "coordination_risk",
            "structural_change",
            "ownership_change",
            "regulatory_action",
        ]

        self.compliance_statuses = ["compliant", "non_compliant", "under_review", "pending"]

    def validate_regulatory_feed(
        self, data: pd.DataFrame, source_metadata: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Validate regulatory feed data and metadata"""
        validation_results = {
            "is_valid": True,
            "errors": [],
            "warnings": [],
            "quality_score": 0.0,
            "compliance_score": 0.0,
        }

        # Check required fields
        missing_fields = [field for field in self.required_fields if field not in data.columns]
        if missing_fields:
            validation_results["errors"].append(f"Missing required fields: {missing_fields}")
            validation_results["is_valid"] = False

        # Validate disclosure types
        if "disclosure_type" in data.columns:
            invalid_types = data[~data["disclosure_type"].isin(self.disclosure_types)][
                "disclosure_type"
            ].unique()
            if len(invalid_types) > 0:
                validation_results["warnings"].append(f"Invalid disclosure types: {invalid_types}")

        # Validate compliance statuses
        if "compliance_status" in data.columns:
            invalid_statuses = data[~data["compliance_status"].isin(self.compliance_statuses)][
                "compliance_status"
            ].unique()
            if len(invalid_statuses) > 0:
                validation_results["errors"].append(
                    f"Invalid compliance statuses: {invalid_statuses}"
                )
                validation_results["is_valid"] = False

        # Validate timestamps
        if "timestamp" in data.columns:
            try:
                pd.to_datetime(data["timestamp"])
            except Exception:
                validation_results["errors"].append("Invalid timestamp format")
                validation_results["is_valid"] = False

        # Validate metadata
        if not self._validate_metadata(source_metadata):
            validation_results["errors"].append("Invalid regulatory metadata")
            validation_results["is_valid"] = False

        # Calculate quality and compliance scores
        validation_results["quality_score"] = self._calculate_quality_score(
            data, validation_results
        )
        validation_results["compliance_score"] = self._calculate_compliance_score(data)

        return validation_results

    def _validate_metadata(self, metadata: Dict[str, Any]) -> bool:
        """Validate regulatory metadata"""
        required_metadata = ["regulatory_authority", "jurisdiction", "compliance_framework"]
        return all(field in metadata for field in required_metadata)

    def _calculate_quality_score(
        self, data: pd.DataFrame, validation_results: Dict[str, Any]
    ) -> float:
        """Calculate quality score based on validation results"""
        base_score = 1.0

        # Penalize errors
        base_score -= len(validation_results["errors"]) * 0.3

        # Penalize warnings
        base_score -= len(validation_results["warnings"]) * 0.1

        # Bonus for data completeness
        completeness = 1 - (data.isnull().sum().sum() / (data.shape[0] * data.shape[1]))
        base_score += completeness * 0.2

        return max(0.0, min(1.0, base_score))

    def _calculate_compliance_score(self, data: pd.DataFrame) -> float:
        """Calculate compliance score"""
        if "compliance_status" not in data.columns:
            return 0.0

        compliant_count = len(data[data["compliance_status"] == "compliant"])
        total_count = len(data)

        return compliant_count / total_count if total_count > 0 else 0.0


class MarketDataProviderValidator:
    """Validator for market data provider feeds"""

    def __init__(self):
        self.required_fields = [
            "timestamp",
            "symbol",
            "price",
            "volume",
            "bid",
            "ask",
            "exchange",
            "currency",
            "data_source",
        ]

        self.supported_exchanges = ["NYSE", "NASDAQ", "LSE", "JSE", "TSE", "ASX", "SGX"]

        self.supported_currencies = ["USD", "EUR", "GBP", "JPY", "ZAR", "AUD", "SGD"]

    def validate_market_data_feed(
        self, data: pd.DataFrame, source_metadata: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Validate market data provider feed"""
        validation_results = {
            "is_valid": True,
            "errors": [],
            "warnings": [],
            "quality_score": 0.0,
            "data_freshness_score": 0.0,
        }

        # Check required fields
        missing_fields = [field for field in self.required_fields if field not in data.columns]
        if missing_fields:
            validation_results["errors"].append(f"Missing required fields: {missing_fields}")
            validation_results["is_valid"] = False

        # Validate exchanges
        if "exchange" in data.columns:
            invalid_exchanges = data[~data["exchange"].isin(self.supported_exchanges)][
                "exchange"
            ].unique()
            if len(invalid_exchanges) > 0:
                validation_results["warnings"].append(f"Unsupported exchanges: {invalid_exchanges}")

        # Validate currencies
        if "currency" in data.columns:
            invalid_currencies = data[~data["currency"].isin(self.supported_currencies)][
                "currency"
            ].unique()
            if len(invalid_currencies) > 0:
                validation_results["warnings"].append(
                    f"Unsupported currencies: {invalid_currencies}"
                )

        # Validate price data
        if "price" in data.columns:
            negative_prices = data[data["price"] < 0]["price"]
            if len(negative_prices) > 0:
                validation_results["errors"].append(
                    f"Negative prices found: {negative_prices.tolist()}"
                )
                validation_results["is_valid"] = False

        # Validate bid-ask spread
        if "bid" in data.columns and "ask" in data.columns:
            invalid_spreads = data[data["bid"] >= data["ask"]]
            if len(invalid_spreads) > 0:
                validation_results["errors"].append(
                    f"Invalid bid-ask spreads: {len(invalid_spreads)} records"
                )
                validation_results["is_valid"] = False

        # Validate metadata
        if not self._validate_metadata(source_metadata):
            validation_results["errors"].append("Invalid market data metadata")
            validation_results["is_valid"] = False

        # Calculate scores
        validation_results["quality_score"] = self._calculate_quality_score(
            data, validation_results
        )
        validation_results["data_freshness_score"] = self._calculate_freshness_score(data)

        return validation_results

    def _validate_metadata(self, metadata: Dict[str, Any]) -> bool:
        """Validate market data metadata"""
        required_metadata = ["provider_name", "data_frequency", "update_latency"]
        return all(field in metadata for field in required_metadata)

    def _calculate_quality_score(
        self, data: pd.DataFrame, validation_results: Dict[str, Any]
    ) -> float:
        """Calculate quality score based on validation results"""
        base_score = 1.0

        # Penalize errors
        base_score -= len(validation_results["errors"]) * 0.25

        # Penalize warnings
        base_score -= len(validation_results["warnings"]) * 0.05

        # Bonus for data completeness
        completeness = 1 - (data.isnull().sum().sum() / (data.shape[0] * data.shape[1]))
        base_score += completeness * 0.15

        return max(0.0, min(1.0, base_score))

    def _calculate_freshness_score(self, data: pd.DataFrame) -> float:
        """Calculate data freshness score"""
        if "timestamp" not in data.columns:
            return 0.0

        try:
            timestamps = pd.to_datetime(data["timestamp"])
            now = pd.Timestamp.now(tz="UTC")

            # Calculate age of most recent data
            max_age = (now - timestamps.max()).total_seconds() / 3600  # hours

            if max_age <= 1:  # 1 hour or less
                return 1.0
            elif max_age <= 24:  # 1 day or less
                return 0.8
            elif max_age <= 168:  # 1 week or less
                return 0.6
            else:
                return 0.3

        except Exception:
            return 0.0


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
            "analyst_feeds": 0,
            "regulatory_feeds": 0,
            "market_data_feeds": 0,
        }

        # Initialize validators
        self.analyst_validator = AnalystFeedValidator()
        self.regulatory_validator = RegulatoryFeedValidator()
        self.market_data_validator = MarketDataProviderValidator()

    def ingest_file(
        self,
        file_path: Union[str, Path],
        source_type: str,
        schema_override: Optional[Dict] = None,
        source_metadata: Optional[Dict[str, Any]] = None,
    ) -> pd.DataFrame:
        """
        Ingest data file with validation and preprocessing

        Args:
            file_path: Path to data file
            source_type: Type of data source ('client', 'analyst', 'regulatory', 'market_data')
            schema_override: Optional schema override for validation
            source_metadata: Metadata about the data source

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

            # Validate and preprocess data based on source type
            validated_data = self._validate_data_by_source(
                raw_data, source_type, schema_override, source_metadata or {}
            )

            # Update ingestion statistics
            self._update_stats(file_path, validated_data, success=True, source_type=source_type)

            logger.info(f"Successfully ingested {file_path} ({len(validated_data)} records)")
            return validated_data

        except Exception as e:
            self._update_stats(file_path, None, success=False, source_type=source_type)
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

    def _validate_data_by_source(
        self,
        data: pd.DataFrame,
        source_type: str,
        schema_override: Optional[Dict],
        source_metadata: Dict[str, Any],
    ) -> pd.DataFrame:
        """Validate data based on source type with enhanced validation"""

        # Apply source-specific validation
        if source_type == "analyst" and self.config.enable_analyst_feeds:
            validation_result = self.analyst_validator.validate_analyst_feed(data, source_metadata)
            if not validation_result["is_valid"] and self.config.analyst_feed_validation:
                raise DataIngestionError(
                    f"Analyst feed validation failed: {validation_result['errors']}"
                )

            # Apply strict quality thresholds if enabled
            if self.config.strict_quality_thresholds and validation_result["quality_score"] < 0.8:
                raise DataIngestionError(
                    f"Analyst feed quality score "
                    f"{validation_result['quality_score']:.2f} below threshold 0.8"
                )

        elif source_type == "regulatory" and self.config.enable_regulatory_feeds:
            validation_result = self.regulatory_validator.validate_regulatory_feed(
                data, source_metadata
            )
            if not validation_result["is_valid"] and self.config.regulatory_compliance_check:
                raise DataIngestionError(
                    f"Regulatory feed validation failed: {validation_result['errors']}"
                )

            # Apply strict quality thresholds if enabled
            if self.config.strict_quality_thresholds and validation_result["quality_score"] < 0.8:
                raise DataIngestionError(
                    f"Regulatory feed quality score "
                    f"{validation_result['quality_score']:.2f} below threshold 0.8"
                )

        elif source_type == "market_data" and self.config.enable_market_data_providers:
            validation_result = self.market_data_validator.validate_market_data_feed(
                data, source_metadata
            )
            if not validation_result["is_valid"]:
                raise DataIngestionError(
                    f"Market data feed validation failed: {validation_result['errors']}"
                )

            # Apply strict quality thresholds if enabled
            if self.config.strict_quality_thresholds and validation_result["quality_score"] < 0.8:
                raise DataIngestionError(
                    f"Market data feed quality score "
                    f"{validation_result['quality_score']:.2f} below threshold 0.8"
                )

        # Apply general validation
        validated_data = self._validate_data(data, source_type, schema_override)

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

    def _update_stats(
        self, file_path: Path, data: Optional[pd.DataFrame], success: bool, source_type: str
    ) -> None:
        """Update ingestion statistics"""
        self.ingestion_stats["total_files"] += 1

        if success:
            self.ingestion_stats["successful_ingestions"] += 1
            if data is not None:
                self.ingestion_stats["total_records"] += len(data)

            # Update source-specific stats
            if source_type == "analyst":
                self.ingestion_stats["analyst_feeds"] += 1
            elif source_type == "regulatory":
                self.ingestion_stats["regulatory_feeds"] += 1
            elif source_type == "market_data":
                self.ingestion_stats["market_data_feeds"] += 1
        else:
            self.ingestion_stats["failed_ingestions"] += 1

        self.ingestion_stats["last_ingestion"] = datetime.now(timezone.utc).isoformat()

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
