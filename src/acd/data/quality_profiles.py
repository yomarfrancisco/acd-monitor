"""
Source-Specific Data Quality Profiles for ACD Monitor.

Defines quality thresholds and validation rules for different data source types.
"""

import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class DataSourceType(Enum):
    """Enumeration of supported data source types."""

    CDS_LIVE = "CDS_live"
    BOND_DAILY = "Bond_daily"
    REGULATORY_DISCLOSURE = "Regulatory_disclosure"
    MARKET_DATA = "Market_data"
    ANALYST_FEED = "Analyst_feed"


@dataclass
class QualityThresholds:
    """Quality thresholds for a specific data source type."""

    timeliness_critical: float = 0.9  # Critical threshold for timeliness
    timeliness_standard: float = 0.7  # Standard threshold for timeliness
    completeness: float = 0.8  # Minimum completeness score
    consistency: float = 0.75  # Minimum consistency score
    accuracy: float = 0.8  # Minimum accuracy score
    overall_min: float = 0.7  # Minimum overall quality score

    # Source-specific thresholds
    staleness_hours_critical: int = 1  # Critical staleness threshold in hours
    staleness_hours_standard: int = 24  # Standard staleness threshold in hours
    outlier_tolerance: float = 0.05  # Tolerance for outlier detection
    cross_field_validation: bool = True  # Enable cross-field validation
    reference_data_consistency: bool = True  # Enable reference data checks


@dataclass
class QualityProfile:
    """Complete quality profile for a data source type."""

    source_type: DataSourceType
    thresholds: QualityThresholds
    description: str
    rationale: str
    validation_rules: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def validate_quality_scores(self, scores: Dict[str, float]) -> Dict[str, Any]:
        """Validate quality scores against profile thresholds."""
        validation_results = {
            "profile": self.source_type.value,
            "overall_score": scores.get("overall_score", 0.0),
            "passes": True,
            "failures": [],
            "warnings": [],
        }

        # Check overall score
        if scores.get("overall_score", 0.0) < self.thresholds.overall_min:
            validation_results["passes"] = False
            validation_results["failures"].append(
                f"Overall score {scores.get('overall_score', 0.0):.3f} below minimum {self.thresholds.overall_min}"
            )

        # Check individual component scores
        component_checks = [
            ("completeness_score", "completeness", "Completeness"),
            ("consistency_score", "consistency", "Consistency"),
            ("accuracy_score", "accuracy", "Accuracy"),
        ]

        for score_key, threshold_key, component_name in component_checks:
            score = scores.get(score_key, 0.0)
            threshold = getattr(self.thresholds, threshold_key)

            if score < threshold:
                validation_results["passes"] = False
                validation_results["failures"].append(
                    f"{component_name} score {score:.3f} below threshold {threshold}"
                )
            elif score < threshold + 0.1:  # Warning if close to threshold
                validation_results["warnings"].append(
                    f"{component_name} score {score:.3f} close to threshold {threshold}"
                )

        # Check timeliness (special handling for different thresholds)
        timeliness_score = scores.get("timeliness_score", 0.0)
        if timeliness_score < self.thresholds.timeliness_critical:
            validation_results["passes"] = False
            validation_results["failures"].append(
                f"Timeliness score {timeliness_score:.3f} below critical threshold {self.thresholds.timeliness_critical}"
            )
        elif timeliness_score < self.thresholds.timeliness_standard:
            validation_results["warnings"].append(
                f"Timeliness score {timeliness_score:.3f} below standard threshold {self.thresholds.timeliness_standard}"
            )

        return validation_results


class QualityProfileManager:
    """Manages quality profiles and their application."""

    def __init__(self, config: Optional[Dict] = None):
        self.config = config or {}
        self.profiles = self._initialize_profiles()
        self.default_profile = DataSourceType.MARKET_DATA

    def _initialize_profiles(self) -> Dict[DataSourceType, QualityProfile]:
        """Initialize quality profiles for all supported source types."""
        profiles = {}

        # CDS Live Data Profile
        cds_thresholds = QualityThresholds(
            timeliness_critical=0.95,
            timeliness_standard=0.8,
            completeness=0.9,
            consistency=0.85,
            accuracy=0.9,
            overall_min=0.7,
            staleness_hours_critical=0.5,  # 30 minutes
            staleness_hours_standard=2,  # 2 hours
            outlier_tolerance=0.03,
            cross_field_validation=True,
            reference_data_consistency=True,
        )

        profiles[DataSourceType.CDS_LIVE] = QualityProfile(
            source_type=DataSourceType.CDS_LIVE,
            thresholds=cds_thresholds,
            description="Credit Default Swap live market data",
            rationale="CDS data requires high accuracy and timeliness for real-time trading decisions",
            validation_rules=[
                "Price changes must be within 3-sigma bounds",
                "Spread calculations must match reference rates",
                "Firm identifiers must be valid ISIN/LEI codes",
            ],
            metadata={
                "update_frequency": "real_time",
                "data_freshness": "critical",
                "regulatory_impact": "high",
            },
        )

        # Bond Daily Data Profile
        bond_thresholds = QualityThresholds(
            timeliness_critical=0.8,
            timeliness_standard=0.6,
            completeness=0.85,
            consistency=0.8,
            accuracy=0.85,
            overall_min=0.65,
            staleness_hours_critical=4,  # 4 hours
            staleness_hours_standard=24,  # 24 hours
            outlier_tolerance=0.05,
            cross_field_validation=True,
            reference_data_consistency=True,
        )

        profiles[DataSourceType.BOND_DAILY] = QualityProfile(
            source_type=DataSourceType.BOND_DAILY,
            thresholds=bond_thresholds,
            description="Daily bond market data and analytics",
            rationale="Bond data has lower timeliness requirements but needs high completeness for portfolio analysis",
            validation_rules=[
                "Yield calculations must be mathematically consistent",
                "Maturity dates must be valid calendar dates",
                "Credit ratings must be from recognized agencies",
            ],
            metadata={
                "update_frequency": "daily",
                "data_freshness": "standard",
                "regulatory_impact": "medium",
            },
        )

        # Regulatory Disclosure Profile
        regulatory_thresholds = QualityThresholds(
            timeliness_critical=0.7,
            timeliness_standard=0.5,
            completeness=0.95,
            consistency=0.9,
            accuracy=0.95,
            overall_min=0.6,
            staleness_hours_critical=24,  # 24 hours
            staleness_hours_standard=72,  # 72 hours
            outlier_tolerance=0.02,
            cross_field_validation=True,
            reference_data_consistency=True,
        )

        profiles[DataSourceType.REGULATORY_DISCLOSURE] = QualityProfile(
            source_type=DataSourceType.REGULATORY_DISCLOSURE,
            thresholds=regulatory_thresholds,
            description="Regulatory filings and disclosure documents",
            rationale="Regulatory data prioritizes completeness and accuracy over timeliness for compliance",
            validation_rules=[
                "All required fields must be present",
                "Document checksums must validate",
                "Filing dates must be within regulatory deadlines",
            ],
            metadata={
                "update_frequency": "as_needed",
                "data_freshness": "flexible",
                "regulatory_impact": "critical",
            },
        )

        # Market Data Profile (default)
        market_thresholds = QualityThresholds(
            timeliness_critical=0.85,
            timeliness_standard=0.7,
            completeness=0.8,
            consistency=0.75,
            accuracy=0.8,
            overall_min=0.7,
            staleness_hours_critical=2,
            staleness_hours_standard=12,
            outlier_tolerance=0.05,
            cross_field_validation=True,
            reference_data_consistency=True,
        )

        profiles[DataSourceType.MARKET_DATA] = QualityProfile(
            source_type=DataSourceType.MARKET_DATA,
            thresholds=market_thresholds,
            description="General market data feeds",
            rationale="Balanced profile for general market monitoring and analysis",
            validation_rules=[
                "Price data must be positive",
                "Volume data must be non-negative",
                "Timestamp must be in valid range",
            ],
            metadata={
                "update_frequency": "variable",
                "data_freshness": "standard",
                "regulatory_impact": "medium",
            },
        )

        # Analyst Feed Profile
        analyst_thresholds = QualityThresholds(
            timeliness_critical=0.7,
            timeliness_standard=0.5,
            completeness=0.75,
            consistency=0.7,
            accuracy=0.75,
            overall_min=0.6,
            staleness_hours_critical=24,
            staleness_hours_standard=48,
            outlier_tolerance=0.08,
            cross_field_validation=False,  # Analyst data may have inconsistencies
            reference_data_consistency=False,
        )

        profiles[DataSourceType.ANALYST_FEED] = QualityProfile(
            source_type=DataSourceType.ANALYST_FEED,
            thresholds=analyst_thresholds,
            description="Third-party analyst and research data",
            rationale="Analyst data has lower quality requirements but provides valuable insights",
            validation_rules=[
                "Source attribution must be present",
                "Publication date must be valid",
                "Content must be non-empty",
            ],
            metadata={
                "update_frequency": "irregular",
                "data_freshness": "flexible",
                "regulatory_impact": "low",
            },
        )

        return profiles

    def get_profile(self, source_type: DataSourceType) -> QualityProfile:
        """Get quality profile for a specific source type."""
        if source_type not in self.profiles:
            logger.warning(f"Profile not found for {source_type}, using default")
            return self.profiles[self.default_profile]

        return self.profiles[source_type]

    def auto_detect_profile(self, source_metadata: Dict[str, Any]) -> QualityProfile:
        """Auto-detect quality profile based on source metadata."""
        source_type = source_metadata.get("type", "").lower()
        source_metadata.get("name", "").lower()

        # Auto-detection logic
        if "cds" in source_type or "credit" in source_type or "swap" in source_type:
            return self.profiles[DataSourceType.CDS_LIVE]
        elif "bond" in source_type or "fixed_income" in source_type:
            return self.profiles[DataSourceType.BOND_DAILY]
        elif "regulatory" in source_type or "filing" in source_type or "disclosure" in source_type:
            return self.profiles[DataSourceType.REGULATORY_DISCLOSURE]
        elif "analyst" in source_type or "research" in source_type:
            return self.profiles[DataSourceType.ANALYST_FEED]
        elif "market" in source_type or "trading" in source_type:
            return self.profiles[DataSourceType.MARKET_DATA]
        else:
            logger.info(f"Could not auto-detect profile for {source_type}, using default")
            return self.profiles[self.default_profile]

    def get_profile_by_name(self, profile_name: str) -> Optional[QualityProfile]:
        """Get quality profile by name string."""
        try:
            source_type = DataSourceType(profile_name)
            return self.profiles[source_type]
        except ValueError:
            logger.warning(f"Invalid profile name: {profile_name}")
            return None

    def list_profiles(self) -> List[Dict[str, Any]]:
        """List all available quality profiles."""
        profile_list = []
        for source_type, profile in self.profiles.items():
            profile_list.append(
                {
                    "name": source_type.value,
                    "description": profile.description,
                    "rationale": profile.rationale,
                    "overall_min": profile.thresholds.overall_min,
                    "timeliness_critical": profile.thresholds.timeliness_critical,
                    "completeness": profile.thresholds.completeness,
                    "consistency": profile.thresholds.consistency,
                    "accuracy": profile.thresholds.accuracy,
                }
            )
        return profile_list

    def validate_source_quality(
        self, source_metadata: Dict[str, Any], quality_scores: Dict[str, float]
    ) -> Dict[str, Any]:
        """Validate quality scores for a specific source using auto-detected profile."""
        profile = self.auto_detect_profile(source_metadata)
        validation_result = profile.validate_quality_scores(quality_scores)

        # Add profile information to result
        validation_result["profile_name"] = profile.source_type.value
        validation_result["profile_description"] = profile.description
        validation_result["profile_rationale"] = profile.rationale

        return validation_result


def create_quality_profile_manager(config: Optional[Dict] = None) -> QualityProfileManager:
    """Factory function to create a quality profile manager."""
    return QualityProfileManager(config)
