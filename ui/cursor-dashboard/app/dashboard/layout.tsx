import type { ReactNode } from "react";
import SideNav from "@/components/dashboard/SideNav";

export default function DashboardRouteLayout({ children }: { children: ReactNode }) {
  return (
    <>
      {/* DASH LAYOUT v3 beacon */}
      <div
        data-ssr-beacon="dash-v3"
        style={{position:'fixed',bottom:0,right:0,zIndex:99999,background:'#333',color:'#fff',padding:'6px 8px',fontSize:12}}
      >
        DASH LAYOUT v4 — {process.env.VERCEL_GIT_COMMIT_SHA?.slice(0,7) ?? 'no-sha'}
      </div>

      {/* Root responsive grid wrapper */}
      <div
        data-root-grid="dash"
        className="grid grid-cols-1 gap-6 lg:[grid-template-columns:18rem_1fr] lg:gap-8 px-4 sm:px-6 lg:px-8"
      >
        {/* Sidebar first = appears above on mobile, left column on desktop */}
        <aside className="lg:sticky lg:top-16 lg:self-start lg:h-[calc(100dvh-4rem)]">
          <SideNav />
        </aside>

        {/* Main content column */}
        <main className="min-w-0">{children}</main>
      </div>
    </>
  );
}