# Coinbase BTC-USD Anomaly QC Report

## Overview
Quality control analysis of Coinbase data to investigate variance ratio anomaly
observed in Wave-1 tests (VR 1.5-18.4 vs 0.3-0.4 for other venues).

**Analysis Date**: 2025-09-30 12:09:37 UTC
**Symbol**: BTC-USD
**Date Range**: 2025-09-29 to 2025-09-30

## Key Findings

### Timestamp Analysis
- **Total Ticks**: 10806
- **Time Span**: 2.0 hours
- **Mean Inter-Arrival**: 666.4ms
- **Duplicate Timestamps**: 3605
- **Non-Monotonic**: 0

### Duplicate Analysis
- **Before Dedup**: 0 duplicates (0.0%)
- **After Dedup**: 0 duplicates (0.0%)
- **Records Removed**: 0 (0.0%)

### Staleness & Burstiness
- **Staleness Rate**: 0.0%
- **Longest Stale Stretch**: 0 seconds
- **Mean Updates/Second**: 1.5

### Spread Analysis
- **Negative Spreads**: 0.0%
- **Mean Spread**: 1.2512039153332735
- **Mean Spread (bps)**: 0.3

### Schema Conformity
- **Canonical Columns Present**: 8
- **Missing Columns**: []

## Plots Generated
- `timestamp_analysis.png` - Inter-arrival time analysis
- `duplicate_analysis.png` - Duplicate record analysis  
- `staleness_analysis.png` - Staleness and burstiness patterns
- `spread_analysis.png` - Spread quality and distribution

## Conclusion
✅ No major data quality issues detected
🔍 Coinbase anomaly may be genuine - requires deeper econometric analysis

## Files
- `coinbase_qc_summary.csv` - Summary metrics
- `coinbase_qc_report.md` - This report
- Various PNG plots for visual analysis
