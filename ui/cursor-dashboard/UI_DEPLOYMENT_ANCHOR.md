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
- **Branch Strategy**: Deploys on all branches (including feature branches)
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

## **Standard Workflow**
1. **Directory**: Always work in `ui/cursor-dashboard/`
2. **Environment**: Verify Node v18.x with `node --version`
3. **Dependencies**: Run `pnpm install` if needed
4. **Development**: Start with `pnpm dev`
5. **Testing**: Run `pnpm typecheck` and `pnpm build`
6. **Local Test**: Verify with `pnpm dev`
7. **Commit**: `git add -A && git commit -m "descriptive message"`
8. **Deploy**: `git push` triggers automatic Vercel deployment

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
- **Build Fails**: Check Vercel dashboard for logs
- **TypeScript Errors**: Run `pnpm typecheck` locally
- **CSS Issues**: Verify classes exist in `globals.css`
- **Font Problems**: Check `/public/` directory or use system fallbacks
- **Mobile Issues**: Test with 16px font sizes
- **Cursor Problems**: Verify `caretColor: "transparent"` and positioning
- **Preview Deployments**: Check Vercel dashboard for feature branch URLs

---

**This document provides complete context for continuing development on the acd-monitor UI project without losing deployment knowledge or encountering previously resolved issues.**
