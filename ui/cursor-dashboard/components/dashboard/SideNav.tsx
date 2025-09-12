"use client";
import { User, Settings, Database, Bot, Zap, ClipboardList, CreditCard, FileText, MessageSquare } from "lucide-react";
import { navList, navItem, navItemActive } from "@/lib/ui";

interface SideNavProps {
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

export default function SideNav({ activeSidebarItem, setActiveSidebarItem }: SideNavProps) {
  const items = [
    { id: "overview", label: "Overview", icon: User },
    { id: "configuration", label: "Configuration", icon: Settings },
    { id: "data-sources", label: "Data Sources", icon: Database },
    { id: "ai-economists", label: "AI Agents", icon: Bot },
    { id: "health-checks", label: "Health Checks", icon: Zap },
    { id: "events-log", label: "Events Log", icon: ClipboardList },
    { id: "billing", label: "Billing & Invoices", icon: CreditCard },
    { id: "compliance", label: "Compliance Reports", icon: FileText },
    { id: "contact", label: "Contact Us", icon: MessageSquare },
  ];

  return (
    <aside className="lg:sticky lg:top-16 self-start">
      <div className="space-y-3">
        {/* User Info */}
        <div className="p-3 bg-white/5 rounded-lg">
          <h3 className="text-xs font-semibold text-[#f9fafb] mb-1">Ygor Francisco</h3>
          <p className="text-[10px] text-[#a1a1aa]">Ent Plan · ygor.francisco@gmail.com</p>
        </div>

        <nav className={navList}>
          {items.map((item) => {
            const active = activeSidebarItem === item.id;
            const Icon = item.icon;
            return (
              <button
                key={item.id}
                onClick={() => setActiveSidebarItem(item.id)}
                className={`${navItem} ${active ? navItemActive : ""}`}
              >
                <Icon className="w-3.5 h-3.5" />
                <span className="text-xs">{item.label}</span>
              </button>
            );
          })}
        </nav>
      </div>
    </aside>
  );
}
