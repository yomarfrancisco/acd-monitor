import DashboardLayout from "@/components/dashboard/Layout";

export default function DashboardRouteLayout({ children }: { children: React.ReactNode }) {
  return (
    <>
      {/* SSR BEACON: if you see this in prod, this exact layout file is in use */}
      <div
        data-which-layout="app/dashboard/layout.tsx"
        style={{
          position: "fixed",
          inset: "auto 0 0 auto",
          zIndex: 9999,
          padding: "2px 6px",
          fontSize: 11,
          background: "#111827",
          color: "#9CA3AF",
          border: "1px solid #374151",
          borderRadius: 4,
          pointerEvents: "none"
        }}
      >
        LAYOUT: app/dashboard/layout.tsx
      </div>
      
      <DashboardLayout>{children}</DashboardLayout>
    </>
  );
}