# RBB Preview Branch Changelog

**Production remains at commit `ec23e38`** - "Change button text from 'Analyze algorithms' to 'Audit my algorithm'"

## Preview Branch Changes (since ec23e38)

### 🚀 **UI & API Integration** (Preview Only)
- **Timeseries Chart**: Fully wired to `/api/metrics/timeseries` with real-time data fetching
- **Events Table**: Connected to `/api/events` with proper error handling and loading states
- **Risk Summary & KPIs**: All dashboard tiles now fetch live data from backend APIs
- **Evidence Export**: ZIP download functionality implemented and tested
- **Self-test Status**: Health check indicator added to dashboard header

### 🔧 **Backend API Routes** (Preview Only)
- **`/api/metrics/timeseries`**: Time series data endpoint with configurable timeframes
- **`/api/events`**: Events log endpoint with pagination support
- **`/api/selftest`**: System health check endpoint
- **Response Headers**: All API routes now include proper CORS and content-type headers

### 🛠️ **CI/CD & Code Quality** (Preview Only)
- **Black Formatting**: Pinned to v24.8.0 for deterministic builds
- **Flake8 Linting**: Scoped to shippable code (`backend/` and `src/` only)
- **Pre-commit Hooks**: Configured for consistent local formatting
- **Line Endings**: Enforced LF via `.gitattributes` to prevent cross-platform issues
- **YAML Syntax**: Fixed GitHub Actions workflow heredoc indentation

### 📚 **Documentation** (Preview Only)
- **Deployment State**: Comprehensive documentation of current system status
- **API Documentation**: Updated with new endpoints and response formats
- **Contributing Guidelines**: Added code formatting and pre-commit instructions

### 🔒 **Safety Measures** (Preview Only)
- **Production Lock**: Local tag `rbb-prod-lock-ec23e38` created for safety
- **Branch Isolation**: All changes confined to `fix/restore-agents-from-preview`
- **No Main Branch Changes**: Production remains completely untouched

## 🎯 **Preview Environment Status**
- **Branch**: `fix/restore-agents-from-preview`
- **Latest Commit**: `53adf8a` - "feat(ci): implement clean & stable CI setup with proper tooling"
- **CI Status**: ✅ Green (flake8 + black + Next.js build passing)
- **Build Status**: ✅ Successful (20/20 pages generated)
- **API Routes**: ✅ All 12 endpoints implemented and tested

## 🔄 **Next Steps (Post-RBB)**
1. Review preview branch changes for potential production merge
2. Decide which features to promote to main branch
3. Remove temporary safety tag when ready
4. Update production deployment with approved changes

---
*This changelog documents preview-only changes. Production remains stable at commit `ec23e38` for the RBB demo.*
