# 📱 Dashboard Mobile Responsiveness & Deployment Anchor

## Purpose

This document anchors the mobile responsiveness structure and the deployment lessons learned. It exists to prevent regressions and provide a reference point for future development.

⚠️ **Important:**
- This anchor applies to the Dashboard only.
- Agents tab mobile responsiveness is already locked in and must not be modified.
- Desktop layout is frozen and must not change.

---

## 1. Desktop Layout (≥ 1024px)

### Structure
- **Two-column CSS Grid**: `grid-template-columns: 18rem 1fr`
- **Left Sidebar (SideNav)**: fixed width 18rem, sticky, margin from screen edge
- **Right Main Content**: flexible width (1fr), contains dashboard content
- **Navigation**: vertical list of menu items, left-aligned, constrained by sidebar width
- **Cards**: 2x2 grid pattern (Cards 1 & 2 in row one, Cards 3 & 4 in row two)
- **Charts/Tables**: span full width of main content area

### Key Features
- SideNav stays visible when scrolling
- Concise navigation (due to 18rem width)
- Optimized for power users
- Desktop functionality must remain unchanged

---

## 2. Mobile Layout (< 1024px)

### Structure
- **Single-column stacking** with `grid-cols-1`
- **SideNav**: full-width, touch-friendly vertical stack above content
- **Main Content**: full-width area below navigation
- **Cards**: stacked vertically (1 → 2 → 3 → 4)
- **Charts/Tables**: span full width below cards

### Key Features
- Touch-optimized full-width buttons
- Vertical scrolling for all content
- Left-aligned text within full-width containers
- Mobile-first responsive design

---

## 3. Responsive Transition

### Breakpoint: `lg:` (1024px)

### CSS Grid Rules
- **Mobile**: `grid-cols-1` (single column)
- **Desktop**: `lg:[grid-template-columns:18rem_1fr]`

### SideNav Button Behavior
- **Mobile**: full-width, left-aligned text
- **Desktop**: constrained by 18rem sidebar width

### Card Behavior
- **Mobile**: stacked vertically, full width
- **Desktop**: 2x2 grid spanning main content width

### Consistency Across Breakpoints
- **Font sizes**: identical
- **Icon sizes**: identical
- **Button styling/shading**: identical
- **Visual design**: consistent look and feel
- **Text**: always left-aligned

---

## 4. Deployment Anchor Lessons

### Core Lesson

**Always deploy from the repository root, with rootDirectory set in Vercel project settings.**
**Do not deploy from inside the subdirectory.**

### Why
- Prevents double-path issues
- Ensures layout files and beacons are correctly deployed
- Keeps builds reproducible and consistent

---

## Appendix A: Deployment Debug Log

This section records debugging artifacts. Do not treat them as required implementation steps.

### Debugging Tools Used
- **SSR Beacons**: temporary markers added to confirm deployment correctness
- **Diagnostic Logging**: checked if mobile breakpoints were applied in production
- **Proof Route (/__proof__)**: validated routing behavior

### Deployment Issues Encountered
- **Root directory misalignment** (deployed from wrong level)
- **Build cache mismatches** (fixed with clean lockfile refresh)
- **Vercel project linking under wrong scope**
- **SSH fingerprint conflicts** blocking GitHub-driven deploys

### Resolution
- Deploy only from repo root
- Align lockfiles and package.json
- Ensure correct Vercel project scope
- Clear and refresh SSH fingerprints if needed

### Specific Debugging Steps Taken
1. **SSH Key Issues**: Added GitHub host keys to `~/.ssh/known_hosts` to avoid fingerprint prompts
2. **Lockfile Mismatch**: Updated `pnpm-lock.yaml` to match restored UI baseline (commit cb42b24)
3. **Vercel CLI Prevention**: Logged out of Vercel CLI and added `.vercel` to `.gitignore`
4. **GitHub Integration**: Created PR #40 to trigger proper GitHub-sourced deployments
5. **Baseline Restoration**: Restored UI to commit cb42b24 while keeping CI/pnpm infrastructure

### Key Commits for Reference
- `cb42b24`: Original baseline with working SSR beacons
- `3390e87`: Latest force deployment commit
- PR #40: Draft PR for GitHub-sourced preview deployment

---

## Next Steps for Developers

1. **Use this doc as the single source of truth for Dashboard mobile responsiveness.**
2. **Do not modify Agents tab responsiveness.**
3. **When debugging deployments, refer to Appendix A but keep the anchor rules untouched.**
4. **Always deploy from repository root with proper Vercel project settings.**
5. **Verify SSR beacons are present in production deployments.**

---

*This document serves as the authoritative reference for Dashboard mobile responsiveness and deployment practices. Any changes to the mobile layout must be validated against this anchor document.*
