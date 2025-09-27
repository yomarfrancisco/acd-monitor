# **UI Deployment Anchor Document**

## **AI Instruction**
When I ask for changes, assume:
- Scope is `ui/cursor-dashboard/` only
- Provide copy-pasteable edits in TypeScript/Tailwind
- Keep strict TypeScript rules intact
- Maintain workflow: dev → typecheck → build → commit → push → deploy

## **Project Context**
**Repository**: `acd-monitor` (Algorithmic Collusion Detection Monitor)  
**Location**: `/Users/ygorfrancisco/Desktop/acd-monitor`  
**UI Framework**: Next.js 14.2.16 with TypeScript  
**UI Directory**: `ui/cursor-dashboard/`  
**Package Manager**: pnpm  
**Development Server**: `http://localhost:3004`  
**Current Branch**: `fix/restore-agents-from-preview`  
**Remote**: `https://github.com/yomarfrancisco/acd-monitor.git`  
**Deployment**: Auto-deploys to Vercel on push  
**Latest Stable Deploy**: 2024-12-19 (cursor fix implementation)
**Fresh Preview Deploy**: 2024-12-19 (deploying clean working state)

## **Environment Requirements**
- **Node.js**: v18.x (required for Next.js 14.2.16)
- **Package Manager**: pnpm (NOT npm or yarn)
- **Dependencies**: Run `pnpm install` if missing
- **Development**: `pnpm dev` (runs on localhost:3004)

## **Package.json Scripts**
```json
{
  "scripts": {
    "dev": "next dev -p 3004",
    "build": "next build",
    "start": "next start",
    "lint": "next lint",
    "typecheck": "tsc -p tsconfig.json --noEmit"
  }
}
```

## **Environment Variables**
- **Location**: `.env.local` in `ui/cursor-dashboard/`
- **Example Variables**: 
  - `NEXT_PUBLIC_API_URL=https://api.example.com`
  - `DATABASE_URL=postgresql://...`
  - `AUTH_SECRET=your-secret-key`
- **Verification**: Check for required API keys and secrets
- **Vercel Impact**: Deployment fails if env vars are missing

## **Vercel Deployment Context**
- **Auto-deployment**: Triggers on push to remote repository
- **Branch Strategy**: ONLY `fix/restore-agents-from-preview` triggers GitHub Actions → Vercel
- **Hotfix Branches**: Do NOT trigger CI/CD workflows
- **Preview Deployments**: Feature branches get preview URLs
- **Production**: Main branch deploys to production
- **Build Logs**: Check Vercel dashboard for error messages
- **Environment Variables**: Must be set in Vercel dashboard

## **Critical Deployment Blockers**
- **TypeScript**: Always run `pnpm typecheck` before committing
- **Build Test**: Run `pnpm build` locally before push (catches missing assets/CSS)
- **Font Files**: Verify font files exist or use system fallbacks
- **Mobile Testing**: Test input focus behavior (iOS zoom prevention)
- **CSS Classes**: Ensure classes are defined in `globals.css`, not just referenced
- **JSX Structure**: Must be valid (unbalanced tags break builds)
- **Missing Env Vars**: Cause Vercel build failures
- **Asset Dependencies**: Images in `/public/`, fonts in `/public/` or system fallbacks

## **Bundle Size Indicators**
- **Clean State**: ~144 kB (no markdown dependencies)
- **With Markdown**: ~269 kB (includes react-markdown, remark-gfm, etc.)
- **Verification**: Always check bundle size before deployment
- **Component Check**: `ls ui/cursor-dashboard/components/` should show expected files
- **Tolerance**: ±10-15% is fine, investigate big jumps

## **Known Issues We've Resolved**
- **Mobile Zoom**: Fixed with 16px font + `agents-no-zoom-wrapper` CSS class
- **Dual Cursor**: Fixed with `style={{ caretColor: "transparent" }}` for complete hiding
- **Missing CSS**: Always check `globals.css` for class definitions
- **Font Loading**: Switched to system font fallback stack
- **JSX Errors**: Fixed unbalanced tags after reverts
- **Cursor Positioning**: Aligned with placeholder baseline using `left-4 top-4`

## **Current Project State**
- **Recent Fix**: Single-caret, baseline-aligned cursor implementation
- **Mobile Responsive**: Dashboard implemented with proper breakpoints
- **Font Compliance**: iOS-compliant (16px) to prevent zoom
- **Cursor Implementation**: Responsive sizing (1px mobile, 2px desktop)
- **Styling**: Tailwind CSS with custom CSS in `app/globals.css`
- **Input Field**: Proper placeholder targeting and iOS-compliant font sizes

## **🔒 Branch Strategy & CI/CD (Required)**
- **Primary working branch**: `fix/restore-agents-from-preview`
  (This is the only branch that triggers the UI GitHub Actions workflow and Preview deploys.)
- **Hotfix branches**: Allowed for experimentation, do not assume CI/CD will run from them.
- **Production**: Merges to main deploy production (when enabled).
- **Force push**: Allowed only when resetting a branch to a known good commit:
  ```bash
  git push origin fix/restore-agents-from-preview --force
  ```
- **Always verify current branch before pushing**:
  ```bash
  git branch --show-current
  ```

## **🧪 Deployment State Verification (Do this before every push)**
Goal: Catch "wrong state" deploys (e.g., stray deps, missing components) before CI/CD.

1. **Branch check**
   ```bash
   git branch --show-current  # must be fix/restore-agents-from-preview
   ```

2. **Typecheck + Build**
   ```bash
   pnpm typecheck
   pnpm build
   ```

3. **Bundle size indicator (sanity check—watch for big swings)**
   - Clean state (no markdown renderer): ~144 kB
   - With markdown stack (react-markdown/remark/katex): ~269 kB
   (Values are guidance—±10–15% is fine. Investigate big jumps.)

4. **Component layout check**
   ```bash
   ls ui/cursor-dashboard/components/
   # Should list only the expected UI components for the current state
   ```

5. **Dependency sanity**
   ```bash
   # If markdown rendering is NOT part of this deploy, these should NOT appear:
   grep -E "(react-markdown|remark-gfm|remark-math|remark-breaks|rehype-katex)" ui/cursor-dashboard/package.json || echo "✅ no markdown deps"
   ```

## **✅ Pre-Deployment Validation (Local gates)**
From `ui/cursor-dashboard/`:

```bash
# Env (once per session)
node --version   # v18.x
pnpm --version

# Install if you pulled new changes
pnpm install

# Typecheck & build MUST pass
pnpm typecheck
pnpm build
```

If both pass, proceed to Direct Push. If either fails, stop and ask for guidance (paste logs).

## **🚀 Direct Push Policy (No PRs)**
1. **Stage & commit (UI scope only)**
   ```bash
   git add -A
   git commit -m "ui: <clear summary>"
   ```

2. **Push directly**
   ```bash
   git push origin fix/restore-agents-from-preview
   ```

3. **Verify CI/CD**
   - GitHub Actions: New run appears for the branch.
   - Vercel: New Preview deployment created.
   - Share: Post the Preview URL + 1–2 screenshots.

Only pause for approval if typecheck/build fails or the Vercel deploy is red.

## **🔍 Deployment Verification Checklist (After push)**
1. GitHub Actions shows a green run for this commit.
2. Vercel Preview exists for the branch + commit.
3. Open the preview URL and confirm:
   - Composer/input looks unchanged (position, size, style).
   - Messages render with the expected formatting (no raw **/### unless intentionally plain text).
   - No console errors in DevTools.
4. Screenshot + link posted in chat.

## **🧱 Adding/Updating Dependencies (pnpm only)**
```bash
# Add dependency to the UI package
pnpm -F cursor-dashboard add <pkg>
# Dev dep:
pnpm -F cursor-dashboard add -D <pkg>

# Commit BOTH files:
git add ui/cursor-dashboard/package.json pnpm-lock.yaml
git commit -m "ui: add <pkg>"
git push origin fix/restore-agents-from-preview
```

Never use npm or yarn in this workspace.

## **🩹 Rollback & Recovery Procedures**

**Single-bad-commit revert (preferred):**
```bash
git log --oneline  # copy BAD_SHA
git revert <BAD_SHA>
git push origin fix/restore-agents-from-preview
```

**Revert a range:**
```bash
git revert <GOOD_SHA>..HEAD --no-commit
git commit -m "revert: roll back to <GOOD_SHA>"
git push origin fix/restore-agents-from-preview
```

**Hard reset (only when directed):**
```bash
git reset --hard <GOOD_SHA>
git push origin fix/restore-agents-from-preview --force
```

## **⚠️ Common Deployment Mistakes to Avoid**
- Pushing from the wrong branch (hotfix/experiment) and expecting CI/CD.
- Bundle size swing without intent (indicates accidental deps).
- Missing/extra components in `ui/cursor-dashboard/components/`.
- Using npm instead of pnpm (breaks lockfile).
- Assuming Vercel CLI deploys; we rely on GitHub → Vercel integration.

## **🔁 Updated Standard Workflow**
1. `cd ui/cursor-dashboard/`
2. `git branch --show-current` → confirm `fix/restore-agents-from-preview`
3. `pnpm install` (if needed)
4. `pnpm typecheck`
5. `pnpm build` (note bundle size sanity)
6. Optional: `ls ui/cursor-dashboard/components/`
7. `git add -A && git commit -m "ui: <summary>"`
8. `git push origin fix/restore-agents-from-preview`
9. Check GitHub Actions + Vercel Preview → share URL + screenshots

## **File Structure**
```
ui/cursor-dashboard/
├── app/
│   ├── page.tsx          # Main dashboard component
│   ├── globals.css       # Custom CSS and utilities
│   └── layout.tsx        # Root layout
├── public/               # Static assets
├── .env.local           # Environment variables
├── package.json         # Dependencies
└── tailwind.config.js   # Tailwind configuration
```

## **Quick Commands Reference**
```bash
# Navigate to project
cd /Users/ygorfrancisco/Desktop/acd-monitor/ui/cursor-dashboard/

# Check environment
node --version  # Should be v18.x
pnpm --version

# Install dependencies
pnpm install

# Development
pnpm dev

# Testing
pnpm typecheck
pnpm build

# Git workflow
git status
git add -A
git commit -m "descriptive message"
git push
```

## **Emergency Debugging**
- **Vercel Dashboard**: https://vercel.com/ygorfrancisco-gmailcoms-projects/cursor-dashboard
- **GitHub Actions**: https://github.com/yomarfrancisco/acd-monitor/actions
- **Project ID**: prj_qgNoPiigyce7K4fFIU97tGG8uS2S (for Vercel API calls)
- **Build Fails**: Check Vercel dashboard for logs
- **TypeScript Errors**: Run `pnpm typecheck` locally
- **CSS Issues**: Verify classes exist in `globals.css`
- **Font Problems**: Check `/public/` directory or use system fallbacks
- **Mobile Issues**: Test with 16px font sizes
- **Cursor Problems**: Verify `caretColor: "transparent"` and positioning
- **Preview Deployments**: Check Vercel dashboard for feature branch URLs

---

**This document provides complete context for continuing development on the acd-monitor UI project without losing deployment knowledge or encountering previously resolved issues.**
Sat Sep 27 11:51:17 UTC 2025 – preview live deploy bump
