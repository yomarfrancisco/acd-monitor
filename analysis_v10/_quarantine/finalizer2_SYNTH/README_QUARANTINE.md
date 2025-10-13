# QUARANTINE: finalizer2_SYNTH

## Reason for Quarantine
This finalizer was quarantined due to **synthetic data fabrication** to meet thresholds, violating integrity rules.

## Violations Detected
1. **Simulation-based coverage adjustment**: Code explicitly states "adjusted the simulation" and "ensured coverage" by tweaking generation parameters
2. **Random number generation for data creation**: Used `np.random` to generate fake timestamps, prices, and trade data
3. **Threshold gaming**: Modified crossing probabilities and beacon generation to artificially meet 85% coverage and IQR≥6 requirements
4. **Synthetic data fabrication**: Created fake tick data, beacon events, and anchor crossings instead of using real data

## Specific Code Violations
- `crossing_prob = 0.90` - artificial probability adjustment
- `np.random.choice([0, 1, 2, 3, 4], p=[0.3, 0.4, 0.2, 0.08, 0.02])` - synthetic beacon generation
- `np.random.normal()` and `np.random.randint()` for fake data creation
- "Simulate realistic crossing rate" and "Simulate beacon events" comments

## Impact
This finalizer cannot be trusted for scaling to 14/30/60/90 days as it contains synthetic data that would contaminate all future batches.

## Required Actions
1. **DO NOT USE** any outputs from this finalizer
2. **REJECT** all results as invalid
3. **REQUIRE** complete re-run with real data only
4. **AUDIT** all future finalizers for simulation tokens

## Status: QUARANTINED - DO NOT PROMOTE





