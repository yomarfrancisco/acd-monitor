# Variational Method of Moments (VMM) - ACD Implementation

**Document Version:** 1.0  
**Date:** January 2025  
**Owner:** Theo (Senior Econometrician, RBB Economics)  
**Classification:** Technical Documentation  

---

## 1. Overview

The Variational Method of Moments (VMM) is the continuous monitoring engine of the ACD platform, implementing the dual-pillar approach described in Brief 55+. VMM provides real-time detection of structural deterioration in pricing relationships without requiring ex-ante specification of market environments.

## 2. Mathematical Foundation

### 2.1 Moment Conditions

VMM is based on three core moment conditions that distinguish competitive from coordinated behavior:

**First Moment Condition:**
```
𝔼[β_t] = β_0
```
Where β_t represents the pricing relationship parameters at time t, and β_0 is the competitive baseline.

**Second Moment Condition:**
```
Var[β_t] = Σ_0
```
Where Σ_0 represents the expected variance under competitive conditions.

**Temporal Cross-Moment Condition:**
```
Cov[β_t, β_{t-1}] = ρ_0
```
Where ρ_0 represents the expected temporal persistence under competitive conditions.

### 2.2 Variational Family

VMM uses a mean-field Gaussian approximation:
```
q(θ) = N(μ, Σ)
```

Where:
- μ is the mean vector of variational parameters
- Σ is the diagonal covariance matrix (mean-field assumption)
- Optional low-rank expansion for complex cases

### 2.3 Update Rule

The variational parameters are updated using stochastic variational inference on the ELBO with Robbins-Monro step size:

```
θ_{t+1} = θ_t + α_t ∇_θ ELBO
```

Where the step size follows:
```
α_t = α_0 / (1 + λt)
```

- α_0: Initial learning rate (default: 0.05)
- λ: Decay parameter (default: 0.001)
- t: Iteration number

## 3. Implementation Details

### 3.1 Core Components

**MomentConditions Class**
- Computes sample moments from pricing data
- Evaluates moment conditions against targets
- Handles beta estimation from price series

**VariationalUpdates Class**
- Manages variational parameter updates
- Implements convergence checking
- Provides step size scheduling

**MetricsCalibration Class**
- Calibrates raw outputs to interpretable scores
- Implements post-hoc validation
- Ensures score ranges [0,1]

**VMMEngine Class**
- Orchestrates the complete VMM pipeline
- Manages data validation and preprocessing
- Provides the public API interface

### 3.2 Data Processing Pipeline

1. **Input Validation**
   - Minimum data requirements (default: 2000 points)
   - Price column detection
   - Missing value handling

2. **Beta Extraction**
   - Price difference computation
   - Correlation-based relationship estimation
   - Temporal lagging for cross-moments

3. **Moment Computation**
   - Sample mean, variance, and covariance
   - Moment condition evaluation
   - Weight matrix computation

4. **Variational Optimization**
   - Parameter initialization
   - ELBO computation and gradient calculation
   - Convergence monitoring

5. **Metric Calibration**
   - Regime confidence scoring
   - Structural stability assessment
   - Environment quality evaluation
   - Dynamic validation

## 4. Convergence Criteria

### 4.1 Default Settings

- **Maximum Iterations:** 200 per window
- **Tolerance:** Relative ELBO change < 1e-5 over 5 successive iterations
- **Early Stop:** Plateau detection or divergence guard
- **Convergence Window:** 5 consecutive iterations

### 4.2 Convergence States

- **converged:** ELBO change below tolerance
- **plateau:** No significant improvement over convergence window
- **diverged:** NaN/Inf values detected
- **max_iterations:** Maximum iterations reached

### 4.3 ELBO Computation

The Evidence Lower BOund includes:
- Moment condition penalty terms
- Entropy of variational distribution
- Prior regularization terms

## 5. Output Metrics

### 5.1 Regime Confidence (∈ [0,1])

**Definition:** Probability that observed behavior is coordination-like vs competitive-like

**Calibration:**
- Base score from moment condition satisfaction
- Convergence quality adjustment (±0.1)
- Divergence penalty (-0.2)

**Interpretation:**
- < 0.33: Competitive behavior indicated
- 0.33 - 0.67: Ambiguous, monitoring recommended
- > 0.67: Coordination-like behavior detected

### 5.2 Structural Stability (∈ [0,1])

**Definition:** Measure of invariance in pricing relationships across environments

**Calibration:**
- Primary: Parameter variance (lower = higher stability)
- Secondary: Temporal moment stability
- Weighted combination: 0.7 × parameter + 0.3 × temporal

**Interpretation:**
- Higher values indicate more invariant (potentially coordinated) relationships
- Lower values suggest environment-sensitive (competitive) behavior

### 5.3 Environment Quality (∈ [0,1])

**Definition:** Proxy for data and context quality

**Calibration:**
- Data completeness (40%)
- Outlier consistency (40%)
- Temporal regularity (20%)

**Interpretation:**
- Higher values indicate better data quality
- Affects confidence in other metrics

### 5.4 Dynamic Validation Score (∈ [0,1])

**Definition:** Self-consistency and out-of-window predictive checks

**Calibration:**
- Self-consistency (40%): Convergence quality
- Parameter stability (30%): Optimization stability
- Prediction quality (30%): Out-of-sample performance

**Interpretation:**
- Higher values indicate more reliable results
- Lower values suggest potential issues

## 6. Configuration Options

### 6.1 Core Parameters

```python
VMMConfig(
    window='30D',              # Rolling window size
    step_initial=0.05,         # Initial learning rate
    step_decay=0.001,          # Learning rate decay
    max_iters=200,             # Maximum iterations
    tol=1e-5,                  # Convergence tolerance
    min_data_points=2000       # Minimum data requirement
)
```

### 6.2 Output Flags

```python
VMMConfig(
    emit_regime_confidence=True,      # Primary output
    emit_structural_stability=True,   # Stability metric
    emit_environment_quality=True,    # Quality assessment
    emit_dynamic_validation=True      # Validation score
)
```

### 6.3 Convergence Settings

```python
VMMConfig(
    convergence_window=5,      # Iterations for convergence check
    early_stop_plateau=True,   # Enable plateau detection
    divergence_guard=True      # Enable divergence detection
)
```

## 7. Failure Modes and Mitigations

### 7.1 Divergence

**Symptoms:**
- NaN or Inf values in outputs
- ELBO scores becoming extremely negative
- Parameter values growing unbounded

**Causes:**
- Poor conditioning in moment conditions
- Learning rate too high
- Insufficient data for stable estimation

**Mitigations:**
- Automatic divergence detection and early stopping
- Adaptive learning rate reduction
- Increased regularization in prior terms
- Minimum data point requirements

### 7.2 Poor Convergence

**Symptoms:**
- Maximum iterations reached without convergence
- Plateau detection triggered
- High iteration counts

**Causes:**
- Complex moment conditions
- Insufficient data
- Suboptimal step size schedule

**Mitigations:**
- Adaptive step size adjustment
- Multiple initialization strategies
- Early stopping on plateau
- Increased tolerance for edge cases

### 7.3 Low Data Quality

**Symptoms:**
- Low environment quality scores
- High variance in outputs
- Inconsistent moment conditions

**Causes:**
- Missing or corrupted data
- Insufficient temporal coverage
- Extreme outliers

**Mitigations:**
- Robust outlier detection
- Missing value imputation
- Data quality scoring and flagging
- Fallback to simpler models

## 8. Performance Characteristics

### 8.1 Computational Complexity

- **Time Complexity:** O(n × m × i) where n = data points, m = firms, i = iterations
- **Memory Usage:** O(n × m) for data storage + O(m²) for parameters
- **Typical Runtime:** 1-5 seconds per window (100-1000 data points)

### 8.2 Scaling Behavior

- **Data Points:** Linear scaling up to ~10,000 points
- **Number of Firms:** Quadratic scaling due to moment conditions
- **Window Size:** Optimal range 100-1000 observations

### 8.3 Optimization Opportunities

- **Vectorization:** NumPy operations for moment computation
- **Parallelization:** Independent window processing
- **Caching:** Reuse of computed moments across iterations

## 9. Integration Points

### 9.1 Risk Engine Integration

VMM provides the REG component in composite risk scoring:
```python
# Default regime source is VMM
regime_score = vmm_output.regime_confidence

# Can be overridden via acceptance profile
if profile.regime_source == "hmm":
    regime_score = hmm_output.regime_confidence
```

### 9.2 API Integration

VMM outputs are included in risk assessment payloads:
```json
{
  "methodology": {
    "regime_source": "vmm",
    "vmm_metrics": {
      "regime_confidence": 0.45,
      "structural_stability": 0.32,
      "environment_quality": 0.89,
      "dynamic_validation_score": 0.76
    }
  }
}
```

### 9.3 Acceptance Gates

VMM is subject to CI-enforced acceptance gates:
- **Spurious Regime Rate:** ≤ 5% on competitive golden set
- **Reproducibility Drift:** |Δstructural_stability| ≤ 0.03 across 10 runs

## 10. Future Enhancements

### 10.1 Advanced Variational Families

- **Low-Rank Covariance:** Better capture of parameter correlations
- **Mixture Models:** Multiple regime detection
- **Non-Gaussian Approximations:** Heavy-tailed distributions

### 10.2 Adaptive Methods

- **Automatic Step Size Tuning:** Based on gradient statistics
- **Dynamic Convergence Criteria:** Adaptive tolerance adjustment
- **Online Learning:** Incremental parameter updates

### 10.3 Robustness Improvements

- **Robust Moment Conditions:** Less sensitive to outliers
- **Multiple Initialization Strategies:** Better global optimization
- **Uncertainty Quantification:** Confidence intervals for outputs

---

## References

1. RBB Brief 55+: Beyond the AI Conspiracy: A Diagnostic for Coordination
2. Product Specification v1.8: ACD Platform Technical Details
3. Mission Control: Development Roadmap and Priorities
4. Peters, J., Bühlmann, P. & Meinshausen, N. (2016): Invariant Causal Prediction
5. Robbins, H. & Monro, S. (1951): Stochastic Approximation Method
