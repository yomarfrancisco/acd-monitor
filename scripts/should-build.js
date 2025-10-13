// scripts/should-build.js
const { execSync } = require('node:child_process');
try {
  const base = process.env.VERCEL_GIT_PREVIOUS_SHA || 'HEAD~1';
  const head = process.env.VERCEL_GIT_COMMIT_SHA || 'HEAD';
  const diff = execSync(, { stdio: ['ignore','pipe','ignore'] })
    .toString().split('
').filter(Boolean);
  const uiTouched = diff.some(p =>
    p.startsWith('ui/') || p.startsWith('ui/cursor-dashboard') || p.startsWith('src/')
  );
  process.exit(uiTouched ? 0 : 1);
} catch { process.exit(0); }
