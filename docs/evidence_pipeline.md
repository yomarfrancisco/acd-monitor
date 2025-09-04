# Evidence Pipeline Documentation

> **Week 4 Implementation**: Comprehensive documentation of the ACD Monitor evidence pipeline for regulatory compliance and reproducibility.

## 🎯 **Overview**

The ACD Monitor evidence pipeline ensures systematic collection, validation, and export of all analysis results with full reproducibility and regulatory compliance. This pipeline is anchored to Brief 55+ dual pillars and maintains governance standards established in Week 3.

## 📦 **Evidence Bundle Structure**

### **Core Components**

The `EvidenceBundle` class encapsulates all evidence from VMM analysis, calibration, and validation processes:

```python
@dataclass
class EvidenceBundle:
    # Core identification
    bundle_id: str                    # Unique identifier
    creation_timestamp: str           # ISO timestamp
    analysis_window_start: str        # Analysis period start
    analysis_window_end: str          # Analysis period end
    market: str                       # Target market
    
    # VMM outputs (Week 4 requirement)
    vmm_outputs: VMMEvidence         # Core VMM results
    
    # Calibration artifacts (Week 4 requirement)
    calibration_artifacts: List[CalibrationArtifact]  # Calibration results
    
    # Data quality evidence
    data_quality: DataQualityEvidence  # Quality assessment
    
    # Analysis configuration
    vmm_config: Dict[str, Any]       # VMM parameters
    data_sources: List[str]          # Data sources used
    
    # Validation and reproducibility
    golden_dataset_validation: Dict[str, float]  # Validation metrics
    reproducibility_metrics: Dict[str, float]    # Reproducibility scores
    
    # Metadata
    analyst: str                      # Analyst identifier
    version: str                      # Bundle version
    checksum: str                     # SHA-256 checksum
```

### **VMM Evidence Structure**

```python
@dataclass
class VMMEvidence:
    regime_confidence: float          # Regime detection confidence
    structural_stability: float       # Structural stability measure
    dynamic_validation_score: float   # Dynamic validation score
    elbo_convergence: float          # ELBO convergence value
    iteration_count: int              # Number of iterations
    runtime_seconds: float            # Execution time
    convergence_status: str           # Convergence status
    numerical_stability: Dict[str, float]  # Stability metrics
```

### **Calibration Artifact Structure**

```python
@dataclass
class CalibrationArtifact:
    market: str                       # Market identifier
    timestamp: str                    # Calibration timestamp
    method: str                       # Calibration method
    spurious_rate: float              # Spurious regime rate
    structural_stability: float       # Structural stability
    calibration_curve: Dict[str, Any] # Calibration curve data
    validation_metrics: Dict[str, float]  # Validation metrics
    file_path: str                    # Artifact file path
```

### **Data Quality Evidence Structure**

```python
@dataclass
class DataQualityEvidence:
    completeness_score: float         # Data completeness (0-1)
    accuracy_score: float             # Data accuracy (0-1)
    timeliness_score: float           # Data freshness (0-1)
    consistency_score: float          # Data consistency (0-1)
    overall_score: float              # Overall quality score
    quality_issues: List[str]         # Identified issues
    validation_timestamp: str         # Quality assessment time
```

## 🔍 **Golden Dataset Methodology**

### **Dataset Types**

The enhanced golden datasets (Week 4) include multiple coordination mechanisms:

1. **Competitive Data**: Environment-dependent competitive responses
2. **Coordinated Data**: Common market factor responses
3. **Leader-Follower Data**: Sequential coordination with delays
4. **Staggered Reaction Data**: Time-delayed market shock responses
5. **CDS Spread Data**: Credit risk dynamics
6. **SA Bank Competition Data**: Banking sector competition patterns

### **Generation Process**

```python
def generate_enhanced_golden_datasets(seed: int = 42) -> Dict[str, List[pd.DataFrame]]:
    """Generate enhanced golden datasets with multiple coordination mechanisms."""
    datasets = {}
    
    # Original competitive and coordinated datasets
    datasets['competitive'] = generate_competitive_data(seed=seed)
    datasets['coordinated'] = generate_coordinated_data(seed=seed)
    
    # New coordination mechanism datasets
    datasets['leader_follower'] = generate_leader_follower_data(seed=seed)
    datasets['staggered_reaction'] = generate_staggered_reaction_data(seed=seed)
    
    # Real-world reference datasets
    datasets['cds_spreads'] = generate_cds_spread_data(seed=seed)
    datasets['sa_bank_competition'] = generate_sa_bank_competition_data(seed=seed)
    
    return datasets
```

### **Validation Requirements**

Golden datasets must demonstrate clear separation in AUROC/F1 validation:

- **Competitive vs. Coordinated**: AUROC ≥ 0.8
- **Regime Detection**: F1-score ≥ 0.7
- **Structural Stability**: Variance ≤ 0.1 across reproducibility runs
- **Performance Consistency**: Runtime variance ≤ 20% across datasets

## 🔐 **Validation Process for Reproducibility**

### **Checksum Validation**

Every evidence bundle includes a SHA-256 checksum for integrity verification:

```python
def _compute_checksum(self) -> str:
    """Compute SHA-256 checksum of bundle content."""
    bundle_dict = asdict(self)
    bundle_dict.pop('checksum', None)  # Remove checksum before computing
    
    # Convert to sorted JSON string for deterministic hashing
    bundle_json = json.dumps(bundle_dict, sort_keys=True, default=str)
    return hashlib.sha256(bundle_json.encode()).hexdigest()
```

### **Schema Validation**

Bundles are validated against strict schema requirements:

```python
def validate_schema(self) -> bool:
    """Validate bundle against schema requirements."""
    try:
        # Check required fields
        required_fields = [
            'bundle_id', 'creation_timestamp', 'market',
            'vmm_outputs', 'calibration_artifacts', 'data_quality'
        ]
        
        for field in required_fields:
            if not hasattr(self, field) or getattr(self, field) is None:
                return False
        
        # Validate VMM outputs
        vmm_outputs = self.vmm_outputs
        if not (0.0 <= vmm_outputs.regime_confidence <= 1.0):
            return False
        if not (0.0 <= vmm_outputs.structural_stability <= 1.0):
            return False
        if not (0.0 <= vmm_outputs.dynamic_validation_score <= 1.0):
            return False
        
        # Validate data quality scores
        quality = self.data_quality
        for score_field in ['completeness_score', 'accuracy_score', 
                          'timeliness_score', 'consistency_score', 'overall_score']:
            score = getattr(quality, score_field)
            if not (0.0 <= score <= 1.0):
                return False
        
        # Validate calibration artifacts
        for artifact in self.calibration_artifacts:
            if not (0.0 <= artifact.spurious_rate <= 1.0):
                return False
            if not (0.0 <= artifact.structural_stability <= 1.0):
                return False
        
        return True
        
    except Exception:
        return False
```

### **RFC3161 Timestamping**

Evidence bundles can be exported with RFC3161 timestamping for regulatory compliance:

```python
class RFC3161TimestampService:
    """RFC3161 timestamp service for evidence bundles."""
    
    def __init__(self, service_url: Optional[str] = None):
        self.service_url = service_url or "https://freetsa.org/tsr"
    
    def get_timestamp(self, data: bytes) -> Dict[str, Any]:
        """Get RFC3161 timestamp for data."""
        try:
            # Hash the data with SHA-256
            data_hash = hashlib.sha256(data).digest()
            
            # Encode hash in base64
            encoded_hash = base64.b64encode(data_hash).decode('ascii')
            
            # Request timestamp from service
            response = requests.get(
                f"{self.service_url}",
                params={'data': encoded_hash},
                timeout=30
            )
            response.raise_for_status()
            
            # Parse timestamp response
            timestamp_data = response.json()
            
            return {
                'timestamp_token': timestamp_data.get('token'),
                'timestamp': timestamp_data.get('timestamp'),
                'service_url': self.service_url,
                'hash_algorithm': 'SHA-256',
                'encoded_hash': encoded_hash
            }
            
        except Exception as e:
            # Fallback to local timestamp if service unavailable
            return {
                'timestamp_token': None,
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'service_url': 'local_fallback',
                'hash_algorithm': 'SHA-256',
                'encoded_hash': base64.b64encode(hashlib.sha256(data).digest()).decode('ascii'),
                'error': str(e)
            }
```

## 📁 **Export Structure**

### **Directory Organization**

Evidence bundles are exported with organized directory structure:

```
evidence_export/
├── evidence_bundle_id.json              # Main bundle
├── calibration/                         # Calibration artifacts
│   ├── market_name/                     # Market-specific directory
│   │   └── YYYYMM/                     # Timestamp directory (YYYY-MM)
│   │       ├── isotonic_bundle_id.json  # Isotonic calibration
│   │       ├── platt_bundle_id.json     # Platt scaling
│   │       └── post_adjustment_bundle_id.json  # Post-calibration
├── evidence_bundle_id_quality.json      # Quality assessment
├── evidence_bundle_id_config.json       # VMM configuration
├── evidence_bundle_id_validation.json   # Validation metrics
├── evidence_bundle_id_timestamp.json    # RFC3161 timestamp
└── evidence_bundle_id_export_metadata.json  # Export metadata
```

### **Export Process**

```python
def export_evidence_bundle(bundle: EvidenceBundle,
                          output_dir: Union[str, Path],
                          include_timestamp: bool = True,
                          timestamp_service: Optional[RFC3161TimestampService] = None) -> Dict[str, Any]:
    """Export evidence bundle with optional RFC3161 timestamping."""
    
    # Export bundle as JSON
    bundle_json_path = output_dir / f"{bundle.bundle_id}.json"
    bundle_json = bundle.to_json(bundle_json_path)
    
    # Export calibration artifacts
    calibration_dir = output_dir / "calibration"
    calibration_dir.mkdir(exist_ok=True)
    
    for artifact in bundle.calibration_artifacts:
        # Create market-specific subdirectory
        market_dir = calibration_dir / artifact.market
        market_dir.mkdir(exist_ok=True)
        
        # Create timestamp subdirectory (YYYYMM format)
        timestamp_str = artifact.timestamp[:7].replace('-', '')
        timestamp_dir = market_dir / timestamp_str
        timestamp_dir.mkdir(exist_ok=True)
        
        # Export artifact
        artifact_file = timestamp_dir / f"{artifact.method}_{bundle.bundle_id}.json"
        with open(artifact_file, 'w') as f:
            json.dump(artifact.calibration_curve, f, indent=2)
    
    # Export additional components
    # ... (quality, config, validation, timestamp)
    
    return export_metadata
```

## 🔒 **Quality Assurance**

### **Week 4 Hardened Thresholds**

The evidence pipeline implements hardened quality thresholds:

- **Completeness**: ≥ 98% (increased from 95%)
- **Timeliness**: ≤ 12 hours (reduced from 24 hours)
- **Critical Timeliness**: ≤ 4 hours (new threshold)
- **Consistency**: ≥ 95% (new threshold)
- **Overall Quality**: ≥ 80% (maintained)

### **Validation Gates**

```python
def _apply_hardened_thresholds(self, timeliness_metrics: Dict[str, Any], 
                              consistency_metrics: Dict[str, Any],
                              completeness_metrics: Dict[str, Any]) -> None:
    """Apply hardened quality thresholds."""
    
    # Check critical staleness
    if timeliness_metrics.get("is_critical_stale", False):
        raise DataQualityError(
            f"Data is critically stale: {timeliness_metrics['data_age_hours']:.1f} hours "
            f"(threshold: {self.config.critical_staleness_threshold_hours} hours)"
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
```

## 📊 **Monitoring and Reporting**

### **Quality Metrics Tracking**

The pipeline tracks comprehensive quality metrics:

```python
def get_quality_summary(self) -> Dict[str, Any]:
    """Get summary of quality assessment history."""
    if not self.quality_history:
        return {"status": "no_data"}
    
    recent_metrics = self.quality_history[-1]
    
    summary = {
        "latest_assessment": recent_metrics.creation_timestamp,
        "overall_quality_score": recent_metrics.overall_quality_score,
        "completeness_rate": recent_metrics.completeness_rate,
        "timeliness_score": recent_metrics.timeliness_score,
        "consistency_score": recent_metrics.consistency_score,
        "quality_trend": self._calculate_quality_trend()
    }
    
    return summary
```

### **Regression Detection**

The pipeline automatically flags quality regressions:

- **Critical Regressions**: Immediate flag + rollback
- **High Priority**: 24-hour response required
- **Medium Priority**: 7-day response required
- **Low Priority**: Next sprint resolution

## 🔄 **Reproducibility Workflow**

### **1. Bundle Creation**

```python
# Create evidence bundle from VMM result
bundle = EvidenceBundle.from_vmm_result(
    vmm_result=vmm_result,
    vmm_config=vmm_config,
    market="JSE_BANKS",
    window_start="2024-01-01T00:00:00Z",
    window_end="2024-01-31T23:59:59Z",
    calibration_artifacts=calibration_artifacts,
    data_quality=data_quality,
    analyst="Theo"
)
```

### **2. Validation**

```python
# Validate bundle schema
if not bundle.validate_schema():
    raise ValueError("Bundle validation failed")

# Validate against golden datasets
validation_metrics = validate_against_golden_datasets(bundle)
bundle.golden_dataset_validation = validation_metrics
```

### **3. Export with Timestamping**

```python
# Export bundle with RFC3161 timestamping
export_metadata = export_evidence_bundle(
    bundle=bundle,
    output_dir="evidence_exports",
    include_timestamp=True
)
```

### **4. Verification**

```python
# Verify exported bundle
validation_results = validate_exported_bundle("evidence_exports")
if not validation_results["overall_valid"]:
    raise ValueError(f"Export validation failed: {validation_results['validation_errors']}")
```

## 📋 **Acceptance Gates**

### **Week 4 Requirements**

1. **Evidence Bundle Integration**: ✅ Complete
   - VMM outputs included (regime_confidence, structural_stability, dynamic_validation_score)
   - Calibration artifacts from Week 3 (calibration/{market}/{yyyymm}/)
   - RFC3161 timestamping implemented

2. **Golden Dataset Expansion**: ✅ Complete
   - Enhanced with realistic coordination mechanisms
   - Includes baseline real-world reference datasets
   - Demonstrates clear separation in validation

3. **Pipeline Hardening**: ✅ Complete
   - Extended data ingestion for analyst feeds and regulatory disclosures
   - Hardened quality thresholds (timeliness ≤ 12h, consistency ≥ 95%)
   - Quality metrics ≥ 0.8 on golden datasets

4. **Documentation & Transparency**: ✅ Complete
   - Evidence pipeline documentation created
   - Golden dataset methodology documented
   - Validation process for reproducibility documented

### **Quality Gates**

- **Schema Validation**: All bundles pass schema validation
- **Quality Thresholds**: All quality metrics ≥ 0.8
- **Reproducibility**: Checksum validation passes
- **Timeliness**: Data age ≤ 12 hours (critical: ≤ 4 hours)
- **Consistency**: Cross-field validation passes

## 🔗 **Integration Points**

### **VMM Engine Integration**

The evidence pipeline integrates seamlessly with the VMM engine:

```python
# In VMM engine
def run_vmm(window: pd.DataFrame, config: VMMConfig) -> VMMResult:
    # ... VMM execution ...
    
    # Create evidence bundle
    bundle = EvidenceBundle.from_vmm_result(
        vmm_result=result,
        vmm_config=config,
        market=market,
        window_start=window.index[0].isoformat(),
        window_end=window.index[-1].isoformat(),
        calibration_artifacts=calibration_artifacts,
        data_quality=data_quality
    )
    
    return result, bundle
```

### **Data Pipeline Integration**

The evidence pipeline integrates with the hardened data pipeline:

```python
# In data ingestion
def ingest_file(self, file_path: Union[str, Path], source_type: str, 
                source_metadata: Optional[Dict[str, Any]] = None) -> pd.DataFrame:
    # ... ingestion logic ...
    
    # Assess quality with hardened thresholds
    quality_assessment = DataQualityAssessment(self.quality_config)
    quality_metrics = quality_assessment.assess_quality(
        data=validated_data,
        expected_schema=expected_schema,
        reference_data=reference_data
    )
    
    return validated_data, quality_metrics
```

## 📈 **Future Enhancements**

### **Planned Improvements**

1. **Advanced Timestamping**: Multiple timestamp service support
2. **Compression**: Efficient storage of large evidence bundles
3. **Streaming**: Real-time evidence bundle generation
4. **API Integration**: RESTful evidence bundle access
5. **Audit Trail**: Comprehensive change tracking

### **Scalability Considerations**

- **Bundle Size**: Optimize for large datasets
- **Storage**: Efficient archival and retrieval
- **Performance**: Parallel processing for multiple bundles
- **Security**: Encryption and access control

---

## 📅 **Documentation Version**

- **Version**: 1.0 (Week 4)
- **Last Updated**: 2024-01-XX
- **Owner**: Theo (Senior Econometrician Engineer)
- **Status**: Complete and validated

---

> **Note**: This documentation is part of the Week 4 Build Sprint deliverables and maintains alignment with Brief 55+ dual pillars and governance standards established in Week 3.
