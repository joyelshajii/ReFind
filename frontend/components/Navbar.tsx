"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useState } from "react";
import { Search, FolderGit2, Settings, Sparkles } from "lucide-react";
import { getHealth } from "@/lib/api";

export default function Navbar() {
  const pathname = usePathname();
  const [health, setHealth] = useState<any>(null);

  useEffect(() => {
    getHealth().then((data) => setHealth(data));
  }, []);

  const navItems = [
    { label: "Search", href: "/", icon: Search },
    { label: "Indexing", href: "/index", icon: FolderGit2 },
    { label: "Settings", href: "/settings", icon: Settings },
  ];

  return (
    <header className="sticky top-0 z-40 border-b border-white/[0.08] bg-black/60 backdrop-blur-xl transition-all">
      <div className="max-w-6xl mx-auto px-4 h-16 flex items-center justify-between">
        {/* Brand */}
        <div className="flex items-center gap-3">
          <Link href="/" className="flex items-center gap-2.5 group">
            <div className="w-9 h-9 rounded-xl bg-gradient-to-tr from-indigo-950/80 via-zinc-900 to-indigo-900/60 border border-indigo-500/35 flex items-center justify-center text-indigo-300 shadow-[0_0_15px_-3px_rgba(99,102,241,0.25)] group-hover:border-indigo-400/50 group-hover:shadow-[0_0_20px_-2px_rgba(99,102,241,0.4)] transition-all">
              <Sparkles className="w-4 h-4" />
            </div>
            <div className="flex flex-col">
              <span className="font-semibold text-base tracking-tight text-white flex items-center gap-2">
                ReFind
                <span className="text-xs font-mono px-2 py-0.5 rounded bg-white/[0.06] text-zinc-300 border border-white/[0.1] font-medium">
                  BitByBit
                </span>
              </span>
            </div>
          </Link>
        </div>

        {/* Navigation */}
        <nav className="flex items-center gap-1.5">
          {navItems.map((item) => {
            const Icon = item.icon;
            const isActive = pathname === item.href || (item.href === "/" && pathname.startsWith("/search"));
            return (
              <Link
                key={item.href}
                href={item.href}
                className={`flex items-center gap-2 px-3.5 py-2 rounded-xl text-sm font-medium transition-all ${
                  isActive
                    ? "bg-white/[0.08] text-white border border-white/[0.14] shadow-[0_0_12px_rgba(255,255,255,0.04)]"
                    : "text-zinc-300 hover:text-white hover:bg-white/[0.04] border border-transparent"
                }`}
              >
                <Icon className="w-4 h-4" />
                {item.label}
              </Link>
            );
          })}
        </nav>

        {/* Engine Status indicator */}
        <div className="flex items-center gap-2.5">
          <div className="flex items-center gap-2 px-3 py-1.5 rounded-full bg-white/[0.04] border border-white/[0.1] text-xs text-zinc-200 backdrop-blur-md">
            <span className={`w-2 h-2 rounded-full ${health ? "bg-emerald-400 shadow-[0_0_8px_#34d399] animate-pulse" : "bg-zinc-500"}`} />
            <span className="font-mono text-xs text-zinc-300 tracking-wide font-medium">
              {health?.database?.pgvector_enabled ? "PostgreSQL + pgvector" : "Local Vector Engine"}
            </span>
          </div>
        </div>
      </div>
    </header>
  );
}
