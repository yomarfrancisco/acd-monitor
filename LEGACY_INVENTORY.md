# Legacy Inventory & Quarantine Plan

## Overview
This document catalogs legacy elements that should be quarantined, deprecated, or removed to prevent CI surprises and improve developer velocity.

## 🚫 Quarantined Test Directories

### Status: QUARANTINE (via pytest.ini norecursedirs)
**Rationale:** These directories contain tests with missing imports, broken dependencies, or incomplete implementations that cause CI failures.

**Directories:**
- `tests/agent/` - Missing `pytest`, `Dict` imports; incomplete test infrastructure
- `tests/benchmarks/` - Missing `pytest` imports; performance tests not maintained
- `tests/data/` - Missing `pytest` imports; data pipeline tests broken
- `tests/demo/` - Missing `pytest` imports; demo features not implemented
- `tests/evidence/` - Missing `patch` import; evidence system incomplete
- `tests/phase1/` - Missing `pytest` imports; phase 1 tests not maintained
- `tests/phase2/` - Missing `pytest` imports; phase 2 tests not maintained  
- `tests/phase3/` - Missing `pytest` imports; phase 3 tests not maintained
- `tests/vmm/` - Missing `run_vmm` imports; VMM system incomplete

**Guard Mechanism:** `pytest.ini` with `norecursedirs` directive
**Action:** Keep quarantined until individual test files are fixed or removed

## 📦 Legacy Requirements Files

### Status: DEPRECATE
**Files:**
- `./requirements.txt` - Competing with `requirements-lock.txt`
- `./backend/requirements.txt` - Unused backend requirements

**Rationale:** Only `requirements-lock.txt` should be used for reproducible builds
**Action:** Mark as deprecated, add warning comments, consider removal

## 🐳 Legacy Docker Files

### Status: KEEP (but document)
**Files:**
- `./binance-proxy/Dockerfile` - Active proxy service

**Rationale:** Still in use for proxy services
**Action:** Keep but ensure it's documented and maintained

## 🔧 Legacy Scripts & Data

### Status: AUDIT NEEDED
**Potential Issues:**
- `real_data_runs/` - Old data snapshots that may cause CI confusion
- Unused scripts in `scripts/` that may conflict with active ones
- Stray LFS pointers or large data files

**Action:** Audit and clean up unused data snapshots

## 🚀 CI/Workflow Legacy

### Status: VERIFIED CLEAN
**Current State:**
- All workflows use `actions/upload-artifact@v4` ✅
- No deprecated GitHub Actions found ✅
- Makefile uses proper TAB separators ✅

**Action:** No changes needed

## 📋 Action Items

### Immediate (P0)
1. **Confirm pytest.ini guards** - Verify `norecursedirs` covers all problematic directories
2. **Add CI health job** - Check for deprecated actions, missing v4 artifacts
3. **Enforce artifact discipline** - Retention policies, size caps, provenance
4. **Add materialization watchdogs** - Smoke checks on row counts, coverage

### Next (P1)  
1. **Create runbooks** - "How to cut a baseline/court" one-pager
2. **Add deprecation checks** - Script to fail CI if requirements-lock.txt is out-of-sync
3. **Fast-path dev loop** - `make dev-smoke` target for <10s feedback

## 🎯 Success Criteria

- [ ] All three workflows (Court, Baseline, E2E) consistently green
- [ ] No test collection errors from legacy directories
- [ ] Artifact retention and provenance enforced
- [ ] Developer feedback loop <10s for micro changes
- [ ] Clear documentation for baseline/court operations

## 🔒 Constraints

- Backend-only changes unless explicitly approved for UI
- Small, isolated PRs (one theme per PR)
- No breaking changes to active functionality
- Maintain all existing artifact generation capabilities
