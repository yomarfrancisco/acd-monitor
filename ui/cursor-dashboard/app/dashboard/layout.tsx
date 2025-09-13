import DashboardLayout from "@/components/dashboard/Layout";

export default function DashboardRouteLayout({ children }: { children: React.ReactNode }) {
  return (
    <>
      {/* DASH LAYOUT v3 beacon */}
      <div
        data-ssr-beacon="dash-v3"
        style={{position:'fixed',bottom:0,right:0,zIndex:99999,background:'#333',color:'#fff',padding:'6px 8px',fontSize:12}}
      >
        DASH LAYOUT v3 — {process.env.VERCEL_GIT_COMMIT_SHA?.slice(0,7) ?? 'no-sha'}
      </div>
      
      <DashboardLayout>{children}</DashboardLayout>
    </>
  );
}