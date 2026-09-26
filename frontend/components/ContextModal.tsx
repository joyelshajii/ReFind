"use client";

import { useEffect, useState } from "react";
import { X, CheckCircle2, ShieldCheck, Sparkles, MapPin, FileText } from "lucide-react";
import { SearchResultItem, ContextDetailResponse } from "@/types";
import { getDocumentContext } from "@/lib/api";

interface ContextModalProps {
  result: SearchResultItem | null;
  query: string;
  onClose: () => void;
}

export default function ContextModal({ result, query, onClose }: ContextModalProps) {
  const [contextData, setContextData] = useState<ContextDetailResponse | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!result) return;
    setLoading(true);
    getDocumentContext(result.document_id, query, result.score, result.score_label)
      .then((data) => setContextData(data))
      .catch((err) => {
        console.error("Context fetch error:", err);
        // Fallback to result data
        setContextData({
          document_id: result.document_id,
          filename: result.filename,
          file_type: result.file_type,
          score: result.score,
          score_label: result.score_label,
          memory_clues: result.matching_clues.map((c) => `Clue: ${c}`),
          document_evidence: result.evidence,
          snippets: [result.snippet],
        });
      })
      .finally(() => setLoading(false));
  }, [result, query]);

  if (!result) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/85 backdrop-blur-md animate-in fade-in duration-200">
      <div
        data-grav-mass="2.0"
        className="w-full max-w-3xl max-h-[90vh] flex flex-col rounded-2xl bg-black/80 border border-white/[0.12] shadow-[0_16px_50px_rgba(0,0,0,0.9),0_0_40px_-10px_rgba(99,102,241,0.25)] overflow-hidden backdrop-blur-2xl"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="px-6 py-5 border-b border-white/[0.08] flex items-center justify-between bg-black/40">
          <div className="flex items-center gap-3.5">
            <div className="p-2.5 rounded-xl bg-indigo-950/40 border border-indigo-500/30 text-indigo-400 shadow-[0_0_12px_rgba(99,102,241,0.2)]">
              <Sparkles className="w-5 h-5" />
            </div>
            <div>
              <div className="flex items-center gap-2.5">
                <h2 className="text-lg sm:text-xl font-semibold text-zinc-100">
                  Why ReFind found this
                </h2>
                <span className="px-3 py-1 rounded-full text-xs sm:text-sm font-mono font-semibold bg-indigo-950/60 text-indigo-300 border border-indigo-500/40">
                  {result.score_label}
                </span>
              </div>
              <p className="text-sm text-zinc-300 font-mono mt-1 truncate max-w-md">
                {result.filename}
              </p>
            </div>
          </div>

          <button
            onClick={onClose}
            className="p-2 rounded-xl text-zinc-400 hover:text-white hover:bg-white/[0.08] transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Content Body */}
        <div className="flex-1 overflow-y-auto p-6 space-y-6">
          {loading ? (
            <div className="flex flex-col items-center justify-center py-16 gap-3 text-zinc-400">
              <span className="w-7 h-7 border-2 border-indigo-500 border-t-transparent rounded-full animate-spin shadow-[0_0_12px_rgba(99,102,241,0.5)]" />
              <span className="text-sm font-mono">Correlating memory clues with indexed evidence...</span>
            </div>
          ) : (
            <>
              {/* Context Breakdown Grid */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {/* Column 1: Your Memory */}
                <div className="p-5 rounded-xl bg-white/[0.02] border border-white/[0.08] flex flex-col gap-3">
                  <div className="flex items-center justify-between border-b border-white/[0.06] pb-2.5">
                    <span className="text-sm font-semibold text-zinc-200 uppercase tracking-wider font-mono">
                      Your Memory
                    </span>
                    <span className="text-xs text-zinc-400 font-mono">Input Clues</span>
                  </div>

                  <div className="space-y-2">
                    {contextData?.memory_clues && contextData.memory_clues.length > 0 ? (
                      contextData.memory_clues.map((clue, idx) => (
                        <div
                          key={idx}
                          className="p-3 rounded-lg bg-black/40 border border-white/[0.06] text-sm text-zinc-200 flex items-center gap-2.5"
                        >
                          <span className="w-2 h-2 rounded-full bg-indigo-400 shadow-[0_0_6px_#818cf8]" />
                          <span className="font-medium">{clue}</span>
                        </div>
                      ))
                    ) : (
                      <p className="text-sm text-zinc-400">Query parsed: {query}</p>
                    )}
                  </div>
                </div>

                {/* Column 2: Document Evidence */}
                <div className="p-5 rounded-xl bg-indigo-950/15 border border-indigo-500/25 flex flex-col gap-3">
                  <div className="flex items-center justify-between border-b border-indigo-500/20 pb-2.5">
                    <span className="text-sm font-semibold text-indigo-300 uppercase tracking-wider font-mono flex items-center gap-2">
                      <ShieldCheck className="w-4 h-4 text-indigo-400" />
                      Document Evidence
                    </span>
                    <span className="text-xs text-indigo-300 font-mono">Verified Match</span>
                  </div>

                  <div className="space-y-2.5">
                    {contextData?.document_evidence && contextData.document_evidence.length > 0 ? (
                      contextData.document_evidence.map((ev, idx) => (
                        <div
                          key={idx}
                          className="p-3 rounded-lg bg-black/50 border border-indigo-500/20 text-sm flex flex-col gap-1.5"
                        >
                          <div className="flex items-center justify-between">
                            <span className="font-semibold text-emerald-400 flex items-center gap-1.5">
                              <CheckCircle2 className="w-4 h-4" />
                              {ev.clue_name}
                            </span>
                            {ev.location && (
                              <span className="text-xs font-mono text-zinc-400 flex items-center gap-1">
                                <MapPin className="w-3.5 h-3.5 text-zinc-500" />
                                {ev.location}
                              </span>
                            )}
                          </div>
                          <p className="text-zinc-200 text-sm leading-relaxed">
                            {ev.matched_text}
                          </p>
                        </div>
                      ))
                    ) : (
                      <p className="text-sm text-zinc-400">No verified evidence found.</p>
                    )}
                  </div>
                </div>
              </div>

              {/* Verified Content Snippets */}
              {contextData?.snippets && contextData.snippets.length > 0 && (
                <div className="space-y-3">
                  <div className="flex items-center gap-2">
                    <FileText className="w-4 h-4 text-zinc-400" />
                    <h3 className="text-sm font-semibold uppercase tracking-wider text-zinc-200 font-mono">
                      Relevant Content Quotes
                    </h3>
                  </div>

                  <div className="space-y-2.5">
                    {contextData.snippets.map((snip, idx) => (
                      <div
                        key={idx}
                        className="p-4 rounded-xl bg-black/60 border border-white/[0.08] text-sm text-zinc-200 font-mono leading-relaxed"
                      >
                        {snip}
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Grounded AI Match Explanation */}
              {contextData?.ai_explanation && (
                <div className="p-4 sm:p-5 rounded-xl bg-indigo-950/25 border border-indigo-500/30 flex items-start gap-3.5 text-sm text-indigo-100">
                  <Sparkles className="w-5 h-5 text-indigo-400 shrink-0 mt-0.5" />
                  <div>
                    <span className="font-semibold text-indigo-300 font-mono text-xs uppercase tracking-wider block mb-1">
                      AI Match Explanation (Grounded)
                    </span>
                    <p className="leading-relaxed font-sans text-sm sm:text-base">{contextData.ai_explanation}</p>
                  </div>
                </div>
              )}

              {/* Grounded Guarantee */}
              <div className="p-4 rounded-xl bg-white/[0.02] border border-white/[0.06] flex items-center gap-3 text-sm text-zinc-300">
                <ShieldCheck className="w-5 h-5 text-indigo-400 shrink-0" />
                <span>
                  ReFind guarantees that every match factor shown is grounded in actual extracted content,
                  timestamps, or filesystem metadata. No hallucinated evidence.
                </span>
              </div>
            </>
          )}
        </div>

        {/* Footer */}
        <div className="px-6 py-4 border-t border-white/[0.08] bg-black/40 flex items-center justify-between">
          <div className="text-xs sm:text-sm text-zinc-400 font-mono">
            Hybrid Relevance Score: <strong className="text-zinc-200">{Math.round(result.score * 100)}%</strong>
          </div>
          <button
            onClick={onClose}
            className="px-5 py-2 rounded-xl bg-white/[0.08] hover:bg-white/[0.16] text-sm font-medium text-white border border-white/[0.12] transition-colors"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  );
}
