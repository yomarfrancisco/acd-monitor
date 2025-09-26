# ACD Monitor - Cursor-based Dashboard

## Overview
This is the Cursor-based UI implementation for the ACD Monitor platform, providing a modern React-based interface for coordination risk monitoring.

## Prerequisites
- Node.js 20.18.0 (LTS) - use `nvm use` to switch to the correct version
- pnpm (recommended) or npm

## Quick Start

### 1. Switch to correct Node version
```bash
nvm use
```

### 2. Install dependencies
```bash
pnpm install
# or
npm install
```

### 3. Start development server
```bash
pnpm dev
# or
npm run dev
```

The app will be available at [http://localhost:3000](http://localhost:3000)

## Available Scripts

- `pnpm dev` - Start development server
- `pnpm build` - Build for production
- `pnpm start` - Start production server
- `pnpm lint` - Run linting

## Environment Variables
No environment variables are currently required. The app uses mock data for demonstration purposes.

## Known Caveats
- Port: 3000 (default Next.js port)
- Assets: RBB Economics logo and placeholder images are included
- Backend: Currently uses mock data - no backend integration yet

## Tech Stack
- Next.js 14
- React 18
- TypeScript
- Tailwind CSS
- Radix UI Components
- Recharts for data visualization

## Mock vs Live (Adapter)

The application supports both mock and live data modes through a backend adapter system.

### Environment Variables

Configure the data mode using these environment variables:

- `NEXT_PUBLIC_DATA_MODE`: Set to `"mock"` (default) or `"live"`
- `NEXT_PUBLIC_BACKEND_BASE_URL`: Backend API base URL (required for live mode)
- `NEXT_PUBLIC_API_BASE`: Local API base path (default: `/api`)

### Switching Modes

**Mock Mode (Default):**
```bash
NEXT_PUBLIC_DATA_MODE=mock
```
- Uses local mock API endpoints
- No backend connection required
- Perfect for development and demos

**Live Mode:**
```bash
NEXT_PUBLIC_DATA_MODE=live
NEXT_PUBLIC_BACKEND_BASE_URL=https://your-backend-api.com
```
- Connects to real backend APIs
- Requires backend to be running and accessible
- Used for production deployments

### Vercel Configuration

**Production (Mock Mode):**
- `NEXT_PUBLIC_DATA_MODE=mock`
- `NEXT_PUBLIC_API_BASE=/api`

**Preview (Live Mode Testing):**
- `NEXT_PUBLIC_DATA_MODE=live`
- `NEXT_PUBLIC_BACKEND_BASE_URL=https://your-backend-api.com`

### Degraded Mode

When backend connectivity issues occur:
- Non-blocking amber banner appears: "Data delayed/stale. Some tiles may be approximate."
- Unaffected tiles continue to render
- Heartbeat monitoring every 30 seconds
- Automatic recovery when backend becomes available

### Contract Testing

Run contract tests to validate API schemas:
```bash
npm run contracts
```

Tests validate golden sample data against expected schemas for all endpoints.
# Trigger fresh deployment
// noop to trigger preview Fri Sep 26 13:28:39 UTC 2025
