# ACD Monitor Operations Guide

This document provides operational guidance for running the ACD Monitor backend systems.

## Makefile Targets

### Basic Operations

```bash
# Build baseline evidence from snapshot
make baseline-from-snapshot SNAPSHOT=baselines/2s

# Build court evidence from snapshot  
make court-from-snapshot SNAPSHOT=court/1s

# Verify all bundles have required files and valid data
make verify-bundles

# Run unit tests
make test

# Clean temporary files
make clean
```

### Examples

```bash
# Build 2s research baseline
make baseline-from-snapshot SNAPSHOT=baselines/2s

# Build 1s court baseline
make court-from-snapshot SNAPSHOT=court/1s

# Verify all evidence bundles
make verify-bundles
```

## CI Sentinel Tags

The system uses structured logging with specific tags for monitoring and debugging.

### Status Tags

- `[MZ:start]` - Materialization started
- `[MZ:schema]` - Schema normalization applied
- `[MZ:done]` - Materialization completed
- `[STATS:materialize:granularity=X]` - Coverage statistics
- `[STATS:leadlag:venues]` - Lead-Lag venue count
- `[STATS:leadlag:edges]` - Lead-Lag edge count
- `[STATS:spread:permute]` - Spread permutation count
- `[STATS:infoshare:bounds]` - InfoShare bounds summary

### Abort Tags

- `[ABORT:leadlag:venues_lt_2]` - Less than 2 venues for Lead-Lag
- `[ABORT:leadlag:edges_empty]` - No edges generated despite venues≥2
- `[ABORT:infoshare:invalid_bounds]` - Invalid or missing bounds
- `[ABORT:spread:permutes]` - Insufficient permutations
- `[ABORT:verify]` - Bundle verification failed

### Warning Tags

- `[WARN:materialize:low_coverage]` - Coverage below threshold
- `[WARN:infoshare:sum!=1]` - InfoShare bounds don't sum to 1

## Coverage Thresholds

### Materialization
- **Seconds**: 0.8 (80% coverage required)
- **Minutes**: 0.9 (90% coverage required)

### Analysis
- **Lead-Lag**: venues≥2, edges>0
- **InfoShare**: bounds in [0,1], sum≈1
- **Spread**: permutations≥1000

## File Structure

```
baselines/2s/
├── OVERLAP.json          # Overlap window metadata
├── MANIFEST.json         # Run manifest with provenance
├── provenance.json       # Detailed provenance information
└── evidence/
    ├── leadlag_results.json
    ├── spread_results.json
    ├── info_share_results.json
    ├── EVIDENCE.md
    └── research_bundle_2s.zip

court/1s/
├── OVERLAP.json          # Court overlap window
├── MANIFEST.json         # Court run manifest
├── provenance.json       # Court provenance
└── evidence/
    ├── leadlag_results.json
    ├── spread_results.json
    ├── info_share_results.json
    ├── EVIDENCE.md
    └── court_bundle_1s.zip
```

## Troubleshooting

### Common Issues

1. **Empty edges in Lead-Lag**
   - Check: `[STATS:leadlag:venues]` and `[STATS:leadlag:edges]`
   - Cause: Less than 2 venues or data quality issues
   - Fix: Ensure sufficient venues and data coverage

2. **Missing bounds in InfoShare**
   - Check: `[STATS:infoshare:bounds]`
   - Cause: Analysis failed or insufficient data
   - Fix: Check data quality and analysis parameters

3. **Low coverage warnings**
   - Check: `[WARN:materialize:low_coverage]`
   - Cause: Data gaps or insufficient materialization
   - Fix: Extend capture window or check data sources

4. **CI failures**
   - Check: `[ABORT:*]` tags in CI logs
   - Cause: Missing files, invalid data, or threshold violations
   - Fix: Address specific abort condition

### Debug Commands

```bash
# Check bundle integrity
make verify-bundles

# Run unit tests
make test

# Check specific bundle
python -c "
import json
with open('baselines/2s/evidence/leadlag_results.json') as f:
    data = json.load(f)
    print(f'Venues: {data.get(\"venues_count\", 0)}')
    print(f'Edges: {data.get(\"edges_count\", 0)}')
"
```

## Provenance

Every run includes detailed provenance information:

- **Git SHA**: Exact code version
- **Python version**: Runtime environment
- **Dependency hash**: Fingerprint of installed packages
- **Platform info**: System details
- **Seeds**: Random number generator seeds
- **Artifact hashes**: SHA256 of all outputs

This ensures complete reproducibility and auditability for court proceedings.
