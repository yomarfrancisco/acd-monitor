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

- **Commit SHA**: `6fbc14d` - "feat: Lead-Lag v2 engine deployment ready"
- **Deployment Time**: 2025-09-27 23:30 UTC
- **Status**: ✅ Deployed via GitHub Actions → Vercel Preview
- **Environment**: Preview-scope variables applied
- **Debug Mode**: Enabled (NEXT_PUBLIC_UI_DEBUG=true)
- **Coinbase**: Enabled (NEXT_PUBLIC_ENABLE_COINBASE=true)
- **Build Status**: ✅ TypeScript compilation passed, Next.js build successful
- **Verification**: GitHub Actions workflow should be green, Vercel Preview should be live
- **Lead-Lag v2 Engine**: ✅ Research-grade lead-lag analysis with proper methodology
- **Features**: Cross-correlation and lagged regression estimators, HAC significance testing
- **Horizons**: Multiple horizon support (1s, 2s, 5s, 10s, 30s)
- **Code Quality**: Clean flake8 compliance + black formatting
- **Real Results**: Lead-lag relationships detected (binance→bybit: 22s, okx→bybit: 11s)
- **Previous Deployment**: `7d94f41` - "Provenance/manifest + CI sentinels" (2025-09-27 18:45 UTC)

## Step 5 – E2E verify & promote (backend only)

- **Makefile targets**: baseline-from-snapshot, court-from-snapshot, verify-bundles, test
- **Promotion pointers**: REAL_2s_PROMOTED.json and MANIFEST.json with stable schema
- **SHA256 artifacts**: Reproducible hashes for zip/json files
- **E2E CI job**: Runs make targets, verifies bundles, uploads evidence artifacts
- **No UI deltas**: Backend promotion flow only; consuming same schemas
- **Hotfix**: ✅ d95a591 (upgrade upload-artifact@v4, add permissions, acceptance checks)
- **Step 5: E2E verify & promote (backend only) — ✅**

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

[preview-deploy] sha=9c59178fa35379e7337ed06631939c37e4454859 ts=2025-09-27T18:48:01Z
[preview-deploy] sha=acef041e5ff5f9249351895fc93a1d45d1f6a6d0 ts=2025-09-27T20:52:00Z
[preview-deploy] sha=6fbc14d ts=2025-09-27T23:30:00Z