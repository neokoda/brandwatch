"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { cn } from "@/lib/utils";
import { useAuth } from "@/components/providers/auth-provider";
import {
  LayoutDashboard,
  MessageSquare,
  BarChart2,
  Layers,
  Bell,
  Lightbulb,
  ClipboardCheck,
  Settings,
  LogOut,
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

export function Sidebar({ accountName }: SidebarProps) {
  const pathname = usePathname();
  const { user, logout } = useAuth();
  const displayName = accountName ?? user?.account_name ?? "Account";

  return (
    <nav className="flex flex-col h-full w-56 shrink-0 border-r border-border bg-background">
      {/* Wordmark */}
      <div className="h-14 flex items-center px-5 border-b border-border">
        <span className="text-sm font-semibold tracking-tight">Brandwatch</span>
      </div>

      {/* Account switcher */}
      <div className="px-3 py-3 border-b border-border">
        <div className="flex items-center gap-2 px-2 py-1.5 rounded text-sm text-foreground">
          <span className="flex-1 font-medium truncate">{displayName}</span>
        </div>
        {user?.email && (
          <p className="px-2 text-xs text-muted-foreground truncate">{user.email}</p>
        )}
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
        <button
          onClick={logout}
          className="w-full flex items-center gap-2.5 px-2.5 py-2 rounded text-sm text-muted-foreground hover:bg-surface hover:text-foreground transition-colors duration-100"
        >
          <LogOut size={15} strokeWidth={2} />
          Sign out
        </button>
      </div>
    </nav>
  );
}
