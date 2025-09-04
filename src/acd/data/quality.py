"""
ACD Data Quality Module

Implements comprehensive data quality metrics and validation:
- Completeness: Data coverage and missing value analysis
- Accuracy: Data validation and outlier detection
- Timeliness: Data freshness and staleness detection
- Consistency: Cross-field validation and data integrity
"""

import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class DataQualityMetrics:
    """Comprehensive data quality metrics"""

    # Completeness metrics
    total_records: int
    complete_records: int
    completeness_rate: float
    missing_values_by_column: Dict[str, int]
    missing_rate_by_column: Dict[str, float]

    # Accuracy metrics
    validation_errors: List[str]
    outlier_count: int
    outlier_rate: float
    data_type_errors: List[str]

    # Timeliness metrics
    data_age_hours: float
    is_stale: bool
    staleness_threshold_hours: float
    last_update: Optional[datetime]

    # Consistency metrics
    consistency_errors: List[str]
    cross_field_validation_passed: bool
    schema_compliance: bool

    # Overall quality score
    overall_quality_score: float

    def __post_init__(self):
        """Calculate derived metrics"""
        if self.total_records > 0:
            self.completeness_rate = self.complete_records / self.total_records
        else:
            self.completeness_rate = 0.0

        if self.total_records > 0:
            self.outlier_rate = self.outlier_count / self.total_records
        else:
            self.outlier_rate = 0.0


class DataQualityError(Exception):
    """Custom exception for data quality errors"""


class DataQualityConfig:
    """Configuration for data quality assessment"""

    def __init__(
        self,
        staleness_threshold_hours: float = 24.0,
        completeness_threshold: float = 0.95,
        outlier_threshold_std: float = 3.0,
        validation_strict: bool = True,
        enable_outlier_detection: bool = True,
    ):
        self.staleness_threshold_hours = staleness_threshold_hours
        self.completeness_threshold = completeness_threshold
        self.outlier_threshold_std = outlier_threshold_std
        self.validation_strict = validation_strict
        self.enable_outlier_detection = enable_outlier_detection


class DataQualityAssessment:
    """Main class for assessing data quality"""

    def __init__(self, config: DataQualityConfig):
        """Initialize data quality assessment with configuration"""
        self.config = config
        self.quality_history = []

    def assess_quality(
        self,
        data: pd.DataFrame,
        expected_schema: Optional[Dict] = None,
        reference_data: Optional[pd.DataFrame] = None,
    ) -> DataQualityMetrics:
        """
        Comprehensive data quality assessment

        Args:
            data: DataFrame to assess
            expected_schema: Expected data schema for validation
            reference_data: Reference data for consistency checks

        Returns:
            DataQualityMetrics object with comprehensive quality assessment
        """
        if data.empty:
            raise DataQualityError("Cannot assess quality of empty DataFrame")

        # Assess completeness
        completeness_metrics = self._assess_completeness(data)

        # Assess accuracy
        accuracy_metrics = self._assess_accuracy(data)

        # Assess timeliness
        timeliness_metrics = self._assess_timeliness(data)

        # Assess consistency
        consistency_metrics = self._assess_consistency(data, expected_schema, reference_data)

        # Calculate overall quality score
        overall_score = self._calculate_overall_score(
            completeness_metrics, accuracy_metrics, timeliness_metrics, consistency_metrics
        )

        # Create quality metrics object
        quality_metrics = DataQualityMetrics(
            total_records=len(data),
            complete_records=completeness_metrics["complete_records"],
            completeness_rate=completeness_metrics["completeness_rate"],
            missing_values_by_column=completeness_metrics["missing_values_by_column"],
            missing_rate_by_column=completeness_metrics["missing_rate_by_column"],
            validation_errors=accuracy_metrics["validation_errors"],
            outlier_count=accuracy_metrics["outlier_count"],
            outlier_rate=accuracy_metrics["outlier_rate"],
            data_type_errors=accuracy_metrics["data_type_errors"],
            data_age_hours=timeliness_metrics["data_age_hours"],
            is_stale=timeliness_metrics["is_stale"],
            staleness_threshold_hours=self.config.staleness_threshold_hours,
            last_update=timeliness_metrics["last_update"],
            consistency_errors=consistency_metrics["consistency_errors"],
            cross_field_validation_passed=consistency_metrics["cross_field_validation_passed"],
            schema_compliance=consistency_metrics["schema_compliance"],
            overall_quality_score=overall_score,
        )

        # Store in history
        self.quality_history.append(
            {"timestamp": datetime.now(timezone.utc), "metrics": quality_metrics}
        )

        return quality_metrics

    def _assess_completeness(self, data: pd.DataFrame) -> Dict[str, Any]:
        """Assess data completeness and missing values"""
        total_records = len(data)

        # Count missing values by column
        missing_values_by_column = {}
        missing_rate_by_column = {}

        for column in data.columns:
            missing_count = data[column].isna().sum()
            missing_values_by_column[column] = missing_count
            missing_rate_by_column[column] = (
                missing_count / total_records if total_records > 0 else 0.0
            )

        # Count complete records (no missing values)
        complete_records = total_records - data.isna().any(axis=1).sum()
        completeness_rate = complete_records / total_records if total_records > 0 else 0.0

        return {
            "total_records": total_records,
            "complete_records": complete_records,
            "completeness_rate": completeness_rate,
            "missing_values_by_column": missing_values_by_column,
            "missing_rate_by_column": missing_rate_by_column,
        }

    def _assess_accuracy(self, data: pd.DataFrame) -> Dict[str, Any]:
        """Assess data accuracy and validation"""
        validation_errors = []
        data_type_errors = []
        outlier_count = 0

        # Check data types and validation
        for column in data.columns:
            # Check for numeric columns that should be numeric
            if "price" in column.lower() or "volume" in column.lower():
                if not pd.api.types.is_numeric_dtype(data[column]):
                    data_type_errors.append(
                        f"Column {column} should be numeric but is {data[column].dtype}"
                    )

            # Check for timestamp columns
            if "timestamp" in column.lower() or "time" in column.lower():
                if not pd.api.types.is_datetime64_any_dtype(data[column]):
                    data_type_errors.append(
                        f"Column {column} should be datetime but is {data[column].dtype}"
                    )

        # Outlier detection for numeric columns
        if self.config.enable_outlier_detection:
            outlier_count = self._detect_outliers(data)

        # Calculate outlier rate
        outlier_rate = outlier_count / len(data) if len(data) > 0 else 0.0

        return {
            "validation_errors": validation_errors,
            "data_type_errors": data_type_errors,
            "outlier_count": outlier_count,
            "outlier_rate": outlier_rate,
        }

    def _detect_outliers(self, data: pd.DataFrame) -> int:
        """Detect outliers using statistical methods"""
        outlier_count = 0

        for column in data.columns:
            if pd.api.types.is_numeric_dtype(data[column]):
                # Remove NaN values for outlier detection
                clean_data = data[column].dropna()

                if len(clean_data) > 0:
                    # Z-score method for outlier detection
                    z_scores = np.abs((clean_data - clean_data.mean()) / clean_data.std())
                    outliers = z_scores > self.config.outlier_threshold_std
                    outlier_count += outliers.sum()

        return outlier_count

    def _assess_timeliness(self, data: pd.DataFrame) -> Dict[str, Any]:
        """Assess data timeliness and freshness"""
        # Look for timestamp columns
        timestamp_columns = [
            col for col in data.columns if "timestamp" in col.lower() or "time" in col.lower()
        ]

        if not timestamp_columns:
            # No timestamp column found
            return {"data_age_hours": float("inf"), "is_stale": True, "last_update": None}

        # Use the first timestamp column found
        timestamp_col = timestamp_columns[0]

        # Convert to datetime if needed
        if not pd.api.types.is_datetime64_any_dtype(data[timestamp_col]):
            try:
                data[timestamp_col] = pd.to_datetime(data[timestamp_col])
            except Exception:
                return {"data_age_hours": float("inf"), "is_stale": True, "last_update": None}

        # Find the most recent timestamp
        last_update = data[timestamp_col].max()

        if pd.isna(last_update):
            return {"data_age_hours": float("inf"), "is_stale": True, "last_update": None}

        # Calculate data age
        now = datetime.now(timezone.utc)
        if last_update.tzinfo is None:
            # Assume UTC if no timezone info
            last_update = last_update.replace(tzinfo=timezone.utc)

        data_age = now - last_update
        data_age_hours = data_age.total_seconds() / 3600

        # Check if data is stale
        is_stale = data_age_hours > self.config.staleness_threshold_hours

        return {"data_age_hours": data_age_hours, "is_stale": is_stale, "last_update": last_update}

    def _assess_consistency(
        self,
        data: pd.DataFrame,
        expected_schema: Optional[Dict],
        reference_data: Optional[pd.DataFrame],
    ) -> Dict[str, Any]:
        """Assess data consistency and integrity"""
        consistency_errors = []
        cross_field_validation_passed = True
        schema_compliance = True

        # Schema compliance check
        if expected_schema:
            schema_compliance = self._check_schema_compliance(data, expected_schema)
            if not schema_compliance:
                consistency_errors.append("Data does not comply with expected schema")

        # Cross-field validation
        cross_field_validation_passed = self._validate_cross_fields(data)
        if not cross_field_validation_passed:
            consistency_errors.append("Cross-field validation failed")

        # Reference data consistency check
        if reference_data is not None:
            ref_consistency = self._check_reference_consistency(data, reference_data)
            if not ref_consistency:
                consistency_errors.append("Data inconsistent with reference dataset")

        return {
            "consistency_errors": consistency_errors,
            "cross_field_validation_passed": cross_field_validation_passed,
            "schema_compliance": schema_compliance,
        }

    def _check_schema_compliance(self, data: pd.DataFrame, expected_schema: Dict) -> bool:
        """Check if data complies with expected schema"""
        try:
            # Check required columns
            if "required_columns" in expected_schema:
                required_cols = expected_schema["required_columns"]
                missing_cols = [col for col in required_cols if col not in data.columns]
                if missing_cols:
                    return False

            # Check data types
            if "dtypes" in expected_schema:
                for col, expected_dtype in expected_schema["dtypes"].items():
                    if col in data.columns:
                        actual_dtype = str(data[col].dtype)
                        if expected_dtype not in actual_dtype:
                            return False

            return True

        except Exception:
            return False

    def _validate_cross_fields(self, data: pd.DataFrame) -> bool:
        """Validate relationships between fields"""
        try:
            # Example: if we have both bid and ask prices, ask should be >= bid
            if "bid_price" in data.columns and "ask_price" in data.columns:
                invalid_spreads = data["ask_price"] < data["bid_price"]
                if invalid_spreads.any():
                    return False

            # Example: if we have volume and price, volume should be positive
            if "volume" in data.columns:
                negative_volumes = data["volume"] < 0
                if negative_volumes.any():
                    return False

            return True

        except Exception:
            return False

    def _check_reference_consistency(
        self, data: pd.DataFrame, reference_data: pd.DataFrame
    ) -> bool:
        """Check consistency with reference dataset"""
        try:
            # Simple consistency check: compare basic statistics
            if len(data) == 0 or len(reference_data) == 0:
                return True

            # Compare numeric columns
            numeric_cols = data.select_dtypes(include=[np.number]).columns
            ref_numeric_cols = reference_data.select_dtypes(include=[np.number]).columns

            common_numeric_cols = set(numeric_cols) & set(ref_numeric_cols)

            for col in common_numeric_cols:
                data_mean = data[col].mean()
                ref_mean = reference_data[col].mean()

                # Check if means are within reasonable range (e.g., 50% difference)
                if abs(data_mean - ref_mean) > 0.5 * abs(ref_mean):
                    return False

            return True

        except Exception:
            return False

    def _calculate_overall_score(
        self, completeness: Dict, accuracy: Dict, timeliness: Dict, consistency: Dict
    ) -> float:
        """Calculate overall quality score (0-1)"""
        scores = []

        # Completeness score
        completeness_score = completeness["completeness_rate"]
        scores.append(completeness_score)

        # Accuracy score (inverse of error rates)
        accuracy_score = 1.0 - accuracy["outlier_rate"]
        scores.append(max(0.0, accuracy_score))

        # Timeliness score
        if timeliness["is_stale"]:
            timeliness_score = 0.0
        else:
            # Score based on how fresh the data is
            max_freshness_hours = self.config.staleness_threshold_hours
            age_hours = timeliness["data_age_hours"]
            timeliness_score = max(0.0, 1.0 - (age_hours / max_freshness_hours))
        scores.append(timeliness_score)

        # Consistency score
        consistency_score = 1.0 if consistency["cross_field_validation_passed"] else 0.0
        scores.append(consistency_score)

        # Calculate weighted average
        weights = [0.3, 0.3, 0.2, 0.2]  # Completeness, Accuracy, Timeliness, Consistency
        overall_score = sum(score * weight for score, weight in zip(scores, weights))

        return max(0.0, min(1.0, overall_score))

    def get_quality_summary(self) -> Dict[str, Any]:
        """Get summary of quality assessment history"""
        if not self.quality_history:
            return {}

        # Calculate trends
        recent_metrics = self.quality_history[-1]["metrics"]

        summary = {
            "current_quality_score": recent_metrics.overall_quality_score,
            "current_completeness_rate": recent_metrics.completeness_rate,
            "current_outlier_rate": recent_metrics.outlier_rate,
            "current_data_age_hours": recent_metrics.data_age_hours,
            "is_currently_stale": recent_metrics.is_stale,
            "total_assessments": len(self.quality_history),
            "quality_trend": self._calculate_quality_trend(),
        }

        return summary

    def _calculate_quality_trend(self) -> str:
        """Calculate quality trend over time"""
        if len(self.quality_history) < 2:
            return "insufficient_data"

        recent_scores = [h["metrics"].overall_quality_score for h in self.quality_history[-5:]]
        if len(recent_scores) < 2:
            return "insufficient_data"

        # Simple trend calculation
        first_score = recent_scores[0]
        last_score = recent_scores[-1]

        if last_score > first_score + 0.1:
            return "improving"
        elif last_score < first_score - 0.1:
            return "declining"
        else:
            return "stable"


def create_quality_config(
    staleness_threshold_hours: float = 24.0,
    completeness_threshold: float = 0.95,
    outlier_threshold_std: float = 3.0,
) -> DataQualityConfig:
    """Create a standard quality configuration"""
    return DataQualityConfig(
        staleness_threshold_hours=staleness_threshold_hours,
        completeness_threshold=completeness_threshold,
        outlier_threshold_std=outlier_threshold_std,
    )


def assess_data_quality(
    data: pd.DataFrame,
    config: Optional[DataQualityConfig] = None,
    expected_schema: Optional[Dict] = None,
) -> DataQualityMetrics:
    """
    Convenience function for assessing data quality

    Args:
        data: DataFrame to assess
        config: Optional quality configuration
        expected_schema: Optional expected schema

    Returns:
        DataQualityMetrics object
    """
    if config is None:
        config = create_quality_config()

    assessor = DataQualityAssessment(config)
    return assessor.assess_quality(data, expected_schema)
