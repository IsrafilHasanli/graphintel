"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  Activity,
  BarChart3,
  Boxes,
  CircleDot,
  Database,
  FileUp,
  GitBranch,
  LayoutDashboard,
  MessageSquareText,
  Network,
  Search,
} from "lucide-react";
import { cx } from "@/lib/format";

const LINKS = [
  { href: "/", label: "Dashboard", icon: LayoutDashboard },
  { href: "/ask", label: "Ask", icon: MessageSquareText },
  { href: "/graph", label: "Graph", icon: Network },
  { href: "/entities", label: "Entities", icon: Boxes },
  { href: "/upload", label: "Upload", icon: FileUp },
  { href: "/jobs", label: "Jobs", icon: Activity },
  { href: "/evaluation", label: "Evaluation", icon: BarChart3 },
];

export function Nav() {
  const pathname = usePathname();
  return (
    <header className="app-chrome sticky top-0 z-40 border-b border-surface-border backdrop-blur-xl">
      <div className="mx-auto flex max-w-[1400px] items-center gap-4 px-4 py-3 sm:px-6 lg:px-8">
        <Link href="/" className="group flex shrink-0 items-center gap-2.5">
          <span
            className="flex h-8 w-8 items-center justify-center rounded-lg border border-cyan-300/30 bg-cyan-300/10 text-cyan-200 transition-transform group-hover:scale-105"
            aria-hidden="true"
          >
            <GitBranch size={17} strokeWidth={2.4} />
          </span>
          <span>
            <span className="block text-sm font-semibold tracking-tight text-slate-100">GraphIntel</span>
            <span className="hidden text-[9px] uppercase tracking-[0.2em] text-slate-500 sm:block">Graph RAG operations</span>
          </span>
        </Link>
        <div className="hidden h-7 w-px bg-surface-border md:block" aria-hidden="true" />
        <nav aria-label="Primary" className="flex min-w-0 flex-1 items-center gap-1 overflow-x-auto">
          {LINKS.map((link) => {
            const active =
              link.href === "/"
                ? pathname === "/"
                : pathname.startsWith(link.href);
            return (
              <Link
                key={link.href}
                href={link.href}
                aria-current={active ? "page" : undefined}
                className={cx(
                  "inline-flex shrink-0 items-center gap-1.5 rounded-md px-2.5 py-2 text-xs font-medium transition-all focus:outline-none focus-visible:ring-2 focus-visible:ring-cyan-300",
                  active
                    ? "bg-cyan-300/10 text-cyan-100 shadow-[inset_0_-1px_0_rgba(103,232,249,0.8)]"
                    : "text-slate-400 hover:bg-surface-panel hover:text-slate-100",
                )}
              >
                <link.icon size={15} strokeWidth={active ? 2.2 : 1.8} aria-hidden="true" />
                {link.label}
              </Link>
            );
          })}
        </nav>
        <div className="hidden items-center gap-2 rounded-md border border-emerald-400/20 bg-emerald-400/5 px-2.5 py-1.5 text-[10px] font-medium uppercase tracking-wider text-emerald-300 lg:flex">
          <span className="status-pulse h-1.5 w-1.5 rounded-full bg-emerald-300" aria-hidden="true" />
          Live graph
        </div>
      </div>
    </header>
  );
}
