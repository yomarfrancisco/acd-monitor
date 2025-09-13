"use client";
import { useEffect, useRef } from "react";
import { dashContainer, dashGrid } from "@/lib/ui";
import SideNav from "./SideNav";

export default function DashboardLayout({ children }: { children: React.ReactNode }) {
  const gridRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const v = "STACK-DIAG v4"; // bump if you redeploy again
    // eslint-disable-next-line no-console
    console.log("STACK-DIAG v4 mounted");
    // eslint-disable-next-line no-console
    window.__stackDiagRan = true;
    
    const log = () => {
      const el = gridRef.current;
      if (!el) {
        // eslint-disable-next-line no-console
        console.log(v, "ERROR: gridRef.current is null");
        return;
      }
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
    
    // Add a small delay to ensure DOM is ready
    setTimeout(log, 100);
    window.addEventListener("resize", log);
    return () => window.removeEventListener("resize", log);
  }, []);

  return (
    <div className={dashContainer}>
      <div ref={gridRef} className={dashGrid} data-stack-diag="dashGrid">
        <SideNav />
        <main className="min-w-0 flex flex-col gap-6">{children}</main>
      </div>
    </div>
  );
}