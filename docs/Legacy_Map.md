# Legacy File Map - ACD Monitor UI

**Generated**: 2024-12-19  
**Purpose**: Categorize files in `ui/cursor-dashboard/` for cleanup planning  
**Status**: Analysis only - no deletions performed

## File Categorization

### Active Files (Keep)
Files actively used in current deployment and development:

```
ui/cursor-dashboard/
├── app/
│   ├── page.tsx                    # Main dashboard (53,527 tokens)
│   ├── layout.tsx                  # Root layout
│   ├── globals.css                 # Global styles
│   ├── loading.tsx                 # Loading component
│   ├── api/                        # All API routes (8 routes)
│   │   ├── agent/chat/route.ts
│   │   ├── datasources/status/route.ts
│   │   ├── debug/route.ts
│   │   ├── events/route.ts
│   │   ├── evidence/export/route.ts
│   │   ├── health/run/route.ts
│   │   ├── metrics/overview/route.ts
│   │   ├── metrics/timeseries/route.ts  # NEW
│   │   ├── risk/summary/route.ts
│   │   ├── selftest/route.ts       # NEW
│   │   ├── status/route.ts
│   │   └── wake/route.ts
│   └── dashboard/                  # Dashboard pages (7 pages)
│       ├── layout.tsx
│       ├── page.tsx
│       ├── background-agents/page.tsx
│       ├── billing/page.tsx
│       ├── contact/page.tsx
│       ├── docs/page.tsx
│       ├── integrations/page.tsx
│       ├── settings/page.tsx
│       └── usage/page.tsx
├── components/
│   ├── ui/                         # UI component library (40+ components)
│   ├── AssistantBubble.tsx         # Chat component
│   ├── DegradedModeBanner.tsx      # Status banner
│   ├── dashboard/
│   │   ├── Layout.tsx
│   │   └── SideNav.tsx
│   └── theme-provider.tsx
├── lib/
│   ├── proxy-utils.ts              # Backend proxy utility
│   ├── backendAdapter.ts
│   ├── resilient-api.ts
│   ├── safe.ts
│   ├── ui.ts
│   └── utils.ts
├── types/
│   ├── api.schemas.ts              # TypeScript schemas
│   ├── api.ts
│   └── window.d.ts
├── scripts/
│   ├── contract-smoke.mjs          # API testing
│   └── golden/                     # Test data (6 files)
├── docs/
│   └── UI-API-MOCKING.md           # API documentation
├── package.json                    # Dependencies
├── pnpm-lock.yaml                  # Lock file
├── tailwind.config.js              # Tailwind configuration
├── tsconfig.json                   # TypeScript configuration
├── next.config.mjs                 # Next.js configuration
├── vercel.json                     # Vercel configuration
├── components.json                 # Component configuration
├── middleware.ts                   # Next.js middleware
└── UI_DEPLOYMENT_ANCHOR.md         # Deployment guide
```

### Suspect Files (Review)
Files that may be unused or need investigation:

```
ui/cursor-dashboard/
├── app/
│   ├── __proof__/                  # Development/testing directory
│   │   └── page.tsx
│   ├── dev/                        # Development tools
│   │   └── palette/page.tsx
│   └── api/datasources/            # PDF files in API directory
│       ├── Product Specification - Algorithmic Coordination Diagnostic (ACD) (1).pdf
│       └── RBB Brief 55+ 11 Sep (6).pdf
├── hooks/                          # Duplicate hooks directory
│   ├── use-mobile.ts
│   └── use-toast.ts
├── styles/                         # Empty styles directory
├── public/fonts/                   # Font directory with README only
│   └── README.md
└── dev.log                         # Development log file
```

### Legacy Files (Safe to Archive)
Duplicate, backup, or outdated files:

```
ui/cursor-dashboard/
├── app/
│   ├── globals 2.css               # Duplicate CSS file
│   ├── layout 2.tsx                # Duplicate layout
│   └── page.tsx.backup             # Backup file
├── package 2.json                  # Duplicate package file
├── package-lock.json               # npm lock file (should use pnpm)
├── postcss.config 2.mjs            # Duplicate config
├── postcss.config.js               # Duplicate config
├── postcss.config.mjs              # Duplicate config
├── README 2.md                     # Duplicate README
└── tsconfig.tsbuildinfo            # TypeScript build cache
```

## Cleanup Recommendations

### Immediate Actions (Safe)
1. **Remove Duplicate Files**: Delete all files with "2" suffix
2. **Remove Backup Files**: Delete `.backup` files
3. **Remove npm Lock File**: Delete `package-lock.json` (use pnpm only)
4. **Remove Build Cache**: Delete `tsconfig.tsbuildinfo`

### Review Required
1. **PDF Files in API**: Move to appropriate documentation directory
2. **Development Directories**: Review `__proof__/` and `dev/` usage
3. **Empty Directories**: Clean up `styles/` and `public/fonts/`
4. **Duplicate Hooks**: Consolidate `hooks/` with `components/ui/`

### Archive Structure
```
ui/cursor-dashboard/archive/
├── backups/
│   ├── page.tsx.backup
│   └── layout 2.tsx
├── duplicates/
│   ├── globals 2.css
│   ├── package 2.json
│   ├── postcss.config 2.mjs
│   ├── postcss.config.js
│   └── README 2.md
├── npm-artifacts/
│   └── package-lock.json
└── build-cache/
    └── tsconfig.tsbuildinfo
```

## File Count Summary

- **Active Files**: ~80 files (core functionality)
- **Suspect Files**: ~10 files (need review)
- **Legacy Files**: ~8 files (safe to remove)

## Risk Assessment

### Low Risk (Safe to Remove)
- Duplicate files with "2" suffix
- Backup files
- npm lock file
- Build cache files

### Medium Risk (Review First)
- Development directories
- PDF files in API directory
- Empty directories

### High Risk (Keep)
- All files in `app/api/`
- All files in `components/`
- Configuration files
- Documentation files

## Next Steps

1. **Backup**: Create archive directory structure
2. **Remove Low Risk**: Delete duplicate and backup files
3. **Review Medium Risk**: Investigate suspect files
4. **Update Documentation**: Remove references to deleted files
5. **Test**: Verify functionality after cleanup

---

**This analysis provides a safe path for cleaning up the codebase while preserving all active functionality.**
