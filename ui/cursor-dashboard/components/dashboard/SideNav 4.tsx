"use client";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { User, Settings, Database, Bot, Zap, ClipboardList, CreditCard, FileText, MessageSquare } from "lucide-react";

const items = [
  { href: "/dashboard",                  label: "Overview",           icon: User },
  { href: "/dashboard/settings",         label: "Settings",      icon: Settings },
  { href: "/dashboard/integrations",     label: "Data",       icon: Database },
  { href: "/dashboard/background-agents",label: "Analysts",          icon: Bot },
  { href: "/dashboard/usage",            label: "Health",      icon: Zap },
  { href: "/dashboard/billing",          label: "Events",         icon: ClipboardList },
  { href: "/dashboard/docs",             label: "Billing", icon: CreditCard },
  { href: "/dashboard/contact",          label: "Reports", icon: FileText }
];

export default function SideNav() {
  const pathname = usePathname();
  return (
    <nav className="flex flex-col gap-2" aria-label="Dashboard sections">
        {items.map(i => {
          const active = pathname === i.href;
          const IconComponent = i.icon;
          return (
            <Link key={i.href} href={i.href} className={`w-full text-left px-3 py-2 rounded hover:bg-muted/50 flex items-center gap-2 text-xs ${active ? "bg-bg-tile text-[#f9fafb]" : "text-[#a1a1aa] hover:bg-bg-tile"}`}>
              <IconComponent className="w-3.5 h-3.5" />
              <span>{i.label}</span>
            </Link>
          );
        })}
        <Link href="/dashboard/contact" className={`w-full text-left px-3 py-2 rounded hover:bg-muted/50 flex items-center gap-2 text-xs ${pathname === "/dashboard/contact" ? "bg-bg-tile text-[#f9fafb]" : "text-[#a1a1aa] hover:bg-bg-tile"}`}>
          <MessageSquare className="w-3.5 h-3.5" />
          <span>Contact</span>
        </Link>
    </nav>
  );
}