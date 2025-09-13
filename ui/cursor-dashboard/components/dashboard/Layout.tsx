"use client";
import { useEffect, useRef } from "react";
import { dashContainer, dashGrid } from "@/lib/ui";
import SideNav from "./SideNav";

export default function DashboardLayout({ children }: { children: React.ReactNode }) {
  const gridRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const v = "STACK-DIAG v3"; // bump if you redeploy again
    const log = () => {
      const el = gridRef.current;
      if (!el) return;
      const cs = window.getComputedStyle(el);
      // eslint-disable-next-line no-console
      console.log(v, {
        className: el.className,
        display: cs.display,
        gridTemplateColumns: cs.gridTemplateColumns,
        width: el.offsetWidth,
        deviceWidth: window.innerWidth,
      });
    };
    log();
    window.addEventListener("resize", log);
    return () => window.removeEventListener("resize", log);
  }, []);

  return (
    <div className={dashContainer}>
      <div ref={gridRef} className={dashGrid}>
        <SideNav />
        <main className="min-w-0 flex flex-col gap-6">{children}</main>
      </div>
    </div>
  );
}