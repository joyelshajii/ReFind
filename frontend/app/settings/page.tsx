"use client";

import { useEffect, useState } from "react";
import {
  HardDrive,
  Mail,
  Cloud,
  Globe,
  Database,
  ShieldCheck,
  Clock
} from "lucide-react";
import { getIndexStats, getHealth } from "@/lib/api";
import { IndexStats } from "@/types";

export default function SettingsPage() {
  const [stats, setStats] = useState<IndexStats | null>(null);
  const [health, setHealth] = useState<any>(null);

  useEffect(() => {
    getIndexStats()
      .then((data) => setStats(data))
      .catch((err) => console.error("Error fetching stats:", err));

    getHealth()
      .then((data) => setHealth(data))
      .catch((err) => console.error("Error fetching health:", err));
  }, []);

  const futureConnectors = [
    { name: "Gmail", icon: Mail, description: "Index emails, threads, and attachments directly" },
    { name: "Google Drive", icon: Cloud, description: "Synchronize cloud folders and Google Docs" },
    { name: "OneDrive", icon: Cloud, description: "Connect Microsoft 365 cloud documents" },
    { name: "Browser History", icon: Globe, description: "Search tabs, articles, and pages you previously visited" },
  ];

  return (
    <div className="max-w-4xl mx-auto px-4 py-10 space-y-8">
      {/* Title */}
      <div className="space-y-2" data-grav-mass="1.2">
        <h1 className="text-2xl sm:text-3xl md:text-4xl font-bold tracking-tight text-white">
          Settings & Architecture
        </h1>
        <p className="text-base text-zinc-300">
          Manage data sources, monitor vector index health, and review privacy controls.
        </p>
      </div>

      {/* Section 1: Data Sources */}
      <div
        data-grav-mass="1.1"
        className="p-6 rounded-2xl bg-black/45 border border-white/[0.08] backdrop-blur-xl space-y-5 shadow-[0_8px_32px_rgba(0,0,0,0.6)]"
      >
        <div className="space-y-1.5 border-b border-white/[0.08] pb-3.5">
          <h2 className="text-lg font-semibold text-zinc-100 flex items-center gap-2.5">
            <HardDrive className="w-5 h-5 text-indigo-400" />
            Data Sources & Connectors
          </h2>
          <p className="text-sm text-zinc-300">
            ReFind abstracts sources through a modular <code className="text-indigo-300 font-mono font-medium">DataSource</code> pipeline.
          </p>
        </div>

        {/* Active Connector: Local Files */}
        <div className="p-4 sm:p-5 rounded-xl bg-black/50 border border-white/[0.08] flex items-center justify-between flex-wrap gap-4">
          <div className="flex items-center gap-3.5">
            <div className="p-3 rounded-xl bg-emerald-950/30 border border-emerald-500/30 text-emerald-400 shadow-[0_0_12px_rgba(16,185,129,0.2)]">
              <HardDrive className="w-5 h-5" />
            </div>
            <div>
              <div className="flex items-center gap-2.5">
                <span className="text-base font-semibold text-zinc-100">Local Files</span>
                <span className="px-2.5 py-0.5 rounded-full text-xs font-mono font-semibold bg-emerald-950/60 text-emerald-300 border border-emerald-500/40">
                  Active
                </span>
              </div>
              <p className="text-sm text-zinc-300 mt-1">
                Indexes PDF, DOCX, PPTX, TXT, and Images (OCR + Vision) from your machine.
              </p>
            </div>
          </div>

          <div className="text-sm font-mono text-zinc-300 font-medium">
            {stats ? `${stats.total_documents} documents indexed` : "Ready"}
          </div>
        </div>

        {/* Future Connectors */}
        <div className="space-y-3 pt-2">
          <span className="text-xs sm:text-sm font-mono text-zinc-400 uppercase tracking-wider block font-medium">
            Future Connectors (Architecture Ready)
          </span>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3.5">
            {futureConnectors.map((c) => {
              const Icon = c.icon;
              return (
                <div
                  key={c.name}
                  className="p-4 rounded-xl bg-white/[0.02] border border-white/[0.06] flex items-center justify-between opacity-80 hover:opacity-100 hover:border-white/[0.14] transition-all"
                >
                  <div className="flex items-center gap-3">
                    <div className="p-2.5 rounded-lg bg-black/40 border border-white/[0.08] text-zinc-300">
                      <Icon className="w-4 h-4" />
                    </div>
                    <div>
                      <span className="text-sm font-semibold text-zinc-200 block">{c.name}</span>
                      <span className="text-xs sm:text-sm text-zinc-400 line-clamp-1 mt-0.5">{c.description}</span>
                    </div>
                  </div>
                  <span className="px-2.5 py-1 rounded text-xs font-mono text-zinc-400 bg-white/[0.04] border border-white/[0.08] shrink-0 font-medium">
                    Coming Soon
                  </span>
                </div>
              );
            })}
          </div>
        </div>
      </div>

      {/* Section 2: Index & Database Status */}
      <div
        data-grav-mass="1.1"
        className="p-6 rounded-2xl bg-black/45 border border-white/[0.08] backdrop-blur-xl space-y-5 shadow-[0_8px_32px_rgba(0,0,0,0.6)]"
      >
        <div className="space-y-1.5 border-b border-white/[0.08] pb-3.5">
          <h2 className="text-lg font-semibold text-zinc-100 flex items-center gap-2.5">
            <Database className="w-5 h-5 text-indigo-400" />
            Index & Storage Statistics
          </h2>
          <p className="text-sm text-zinc-300">
            Real-time status of the database and dense embedding index.
          </p>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4 gap-3.5">
          <div className="p-4 rounded-xl bg-black/50 border border-white/[0.08]">
            <span className="text-xs font-mono text-zinc-400 uppercase tracking-wider block font-medium">
              Total Documents
            </span>
            <span className="text-2xl sm:text-3xl font-bold text-white mt-1.5 block">
              {stats?.total_documents ?? 0}
            </span>
          </div>

          <div className="p-4 rounded-xl bg-black/50 border border-white/[0.08]">
            <span className="text-xs font-mono text-zinc-400 uppercase tracking-wider block font-medium">
              Indexed Chunks
            </span>
            <span className="text-2xl sm:text-3xl font-bold text-white mt-1.5 block">
              {stats?.total_chunks ?? 0}
            </span>
          </div>

          <div className="p-4 rounded-xl bg-black/50 border border-white/[0.08]">
            <span className="text-xs font-mono text-zinc-400 uppercase tracking-wider block font-medium">
              Vector Dimension
            </span>
            <span className="text-2xl sm:text-3xl font-bold text-white mt-1.5 block">
              {stats?.embedding_dimension ?? 384}d
            </span>
          </div>

          <div className="p-4 rounded-xl bg-black/50 border border-white/[0.08]">
            <span className="text-xs font-mono text-zinc-400 uppercase tracking-wider block font-medium">
              Engine Status
            </span>
            <span className="text-sm font-mono font-semibold text-emerald-400 mt-2 block truncate">
              {health?.database?.pgvector_enabled ? "PostgreSQL + pgvector" : "Local Vector Store"}
            </span>
          </div>
        </div>

        <div className="p-3.5 rounded-xl bg-black/50 border border-white/[0.08] flex items-center justify-between text-sm text-zinc-300 font-mono">
          <span className="flex items-center gap-2">
            <Clock className="w-4 h-4 text-zinc-400" />
            Last Indexed:
          </span>
          <span className="text-zinc-100 font-medium">
            {stats?.last_indexed_at ? new Date(stats.last_indexed_at).toLocaleString() : "Never"}
          </span>
        </div>
      </div>

      {/* Section 3: Privacy & Security */}
      <div
        data-grav-mass="1.0"
        className="p-6 rounded-2xl bg-black/45 border border-white/[0.08] backdrop-blur-xl space-y-4 shadow-[0_8px_32px_rgba(0,0,0,0.6)]"
      >
        <div className="space-y-1.5 border-b border-white/[0.08] pb-3.5">
          <h2 className="text-lg font-semibold text-zinc-100 flex items-center gap-2.5">
            <ShieldCheck className="w-5 h-5 text-emerald-400" />
            Privacy & Data Sovereignty
          </h2>
          <p className="text-sm text-zinc-300">
            ReFind is built strictly on local-first principles.
          </p>
        </div>

        <div className="space-y-3.5 text-sm sm:text-base text-zinc-200 leading-relaxed font-sans">
          <p>
            • <strong className="text-white font-semibold">Local-First Indexing:</strong> All documents, chunks, and metadata are parsed directly on your local system or self-hosted PostgreSQL cluster.
          </p>
          <p>
            • <strong className="text-white font-semibold">Zero Surveillance:</strong> ReFind does not scrape your web browsing, background apps, or personal accounts. No file uploads occur to third-party servers unless you explicitly configure external cloud LLM providers in your <code className="text-indigo-300 font-mono">.env</code>.
          </p>
          <p>
            • <strong className="text-white font-semibold">Grounded Evidence:</strong> Search explanations only quote text and metadata that actually exist in your indexed content, avoiding hallucinations.
          </p>
        </div>
      </div>
    </div>
  );
}
