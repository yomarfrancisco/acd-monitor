# Mobile Dashboard — Anchor (Updated)

## 0) Non-negotiables
- **Desktop stays frozen (unchanged visuals)**:
  - Sticky left sidebar ~18rem, main content right.
  - Overview uses 2×2 cards, chart/table below.
  - Agents tab: out of scope (already mobile-responsive).
- **Deploy from GitHub, not CLI**. Vercel Project → Root Directory = ui/cursor-dashboard. Always deploy from repo root.

## 1) Routing reality (Baseline "A")
- The Dashboard UI lives under `app/page.tsx` behind a tab (`activeTab === "dashboard"`).
- `app/dashboard/layout.tsx` is not used in this baseline.
- Therefore the responsive root grid and cards section must be implemented inside `app/page.tsx` (only when dashboard tab is active).

(Optional "Baseline B" later: migrate Dashboard to `/dashboard` route. Until then, all work happens in `app/page.tsx`.)

## 2) Structure to implement (in app/page.tsx when dashboard tab is active)

### Root container (controls sidebar/main split):

```tsx
<div
  data-root-grid="dash"
  className="grid grid-cols-1 gap-6 lg:grid-cols-[18rem_1fr] lg:gap-8 px-4 sm:px-6 lg:px-8"
>
  <aside className="lg:sticky lg:top-16 lg:h-[calc(100dvh-4rem)]">
    <SideNav /> {/* nav renders full-width above content on mobile */}
  </aside>

  <main className="min-w-0">
    {/* Dashboard body */}
  </main>
</div>
```

### Cards section (controls card stacking):

```tsx
<section className="grid grid-cols-1 gap-6 lg:grid-cols-2" data-probe="dash-cards-section">
  {/* Card 1 */}
  {/* Card 2 */}
  {/* Card 3 */}
  {/* Card 4 */}
</section>

<section className="w-full mt-6">
  {/* Chart/Table */}
</section>
```

### Inner card grids (controls card content):

```tsx
// INSIDE cards – never use lg: here; use a smaller breakpoint
<div className="grid grid-cols-1 gap-6 sm:grid-cols-2">
  {/* inner content */}
</div>
```

### Critical syntax gotcha (Tailwind)
- Use `lg:grid-cols-[18rem_1fr]` (✅)
- Do not use `lg:[grid-template-columns:18rem_1fr]` (❌) — Tailwind won't apply that in JIT by default.

## 3) Breakpoint rules
- **One flip for layout**: `lg:` (1024px)
- **Mobile**: `grid-cols-1` (sidebar above content; full-width cards)
- **Desktop**: `lg:grid-cols-[18rem_1fr]` (sidebar left, content right); cards section `lg:grid-cols-2`.
- **Inner content**: use `sm:` (640px) for two-up inside a card. Never let inner grids force desktop layout.

## 4) Acceptance criteria

### Desktop (≥1024px) unchanged
- 18rem sticky sidebar; 2×2 cards; chart full width; no spacing/typography regressions.

### Mobile (<1024px)
- SideNav appears above content (full-width vertical list).
- Cards stack 1→2→3→4, then chart/table.
- No horizontal scroll; touch targets comfy; text left-aligned.

## 5) Debug & verify (copy/paste in console on preview)

```javascript
// Root exists
document.querySelector('[data-root-grid="dash"]')

// Cards section exists
document.querySelector('main section.grid')

// Root columns
(() => {
  const el = document.querySelector('[data-root-grid="dash"]');
  if (!el) return 'no root';
  const cs = getComputedStyle(el);
  return { display: cs.display, cols: cs.gridTemplateColumns };
})()

// Inspect all grids inside main
Array.from(document.querySelectorAll('main *'))
  .filter(el => getComputedStyle(el).display === 'grid')
  .map(el => ({
    tag: el.tagName.toLowerCase(),
    class: String(el.className),
    cols: getComputedStyle(el).gridTemplateColumns
  }))
```

### Expect:
- **Mobile**: root shows `1fr`; inner card grids show single column; no element reporting two equal columns at base (`grid-cols-2` without `sm:`).
- **Desktop**: root shows `18rem 1fr`; cards section shows two columns.

## 6) Deployment guardrails
- Vercel "Source" must be GitHub with a clear commit SHA.
- If lockfile mismatch: update `pnpm-lock.yaml` from repo root and re-push.
- Add `<html data-build-sha={process.env.VERCEL_GIT_COMMIT_SHA ?? 'no-sha'}>` in root layout temporarily to confirm the live SHA.

## 7) Cleanup (after mobile verified)
- Remove temporary probes (`data-*` beacons).
- Keep desktop frozen.
- Consider a follow-up migration to `/dashboard` route if we want a cleaner layout stack.

---

## PR Checklist Template

### Mobile Dashboard Implementation Checklist

- [ ] **Routing**: Implementation in `app/page.tsx` (dashboard tab), not `/dashboard` route
- [ ] **Root Container**: `data-root-grid="dash"` with `grid grid-cols-1 gap-6 lg:grid-cols-[18rem_1fr] lg:gap-8`
- [ ] **Cards Section**: `data-probe="dash-cards-section"` with `grid grid-cols-1 gap-6 lg:grid-cols-2`
- [ ] **Inner Grids**: `grid grid-cols-1 gap-6 sm:grid-cols-2` (no `lg:` prefixes)
- [ ] **Desktop Unchanged**: Visual regression test passed
- [ ] **Mobile Stacking**: Sidebar above content, cards stack vertically
- [ ] **Console Verification**: All queries return expected results
- [ ] **Screenshots**: Mobile (<1024px) and Desktop (≥1024px) provided
- [ ] **No Horizontal Scroll**: Mobile viewport test passed

### Console Verification Results
```javascript
// Paste console output here
```

### Screenshots
- [ ] Mobile view (<1024px)
- [ ] Desktop view (≥1024px)
