"use client";
import { useEffect, useRef } from "react";
import { dashContainer, dashGrid } from "@/lib/ui";
import SideNav from "./SideNav";

export default function DashboardLayout({ children }: { children: React.ReactNode }) {
  const gridRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const el = document.querySelector('[data-root-grid="dash"]') as HTMLElement | null;
    if (!el) return console.log('ROOT-DIAG: no root grid');
    const kids = Array.from(el.children).map(n => n.tagName.toLowerCase());
    const cs = getComputedStyle(el);
    console.log('ROOT-DIAG', {
      className: el.className,
      kids,                        // should be ['aside','main']
      display: cs.display,
      gridTemplateColumns: cs.gridTemplateColumns,
      width: el.getBoundingClientRect().width,
      innerWidth,
    });
  }, []);

  return (
    <div className={dashContainer}>
      <div
        ref={gridRef}
        data-root-grid="dash"
        className={dashGrid}
        style={{ outline: '2px solid red' }}
      >
        <SideNav />
        <main className="min-w-0 flex flex-col gap-6" data-stack-diag="main">{children}</main>
      </div>
      <pre id="stack-diag" data-stack-diag="dashGrid" className="sr-only"></pre>
    </div>
  );
}