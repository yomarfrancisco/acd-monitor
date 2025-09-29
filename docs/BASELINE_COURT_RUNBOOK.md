# Baseline & Court Operations Runbook

## Overview
This runbook provides exact commands and acceptance criteria for cutting baseline and court evidence bundles.

## 🎯 Baseline Operations

### Prerequisites
- Valid 2s snapshot in `baselines/2s/`
- All required dependencies installed from `requirements-lock.txt`

### Command
```bash
make baseline-from-snapshot SNAPSHOT=baselines/2s
```

### Expected Output
```
[BASELINE:2s:pin] {"baseline": "2s", "duration_minutes": 2.0, "coverage": 0.99, "venues": ["binance", "coinbase", "kraken", "okx", "bybit"], "policy": "RESEARCH_g=2s", "timestamp": "..."}
[BASELINE:2s:evidence] {"baseline": "2s", "evidence_dir": "baselines/2s/evidence", "bundle_file": "baselines/2s/evidence/research_bundle_2s.zip", "timestamp": "..."}
[PROVENANCE:generated] baselines/2s/provenance.json
[PROVENANCE:done] Generated provenance with 5 artifacts
```

### Acceptance Criteria
- [ ] `baselines/2s/OVERLAP.json` created
- [ ] `baselines/2s/evidence/` directory populated
- [ ] `research_bundle_2s.zip` created
- [ ] `provenance.json` generated with git SHA, python version, pip freeze hash
- [ ] All evidence files present: `leadlag_results.json`, `spread_results.json`, `info_share_results.json`, `EVIDENCE.md`, `MANIFEST.json`

## ⚖️ Court Operations

### Prerequisites
- Valid 1s snapshot in `court/1s/`
- All required dependencies installed from `requirements-lock.txt`

### Command
```bash
make court-from-snapshot SNAPSHOT=court/1s
```

### Expected Output
```
INFO:__main__:Court bundle validation: 5 venues
INFO:__main__:Running InfoShare analysis...
INFO:__main__:Running Spread analysis...
INFO:__main__:Running Lead-Lag analysis...
INFO:__main__:Evidence bundle written to court/1s/evidence/EVIDENCE.md
INFO:__main__:Court evidence bundle generated successfully
[PROVENANCE:generated] court/1s/provenance.json
[PROVENANCE:done] Generated provenance with 5 artifacts
```

### Acceptance Criteria
- [ ] `court/1s/OVERLAP.json` created
- [ ] `court/1s/evidence/` directory populated
- [ ] All evidence files present with court-specific analysis
- [ ] `provenance.json` generated with complete audit trail
- [ ] Court-specific validation: ALL5 venues, no stitching, coverage ≥ 0.999

## 🔍 Verification Commands

### Verify Bundles
```bash
make verify-bundles
```

### Fast Developer Feedback
```bash
make dev-smoke
```

### Micro Tests Only
```bash
make test-micro
```

## 📊 Expected Metrics

### Baseline (2s)
- **Duration**: ~2 minutes
- **Coverage**: ≥ 0.99
- **Venues**: 5 (binance, coinbase, kraken, okx, bybit)
- **Policy**: RESEARCH_g=2s
- **Permutations**: ≥ 2000

### Court (1s)
- **Duration**: ~1 minute  
- **Coverage**: ≥ 0.999
- **Venues**: 5 (ALL5 policy)
- **Policy**: COURT_1s
- **Permutations**: ≥ 5000
- **Stitching**: OFF

## 🚨 Troubleshooting

### Common Issues
1. **Missing dependencies**: Ensure `requirements-lock.txt` is installed
2. **Snapshot not found**: Verify snapshot directory exists and contains valid data
3. **Permission errors**: Check file permissions on snapshot directories
4. **Memory issues**: Ensure sufficient RAM for large datasets

### Debug Commands
```bash
# Check snapshot structure
ls -la baselines/2s/
ls -la court/1s/

# Verify Python environment
python --version
pip list | grep -E "(pandas|numpy|scipy|statsmodels)"

# Test micro tests
make test-micro

# Check bundle verification
make verify-bundles
```

## 📋 Pre-Flight Checklist

Before running baseline/court operations:

- [ ] Git status is clean
- [ ] All dependencies installed from `requirements-lock.txt`
- [ ] Snapshot directories exist and contain valid data
- [ ] Sufficient disk space for evidence generation
- [ ] Python environment is correct version (3.9+)

## 🎯 Success Criteria

A successful baseline/court operation should produce:

1. **Green CI runs** for all three workflows (Court Integrity, Baseline Integrity, E2E Verify)
2. **Complete evidence bundles** with all required JSON files
3. **Valid provenance** with git SHA, python version, and artifact hashes
4. **Proper retention** of artifacts (7-14 days)
5. **No regressions** in existing functionality

## 📞 Support

For issues or questions:
1. Check this runbook first
2. Run `make dev-smoke` for fast feedback
3. Review CI logs for specific error messages
4. Ensure all prerequisites are met
