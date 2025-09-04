"""
ACD Data Quality Module

Implements comprehensive data quality metrics and validation:
- Completeness: Data coverage and missing value analysis
- Accuracy: Data validation and outlier detection
- Timeliness: Data freshness and staleness detection (Week 4: Hardened)
- Consistency: Cross-field validation and data integrity (Week 4: Hardened)
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

    # Timeliness metrics (Week 4: Hardened)
    data_age_hours: float
    is_stale: bool
    staleness_threshold_hours: float
    last_update: Optional[datetime]
    timeliness_score: float  # Week 4: New field

    # Consistency metrics (Week 4: Hardened)
    consistency_errors: List[str]
    cross_field_validation_passed: bool
    schema_compliance: bool
    consistency_score: float  # Week 4: New field

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
    """Configuration for data quality assessment (Week 4: Hardened thresholds)"""

    def __init__(
        self,
        # Week 4: Hardened timeliness thresholds
        staleness_threshold_hours: float = 12.0,  # Reduced from 24.0
        critical_staleness_threshold_hours: float = 4.0,  # Week 4: New critical threshold
        completeness_threshold: float = 0.98,  # Increased from 0.95
        outlier_threshold_std: float = 2.5,  # Reduced from 3.0
        validation_strict: bool = True,
        enable_outlier_detection: bool = True,
        # Week 4: New consistency thresholds
        consistency_threshold: float = 0.95,  # Week 4: New field
        cross_field_validation_required: bool = True,  # Week 4: New field
        schema_validation_strict: bool = True,  # Week 4: New field
        # Week 4: New timeliness thresholds
        timeliness_threshold: float = 0.9,  # Week 4: New field
        enable_freshness_monitoring: bool = True,  # Week 4: New field
        # Week 4: New strict thresholds flag
        strict_quality_thresholds: bool = True,  # Week 4: New field
    ):
        # Week 4: Validate hardened thresholds
        if staleness_threshold_hours <= 0:
            raise ValueError("staleness_threshold_hours must be positive")
        if critical_staleness_threshold_hours <= 0:
            raise ValueError("critical_staleness_threshold_hours must be positive")
        if critical_staleness_threshold_hours >= staleness_threshold_hours:
            raise ValueError(
                "critical_staleness_threshold_hours must be less than staleness_threshold_hours"
            )
        if not (0.0 <= completeness_threshold <= 1.0):
            raise ValueError("completeness_threshold must be between 0.0 and 1.0")
        if not (0.0 <= consistency_threshold <= 1.0):
            raise ValueError("consistency_threshold must be between 0.0 and 1.0")
        if not (0.0 <= timeliness_threshold <= 1.0):
            raise ValueError("timeliness_threshold must be between 0.0 and 1.0")

        self.staleness_threshold_hours = staleness_threshold_hours
        self.critical_staleness_threshold_hours = critical_staleness_threshold_hours
        self.completeness_threshold = completeness_threshold
        self.outlier_threshold_std = outlier_threshold_std
        self.validation_strict = validation_strict
        self.enable_outlier_detection = enable_outlier_detection
        self.consistency_threshold = consistency_threshold
        self.cross_field_validation_required = cross_field_validation_required
        self.schema_validation_strict = schema_validation_strict
        self.timeliness_threshold = timeliness_threshold
        self.enable_freshness_monitoring = enable_freshness_monitoring
        self.strict_quality_thresholds = strict_quality_thresholds


class DataQualityAssessment:
    """Main class for assessing data quality (Week 4: Enhanced with hardened thresholds)"""

    def __init__(self, config: DataQualityConfig):
        """Initialize data quality assessment with configuration"""
        self.config = config
        self.quality_history = []

    def assess_quality(
        self,
        data: pd.DataFrame,
        expected_schema: Optional[Dict[str, Any]] = None,
        reference_data: Optional[pd.DataFrame] = None,
    ) -> DataQualityMetrics:
        """
        Assess data quality with comprehensive metrics (Week 4: Enhanced)

        Args:
            data: DataFrame to assess
            expected_schema: Expected schema for validation
            reference_data: Reference data for consistency checks

        Returns:
            Comprehensive quality metrics
        """
        if data.empty:
            raise DataQualityError("Cannot assess quality of empty DataFrame")

        # Week 4: Enhanced timeliness assessment
        timeliness_metrics = self._assess_timeliness(data)

        # Week 4: Enhanced consistency assessment
        consistency_metrics = self._assess_consistency(data, expected_schema, reference_data)

        # Standard assessments
        completeness_metrics = self._assess_completeness(data)
        accuracy_metrics = self._assess_accuracy(data)

        # Week 4: Calculate enhanced quality scores
        timeliness_score = self._calculate_timeliness_score(timeliness_metrics)
        consistency_score = self._calculate_consistency_score(consistency_metrics)

        # Week 4: Apply hardened thresholds
        self._apply_hardened_thresholds(
            timeliness_metrics, consistency_metrics, completeness_metrics
        )

        # Create metrics object
        metrics = DataQualityMetrics(
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
            timeliness_score=timeliness_score,
            consistency_errors=consistency_metrics["consistency_errors"],
            cross_field_validation_passed=consistency_metrics["cross_field_validation_passed"],
            schema_compliance=consistency_metrics["schema_compliance"],
            consistency_score=consistency_score,
            overall_quality_score=0.0,  # Will be calculated below
        )

        # Week 4: Calculate overall quality score with hardened weights
        metrics.overall_quality_score = self._calculate_overall_quality_score(metrics)

        # Store in history
        self.quality_history.append(metrics)

        return metrics

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
        """Week 4: Enhanced timeliness assessment with hardened thresholds"""
        timeliness_metrics = {
            "data_age_hours": 0.0,
            "is_stale": False,
            "is_critical_stale": False,  # Week 4: New critical staleness flag
            "last_update": None,
            "freshness_score": 0.0,
        }

        # Check for timestamp column
        timestamp_cols = [
            col for col in data.columns if "timestamp" in col.lower() or "date" in col.lower()
        ]

        if timestamp_cols:
            # Use first timestamp column found
            timestamp_col = timestamp_cols[0]

            try:
                # Convert to datetime
                timestamps = pd.to_datetime(data[timestamp_col])
                last_update = timestamps.max()
                timeliness_metrics["last_update"] = last_update

                # Calculate data age
                now = datetime.now(timezone.utc)
                data_age = (now - last_update).total_seconds() / 3600
                timeliness_metrics["data_age_hours"] = data_age

                # Week 4: Apply hardened staleness thresholds
                timeliness_metrics["is_stale"] = data_age > self.config.staleness_threshold_hours
                timeliness_metrics["is_critical_stale"] = (
                    data_age > self.config.critical_staleness_threshold_hours
                )

                # Week 4: Calculate freshness score
                timeliness_metrics["freshness_score"] = self._calculate_freshness_score(data_age)

            except Exception as e:
                logger.warning(f"Could not parse timestamps: {e}")
                timeliness_metrics["is_stale"] = True
                timeliness_metrics["is_critical_stale"] = True
                timeliness_metrics["freshness_score"] = 0.0
        else:
            # No timestamp column - assume stale
            timeliness_metrics["is_stale"] = True
            timeliness_metrics["is_critical_stale"] = True
            timeliness_metrics["freshness_score"] = 0.0

        return timeliness_metrics

    def _assess_consistency(
        self,
        data: pd.DataFrame,
        expected_schema: Optional[Dict[str, Any]],
        reference_data: Optional[pd.DataFrame],
    ) -> Dict[str, Any]:
        """Week 4: Enhanced consistency assessment with hardened thresholds"""
        consistency_metrics = {
            "consistency_errors": [],
            "cross_field_validation_passed": True,
            "schema_compliance": True,
            "field_relationships_valid": True,
            "data_integrity_score": 0.0,
        }

        # Week 4: Enhanced schema validation
        if expected_schema and self.config.schema_validation_strict:
            schema_errors = self._validate_schema_strict(data, expected_schema)
            consistency_metrics["consistency_errors"].extend(schema_errors)
            consistency_metrics["schema_compliance"] = len(schema_errors) == 0

        # Week 4: Enhanced cross-field validation
        if self.config.cross_field_validation_required:
            cross_field_errors = self._validate_cross_field_relationships(data)
            consistency_metrics["consistency_errors"].extend(cross_field_errors)
            consistency_metrics["cross_field_validation_passed"] = len(cross_field_errors) == 0
            consistency_metrics["field_relationships_valid"] = len(cross_field_errors) == 0

        # Week 4: Reference data consistency check
        if reference_data is not None:
            reference_errors = self._validate_against_reference(data, reference_data)
            consistency_metrics["consistency_errors"].extend(reference_errors)

        # Week 4: Calculate data integrity score
        consistency_metrics["data_integrity_score"] = self._calculate_data_integrity_score(
            consistency_metrics
        )

        return consistency_metrics

    def _validate_schema_strict(
        self, data: pd.DataFrame, expected_schema: Dict[str, Any]
    ) -> List[str]:
        """Week 4: Strict schema validation with hardened requirements"""
        errors = []

        for column, expected_type in expected_schema.items():
            if column not in data.columns:
                errors.append(f"Missing required column: {column}")
                continue

            # Check data type
            actual_type = str(data[column].dtype)
            if not self._is_compatible_type(actual_type, expected_type):
                errors.append(f"Column {column}: expected {expected_type}, got {actual_type}")

            # Check for null values in required fields
            if expected_schema.get(f"{column}_required", False):
                null_count = data[column].isnull().sum()
                if null_count > 0:
                    errors.append(f"Column {column}: {null_count} null values in required field")

        return errors

    def _validate_cross_field_relationships(self, data: pd.DataFrame) -> List[str]:
        """Week 4: Enhanced cross-field validation with hardened logic"""
        errors = []

        # Validate price relationships
        price_cols = [col for col in data.columns if "price" in col.lower()]
        bid_cols = [col for col in data.columns if "bid" in col.lower()]
        ask_cols = [col for col in data.columns if "ask" in col.lower()]

        # Bid-ask spread validation
        for i, bid_col in enumerate(bid_cols):
            if i < len(ask_cols):
                ask_col = ask_cols[i]
                invalid_spreads = data[data[bid_col] >= data[ask_col]]
                if len(invalid_spreads) > 0:
                    errors.append(
                        f"Invalid bid-ask spread: {bid_col} >= {ask_col} "
                        f"in {len(invalid_spreads)} records"
                    )

        # Price consistency across related fields
        if len(price_cols) > 1:
            for i, col1 in enumerate(price_cols[:-1]):
                for col2 in price_cols[i + 1 :]:
                    # Check for extreme price differences (>50%)
                    price_diff = abs(data[col1] - data[col2]) / data[col1]
                    extreme_diffs = price_diff > 0.5
                    if extreme_diffs.sum() > 0:
                        errors.append(
                            f"Extreme price difference between {col1} and {col2}: "
                            f"{extreme_diffs.sum()} records"
                        )

        # Week 4: Validate negative values in price and volume columns
        for col in data.columns:
            if "price" in col.lower() or "volume" in col.lower():
                negative_values = data[data[col] < 0]
                if len(negative_values) > 0:
                    errors.append(f"Negative values found in {col}: {len(negative_values)} records")

        return errors

    def _validate_against_reference(
        self, data: pd.DataFrame, reference_data: pd.DataFrame
    ) -> List[str]:
        """Week 4: Validate data against reference dataset"""
        errors = []

        # Check for significant deviations from reference
        common_cols = set(data.columns) & set(reference_data.columns)

        for col in common_cols:
            if col in data.columns and col in reference_data.columns:
                # Calculate statistical differences
                data_mean = data[col].mean()
                ref_mean = reference_data[col].mean()

                if ref_mean != 0:
                    relative_diff = abs(data_mean - ref_mean) / abs(ref_mean)
                    if relative_diff > 0.2:  # 20% threshold
                        errors.append(
                            f"Column {col}: significant deviation from reference "
                            f"(diff: {relative_diff:.2%})"
                        )

        return errors

    def _calculate_freshness_score(self, data_age_hours: float) -> float:
        """Week 4: Calculate data freshness score with hardened thresholds"""
        if data_age_hours <= 1:  # 1 hour or less
            return 1.0
        elif data_age_hours <= 4:  # 4 hours or less (critical threshold)
            return 0.8
        elif data_age_hours <= 12:  # 12 hours or less (standard threshold)
            return 0.6
        elif data_age_hours <= 24:  # 24 hours or less
            return 0.3
        else:
            return 0.0

    def _calculate_data_integrity_score(self, consistency_metrics: Dict[str, Any]) -> float:
        """Week 4: Calculate data integrity score"""
        base_score = 1.0

        # Penalize consistency errors
        error_count = len(consistency_metrics["consistency_errors"])
        base_score -= error_count * 0.1

        # Penalize failed validations
        if not consistency_metrics["schema_compliance"]:
            base_score -= 0.3
        if not consistency_metrics["cross_field_validation_passed"]:
            base_score -= 0.2
        if not consistency_metrics["field_relationships_valid"]:
            base_score -= 0.2

        return max(0.0, min(1.0, base_score))

    def _calculate_timeliness_score(self, timeliness_metrics: Dict[str, Any]) -> float:
        """Week 4: Calculate timeliness score"""
        return timeliness_metrics.get("freshness_score", 0.0)

    def _calculate_consistency_score(self, consistency_metrics: Dict[str, Any]) -> float:
        """Week 4: Calculate consistency score"""
        return consistency_metrics.get("data_integrity_score", 0.0)

    def _calculate_overall_quality_score(self, metrics: DataQualityMetrics) -> float:
        """Week 4: Calculate overall quality score with hardened weights"""
        # Week 4: Hardened weights emphasizing timeliness and consistency
        weights = {
            "completeness": 0.25,  # Reduced from previous versions
            "accuracy": 0.25,  # Standard weight
            "timeliness": 0.30,  # Increased weight for Week 4
            "consistency": 0.20,  # Increased weight for Week 4
        }

        scores = {
            "completeness": metrics.completeness_rate,
            "accuracy": 1.0 - metrics.outlier_rate,
            "timeliness": metrics.timeliness_score,
            "consistency": metrics.consistency_score,
        }

        overall_score = sum(weights[key] * scores[key] for key in weights)
        return max(0.0, min(1.0, overall_score))

    def _apply_hardened_thresholds(
        self,
        timeliness_metrics: Dict[str, Any],
        consistency_metrics: Dict[str, Any],
        completeness_metrics: Dict[str, Any],
    ) -> None:
        """Week 4: Apply hardened quality thresholds"""

        # Only apply strict thresholds if enabled
        if not self.config.strict_quality_thresholds:
            return

        # Check critical staleness
        if timeliness_metrics.get("is_critical_stale", False):
            raise DataQualityError(
                f"Data is critically stale: {timeliness_metrics['data_age_hours']:.1f} hours "
                f"(threshold: {self.config.critical_staleness_threshold_hours} hours)"
            )

        # Check standard staleness
        if timeliness_metrics.get("is_stale", False):
            logger.warning(
                f"Data is stale: {timeliness_metrics['data_age_hours']:.1f} hours "
                f"(threshold: {self.config.staleness_threshold_hours} hours)"
            )

        # Check completeness threshold
        if completeness_metrics["completeness_rate"] < self.config.completeness_threshold:
            raise DataQualityError(
                f"Completeness rate {completeness_metrics['completeness_rate']:.2%} "
                f"below threshold {self.config.completeness_threshold:.2%}"
            )

        # Check consistency threshold
        consistency_score = self._calculate_consistency_score(consistency_metrics)
        if consistency_score < self.config.consistency_threshold:
            raise DataQualityError(
                f"Consistency score {consistency_score:.2%} "
                f"below threshold {self.config.consistency_threshold:.2%}"
            )

        # Check timeliness threshold
        timeliness_score = self._calculate_timeliness_score(timeliness_metrics)
        if timeliness_score < self.config.timeliness_threshold:
            raise DataQualityError(
                f"Timeliness score {timeliness_score:.2%} "
                f"below threshold {self.config.timeliness_threshold:.2%}"
            )

    def get_quality_summary(self) -> Dict[str, Any]:
        """Get summary of quality assessment history"""
        if not self.quality_history:
            return {}

        # Calculate trends
        recent_metrics = self.quality_history[-1]

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

        recent_scores = [h.overall_quality_score for h in self.quality_history[-5:]]
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
    # Week 4: New parameters for hardened thresholds
    strict_quality_thresholds: bool = False,
    consistency_threshold: float = 0.95,
    timeliness_threshold: float = 0.9,
) -> DataQualityConfig:
    """Create a standard quality configuration"""
    return DataQualityConfig(
        staleness_threshold_hours=staleness_threshold_hours,
        completeness_threshold=completeness_threshold,
        outlier_threshold_std=outlier_threshold_std,
        strict_quality_thresholds=strict_quality_thresholds,
        consistency_threshold=consistency_threshold,
        timeliness_threshold=timeliness_threshold,
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
