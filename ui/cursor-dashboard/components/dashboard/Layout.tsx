"use client";
import { ReactNode } from "react";
import { dashContainer, dashGrid } from "@/lib/ui";
import SideNav from "./SideNav";

export default function DashboardLayout({ children }: { children: ReactNode }) {
  return (
    <div className={dashContainer}>
      <div className={dashGrid}>
        {/* Nav renders FIRST so it appears above content on mobile */}
        <SideNav />
        <main className="flex flex-col gap-6">{children}</main>
      </div>
    </div>
  );
}
