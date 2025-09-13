"use client";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { navList, navItem, navItemActive } from "@/lib/ui";

const items = [
  { href: "/dashboard",                  label: "Overview",           icon: "⏱️" },
  { href: "/dashboard/settings",         label: "Settings",           icon: "⚙️" },
  { href: "/dashboard/integrations",     label: "Integrations",       icon: "📦" },
  { href: "/dashboard/background-agents",label: "Background Agents",  icon: "☁️" },
  { href: "/dashboard/usage",            label: "Usage",              icon: "📊" },
  { href: "/dashboard/billing",          label: "Billing & Invoices", icon: "🧾" },
  { href: "/dashboard/docs",             label: "Docs",               icon: "📄" },
  { href: "/dashboard/contact",          label: "Contact Us",         icon: "✉️" },
];

export default function SideNav() {
  const pathname = usePathname();
  return (
    <aside className="lg:sticky lg:top-16 self-start">
      <nav className={navList} aria-label="Dashboard sections">
        {items.map(i => {
          const active = pathname === i.href;
          return (
            <Link key={i.href} href={i.href} className={`${navItem} ${active ? navItemActive : ""}`}>
              <span aria-hidden>{i.icon}</span>
              <span>{i.label}</span>
            </Link>
          );
        })}
      </nav>
    </aside>
  );
}