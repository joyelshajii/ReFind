"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { Settings, ShieldCheck, HardDrive, ArrowUpRight } from "lucide-react";
import SearchBar from "@/components/SearchBar";
import { getIndexStats } from "@/lib/api";
import { IndexStats } from "@/types";

export default function HomePage() {
  const [stats, setStats] = useState<IndexStats | null>(null);

  useEffect(() => {
    getIndexStats()
      .then((data) => setStats(data))
      .catch((err) => console.error("Could not fetch stats:", err));
  }, []);

  return (
    <div className="flex-1 flex flex-col items-center justify-center px-4 py-16 sm:py-24 relative overflow-hidden">
      {/* Central Interactive Hub with gravitational mass anchor */}
      <div
        data-grav-mass="2.0"
        className="w-full max-w-2xl flex flex-col items-center text-center space-y-7 relative z-10"
      >
        {/* Brand Header */}
        <div className="space-y-4">
          <div className="inline-flex items-center gap-2.5 px-4 py-1.5 rounded-full bg-white/[0.04] border border-white/[0.1] backdrop-blur-md text-xs sm:text-sm text-zinc-300 font-mono">
            <span className="w-2 h-2 rounded-full bg-indigo-400 shadow-[0_0_8px_#818cf8]" />
            <span className="font-semibold text-zinc-200">BitByBit</span>
            <span className="text-zinc-600">/</span>
            <span className="text-zinc-300">Local-First Digital Memory</span>
          </div>

          <h1 className="text-5xl sm:text-6xl md:text-7xl font-extrabold tracking-tight text-white drop-shadow-[0_2px_24px_rgba(255,255,255,0.18)]">
            ReFind
          </h1>

          <p className="text-lg sm:text-xl text-zinc-300 font-normal tracking-tight">
            Find what you remember.
          </p>
        </div>

        {/* Large Pill-Shaped Search Box matching reference composition */}
        <div className="w-full pt-1">
          <SearchBar autoFocus />
        </div>

        {/* Below the search box section */}
        <div className="w-full flex flex-col items-center gap-4 pt-6 border-t border-white/[0.08]">
          <span className="text-xs uppercase tracking-[0.25em] text-zinc-400 font-mono font-medium">
            Search your digital memory
          </span>

          {/* Currently indexed source badge */}
          <div className="flex items-center gap-2.5 flex-wrap justify-center">
            <Link
              href="/index"
              className="inline-flex items-center gap-2.5 px-5 py-2.5 rounded-full bg-black/60 hover:bg-black/90 border border-white/[0.1] hover:border-white/[0.22] backdrop-blur-md text-sm text-zinc-200 transition-all shadow-[0_4px_20px_rgba(0,0,0,0.6)] group"
            >
              <HardDrive className="w-4 h-4 text-indigo-400" />
              <span>
                <strong className="text-white font-semibold">Local Files</strong> ·{" "}
                <span className="text-zinc-300">
                  {stats ? `${stats.total_documents} files indexed` : "Loading index..."}
                </span>
              </span>
              <ArrowUpRight className="w-4 h-4 text-zinc-400 group-hover:text-white transition-colors" />
            </Link>

            <Link
              href="/settings"
              className="p-2.5 rounded-full bg-black/60 hover:bg-black/90 border border-white/[0.1] hover:border-white/[0.22] backdrop-blur-md text-zinc-400 hover:text-zinc-200 transition-all shadow-[0_4px_20px_rgba(0,0,0,0.6)]"
              title="Data source settings"
            >
              <Settings className="w-4 h-4" />
            </Link>
          </div>

          {/* Privacy badge */}
          <div className="flex items-center gap-2 text-xs sm:text-sm text-zinc-400 font-mono">
            <ShieldCheck className="w-4 h-4 text-emerald-400" />
            <span>Local embeddings & vector index · No surveillance</span>
          </div>
        </div>
      </div>
    </div>
  );
}
