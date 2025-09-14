import type React from "react";
import SideNav from "@/components/dashboard/SideNav";

export default function DashboardRouteLayout({ children }: { children: React.ReactNode }) {
  return (
    <>
      {/* VISIBLE PROBE - should be impossible to miss */}
      <div style={{position:'fixed',top:0,right:0,zIndex:99999,background:'#00ff00',color:'#000',padding:'8px',fontWeight:700}}>
        DASH LAYOUT MOUNTED - {process.env.VERCEL_GIT_COMMIT_SHA?.slice(0,7) ?? 'no-sha'}
      </div>
      
      <div
        data-probe="dash-layout"
        data-root-grid="dash"
        className="grid grid-cols-1 gap-6 lg:grid-cols-[18rem_1fr] lg:gap-8 px-4 sm:px-6 lg:px-8 overflow-x-hidden"
      >
        <aside className="lg:sticky lg:top-16 lg:h-[calc(100dvh-4rem)]">
          <div data-probe="dash-sidenav-mount" className="sr-only">dash-sidenav</div>
          <SideNav />
        </aside>

        <main className="min-w-0">
          {children}
        </main>
      </div>
    </>
  );
}