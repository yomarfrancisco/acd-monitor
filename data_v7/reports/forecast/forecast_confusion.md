
# Forecast Validation Visualizations


## ROC Curve (ASCII)

```
    1.0 |     ●
        |    ╱
    0.8 |   ╱
  TPR   |  ╱
    0.6 | ╱
        |╱
    0.4 |●
        |
    0.2 |●
        |
    0.0 |●
        +───────────────
        0.0  0.2  0.4  0.6  0.8  1.0
                    FPR
```



## Precision-Recall Curve (ASCII)

```
    1.0 |●
        |
    0.8 | ●
        |
  Prec  |  ●
    0.6 |   ●
        |
    0.4 |    ●
        |
    0.2 |     ●
        |
    0.0 |      ●
        +───────────────
        0.0  0.2  0.4  0.6  0.8  1.0
                    Recall
```


## Lead Time Distribution (ASCII)

```
    0-4h |                     (0)
    4-8h |████████████████████ (156)
   8-12h |█████████            (73)
  12-16h |██████               (51)
  16-20h |████                 (35)
  20-24h |███████████          (92)
```


## Performance Summary

| Metric | Value | Status |
|--------|-------|--------|
| AUC | 0.627 | ❌ |
| Precision | 0.000 | ❌ |
| Recall | 0.000 | - |
| F1 Score | 0.000 | - |
| Hit Rate | 0.000 | - |
| False Positive Rate | 0.000 | ✅ |
| Median Lead Time | 8.0h | ✅ |

## Acceptance Criteria Status

- ✅ AUC ≥ 0.75: FAIL
- ✅ Precision ≥ 0.70: FAIL
- ✅ Median lead-time ≥ 4h: PASS
- ✅ False-positive rate < 25%: PASS
