# Source-Specific Quality Profiles

## Overview

The ACD Monitor implements source-specific data quality profiles that automatically adjust validation thresholds based on the type and characteristics of incoming data. This system ensures appropriate quality standards are applied while maintaining operational flexibility.

## Architecture

### Profile-Based Quality Assessment

Quality profiles define different thresholds and validation rules for various data source types:

- **CDS Live Data**: High accuracy and timeliness requirements
- **Bond Daily Data**: Balanced quality with focus on completeness
- **Regulatory Disclosure**: High completeness and accuracy requirements
- **Market Data**: General quality standards
- **Analyst Feed**: Lower quality requirements for research data

### Automatic Profile Detection

The system automatically detects appropriate quality profiles based on:
- Source type metadata
- Source name patterns
- Configuration overrides
- Fallback to default profile

## Quality Profile Types

### CDS Live Data Profile

**Use Case**: Real-time credit default swap trading data

**Thresholds**:
- **Timeliness Critical**: ≥95% (30-minute staleness)
- **Timeliness Standard**: ≥80% (2-hour staleness)
- **Completeness**: ≥90%
- **Consistency**: ≥85%
- **Accuracy**: ≥90%
- **Overall Minimum**: ≥70%

**Rationale**: CDS data requires high accuracy and timeliness for real-time trading decisions

**Validation Rules**:
- Price changes must be within 3-sigma bounds
- Spread calculations must match reference rates
- Firm identifiers must be valid ISIN/LEI codes

**Metadata**:
- Update frequency: real-time
- Data freshness: critical
- Regulatory impact: high

### Bond Daily Data Profile

**Use Case**: Daily bond market data and analytics

**Thresholds**:
- **Timeliness Critical**: ≥80% (4-hour staleness)
- **Timeliness Standard**: ≥60% (24-hour staleness)
- **Completeness**: ≥85%
- **Consistency**: ≥80%
- **Accuracy**: ≥85%
- **Overall Minimum**: ≥65%

**Rationale**: Bond data has lower timeliness requirements but needs high completeness for portfolio analysis

**Validation Rules**:
- Yield calculations must be mathematically consistent
- Maturity dates must be valid calendar dates
- Credit ratings must be from recognized agencies

**Metadata**:
- Update frequency: daily
- Data freshness: standard
- Regulatory impact: medium

### Regulatory Disclosure Profile

**Use Case**: Regulatory filings and disclosure documents

**Thresholds**:
- **Timeliness Critical**: ≥70% (24-hour staleness)
- **Timeliness Standard**: ≥50% (72-hour staleness)
- **Completeness**: ≥95%
- **Consistency**: ≥90%
- **Accuracy**: ≥95%
- **Overall Minimum**: ≥60%

**Rationale**: Regulatory data prioritizes completeness and accuracy over timeliness for compliance

**Validation Rules**:
- All required fields must be present
- Document checksums must validate
- Filing dates must be within regulatory deadlines

**Metadata**:
- Update frequency: as needed
- Data freshness: flexible
- Regulatory impact: critical

### Market Data Profile (Default)

**Use Case**: General market data feeds

**Thresholds**:
- **Timeliness Critical**: ≥85% (2-hour staleness)
- **Timeliness Standard**: ≥70% (12-hour staleness)
- **Completeness**: ≥80%
- **Consistency**: ≥75%
- **Accuracy**: ≥80%
- **Overall Minimum**: ≥70%

**Rationale**: Balanced profile for general market monitoring and analysis

**Validation Rules**:
- Price data must be positive
- Volume data must be non-negative
- Timestamp must be in valid range

**Metadata**:
- Update frequency: variable
- Data freshness: standard
- Regulatory impact: medium

### Analyst Feed Profile

**Use Case**: Third-party analyst and research data

**Thresholds**:
- **Timeliness Critical**: ≥70% (24-hour staleness)
- **Timeliness Standard**: ≥50% (48-hour staleness)
- **Completeness**: ≥75%
- **Consistency**: ≥70%
- **Accuracy**: ≥75%
- **Overall Minimum**: ≥60%

**Rationale**: Analyst data has lower quality requirements but provides valuable insights

**Validation Rules**:
- Source attribution must be present
- Publication date must be valid
- Content must be non-empty

**Metadata**:
- Update frequency: irregular
- Data freshness: flexible
- Regulatory impact: low

## Components

### QualityThresholds

Defines quality thresholds for a specific data source type:

```python
@dataclass
class QualityThresholds:
    timeliness_critical: float = 0.9
    timeliness_standard: float = 0.7
    completeness: float = 0.8
    consistency: float = 0.75
    accuracy: float = 0.8
    overall_min: float = 0.7
    
    # Source-specific thresholds
    staleness_hours_critical: int = 1
    staleness_hours_standard: int = 24
    outlier_tolerance: float = 0.05
    cross_field_validation: bool = True
    reference_data_consistency: bool = True
```

### QualityProfile

Complete quality profile for a data source type:

```python
@dataclass
class QualityProfile:
    source_type: DataSourceType
    thresholds: QualityThresholds
    description: str
    rationale: str
    validation_rules: List[str]
    metadata: Dict[str, Any]
    
    def validate_quality_scores(self, scores: Dict[str, float]) -> Dict[str, Any]
```

### QualityProfileManager

Manages quality profiles and their application:

```python
class QualityProfileManager:
    def __init__(self, config: Optional[Dict] = None)
    def get_profile(self, source_type: DataSourceType) -> QualityProfile
    def auto_detect_profile(self, source_metadata: Dict[str, Any]) -> QualityProfile
    def get_profile_by_name(self, profile_name: str) -> Optional[QualityProfile]
    def list_profiles(self) -> List[Dict[str, Any]]
    def validate_source_quality(self, source_metadata: Dict[str, Any], quality_scores: Dict[str, float]) -> Dict[str, Any]
```

## Usage

### Basic Profile Management

```python
from acd.data.quality_profiles import create_quality_profile_manager

# Create manager
manager = create_quality_profile_manager()

# Get specific profile
cds_profile = manager.get_profile(DataSourceType.CDS_LIVE)

# List all profiles
profiles = manager.list_profiles()
```

### Automatic Profile Detection

```python
# Auto-detect profile based on source metadata
source_metadata = {
    "type": "cds_live",
    "name": "bloomberg_cds_feed"
}

profile = manager.auto_detect_profile(source_metadata)
print(f"Detected profile: {profile.source_type.value}")
```

### Quality Validation

```python
# Validate quality scores against profile
quality_scores = {
    "completeness_score": 0.85,
    "accuracy_score": 0.92,
    "timeliness_score": 0.88,
    "consistency_score": 0.87,
    "overall_score": 0.88
}

validation_result = profile.validate_quality_scores(quality_scores)

if validation_result["passes"]:
    print("✅ Quality validation passed")
else:
    print("❌ Quality validation failed:")
    for failure in validation_result["failures"]:
        print(f"   - {failure}")
```

### Source-Specific Validation

```python
# Validate using auto-detected profile
validation_result = manager.validate_source_quality(source_metadata, quality_scores)

print(f"Profile: {validation_result['profile_name']}")
print(f"Description: {validation_result['profile_description']}")
print(f"Rationale: {validation_result['profile_rationale']}")
```

## Configuration

### Profile Configuration

```python
config = {
    "profiles": {
        "CDS_live": {
            "timeliness_critical": 0.95,
            "timeliness_standard": 0.8,
            "completeness": 0.9,
            "consistency": 0.85,
            "accuracy": 0.9,
            "overall_min": 0.7
        }
    }
}

manager = create_quality_profile_manager(config)
```

### Source Type Mapping

```python
# Custom source type mapping
source_mapping = {
    "bloomberg_cds": DataSourceType.CDS_LIVE,
    "reuters_bonds": DataSourceType.BOND_DAILY,
    "sec_filings": DataSourceType.REGULATORY_DISCLOSURE
}
```

## Integration

### Data Ingestion Integration

```python
from acd.data.ingestion import DataIngestion
from acd.data.quality_profiles import create_quality_profile_manager

class EnhancedDataIngestion(DataIngestion):
    def __init__(self):
        super().__init__()
        self.quality_profile_manager = create_quality_profile_manager()
    
    def validate_data_quality(self, data, source_metadata):
        # Get quality profile
        profile = self.quality_profile_manager.auto_detect_profile(source_metadata)
        
        # Assess quality
        quality_scores = self._assess_quality(data)
        
        # Validate against profile
        validation_result = profile.validate_quality_scores(quality_scores)
        
        return {
            "scores": quality_scores,
            "profile": profile.source_type.value,
            "validation": validation_result
        }
```

### Evidence Bundle Integration

```python
from acd.evidence.bundle import EvidenceBundle

# Create bundle with quality profile
bundle = EvidenceBundle.create_demo_bundle(
    # ... other parameters ...
    quality_profile=quality_profile
)

# Quality profile is now included in bundle
print(f"Quality profile: {bundle.quality_profile.source_type.value}")
```

### Demo Dashboard Integration

```python
# Quality profile information appears in dashboard
dashboard_data = {
    "quality_profiles": {
        "profile_name": "CDS_live",
        "description": "Credit Default Swap live market data",
        "thresholds": {
            "overall_min": 0.7,
            "completeness": 0.9,
            "accuracy": 0.9
        }
    }
}
```

## Validation Logic

### Score Validation

The system validates quality scores against profile thresholds:

1. **Overall Score Check**: Must meet minimum overall threshold
2. **Component Score Checks**: Individual scores must meet component thresholds
3. **Timeliness Special Handling**: Dual threshold system (critical vs. standard)
4. **Warning System**: Alerts when scores are close to thresholds

### Timeliness Validation

Timeliness uses a dual-threshold system:

- **Critical Threshold**: Must be met for real-time operations
- **Standard Threshold**: Must be met for general operations
- **Warnings**: Issued when between thresholds

### Validation Results

```python
validation_result = {
    "profile": "CDS_live",
    "overall_score": 0.88,
    "passes": True,
    "failures": [],
    "warnings": [
        "Timeliness score 0.82 below standard threshold 0.85"
    ]
}
```

## Monitoring and Metrics

### Quality Metrics

- **Profile Distribution**: Count of bundles by quality profile
- **Threshold Compliance**: Success rates for each threshold type
- **Warning Rates**: Frequency of near-threshold scores
- **Profile Switching**: Frequency of profile changes

### Dashboard Metrics

```python
quality_metrics = {
    "total_bundles": 100,
    "profile_distribution": {
        "CDS_live": 25,
        "Bond_daily": 30,
        "Regulatory_disclosure": 15,
        "Market_data": 20,
        "Analyst_feed": 10
    },
    "compliance_rates": {
        "overall": 0.95,
        "timeliness": 0.92,
        "completeness": 0.98,
        "consistency": 0.94,
        "accuracy": 0.96
    }
}
```

## Error Handling

### Profile Detection Failures

- **Unknown Source Type**: Fallback to default profile
- **Invalid Metadata**: Log warning and use default
- **Configuration Errors**: Use built-in profiles

### Validation Failures

- **Missing Scores**: Mark validation as failed
- **Invalid Thresholds**: Use profile defaults
- **Profile Mismatch**: Log error and continue

## Performance Considerations

### Profile Caching

- Profiles are cached after first access
- Configuration changes trigger cache invalidation
- Memory usage scales with profile count

### Validation Performance

- Validation is O(1) for score checks
- Profile detection is O(n) for metadata matching
- Overall performance impact is minimal

## Future Enhancements

### Planned Features

- **Dynamic Thresholds**: Thresholds that adjust based on market conditions
- **Machine Learning**: Automated profile optimization
- **Custom Profiles**: User-defined quality profiles
- **Profile Evolution**: Historical threshold tracking

### Integration Opportunities

- **External Quality Services**: Integration with third-party quality assessment
- **Real-time Monitoring**: Live quality score monitoring
- **Predictive Quality**: Quality prediction based on historical data
- **Regulatory Compliance**: Automated compliance reporting

## Compliance and Standards

### Regulatory Alignment

- **Basel III**: Risk data quality requirements
- **MiFID II**: Market data quality standards
- **GDPR**: Data accuracy and completeness
- **SOX**: Financial data quality controls

### Industry Standards

- **ISO 8000**: Data quality standards
- **DAMA-DMBOK**: Data management best practices
- **DCAM**: Data capability assessment model

## Troubleshooting

### Common Issues

1. **Profile Not Detected**: Check source metadata format
2. **Threshold Mismatch**: Verify profile configuration
3. **Validation Failures**: Review quality score calculations
4. **Performance Issues**: Check profile caching

### Debug Mode

```python
import logging
logging.getLogger("acd.data.quality_profiles").setLevel(logging.DEBUG)

# Enable detailed logging
manager = create_quality_profile_manager()
profile = manager.auto_detect_profile(source_metadata)
```

### Profile Override

```python
# Force specific profile
profile = manager.get_profile(DataSourceType.CDS_LIVE)

# Override thresholds
profile.thresholds.overall_min = 0.8
```

## References

- [ISO 8000 - Data Quality](https://www.iso.org/standard/50798.html)
- [DAMA-DMBOK - Data Management](https://www.dama.org/cpages/body-of-knowledge)
- [DCAM - Data Capability Assessment](https://www.edmcouncil.org/dcam)
- [Basel III - Risk Data Requirements](https://www.bis.org/basel_framework/)
