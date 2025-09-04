# Adaptive Threshold Framework

## Overview

The Adaptive Threshold Framework implements dataset-size-aware thresholds for spurious regime detection in the ACD Monitor. This framework addresses the statistical reality that larger datasets can tolerate slightly higher spurious regime rates while maintaining the same level of confidence in detecting true coordination.

## Mathematical Formulation

### Threshold Categories

The framework defines three dataset size categories with corresponding thresholds:

1. **Small Datasets** (≤200 windows): ≤2% spurious rate
2. **Medium Datasets** (201–800 windows): ≤5% spurious rate  
3. **Large Datasets** (>800 windows): ≤8% spurious rate

### Continuous Scaling

For medium datasets, the framework implements continuous scaling to provide smooth transitions:

```
threshold = base + (dataset_size - small_max) × scaling_factor
```

Where:
- `base` = small dataset threshold (2%)
- `small_max` = 200 windows
- `scaling_factor` = 0.006 per window

This ensures that a 400-window dataset gets a threshold of approximately 3.2% rather than an abrupt jump to 5%.

### Statistical Justification

The adaptive thresholds are based on statistical power considerations:

- **Small datasets**: Require strict thresholds to avoid false positives
- **Medium datasets**: Can tolerate moderate threshold relaxation due to increased statistical power
- **Large datasets**: Have sufficient statistical power to detect true coordination even with relaxed thresholds

## Configuration

### Basic Configuration

```python
from acd.vmm.adaptive_thresholds import AdaptiveThresholdConfig, AdaptiveThresholdManager

# Use default configuration
config = AdaptiveThresholdConfig()
manager = AdaptiveThresholdManager(config)

# Custom configuration
custom_config = AdaptiveThresholdConfig(
    small_dataset_threshold=0.015,    # 1.5%
    medium_dataset_threshold=0.04,    # 4%
    large_dataset_threshold=0.06,     # 6%
    small_dataset_max=150,            # Custom boundary
    medium_dataset_max=600,           # Custom boundary
    enable_continuous_scaling=True,   # Enable smooth transitions
    scaling_factor=0.008,             # Custom scaling
    strict_mode=True                  # Fail fast on violations
)
```

### Predefined Profiles

The framework provides three predefined profiles:

```python
from acd.vmm.adaptive_thresholds import get_profile

# Conservative: Lower thresholds, stricter validation
conservative = get_profile("conservative")
# Small: ≤1.5%, Medium: ≤4%, Large: ≤6%

# Balanced: Default thresholds (recommended)
balanced = get_profile("balanced")  
# Small: ≤2%, Medium: ≤5%, Large: ≤8%

# Permissive: Higher thresholds, relaxed validation
permissive = get_profile("permissive")
# Small: ≤2.5%, Medium: ≤6%, Large: ≤10%
```

## Usage Examples

### Basic Threshold Selection

```python
manager = AdaptiveThresholdManager()

# Get threshold for different dataset sizes
small_threshold = manager.get_threshold(100)      # Returns 0.02
medium_threshold = manager.get_threshold(500)     # Returns ~0.038
large_threshold = manager.get_threshold(1000)     # Returns 0.08
```

### Spurious Rate Validation

```python
# Validate a dataset against adaptive thresholds
result = manager.validate_spurious_rate(
    dataset_size=500,
    spurious_rate=0.04
)

print(f"Dataset size: {result['dataset_size']}")
print(f"Category: {result['dataset_category']}")
print(f"Threshold applied: {result['threshold_applied']:.1%}")
print(f"Spurious rate: {result['spurious_rate']:.1%}")
print(f"Passes: {result['passes']}")
print(f"Margin: {result['margin']:.1%}")
```

### Integration with VMM Metrics

```python
from acd.vmm.metrics import calculate_spurious_rate_with_adaptive_thresholds

# Calculate spurious rate with adaptive thresholds
regime_confidences = [0.1, 0.2, 0.8, 0.3, 0.9, ...]  # VMM outputs
dataset_size = len(regime_confidences)

analysis = calculate_spurious_rate_with_adaptive_thresholds(
    regime_confidences=regime_confidences,
    dataset_size=dataset_size
)

print(f"Spurious rate: {analysis['spurious_rate_percentage']:.1f}%")
print(f"Threshold validation: {analysis['threshold_validation']['passes']}")
```

## Evidence Bundle Integration

The framework automatically integrates with evidence bundles:

```python
from acd.evidence.bundle import EvidenceBundle

# Create bundle with threshold profile
bundle = EvidenceBundle.create_demo_bundle(
    bundle_id="demo_bundle",
    market="demo_market",
    analyst="demo_pipeline",
    # ... other parameters ...
    adaptive_threshold_profile=threshold_manager.get_threshold_profile()
)

# Access threshold information
profile = bundle.adaptive_threshold_profile
print(f"Framework version: {profile['framework_version']}")
print(f"Small dataset threshold: {profile['small_dataset']['threshold']:.1%}")
```

## Demo Dashboard Integration

The demo dashboard automatically displays threshold information:

```json
{
  "adaptive_thresholds": {
    "framework_version": "1.0.0",
    "small_dataset": {
      "max_size": 200,
      "threshold": 0.02,
      "description": "≤200 windows: ≤2%"
    },
    "medium_dataset": {
      "min_size": 201,
      "max_size": 800,
      "threshold": 0.05,
      "description": "201-800 windows: ≤5%"
    },
    "large_dataset": {
      "min_size": 801,
      "threshold": 0.08,
      "description": ">800 windows: ≤8%"
    },
    "continuous_scaling": {
      "enabled": true,
      "scaling_factor": 0.006,
      "description": "Smooth threshold transitions for medium datasets"
    },
    "strict_mode": true
  }
}
```

## Validation and Testing

### Golden Dataset Validation

The framework maintains backward compatibility with existing golden datasets:

- **190-window datasets**: Still pass with ≤2% threshold (small category)
- **Large synthetic datasets**: Can be created and validated with ≤8% threshold

### Test Coverage

Comprehensive test coverage includes:

- Configuration validation
- Threshold selection logic
- Continuous scaling calculations
- Validation logic
- Integration scenarios
- Edge cases and error handling

## Configuration Files

Threshold profiles can be configured via YAML files:

```yaml
# config/thresholds.yaml
profiles:
  production:
    small_dataset_threshold: 0.02
    medium_dataset_threshold: 0.05
    large_dataset_threshold: 0.08
    small_dataset_max: 200
    medium_dataset_max: 800
    enable_continuous_scaling: true
    scaling_factor: 0.006
    strict_mode: true
  
  development:
    small_dataset_threshold: 0.025
    medium_dataset_threshold: 0.06
    large_dataset_threshold: 0.10
    strict_mode: false
```

## Migration Guide

### From Fixed Thresholds

1. **Update imports**: Add adaptive threshold imports
2. **Replace hardcoded thresholds**: Use `manager.get_threshold(dataset_size)`
3. **Update validation logic**: Use `manager.validate_spurious_rate()`
4. **Add threshold profiles**: Include in evidence bundles and dashboards

### Backward Compatibility

- Existing 5% threshold logic continues to work
- New adaptive thresholds are additive, not breaking
- Gradual migration supported

## Performance Considerations

- **Threshold calculation**: O(1) complexity
- **Validation**: O(1) complexity  
- **Memory usage**: Minimal (configuration objects are small)
- **Logging overhead**: Configurable via `log_threshold_applied`

## Future Enhancements

- **Dynamic thresholds**: Based on market conditions
- **Machine learning**: Adaptive threshold optimization
- **Multi-dimensional scaling**: Consider data quality, market volatility
- **Real-time adjustment**: Threshold updates during monitoring

## Troubleshooting

### Common Issues

1. **Threshold validation failures**: Check dataset size categorization
2. **Configuration errors**: Validate threshold ordering
3. **Import errors**: Ensure adaptive_thresholds module is available

### Debug Mode

Enable detailed logging:

```python
import logging
logging.getLogger("acd.vmm.adaptive_thresholds").setLevel(logging.DEBUG)
```

## References

- **Statistical Power Analysis**: Cohen, J. (1988). Statistical Power Analysis for the Behavioral Sciences
- **False Discovery Rate Control**: Benjamini, Y., & Hochberg, Y. (1995). Controlling the false discovery rate
- **Adaptive Thresholds**: Literature on dataset-size-dependent statistical thresholds
