import DashboardLayout from "@/components/dashboard/Layout";

export default function DashboardRouteLayout({ children }: { children: React.ReactNode }) {
  return (
    <>
      {/* SSR BEACON: if you see this in prod, this exact layout file is in use */}
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