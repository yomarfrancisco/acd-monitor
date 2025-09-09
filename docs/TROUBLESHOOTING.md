# Troubleshooting Guide

## Common Issues and Solutions

### UI Looks Unstyled or _next Assets 404

**Problem:** The dashboard appears unstyled, or you see 404 errors for `_next/static/css/*` and `_next/static/chunks/app/*` assets in the browser console.

**Root Cause:** Corrupted Next.js build cache in the `.next` directory.

**Solution:**
```bash
# Navigate to UI directory
cd ui/cursor-dashboard

# Clean the build cache
npm run clean

# Restart development server
npm run dev

# Or use the combined command
npm run dev:clean
```

**Alternative Solutions:**
- For production builds: `npm run build:clean`
- Manual cleanup: `rm -rf .next` then restart

### Password Gate Removed

**Status:** Password gate has been completely removed from the application. No authentication is required for demo access.

**Note:** If you previously had `DEMO_PASSCODE` environment variable set in Vercel, it has been removed. Redeploy with Clear Cache if you need to reintroduce authentication.
4. Try incognito/private window

### MetaMask Console Errors

**Problem:** Console shows "Failed to connect to MetaMask" errors.

**Root Cause:** Browser extension trying to inject into the page.

**Solution:** These errors can be safely ignored - they're from the MetaMask browser extension and don't affect dashboard functionality.

### Development Server Won't Start

**Problem:** `Error: listen EADDRINUSE: address already in use :::3004`

**Root Cause:** Another process is using port 3004.

**Solution:**
```bash
# Kill existing process on port 3004
lsof -ti:3004 | xargs kill -9

# Then start server
npm run dev
```

## Available Scripts

- `npm run clean` - Remove `.next` build cache
- `npm run dev:clean` - Clean cache and start dev server
- `npm run build:clean` - Clean cache and build for production
- `npm run dev` - Start development server
- `npm run build` - Build for production
- `npm run typecheck` - Run TypeScript type checking

## Getting Help

If issues persist after trying these solutions:
1. Check the terminal output for specific error messages
2. Verify you're in the correct directory (`ui/cursor-dashboard`)
3. Ensure all dependencies are installed: `npm ci`
4. Check that the server is running on the expected port (3004)
