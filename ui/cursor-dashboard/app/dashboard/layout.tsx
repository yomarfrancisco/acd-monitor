import DashboardLayout from "@/components/dashboard/Layout";

export default function DashboardRouteLayout({ children }: { children: React.ReactNode }) {
  return (
    <>
      {/* SUPER-OBVIOUS SSR BEACON: red banner at top of body */}
      <div
        data-deployment-beacon="v2"
        style={{
          position: 'fixed',
          top: 0,
          left: 0,
          right: 0,
          zIndex: 99999,
          background: '#ff0000',
          color: '#ffffff',
          padding: '8px 16px',
          fontSize: 16,
          fontWeight: 'bold',
          textAlign: 'center',
          borderBottom: '3px solid #ffffff',
        }}
      >
        🚨 DEPLOYMENT BEACON v2 - app/dashboard/layout.tsx IS ACTIVE 🚨
      </div>
      
      {/* Original beacon for backup */}
      <div
        data-which-layout="app/dashboard/layout.tsx"
        style={{
          position: 'fixed',
          bottom: 0,
          right: 0,
          zIndex: 9999,
          background: '#333',
          color: '#fff',
          padding: '4px 6px',
          fontSize: 12,
          borderRadius: 4,
        }}
      >
        LAYOUT: app/dashboard/layout.tsx
      </div>
      
      <DashboardLayout>{children}</DashboardLayout>
    </>
  );
}