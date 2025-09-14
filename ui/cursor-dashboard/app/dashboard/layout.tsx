import type React from "react";
import SideNav from "@/components/dashboard/SideNav";

export default function DashboardRouteLayout({ children }: { children: React.ReactNode }) {
  return (
    <div
      data-root-grid="dash"
      className="grid grid-cols-1 gap-6 lg:grid-cols-[18rem_1fr] lg:gap-8 px-4 sm:px-6 lg:px-8"
    >
      <aside className="lg:sticky lg:top-16 lg:h-[calc(100dvh-4rem)]">
        <SideNav />
      </aside>

      <main className="min-w-0">
        {children}
      </main>
    </div>
  );
}