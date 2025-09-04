# VMM Performance Report

## Executive Summary

- **Total Runs**: 19
- **Success Rate**: 100.0%
- **P95 Runtime**: 0.067s
- **Target P95**: 2.0s
- **Meets P95 Target**: ✅
- **Median Runtime**: 0.016s
- **Target Median**: 1.0s
- **Meets Median Target**: ✅

## Detailed Timing Statistics

| Metric | Value (seconds) |
|--------|----------------|
| Mean | 0.026 |
| Median | 0.016 |
| Std Dev | 0.019 |
| Min | 0.014 |
| Max | 0.068 |
| P50 | 0.016 |
| P75 | 0.022 |
| P90 | 0.066 |
| P95 | 0.067 |
| P99 | 0.068 |

## Convergence Analysis

- **Mean Iterations**: 100.0
- **Median Iterations**: 100.0
- **Max Iterations**: 100

**Convergence Distribution**:
- max_iterations: 19 runs

## Performance Bottlenecks

| Function | Avg Time (s) | Total Calls |
|----------|--------------|-------------|
| /Users/ygorfrancisco/Desktop/acd-monitor/src/acd/vmm/engine.py:286(run_vmm) | 0.0259 | 19 |
| /Users/ygorfrancisco/Desktop/acd-monitor/src/acd/vmm/engine.py:216(run_vmm) | 0.0259 | 19 |
| /Users/ygorfrancisco/Desktop/acd-monitor/src/acd/vmm/engine.py:116(_run_variational_optimization) | 0.0179 | 19 |
| /opt/homebrew/lib/python3.10/site-packages/pandas/core/indexes/base.py:6076(get_indexer_for) | 0.0120 | 1 |
| /opt/homebrew/lib/python3.10/site-packages/pandas/core/indexes/base.py:3858(get_indexer) | 0.0120 | 1 |
| /opt/homebrew/lib/python3.10/site-packages/numpy/lib/function_base.py:1324(diff) | 0.0120 | 1 |
| {built-in | 0.0120 | 1 |
| /Users/ygorfrancisco/Desktop/acd-monitor/src/acd/vmm/metrics.py:128(calibrate_environment_quality) | 0.0100 | 1 |
| /opt/homebrew/lib/python3.10/site-packages/pandas/core/indexes/base.py:6250(_maybe_promote) | 0.0090 | 1 |
| /opt/homebrew/lib/python3.10/site-packages/pandas/core/indexes/base.py:6100(_get_indexer_strict) | 0.0067 | 3 |

## Recommendations

- **✅**: P95 runtime meets 2s target
- **✅**: Median runtime meets 1s target
