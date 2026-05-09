"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { cn } from "@/lib/utils";
import {
  LayoutDashboard,
  MessageSquare,
  BarChart2,
  Layers,
  Bell,
  Lightbulb,
  ClipboardCheck,
  Settings,
} from "lucide-react";

const navItems = [
  { href: "/dashboard", label: "Dashboard", icon: LayoutDashboard },
  { href: "/mentions", label: "Mentions", icon: MessageSquare },
  { href: "/analytics", label: "Analytics", icon: BarChart2 },
  { href: "/topics", label: "Topics", icon: Layers },
  { href: "/alerts", label: "Alerts", icon: Bell },
  { href: "/insights", label: "Insights", icon: Lightbulb },
  { href: "/triage", label: "Triage", icon: ClipboardCheck },
];

const bottomItems = [
  { href: "/settings", label: "Settings", icon: Settings },
];

interface SidebarProps {
  accountName?: string;
}

export function Sidebar({ accountName = "Account" }: SidebarProps) {
  const pathname = usePathname();

  return (
    <nav className="flex flex-col h-full w-56 shrink-0 border-r border-border bg-background">
      {/* Wordmark */}
      <div className="h-14 flex items-center px-5 border-b border-border">
        <span className="text-sm font-semibold tracking-tight">Brandwatch</span>
      </div>

      {/* Account switcher */}
      <div className="px-3 py-3 border-b border-border">
        <button className="w-full flex items-center gap-2 px-2 py-1.5 rounded text-sm text-foreground hover:bg-surface transition-colors duration-100 text-left">
          <span className="flex-1 font-medium truncate">{accountName}</span>
          <svg
            width="10"
            height="10"
            viewBox="0 0 10 10"
            fill="none"
            className="shrink-0 text-muted-foreground"
          >
            <path d="M2 3.5L5 6.5L8 3.5" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
          </svg>
        </button>
      </div>

      {/* Main nav */}
      <div className="flex-1 overflow-y-auto py-2 px-2">
        {navItems.map(({ href, label, icon: Icon }) => {
          const active = pathname === href || pathname.startsWith(href + "/");
          return (
            <Link
              key={href}
              href={href}
              className={cn(
                "flex items-center gap-2.5 px-2.5 py-2 rounded text-sm transition-colors duration-100",
                active
                  ? "bg-foreground text-background font-medium"
                  : "text-muted-foreground hover:bg-surface hover:text-foreground"
              )}
            >
              <Icon size={15} strokeWidth={active ? 2.5 : 2} />
              {label}
            </Link>
          );
        })}
      </div>

      {/* Bottom nav */}
      <div className="py-2 px-2 border-t border-border">
        {bottomItems.map(({ href, label, icon: Icon }) => {
          const active = pathname === href || pathname.startsWith(href + "/");
          return (
            <Link
              key={href}
              href={href}
              className={cn(
                "flex items-center gap-2.5 px-2.5 py-2 rounded text-sm transition-colors duration-100",
                active
                  ? "bg-foreground text-background font-medium"
                  : "text-muted-foreground hover:bg-surface hover:text-foreground"
              )}
            >
              <Icon size={15} strokeWidth={active ? 2.5 : 2} />
              {label}
            </Link>
          );
        })}
      </div>
    </nav>
  );
}
