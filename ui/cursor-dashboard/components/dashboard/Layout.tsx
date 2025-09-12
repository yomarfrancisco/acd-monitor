import { dashContainer, dashGrid } from "@/lib/ui";
import SideNav from "./SideNav";

interface DashboardLayoutProps {
  children: React.ReactNode;
  activeSidebarItem: 
    | "overview"
    | "configuration" 
    | "data-sources"
    | "ai-economists"
    | "health-checks"
    | "events-log"
    | "billing"
    | "compliance"
    | "contact";
  setActiveSidebarItem: (item: 
    | "overview"
    | "configuration" 
    | "data-sources"
    | "ai-economists"
    | "health-checks"
    | "events-log"
    | "billing"
    | "compliance"
    | "contact") => void;
}

export default function DashboardLayout({ children, activeSidebarItem, setActiveSidebarItem }: DashboardLayoutProps) {
  return (
    <div className={dashContainer}>
      <div className={dashGrid}>
        {/* Nav renders FIRST so it appears above content on mobile */}
        <SideNav activeSidebarItem={activeSidebarItem} setActiveSidebarItem={setActiveSidebarItem} />
        <main className="flex flex-col gap-6">{children}</main>
      </div>
    </div>
  );
}
