"use client";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { User, Settings, Database, Bot, Zap, ClipboardList, CreditCard, FileText, MessageSquare } from "lucide-react";

const items = [
  { href: "/dashboard",                  label: "Overview",           icon: User },
  { href: "/dashboard/settings",         label: "Configuration",      icon: Settings },
  { href: "/dashboard/integrations",     label: "Data Sources",       icon: Database },
  { href: "/dashboard/background-agents",label: "AI Agents",          icon: Bot },
  { href: "/dashboard/usage",            label: "Health Checks",      icon: Zap },
  { href: "/dashboard/billing",          label: "Events Log",         icon: ClipboardList },
  { href: "/dashboard/docs",             label: "Billing & Invoices", icon: CreditCard },
  { href: "/dashboard/contact",          label: "Compliance Reports", icon: FileText }
];

export default function SideNav() {
  const pathname = usePathname();
  return (
    <aside className="w-full min-w-0 lg:sticky lg:top-16 self-start">
      <nav className="flex flex-col gap-1" aria-label="Dashboard sections">
        {items.map(i => {
          const active = pathname === i.href;
          const IconComponent = i.icon;
          return (
            <Link key={i.href} href={i.href} className={`flex items-center gap-2 text-xs px-1.5 py-0.5 rounded-md cursor-pointer ${active ? "bg-bg-tile text-[#f9fafb]" : "text-[#a1a1aa] hover:bg-bg-tile"}`}>
              <IconComponent className="w-3.5 h-3.5" />
              <span>{i.label}</span>
            </Link>
          );
        })}
        <Link href="/dashboard/contact" className={`flex items-center gap-2 text-xs px-1.5 py-0.5 rounded-md cursor-pointer ${pathname === "/dashboard/contact" ? "bg-bg-tile text-[#f9fafb]" : "text-[#a1a1aa] hover:bg-bg-tile"}`}>
          <MessageSquare className="w-3.5 h-3.5" />
          <span>Contact Us</span>
        </Link>
      </nav>
    </aside>
  );
}