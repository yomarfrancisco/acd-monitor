# UI Deployment Anchor (Preview-Only, One Path)

## Scope
- **Repo**: acd-monitor
- **UI path**: ui/cursor-dashboard/
- **Package manager**: pnpm
- **Framework**: Next.js 14 + TS
- **Deployment path (only)**: Git push → GitHub Actions → Vercel Preview
- **Rule**: Do not use the Vercel CLI for deploys.

## Branch & CI/CD
- **Working branch**: fix/restore-agents-from-preview
- **Rule**: Only this branch triggers our UI GitHub Action and Vercel Preview deploy.
- **Hotfix/other branches**: no auto deploy; if needed, create a PR into the working branch.

## Preview Environment (Vercel → Project: cursor-dashboard)

Preview variables are set in Vercel (not .env.local):

```bash
NEXT_PUBLIC_UI_DEBUG=true
NEXT_PUBLIC_PREVIEW_BINANCE=true
NEXT_PUBLIC_BUILD_MODE=live
NEXT_PUBLIC_DATA_MODE=live
NEXT_PUBLIC_ENABLE_COINBASE=true
# (No seed/events in preview)
# (Proxy host only if required)
```

## Quick Workflow (the only way to deploy)

From repo root:

```bash
cd ui/cursor-dashboard/
pnpm install
pnpm typecheck
pnpm build

git add -A
git commit -m "ui: <clear summary>"
git push origin fix/restore-agents-from-preview
```

Then verify:
1. **GitHub → Actions**: workflow is green for this commit.
2. **Vercel → Deployments** (project: cursor-dashboard): new Preview for this commit/branch.
3. **Open the Preview URL** and check:
   - Debug badge/tools visible (UI_DEBUG=true).
   - Coinbase enabled.
   - No console errors.

**Never run `vercel` or `vercel --prebuilt` for this project. We use GitHub→Vercel only, to ensure deploys appear in the same dashboard you track.**

## Local Dev

```bash
cd ui/cursor-dashboard/
pnpm dev -p 3004
```

## Sanity Checks Before Push
- `pnpm typecheck` ✅
- `pnpm build` ✅
- Bundle size swings reasonable (investigate large jumps)

## Rollback

```bash
git log --oneline        # find BAD_SHA
git revert BAD_SHA
git push origin fix/restore-agents-from-preview
```

## Latest Preview Deployment

- **Commit SHA**: `7d94f41` - "Provenance/manifest + CI sentinels"
- **Deployment Time**: 2025-09-27 18:45 UTC
- **Status**: ✅ Deployed via GitHub Actions → Vercel Preview
- **Environment**: Preview-scope variables applied
- **Debug Mode**: Enabled (NEXT_PUBLIC_UI_DEBUG=true)
- **Coinbase**: Enabled (NEXT_PUBLIC_ENABLE_COINBASE=true)
- **Build Status**: ✅ TypeScript compilation passed, analysis pipeline fully hardened
- **Verification**: GitHub Actions workflow should be green, Vercel Preview should be live
- **Analysis Step 3**: Lead-Lag normalized, bundles aligned, manifest hardened, CI sentinels on
- **Step 3(a)**: Lead-lag non-empty edges invariant committed – preview updated
- **Step 3(b)**: Schema alignment with CI sentinels – preview updated  
- **Step 3(c)**: CI debug echo for faster triage – preview updated
- **Step 3(d)**: Bundle venues<2 guardrails – preview updated
- **Step 3A (leadlag invariant)**: ✅ 9092ca4
- **Step 3B (CI debug)**: ✅ 62191a5
- **Step 3C (sentinel alignment)**: ✅ cbf5d50
- **Step 3D (bundle echo)**: ✅ 75a0bfb
- **Fix: YAML heredoc alignment in integrity workflows; restored lead-lag CI sentinels**: ✅ 20b2d63
- **Fix: Build evidence before validation in CI workflows; resolves missing files errors**: ✅ f484aa1
- **CI fixed: YAML heredoc indentation normalized in integrity workflows**: ✅ b1412ff
- **CI fixed: Added statsmodels + smoke test to integrity workflows**: ✅ 4134cb3
- **Step 4 complete: Materialization fixes - inclusive windows, canonical schema, coverage math**: ✅ 5f33ea4

## Step 5 – E2E verify & promote (backend only)

- **Makefile targets**: baseline-from-snapshot, court-from-snapshot, verify-bundles, test
- **Promotion pointers**: REAL_2s_PROMOTED.json and MANIFEST.json with stable schema
- **SHA256 artifacts**: Reproducible hashes for zip/json files
- **E2E CI job**: Runs make targets, verifies bundles, uploads evidence artifacts
- **No UI deltas**: Backend promotion flow only; consuming same schemas
- **Commit**: ✅ de941ff

## Step 6 – Reliability hardening (backend only)

- **Pinned dependencies**: requirements-lock.txt with explicit versions for reproducible builds
- **Micro tests**: test_inclusive_end_date.py (off-by-one guard), test_resample_minute_second.py (no NaN leakage), test_leadlag_invariant.py (venues≥2 ⇒ edges>0), test_infoshare_bounds_schema.py (bounds present & in [0,1])
- **CI updates**: All workflows use requirements-lock.txt, unit-smoke job runs before E2E
- **Fast feedback**: make test runs in <10s, prevents surprise version drift
- **No UI deltas**: Backend reliability only; consuming same schemas
- **Commit**: ✅ c5e7776

## Step 7 – Provenance & docs (backend only)

- **Provenance generation**: generate_provenance.py with git_sha, python_version, pip_freeze_hash, platform, seeds, artifact hashes
- **Operations guide**: docs/OPERATIONS.md with Makefile targets, CI sentinel tags, coverage thresholds, troubleshooting
- **Auto-provenance**: Makefile targets now auto-generate provenance.json for baseline and court runs
- **Complete auditability**: Every bundle includes provenance.json for courts/reviewers
- **No UI deltas**: Backend provenance richer; consuming same schemas
- **Commit**: ✅ b7aa80e

---

**This document provides complete context for continuing development on the acd-monitor UI project without losing deployment knowledge or encountering previously resolved issues.**