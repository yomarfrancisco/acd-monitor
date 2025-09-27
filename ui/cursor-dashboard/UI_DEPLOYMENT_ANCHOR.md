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

---

**This document provides complete context for continuing development on the acd-monitor UI project without losing deployment knowledge or encountering previously resolved issues.**