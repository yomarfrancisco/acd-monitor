# ACD Monitor - Deployment State Documentation

**Generated**: 2024-12-19  
**Updated**: 2024-12-19  
**Branch**: `fix/restore-agents-from-preview`  
**Commit**: `ec23e38` - "Change button text from 'Analyze algorithms' to 'Audit my algorithm'"

## 🚀 Deployment Configuration

### Branch → Deploy Mapping
- **Staging/Preview**: `fix/restore-agents-from-preview` ✅
- **Production**: `main` (currently not deployed)
- **CI/CD Trigger**: Only `fix/restore-agents-from-preview` branch triggers GitHub Actions → Vercel
- **Hotfix Branches**: No automatic deployment (manual trigger required)

### Repository Configuration
- **Remote**: `https://github.com/yomarfrancisco/acd-monitor.git`
- **UI Directory**: `ui/cursor-dashboard/`
- **Framework**: Next.js 14.2.16 with TypeScript
- **Package Manager**: pnpm
- **Development Server**: `localhost:3004`

## 🔧 Environment Variables

### Required Environment Variables (Vercel Dashboard)
*Note: Values redacted for security*

| Variable Name | Purpose | Required |
|---------------|---------|----------|
| `CHATBASE_API_KEY` | Chatbase API authentication | Yes |
| `CHATBASE_ASSISTANT_ID` | Chatbase chatbot identifier | Yes |
| `CHATBASE_SIGNING_SECRET` | Chatbase identity verification | Yes |
| `CHATBASE_USE_LEGACY` | Feature flag for legacy endpoints | No |
| `BACKEND_URL` | Backend service URL | No (defaults to Render) |
| `NEXT_PUBLIC_AGENT_CHAT_ENABLED` | Enable/disable chat functionality | No |
| `NEXT_PUBLIC_AGENT_CHAT_STREAM` | Enable/disable streaming responses | No |
| `NEXT_PUBLIC_DATA_MODE` | Data mode (live/mock) | No |
| `VERCEL_ENV` | Vercel environment (auto-set) | Auto |
| `VERCEL_GIT_COMMIT_SHA` | Git commit hash (auto-set) | Auto |

### Environment Variable Usage in Code
- **Chat Integration**: `process.env.CHATBASE_*` variables for API authentication
- **Feature Flags**: `NEXT_PUBLIC_*` variables for client-side feature toggles
- **Backend Proxy**: `BACKEND_URL` for API routing
- **Build Metadata**: `VERCEL_*` variables for deployment tracking

## 📡 API Routes Status

### Live vs Mock/Degraded Mode Analysis

| Route | Status | Mode | Notes |
|-------|--------|------|-------|
| `/api/risk/summary` | ✅ Live | Mock Fallback | Proxy with deterministic jitter |
| `/api/metrics/overview` | ✅ Live | Mock Fallback | Timeframe-aware mock data |
| `/api/metrics/timeseries?metric=ci` | ✅ Live | Mock Fallback | Time series data with thresholds |
| `/api/events` | ✅ Live | Mock Fallback | Event generation with severity levels |
| `/api/datasources/status` | ✅ Live | Mock Fallback | Data source health monitoring |
| `/api/health/run` | ✅ Live | Mock Fallback | Health check with backend proxy |
| `/api/agent/chat` | ✅ Live | Chatbase + Mock | SSE streaming support |
| `/api/evidence/export` | ✅ Live | Mock Fallback | ZIP generation with backend fallback |

### API Implementation Details
- **Proxy Pattern**: All routes use `proxyJson()` utility for backend communication
- **Mock Fallback**: Deterministic pseudo-random data with jitter for "live-ish" feel
- **Error Handling**: Graceful degradation with 503/504 status codes
- **Streaming**: Chat API supports Server-Sent Events (SSE)
- **File Generation**: Evidence export creates ZIP files with multiple data formats
- **Response Headers**: All API responses include `x-acd-bundle-version: v1.9+` and `x-case-library-version: v1.9`

## 🎨 UI Components & Schemas

### v1.9+ Schema Compliance
- **Risk Summary**: ✅ Compliant with score/band/confidence structure
- **KPI Tiles**: ✅ Compliant with timeframe-aware metrics
- **Events**: ✅ Compliant with severity/type/riskScore structure
- **Evidence Export**: ✅ Compliant with ZIP bundle format

### Identified Placeholders
1. **Chart Visualization**: Dashboard shows "Chart Placeholder" text
2. **Timeseries Metrics**: `/api/metrics/timeseries` route not implemented
3. **Interactive Elements**: Some buttons show placeholder functionality

### UI Customizations Required
- **Chart Integration**: Replace placeholder with actual chart component
- **Timeseries API**: Implement missing metrics endpoint
- **Button Actions**: Connect placeholder buttons to actual functionality

## 📁 File Structure Analysis

### Live Files (Active in Current Deployment)
```
ui/cursor-dashboard/
├── app/
│   ├── page.tsx                    # Main dashboard (53,527 tokens)
│   ├── layout.tsx                  # Root layout
│   ├── globals.css                 # Global styles
│   ├── api/                        # All API routes
│   └── dashboard/                  # Dashboard pages
├── components/
│   ├── ui/                         # UI component library
│   ├── AssistantBubble.tsx         # Chat component
│   └── DegradedModeBanner.tsx      # Status banner
├── lib/
│   ├── proxy-utils.ts              # Backend proxy utility
│   └── utils.ts                    # Utility functions
├── types/
│   └── api.schemas.ts              # TypeScript schemas
└── package.json                    # Dependencies
```

### Supportive Files (Development/Deployment)
```
├── scripts/
│   ├── contract-smoke.mjs          # API testing
│   └── golden/                     # Test data
├── docs/
│   └── UI-API-MOCKING.md           # API documentation
├── UI_DEPLOYMENT_ANCHOR.md         # Deployment guide
├── vercel.json                     # Vercel configuration
├── tailwind.config.js              # Tailwind configuration
└── tsconfig.json                   # TypeScript configuration
```

### Legacy Files (Safe to Archive)
```
├── app/
│   ├── globals 2.css               # Duplicate CSS file
│   ├── layout 2.tsx                # Duplicate layout
│   └── page.tsx.backup             # Backup file
├── package 2.json                  # Duplicate package file
├── postcss.config 2.mjs            # Duplicate config
├── postcss.config.js               # Duplicate config
├── README 2.md                     # Duplicate README
└── dev.log                         # Development log
```

## 🧹 Cleanup Recommendations

### Immediate Actions
1. **Remove Duplicate Files**: Delete all files with "2" suffix
2. **Archive Backup Files**: Move `.backup` files to archive
3. **Clean Development Logs**: Remove `dev.log` and similar files

### Archive Structure
```
ui/cursor-dashboard/archive/
├── backups/
│   ├── page.tsx.backup
│   └── layout 2.tsx
├── duplicates/
│   ├── globals 2.css
│   ├── package 2.json
│   └── postcss.config 2.mjs
└── logs/
    └── dev.log
```

## 🔍 Deployment Verification Checklist

### ✅ Completed Validations
- [x] Branch deployment mapping confirmed
- [x] Environment variables documented
- [x] API routes tested and categorized
- [x] UI components schema compliance verified
- [x] File structure analyzed and categorized
- [x] TypeScript compilation successful
- [x] Build process successful (411 kB bundle)

### ❌ Outstanding Issues
- [ ] Chart placeholder needs replacement
- [ ] Legacy file cleanup required
- [ ] Button action connections needed

### 🔄 Next Steps
1. Replace chart placeholder with actual visualization
2. Clean up legacy files
3. Connect placeholder button actions
4. Update documentation with new features

## 📊 Bundle Analysis

### Current Bundle Size
- **Main Page**: 317 kB (411 kB First Load JS)
- **Shared Chunks**: 87.4 kB
- **Middleware**: 26.5 kB
- **Total**: ~411 kB (within acceptable range)

### Bundle Composition
- **React/Next.js**: Core framework
- **UI Components**: Radix UI + Tailwind
- **Markdown Rendering**: react-markdown + remark plugins
- **Charts**: Recharts (if implemented)
- **Utilities**: Date-fns, clsx, etc.

## 🚨 Critical Notes

1. **No .env.local File**: Environment variables must be set in Vercel dashboard
2. **Backend Dependency**: Some features require backend service availability
3. **Chatbase Integration**: Chat functionality depends on external API
4. **Preview Mode**: Backend proxy only works in preview environment
5. **Bundle Size**: Monitor for unexpected increases during development

---

**This document provides a complete snapshot of the current deployment state and should be updated with each significant change to the system.**
