# Economic Harm Analysis Methodology

## Overview

This document outlines the redesigned economic harm analysis framework that addresses the methodological concerns raised by reviewers. The new approach focuses on venue excess fee revenue and consumer cost uplift as proper measures of coordination harm.

## Key Methodological Improvements

### 1. Venue Excess Fee Revenue (Coordination Profits Proxy)

**Rationale**: Real coordination profits come from supra-competitive fees, not arbitrage opportunities.

**Methodology**:
- **Fee Schedule Collection**: Scrape and normalize fee schedules for all venues
- **Revenue Calculation**: `fee_revenue_vw = taker_fee_bps * notional_traded_vw`
- **Baseline Model**: Build competitive baseline using non-episode, low-stress windows
- **Excess Revenue**: `Δ_fee_revenue = actual_revenue - baseline_prediction`

**Controls**:
- Realized volatility (30s, 5s windows)
- Price momentum (1s, 5s, 30s returns)
- Time-of-day effects (hour, minute, session)
- Market stress indicators

**Outputs**:
- Per-venue excess revenue during episodes
- Bootstrap confidence intervals
- Retail vs. best-tier comparisons

### 2. Consumer Cost Uplift (Welfare Loss Proxy)

**Rationale**: Consumer harm is welfare loss vs. competitive benchmark, not just spread widening.

**Methodology**:
- **Execution Cost**: `eff_cost_bps = half_spread + slippage + taker_fee`
- **Baseline Model**: Build competitive baseline with microstructure controls
- **Cost Uplift**: `residual_uplift = actual_cost - baseline_prediction`
- **Welfare Loss**: `uplift * notional_traded`

**Controls**:
- Realized volatility (30s, 5s windows)
- Market depth and imbalance
- Time-of-day effects
- Volatility regime indicators

**Outputs**:
- Per-episode consumer cost uplift
- Total welfare loss estimates
- Bootstrap confidence intervals

## Data Requirements

### 1. Fee Schedules
- **Source**: Venue APIs and public fee schedules
- **Format**: Normalized JSON with maker/taker rates by tier
- **Storage**: S3 bucket `acd-monitor-snapshots/fee_schedules/`
- **Update Frequency**: Daily or weekly

### 2. Microstructure Controls
- **Per-Second Aggregates**: Spread, depth, volatility, imbalance
- **Cross-Venue Metrics**: Inter-venue spreads and correlations
- **Temporal Features**: Time-of-day, session, day-of-week
- **Storage**: `micro_controls.json` per window

### 3. Episode Data
- **Source**: Spread v2 detector results
- **Format**: Standardized episode JSON with timestamps
- **Validation**: Ensure episode periods are properly defined

## Implementation Framework

### 1. Fee Schedule Collection
```bash
python scripts/econ/fetch_fee_schedules.py \
  --bucket acd-monitor-snapshots \
  --key fee_schedules/normalized_fees.json
```

**Outputs**:
- Normalized fee schedules for all venues
- Tier-based fee structures (retail to institutional)
- Last updated timestamps

### 2. Microstructure Controls Export
```bash
python scripts/econ/export_micro_controls.py \
  --snapshot snapshots/btc_window1/OVERLAP.json \
  --output experiments/phase5/btc_window1/micro_controls.json
```

**Outputs**:
- Per-second microstructure controls
- Cross-venue spread metrics
- Temporal and volatility features

### 3. Venue Excess Revenue Analysis
```bash
python scripts/econ/venue_excess_revenue.py \
  --snapshot snapshots/btc_window1/OVERLAP.json \
  --episodes experiments/phase5/btc_window1/spread_v2/control_v2_results.json \
  --micro-controls experiments/phase5/btc_window1/micro_controls.json \
  --output experiments/phase5/btc_window1/venue_excess_revenue.json
```

**Outputs**:
- Per-episode venue excess revenue
- Baseline model performance metrics
- Bootstrap confidence intervals

### 4. Consumer Cost Uplift Analysis
```bash
python scripts/econ/consumer_cost_uplift.py \
  --snapshot snapshots/btc_window1/OVERLAP.json \
  --episodes experiments/phase5/btc_window1/spread_v2/control_v2_results.json \
  --micro-controls experiments/phase5/btc_window1/micro_controls.json \
  --output experiments/phase5/btc_window1/consumer_cost_uplift.json
```

**Outputs**:
- Per-episode consumer cost uplift
- Welfare loss estimates
- Baseline model performance metrics

## Statistical Methodology

### 1. Baseline Model Construction
- **Features**: Volatility, momentum, time-of-day, market stress
- **Model**: Linear regression with standardized features
- **Validation**: R², residual analysis, cross-validation
- **Robustness**: Bootstrap confidence intervals

### 2. Episode Analysis
- **Matching**: Episodes matched to baseline predictions
- **Controls**: All relevant microstructure variables
- **Placebo Tests**: Shuffled timestamps to ensure robustness
- **Significance**: Bootstrap p-values and confidence intervals

### 3. Aggregation
- **Per-Episode**: Individual episode excess revenue/cost uplift
- **Cross-Episode**: Aggregate statistics across all episodes
- **Confidence Intervals**: Bootstrap-based uncertainty quantification

## Validation Framework

### 1. Data Quality Checks
- **Fee Schedule Validation**: Ensure all venues have complete fee data
- **Microstructure Controls**: Validate control variable ranges
- **Episode Validation**: Ensure episode periods are properly defined

### 2. Model Validation
- **Baseline Performance**: R² and residual analysis
- **Placebo Tests**: Shuffled timestamps should show no effect
- **Sensitivity Analysis**: Robustness to different control specifications

### 3. Economic Validation
- **Sign Magnitude**: Excess revenue/cost uplift should be economically meaningful
- **Cross-Venue Consistency**: Similar patterns across venues
- **Temporal Patterns**: Episodes should show consistent timing

## Output Schema

### 1. Venue Excess Revenue
```json
{
  "baseline_model": {
    "model_type": "linear_regression",
    "r_squared": 0.85,
    "features": ["rv_30s", "momentum_1s", "hour", "session"]
  },
  "episode_results": [
    {
      "episode_index": 0,
      "start_time": "2025-09-28T10:02:58Z",
      "end_time": "2025-09-28T10:02:59Z",
      "venue_revenues": {
        "binance": 15.2,
        "coinbase": 18.7,
        "kraken": 12.3
      },
      "excess_revenue_bps": 8.5,
      "excess_revenue_pct": 12.3
    }
  ],
  "summary": {
    "n_episodes": 48,
    "total_excess_revenue_bps": 245.6,
    "mean_excess_revenue_bps": 5.1
  }
}
```

### 2. Consumer Cost Uplift
```json
{
  "baseline_model": {
    "model_type": "linear_regression",
    "r_squared": 0.78,
    "features": ["rv_30s", "momentum_1s", "hour", "session"]
  },
  "episode_results": [
    {
      "episode_index": 0,
      "start_time": "2025-09-28T10:02:58Z",
      "end_time": "2025-09-28T10:02:59Z",
      "actual_cost_bps": 25.3,
      "baseline_cost_bps": 18.7,
      "cost_uplift_bps": 6.6,
      "welfare_loss_usd": 12.4
    }
  ],
  "summary": {
    "n_episodes": 48,
    "total_cost_uplift_bps": 156.8,
    "mean_cost_uplift_bps": 3.3,
    "total_welfare_loss_usd": 298.7
  }
}
```

## Limitations and Caveats

### 1. Data Limitations
- **Fee Schedules**: May not capture all fee structures (volume discounts, etc.)
- **Microstructure Controls**: Simplified spread estimation
- **Trade Data**: Limited access to actual trade volumes

### 2. Methodological Limitations
- **Baseline Model**: Linear regression may not capture all non-linearities
- **Control Variables**: May not capture all relevant market microstructure
- **Episode Definition**: Depends on spread v2 detector performance

### 3. Economic Interpretation
- **Coordination vs. Competition**: Results may reflect competitive behavior
- **Market Efficiency**: Wider spreads may be due to information asymmetry
- **Regulatory Context**: Results should be interpreted in regulatory framework

## Future Enhancements

### 1. Data Improvements
- **Real Trade Data**: Access to actual trade volumes and fees
- **Order Book Data**: More accurate spread and depth measures
- **Fee Schedule Updates**: Real-time fee schedule monitoring

### 2. Methodological Improvements
- **Non-Linear Models**: Machine learning approaches for baseline models
- **Dynamic Controls**: Time-varying control specifications
- **Cross-Asset Analysis**: Extend to multiple trading pairs

### 3. Validation Enhancements
- **Placebo Tests**: More sophisticated placebo testing
- **Sensitivity Analysis**: Robustness to different specifications
- **Cross-Validation**: Out-of-sample validation

## Conclusion

The redesigned economic harm analysis framework addresses the methodological concerns raised by reviewers by:

1. **Focusing on Proper Harm Measures**: Venue excess revenue and consumer cost uplift
2. **Implementing Robust Controls**: Volatility, depth, time-of-day, and market stress
3. **Using Placebo Tests**: Ensuring results aren't capturing normal market stress
4. **Providing Clear Documentation**: Transparent methodology and limitations

This framework provides a solid foundation for regulatory-grade economic harm analysis while maintaining scientific rigor and transparency.
