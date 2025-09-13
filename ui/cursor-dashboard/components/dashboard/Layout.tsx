"use client";
import { ReactNode, useEffect, useRef } from "react";
import { dashContainer, dashGrid } from "@/lib/ui";
import SideNav from "./SideNav";

export default function DashboardLayout({ children }: { children: ReactNode }) {
  const gridRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const log = () => {
      if (!gridRef.current) return;
      const cs = window.getComputedStyle(gridRef.current);
      // eslint-disable-next-line no-console
      console.log("[dash grid] grid-template-columns:", cs.gridTemplateColumns, "width:", gridRef.current.offsetWidth);
      // eslint-disable-next-line no-console
      console.log("[dash grid] className:", gridRef.current?.className);
    };
    log();
    window.addEventListener("resize", log);
    return () => window.removeEventListener("resize", log);
  }, []);

  return (
    <div className={dashContainer}>
      <div ref={gridRef} className={dashGrid}>
        {/* Nav renders FIRST so it appears above content on mobile */}
        <SideNav />
        <main className="min-w-0 flex flex-col gap-6">{children}</main>
      </div>
    </div>
  );
}