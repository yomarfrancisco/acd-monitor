# ACD Spread v2 Calibration Roadmap

**Date**: 2025-09-29  
**Scope**: BTC-USD and ETH-USD Spread v2 detector calibration  
**Status**: Phase 0 (Provisional)  

## Overview

This document outlines the phased approach for calibrating the Spread v2 detector across different market environments and data availability scenarios.

## Phase 0: 2-Hour Provisional Calibration (Current)

### **Status**: ✅ COMPLETED
- **Duration**: 2 hours (12:00-14:00 UTC)
- **Data**: 4 high-quality BTC windows
- **Environments**: 6 environment types (volatility, liquidity, time-of-day, VWAP, high/low, trading session)
- **Results**: Baseline statistics and synthetic calibration framework

### **Deliverables**
- ✅ Environment partition strategy (`docs/calibration/ENV_PARTITION_NOTES.md`)
- ✅ Baseline spread estimation (`calibration/spread/baseline_env_stats.json`)
- ✅ Synthetic calibration framework (`calibration/spread/synthetic_runs/`)
- ✅ Real data calibration attempt (`calibration/spread/real_runs/`)
- ✅ Provenance tracking and S3 storage

### **Limitations**
- **Sample Size**: 4 windows is minimal for robust analysis
- **Time Span**: 2-hour window limits temporal pattern detection
- **Detector Issues**: Spread v2 detector requires fixes for real data
- **Missing Data**: Only 2 of 4 expected snapshots available

### **Next Steps**
1. **Fix Detector**: Resolve Spread v2 detector issues with real data
2. **Extend Capture**: Collect more high-quality windows
3. **Environment Analysis**: Implement extended environment partitions
4. **Threshold Calibration**: Adjust thresholds based on real data

## Phase 1: ≥7 Days Continuous Capture

### **Status**: 🔄 PLANNED
- **Duration**: 7+ days continuous monitoring
- **Data**: 30-minute windows with 50% overlap (new window every 15 minutes)
- **Target**: ≥672 windows (7 days × 96 windows/day)
- **Quality Gate**: ≥95% coverage per window

### **Objectives**
1. **Extended Baseline**: Robust environment-specific baseline statistics
2. **Temporal Patterns**: Intraday and interday spread behavior
3. **Environment Validation**: Test all 6 environment types with sufficient data
4. **Threshold Calibration**: Calibrate thresholds on real market data

### **Environment Partitions**
| Environment | Bins | Data Requirements | Validation |
|-------------|------|------------------|------------|
| **Volatility** | 3 (low/mid/high) | ≥672 windows | ✅ Sufficient |
| **Liquidity** | 3 (low/mid/high) | Volume data | ✅ Sufficient |
| **Time-of-Day** | 4 (Asia/Europe/US/Overlap) | 24-hour coverage | ✅ Sufficient |
| **VWAP** | 2 (below/above) | Daily VWAP calculation | ✅ Sufficient |
| **High/Low** | 3 (near high/mid/near low) | Daily high/low data | ✅ Sufficient |
| **Trading Session** | 4 (Asia/Europe/US/Overlap) | Session timing | ✅ Sufficient |

### **Deliverables**
- **Extended Baseline**: 7-day baseline statistics per environment
- **Calibrated Thresholds**: Production-ready thresholds
- **Environment Analysis**: Comprehensive environment-specific analysis
- **Validation Report**: Phase 1 validation results

### **Success Criteria**
- **Data Quality**: ≥95% coverage for ≥90% of windows
- **Environment Coverage**: All 6 environment types with ≥50 windows each
- **Threshold Calibration**: ROC curves with AUC ≥0.8
- **Reproducibility**: All results reproducible with fixed seeds

## Phase 2: ≥30 Days Full ICP Validation

### **Status**: 🔮 FUTURE
- **Duration**: 30+ days continuous monitoring
- **Data**: ≥2,880 windows (30 days × 96 windows/day)
- **Quality Gate**: ≥95% coverage per window
- **Cross-Asset**: BTC-USD and ETH-USD

### **Objectives**
1. **Full Validation**: Complete ICP validation across all environments
2. **Cross-Asset Calibration**: BTC-USD and ETH-USD comparison
3. **Regime Testing**: Different market regimes and conditions
4. **Production Deployment**: Production-ready calibration

### **Environment Extensions**
| Environment | Phase 2 Extensions | Data Requirements |
|-------------|-------------------|-------------------|
| **Volatility** | 5 bins (very low/low/mid/high/very high) | 30-day volatility data |
| **Liquidity** | 5 bins (very low/low/mid/high/very high) | 30-day volume data |
| **Time-of-Day** | 8 bins (3-hour intervals) | 24-hour coverage |
| **VWAP** | 3 bins (below/mid/above) | Intraday VWAP references |
| **High/Low** | 5 bins (very near high/near high/mid/near low/very near low) | Weekly/monthly references |
| **Trading Session** | 8 bins (3-hour intervals) | Session timing |
| **Regime** | 3 bins (normal/stress/event) | Market regime classification |

### **Deliverables**
- **Production Calibration**: Final production-ready thresholds
- **Cross-Asset Analysis**: BTC-USD vs ETH-USD comparison
- **Regime Analysis**: Different market regime behavior
- **Deployment Package**: Production deployment artifacts

### **Success Criteria**
- **Data Quality**: ≥95% coverage for ≥95% of windows
- **Environment Coverage**: All environment types with ≥100 windows each
- **Cross-Asset Validation**: Consistent behavior across BTC-USD and ETH-USD
- **Production Readiness**: All artifacts ready for production deployment

## Data Limitations and Guardrails

### **Current Limitations (Phase 0)**
- **Sample Size**: 4 windows insufficient for robust statistical analysis
- **Time Span**: 2-hour window limits temporal pattern detection
- **Detector Issues**: Spread v2 detector requires fixes for real data
- **Missing Data**: Only 2 of 4 expected snapshots available

### **Phase 1 Guardrails**
- **Data Quality**: Reject windows with <95% coverage
- **Environment Balance**: Ensure balanced representation across environments
- **Temporal Coverage**: Ensure 24-hour coverage across all days
- **Venue Coverage**: Ensure all 5 venues (binance, coinbase, kraken, okx, bybit)

### **Phase 2 Guardrails**
- **Extended Validation**: 30-day minimum for robust statistical analysis
- **Cross-Asset Validation**: Both BTC-USD and ETH-USD required
- **Regime Testing**: Test across different market regimes
- **Production Readiness**: All artifacts must be production-ready

## Implementation Timeline

### **Phase 0 (Completed)**
- ✅ Environment partition strategy
- ✅ Baseline spread estimation
- ✅ Synthetic calibration framework
- ✅ Real data calibration attempt
- ✅ Provenance tracking and S3 storage

### **Phase 1 (Next 2-3 weeks)**
- 🔄 Fix Spread v2 detector issues
- 🔄 Extend capture to 7+ days
- 🔄 Implement extended environment partitions
- 🔄 Calibrate thresholds on real data
- 🔄 Generate Phase 1 validation report

### **Phase 2 (Next 2-3 months)**
- 🔮 Extend capture to 30+ days
- 🔮 Cross-asset validation (BTC-USD and ETH-USD)
- 🔮 Regime testing and analysis
- 🔮 Production deployment preparation

## Success Metrics

### **Phase 0 Metrics**
- ✅ Environment partition strategy documented
- ✅ Baseline statistics computed
- ✅ Synthetic calibration framework created
- ✅ Real data calibration attempted
- ✅ Provenance tracking implemented

### **Phase 1 Metrics**
- **Data Quality**: ≥95% coverage for ≥90% of windows
- **Environment Coverage**: All 6 environment types with ≥50 windows each
- **Threshold Calibration**: ROC curves with AUC ≥0.8
- **Reproducibility**: All results reproducible with fixed seeds

### **Phase 2 Metrics**
- **Data Quality**: ≥95% coverage for ≥95% of windows
- **Environment Coverage**: All environment types with ≥100 windows each
- **Cross-Asset Validation**: Consistent behavior across BTC-USD and ETH-USD
- **Production Readiness**: All artifacts ready for production deployment

## Risk Mitigation

### **Data Risks**
- **Missing Data**: Implement robust data quality gates
- **Coverage Issues**: Monitor venue coverage continuously
- **Temporal Gaps**: Ensure continuous monitoring

### **Technical Risks**
- **Detector Issues**: Fix Spread v2 detector for real data
- **Environment Imbalance**: Ensure balanced environment representation
- **Threshold Calibration**: Validate thresholds on extended data

### **Operational Risks**
- **S3 Storage**: Monitor S3 storage costs and lifecycle
- **Compute Resources**: Monitor compute costs for extended analysis
- **Reproducibility**: Ensure all results are reproducible

## Conclusion

The phased approach ensures:
1. **Incremental Progress**: Each phase builds on the previous
2. **Risk Mitigation**: Early identification and resolution of issues
3. **Quality Assurance**: Robust validation at each phase
4. **Production Readiness**: Gradual progression to production deployment

**Current Status**: Phase 0 completed, Phase 1 planning in progress.

---
*This roadmap will be updated as we progress through each phase.*
