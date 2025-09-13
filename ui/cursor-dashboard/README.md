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
