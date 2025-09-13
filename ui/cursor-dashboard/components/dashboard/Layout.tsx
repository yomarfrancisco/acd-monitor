"use client";
import { ReactNode } from "react";
import { dashContainer, dashGrid } from "@/lib/ui";
import SideNav from "./SideNav";

export default function DashboardLayout({ children }: { children: ReactNode }) {
  return (
    <div className={dashContainer}>
      <div className={dashGrid}>
        {/* Nav renders FIRST in DOM: above content on mobile; left rail on desktop */}
        <SideNav />
        <main className="flex flex-col gap-6">{children}</main>
      </div>
    </div>
  );
}