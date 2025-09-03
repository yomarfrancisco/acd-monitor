# Golden Datasets (Week-1)

Purpose: deterministic fixtures used by CI to validate contracts, metric math, and report reproducibility.

## Datasets

1) **synthetic_competitive.csv**
- Two firms (FNB, NED) with environment-dependent responses.
- High environmental sensitivity (competitive).
- Expect: low INV, low SYNC, normal STAB, REG ~ competitive.

2) **synthetic_coordinated.csv**
- Two firms with near-invariant relationship across environments.
- Expect: high INV, higher SYNC, suppressed STAB, REG ~ coordination-like.

3) **sample_sa_cds_public.csv**
- Small hand-crafted sample emulating SA bank CDS with realistic magnitudes (for contract tests only).
- Sources tagged `derived` and `jse` to exercise source/confidence logic.

## Columns
`ts,firm_id,price,unit,src,confidence,hash`

- `ts`: UTC ISO 8601
- `price`: bps (integer/float)
- `src`: client|spglobal|ice|refinitiv|jse|derived
- `confidence`: 0–100
- `hash`: SHA-256(hex) of the raw row (reproducibility)

## Expected properties (asserted in tests)
- No duplicate `(ts,firm_id,src)` rows
- Monotonic timestamps (per firm)
- Competitive set: cross-corr(|lag|≤3) < 0.3
- Coordinated set: cross-corr(|lag|≤3) > 0.7
