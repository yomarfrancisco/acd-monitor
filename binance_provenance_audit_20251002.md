# Binance Provenance Audit Report
**Generated**: 2025-10-02T16:58:22.159026+00:00

## Executive Summary

- **Total Slices Analyzed**: 2
- **Synthetic Slices**: 0
- **Real Slices**: 0
- **Indeterminate Slices**: 1

## Detailed Analysis

### SLICE_00

**Verdict**: INDETERMINATE (LOW confidence)
**Synthetic Score**: 15/100

**Evidence**:
- Duplicate Ratio: 4.0%
- API Traces: ❌ Absent
- Regular Intervals: ✅ No
- Perfect 1s Spacing: ✅ No
- High Duplicates: ✅ No
- Geometric Brownian: ⚠️ Yes

**Statistics**:
- Total Rows: 50
- Time Span: 1.3 seconds
- Mean Price: $118,596.10
- Price Range: $118,594.98 - $118,598.87

### SLICE_01

**Verdict**: LIKELY_SYNTHETIC (MEDIUM confidence)
**Synthetic Score**: 45/100

**Evidence**:
- Duplicate Ratio: 44.0%
- API Traces: ❌ Absent
- Regular Intervals: ✅ No
- Perfect 1s Spacing: ✅ No
- High Duplicates: ⚠️ Yes
- Geometric Brownian: ⚠️ Yes

**Statistics**:
- Total Rows: 50
- Time Span: 3.5 seconds
- Mean Price: $118,765.72
- Price Range: $118,765.72 - $118,765.73

## Recommendations

✅ **No synthetic data detected** - Binance data appears to be real.
