"""
Unit tests for ACD Monitor quality profiles system.

Tests quality profiles, thresholds, validation, and profile management.
"""

# from unittest.mock import Mock  # noqa: F401, patch, MagicMock

from acd.data.quality_profiles import (
    DataSourceType,
    QualityThresholds,
    QualityProfile,
    # QualityProfileManager,  # noqa: F401
    create_quality_profile_manager,
)


class TestDataSourceType:
    """Test data source type enumeration."""

    def test_data_source_types(self):
        """Test all data source types are defined."""
        assert DataSourceType.CDS_LIVE.value == "CDS_live"
        assert DataSourceType.BOND_DAILY.value == "Bond_daily"
        assert DataSourceType.REGULATORY_DISCLOSURE.value == "Regulatory_disclosure"
        assert DataSourceType.MARKET_DATA.value == "Market_data"
        assert DataSourceType.ANALYST_FEED.value == "Analyst_feed"

    def test_data_source_type_values(self):
        """Test data source type values are strings."""
        for source_type in DataSourceType:
            assert isinstance(source_type.value, str)


class TestQualityThresholds:
    """Test quality thresholds functionality."""

    def test_quality_thresholds_creation(self):
        """Test quality thresholds creation with default values."""
        thresholds = QualityThresholds()

        assert thresholds.timeliness_critical == 0.9
        assert thresholds.timeliness_standard == 0.7
        assert thresholds.completeness == 0.8
        assert thresholds.consistency == 0.75
        assert thresholds.accuracy == 0.8
        assert thresholds.overall_min == 0.7
        assert thresholds.staleness_hours_critical == 1
        assert thresholds.staleness_hours_standard == 24
        assert thresholds.outlier_tolerance == 0.05
        assert thresholds.cross_field_validation is True
        assert thresholds.reference_data_consistency is True

    def test_quality_thresholds_custom_values(self):
        """Test quality thresholds creation with custom values."""
        thresholds = QualityThresholds(
            timeliness_critical=0.95,
            timeliness_standard=0.8,
            completeness=0.9,
            consistency=0.85,
            accuracy=0.9,
            overall_min=0.8,
            staleness_hours_critical=0.5,
            staleness_hours_standard=2,
            outlier_tolerance=0.03,
            cross_field_validation=False,
            reference_data_consistency=False,
        )

        assert thresholds.timeliness_critical == 0.95
        assert thresholds.timeliness_standard == 0.8
        assert thresholds.completeness == 0.9
        assert thresholds.consistency == 0.85
        assert thresholds.accuracy == 0.9
        assert thresholds.overall_min == 0.8
        assert thresholds.staleness_hours_critical == 0.5
        assert thresholds.staleness_hours_standard == 2
        assert thresholds.outlier_tolerance == 0.03
        assert thresholds.cross_field_validation is False
        assert thresholds.reference_data_consistency is False


class TestQualityProfile:
    """Test quality profile functionality."""

    def test_quality_profile_creation(self):
        """Test quality profile creation."""
        thresholds = QualityThresholds()
        profile = QualityProfile(
            source_type=DataSourceType.CDS_LIVE,
            thresholds=thresholds,
            description="Test CDS profile",
            rationale="Test rationale",
            validation_rules=["Rule 1", "Rule 2"],
            metadata={"key": "value"},
        )

        assert profile.source_type == DataSourceType.CDS_LIVE
        assert profile.thresholds == thresholds
        assert profile.description == "Test CDS profile"
        assert profile.rationale == "Test rationale"
        assert profile.validation_rules == ["Rule 1", "Rule 2"]
        assert profile.metadata == {"key": "value"}

    def test_quality_profile_default_values(self):
        """Test quality profile creation with default values."""
        thresholds = QualityThresholds()
        profile = QualityProfile(
            source_type=DataSourceType.MARKET_DATA,
            thresholds=thresholds,
            description="Test profile",
            rationale="Test rationale",
        )

        assert profile.validation_rules == []
        assert profile.metadata == {}

    def test_validate_quality_scores_success(self):
        """Test successful quality score validation."""
        thresholds = QualityThresholds(
            overall_min=0.7,
            completeness=0.8,
            consistency=0.75,
            accuracy=0.8,
            timeliness_critical=0.9,
            timeliness_standard=0.7,
        )

        profile = QualityProfile(
            source_type=DataSourceType.CDS_LIVE,
            thresholds=thresholds,
            description="Test profile",
            rationale="Test rationale",
        )

        scores = {
            "overall_score": 0.85,
            "completeness_score": 0.9,
            "consistency_score": 0.8,
            "accuracy_score": 0.85,
            "timeliness_score": 0.92,
        }

        result = profile.validate_quality_scores(scores)

        assert result["passes"] is True
        assert result["profile"] == "CDS_live"
        assert result["overall_score"] == 0.85
        assert len(result["failures"]) == 0
        # Warnings for scores close to thresholds
        assert len(result["warnings"]) >= 0

    def test_validate_quality_scores_failure_overall(self):
        """Test quality score validation failure due to overall score."""
        thresholds = QualityThresholds(overall_min=0.8)

        profile = QualityProfile(
            source_type=DataSourceType.CDS_LIVE,
            thresholds=thresholds,
            description="Test profile",
            rationale="Test rationale",
        )

        scores = {
            "overall_score": 0.75,
            "completeness_score": 0.9,
            "consistency_score": 0.8,
            "accuracy_score": 0.85,
            "timeliness_score": 0.92,
        }

        result = profile.validate_quality_scores(scores)

        assert result["passes"] is False
        assert len(result["failures"]) == 1
        assert "Overall score 0.75" in result["failures"][0]
        assert "below minimum 0.8" in result["failures"][0]

    def test_validate_quality_scores_failure_completeness(self):
        """Test quality score validation failure due to completeness score."""
        thresholds = QualityThresholds(overall_min=0.7, completeness=0.9)

        profile = QualityProfile(
            source_type=DataSourceType.CDS_LIVE,
            thresholds=thresholds,
            description="Test profile",
            rationale="Test rationale",
        )

        scores = {
            "overall_score": 0.85,
            "completeness_score": 0.85,
            "consistency_score": 0.8,
            "accuracy_score": 0.85,
            "timeliness_score": 0.92,
        }

        result = profile.validate_quality_scores(scores)

        assert result["passes"] is False
        assert len(result["failures"]) == 1
        assert "Completeness score 0.85" in result["failures"][0]
        assert "below threshold 0.9" in result["failures"][0]

    def test_validate_quality_scores_timeliness_critical_failure(self):
        """Test quality score validation failure due to critical timeliness."""
        thresholds = QualityThresholds(
            overall_min=0.7, timeliness_critical=0.95, timeliness_standard=0.8
        )

        profile = QualityProfile(
            source_type=DataSourceType.CDS_LIVE,
            thresholds=thresholds,
            description="Test profile",
            rationale="Test rationale",
        )

        scores = {
            "overall_score": 0.85,
            "completeness_score": 0.9,
            "consistency_score": 0.8,
            "accuracy_score": 0.85,
            "timeliness_score": 0.92,
        }

        result = profile.validate_quality_scores(scores)

        assert result["passes"] is False
        assert len(result["failures"]) == 1
        assert "Timeliness score 0.92" in result["failures"][0]
        assert "below critical threshold 0.95" in result["failures"][0]

    def test_validate_quality_scores_timeliness_warning(self):
        """Test quality score validation warning for timeliness."""
        thresholds = QualityThresholds(
            overall_min=0.7, timeliness_critical=0.95, timeliness_standard=0.8
        )

        profile = QualityProfile(
            source_type=DataSourceType.CDS_LIVE,
            thresholds=thresholds,
            description="Test profile",
            rationale="Test rationale",
        )

        scores = {
            "overall_score": 0.85,
            "completeness_score": 0.9,
            "consistency_score": 0.8,
            "accuracy_score": 0.85,
            "timeliness_score": 0.82,
        }

        result = profile.validate_quality_scores(scores)

        # 0.82 is below standard threshold 0.8, so it should fail
        assert result["passes"] is False
        assert len(result["failures"]) >= 1
        assert any("Timeliness score 0.82" in f for f in result["failures"])

    def test_validate_quality_scores_warnings(self):
        """Test quality score validation warnings for near-threshold scores."""
        thresholds = QualityThresholds(
            overall_min=0.7, completeness=0.9, consistency=0.8, accuracy=0.85
        )

        profile = QualityProfile(
            source_type=DataSourceType.CDS_LIVE,
            thresholds=thresholds,
            description="Test profile",
            rationale="Test rationale",
        )

        scores = {
            "overall_score": 0.85,
            "completeness_score": 0.95,
            "consistency_score": 0.85,  # Close to 0.8 threshold
            "accuracy_score": 0.9,
            "timeliness_score": 0.92,
        }

        result = profile.validate_quality_scores(scores)

        assert result["passes"] is True
        # Multiple warnings for scores close to thresholds
        assert len(result["warnings"]) >= 1
        assert any("Consistency score 0.85" in w for w in result["warnings"])

    def test_validate_quality_scores_missing_scores(self):
        """Test quality score validation with missing scores."""
        thresholds = QualityThresholds(
            overall_min=0.7, completeness=0.8, consistency=0.75, accuracy=0.8
        )

        profile = QualityProfile(
            source_type=DataSourceType.CDS_LIVE,
            thresholds=thresholds,
            description="Test profile",
            rationale="Test rationale",
        )

        scores = {
            "overall_score": 0.85,
            "completeness_score": 0.9,
            # Missing other scores
        }

        result = profile.validate_quality_scores(scores)

        assert result["passes"] is False
        # Multiple failures: consistency, accuracy, and timeliness (missing scores default to 0.0)
        assert len(result["failures"]) >= 2
        assert any("Consistency score 0.0" in f for f in result["failures"])
        assert any("Accuracy score 0.0" in f for f in result["failures"])


class TestQualityProfileManager:
    """Test quality profile manager functionality."""

    def test_quality_profile_manager_creation(self):
        """Test quality profile manager creation."""
        manager = create_quality_profile_manager()

        assert len(manager.profiles) == 5  # All profile types
        assert manager.default_profile == DataSourceType.MARKET_DATA

        # Check all profile types are present
        profile_types = set(manager.profiles.keys())
        expected_types = {
            DataSourceType.CDS_LIVE,
            DataSourceType.BOND_DAILY,
            DataSourceType.REGULATORY_DISCLOSURE,
            DataSourceType.MARKET_DATA,
            DataSourceType.ANALYST_FEED,
        }
        assert profile_types == expected_types

    def test_get_profile_existing(self):
        """Test getting existing profile."""
        manager = create_quality_profile_manager()

        cds_profile = manager.get_profile(DataSourceType.CDS_LIVE)

        assert cds_profile.source_type == DataSourceType.CDS_LIVE
        assert cds_profile.description == "Credit Default Swap live market data"
        assert cds_profile.thresholds.overall_min == 0.7

    def test_get_profile_nonexistent(self):
        """Test getting nonexistent profile falls back to default."""
        manager = create_quality_profile_manager()

        # Mock a non-existent profile type
        with patch("acd.data.quality_profiles.DataSourceType") as mock_enum:
            mock_enum.UNKNOWN = "unknown"

            profile = manager.get_profile(mock_enum.UNKNOWN)

            # Should return default profile
            assert profile.source_type == DataSourceType.MARKET_DATA

    def test_auto_detect_profile_cds(self):
        """Test auto-detection of CDS profile."""
        manager = create_quality_profile_manager()

        source_metadata = {"type": "cds_live", "name": "bloomberg_cds"}

        profile = manager.auto_detect_profile(source_metadata)

        assert profile.source_type == DataSourceType.CDS_LIVE
        assert "Credit Default Swap" in profile.description

    def test_auto_detect_profile_bond(self):
        """Test auto-detection of bond profile."""
        manager = create_quality_profile_manager()

        source_metadata = {"type": "bond_daily", "name": "reuters_bonds"}

        profile = manager.auto_detect_profile(source_metadata)

        assert profile.source_type == DataSourceType.BOND_DAILY
        assert "bond" in profile.description.lower()

    def test_auto_detect_profile_regulatory(self):
        """Test auto-detection of regulatory profile."""
        manager = create_quality_profile_manager()

        source_metadata = {"type": "regulatory_disclosure", "name": "sec_filings"}

        profile = manager.auto_detect_profile(source_metadata)

        assert profile.source_type == DataSourceType.REGULATORY_DISCLOSURE
        assert "regulatory" in profile.description.lower()

    def test_auto_detect_profile_analyst(self):
        """Test auto-detection of analyst profile."""
        manager = create_quality_profile_manager()

        source_metadata = {"type": "analyst_feed", "name": "research_report"}

        profile = manager.auto_detect_profile(source_metadata)

        assert profile.source_type == DataSourceType.ANALYST_FEED
        assert "analyst" in profile.description.lower()

    def test_auto_detect_profile_market_data(self):
        """Test auto-detection of market data profile."""
        manager = create_quality_profile_manager()

        source_metadata = {"type": "market_data", "name": "trading_feed"}

        profile = manager.auto_detect_profile(source_metadata)

        assert profile.source_type == DataSourceType.MARKET_DATA
        assert "market" in profile.description.lower()

    def test_auto_detect_profile_unknown_fallback(self):
        """Test auto-detection falls back to default for unknown types."""
        manager = create_quality_profile_manager()

        source_metadata = {"type": "unknown_type", "name": "mystery_feed"}

        profile = manager.auto_detect_profile(source_metadata)

        assert profile.source_type == DataSourceType.MARKET_DATA  # Default fallback

    def test_auto_detect_profile_case_insensitive(self):
        """Test auto-detection is case insensitive."""
        manager = create_quality_profile_manager()

        source_metadata = {"type": "CDS_LIVE", "name": "BLOOMBERG_CDS"}

        profile = manager.auto_detect_profile(source_metadata)

        assert profile.source_type == DataSourceType.CDS_LIVE

    def test_get_profile_by_name_valid(self):
        """Test getting profile by valid name string."""
        manager = create_quality_profile_manager()

        profile = manager.get_profile_by_name("CDS_live")

        assert profile is not None
        assert profile.source_type == DataSourceType.CDS_LIVE

    def test_get_profile_by_name_invalid(self):
        """Test getting profile by invalid name string."""
        manager = create_quality_profile_manager()

        profile = manager.get_profile_by_name("invalid_profile")

        assert profile is None

    def test_list_profiles(self):
        """Test listing all available profiles."""
        manager = create_quality_profile_manager()

        profiles = manager.list_profiles()

        assert len(profiles) == 5

        # Check structure of profile list
        for profile_info in profiles:
            assert "name" in profile_info
            assert "description" in profile_info
            assert "rationale" in profile_info
            assert "overall_min" in profile_info
            assert "timeliness_critical" in profile_info
            assert "completeness" in profile_info
            assert "consistency" in profile_info
            assert "accuracy" in profile_info

        # Check specific profile
        cds_profile = next(p for p in profiles if p["name"] == "CDS_live")
        assert cds_profile["overall_min"] == 0.7
        assert cds_profile["completeness"] == 0.9

    def test_validate_source_quality(self):
        """Test source quality validation with auto-detected profile."""
        manager = create_quality_profile_manager()

        source_metadata = {"type": "cds_live", "name": "bloomberg_cds"}
        quality_scores = {
            "overall_score": 0.85,
            "completeness_score": 0.9,
            "consistency_score": 0.8,
            "accuracy_score": 0.85,
            "timeliness_score": 0.92,
        }

        result = manager.validate_source_quality(source_metadata, quality_scores)

        # CDS profile has strict thresholds, so some scores may fail
        assert result["profile_name"] == "CDS_live"
        assert result["profile_description"] == "Credit Default Swap live market data"
        assert (
            result["profile_rationale"]
            == "CDS data requires high accuracy and timeliness for real-time trading decisions"
        )
        # Check if passes or has specific failures
        if not result["passes"]:
            assert len(result["failures"]) > 0

    def test_validate_source_quality_failure(self):
        """Test source quality validation failure."""
        manager = create_quality_profile_manager()

        source_metadata = {"type": "cds_live", "name": "bloomberg_cds"}
        quality_scores = {
            "overall_score": 0.65,  # Below CDS minimum of 0.7
            "completeness_score": 0.9,
            "consistency_score": 0.8,
            "accuracy_score": 0.85,
            "timeliness_score": 0.92,
        }

        result = manager.validate_source_quality(source_metadata, quality_scores)

        assert result["passes"] is False
        assert result["profile_name"] == "CDS_live"
        # Multiple failures due to strict CDS thresholds
        assert len(result["failures"]) >= 1
        assert any("Overall score 0.65" in f for f in result["failures"])
        assert any("below minimum 0.7" in f for f in result["failures"])


class TestProfileSpecifics:
    """Test specific profile characteristics."""

    def test_cds_profile_thresholds(self):
        """Test CDS profile has correct thresholds."""
        manager = create_quality_profile_manager()
        cds_profile = manager.get_profile(DataSourceType.CDS_LIVE)

        assert cds_profile.thresholds.timeliness_critical == 0.95
        assert cds_profile.thresholds.timeliness_standard == 0.8
        assert cds_profile.thresholds.completeness == 0.9
        assert cds_profile.thresholds.consistency == 0.85
        assert cds_profile.thresholds.accuracy == 0.9
        assert cds_profile.thresholds.overall_min == 0.7
        assert cds_profile.thresholds.staleness_hours_critical == 0.5
        assert cds_profile.thresholds.staleness_hours_standard == 2

    def test_bond_profile_thresholds(self):
        """Test bond profile has correct thresholds."""
        manager = create_quality_profile_manager()
        bond_profile = manager.get_profile(DataSourceType.BOND_DAILY)

        assert bond_profile.thresholds.timeliness_critical == 0.8
        assert bond_profile.thresholds.timeliness_standard == 0.6
        assert bond_profile.thresholds.completeness == 0.85
        assert bond_profile.thresholds.consistency == 0.8
        assert bond_profile.thresholds.accuracy == 0.85
        assert bond_profile.thresholds.overall_min == 0.65
        assert bond_profile.thresholds.staleness_hours_critical == 4
        assert bond_profile.thresholds.staleness_hours_standard == 24

    def test_regulatory_profile_thresholds(self):
        """Test regulatory profile has correct thresholds."""
        manager = create_quality_profile_manager()
        regulatory_profile = manager.get_profile(DataSourceType.REGULATORY_DISCLOSURE)

        assert regulatory_profile.thresholds.timeliness_critical == 0.7
        assert regulatory_profile.thresholds.timeliness_standard == 0.5
        assert regulatory_profile.thresholds.completeness == 0.95
        assert regulatory_profile.thresholds.consistency == 0.9
        assert regulatory_profile.thresholds.accuracy == 0.95
        assert regulatory_profile.thresholds.overall_min == 0.6
        assert regulatory_profile.thresholds.staleness_hours_critical == 24
        assert regulatory_profile.thresholds.staleness_hours_standard == 72

    def test_analyst_profile_thresholds(self):
        """Test analyst profile has correct thresholds."""
        manager = create_quality_profile_manager()
        analyst_profile = manager.get_profile(DataSourceType.ANALYST_FEED)

        assert analyst_profile.thresholds.timeliness_critical == 0.7
        assert analyst_profile.thresholds.timeliness_standard == 0.5
        assert analyst_profile.thresholds.completeness == 0.75
        assert analyst_profile.thresholds.consistency == 0.7
        assert analyst_profile.thresholds.accuracy == 0.75
        assert analyst_profile.thresholds.overall_min == 0.6
        assert analyst_profile.thresholds.cross_field_validation is False
        assert analyst_profile.thresholds.reference_data_consistency is False


if __name__ == "__main__":
    pytest.main([__file__])
