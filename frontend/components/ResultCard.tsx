"use client";

import {
  FileText,
  FileCode,
  Image as ImageIcon,
  Presentation,
  Check,
  Calendar,
  Layers,
  Sparkles,
  Download,
  Info
} from "lucide-react";
import { SearchResultItem } from "@/types";
import { getDocumentDownloadUrl } from "@/lib/api";

interface ResultCardProps {
  result: SearchResultItem;
  rank: number;
  isBestMatch?: boolean;
  onShowContext: (result: SearchResultItem) => void;
}

export default function ResultCard({
  result,
  rank,
  isBestMatch = false,
  onShowContext,
}: ResultCardProps) {
  const getFileIcon = (type: string) => {
    switch (type.toLowerCase()) {
      case "pdf":
        return <FileText className="w-5 h-5 text-red-400/90" />;
      case "docx":
      case "doc":
        return <FileText className="w-5 h-5 text-blue-400/90" />;
      case "pptx":
      case "ppt":
        return <Presentation className="w-5 h-5 text-amber-400/90" />;
      case "png":
      case "jpg":
      case "jpeg":
      case "webp":
      case "gif":
      case "bmp":
      case "tiff":
      case "heic":
      case "heif":
        return <ImageIcon className="w-5 h-5 text-emerald-400/90" />;
      default:
        return <FileCode className="w-5 h-5 text-zinc-400" />;
    }
  };

  const formatFileSize = (bytes: number) => {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  };

  const formatDate = (dateStr: string) => {
    try {
      const d = new Date(dateStr);
      return d.toLocaleDateString("en-US", {
        month: "short",
        day: "numeric",
        year: "numeric",
      });
    } catch {
      return dateStr;
    }
  };

  const matchPercentage = Math.round(result.score * 100);

  return (
    <div
      data-grav-mass={isBestMatch ? "1.4" : "1.0"}
      className={`group relative rounded-2xl transition-all duration-300 border backdrop-blur-xl ${
        isBestMatch
          ? "bg-black/60 border-indigo-500/40 shadow-[0_8px_32px_rgba(0,0,0,0.8),0_0_25px_-5px_rgba(99,102,241,0.2)] hover:border-indigo-400/60"
          : "bg-black/40 hover:bg-black/60 border-white/[0.07] hover:border-white/[0.18] shadow-[0_8px_24px_rgba(0,0,0,0.6)]"
      }`}
    >
      {/* Top Best Match Ribbon if #1 */}
      {isBestMatch && (
        <div className="absolute -top-3.5 left-4 px-3 py-1 rounded-full bg-gradient-to-r from-indigo-950 via-zinc-900 to-indigo-950 border border-indigo-500/40 text-indigo-300 text-xs font-mono tracking-wider uppercase shadow-[0_0_15px_-2px_rgba(99,102,241,0.4)] flex items-center gap-1.5 font-semibold">
          <Sparkles className="w-3.5 h-3.5 text-indigo-400" />
          <span>Best Match</span>
        </div>
      )}

      <div className="p-5 sm:p-6 flex flex-col gap-4">
        {/* Header: Title, Format Badge, Score */}
        <div className="flex items-start justify-between gap-4">
          <div className="flex items-start gap-3.5 min-w-0">
            <div className="p-2.5 rounded-xl bg-white/[0.04] border border-white/[0.08] group-hover:border-white/[0.15] shrink-0 transition-colors">
              {getFileIcon(result.file_type)}
            </div>

            <div className="flex flex-col min-w-0">
              <div className="flex items-center gap-2.5 flex-wrap">
                <h3 className="text-lg sm:text-xl font-semibold text-zinc-100 truncate group-hover:text-white transition-colors">
                  {result.filename}
                </h3>
                <span className="uppercase text-xs font-mono font-medium px-2.5 py-0.5 rounded bg-white/[0.06] text-zinc-200 border border-white/[0.1]">
                  {result.file_type}
                </span>
                {result.page_or_slide && (
                  <span className="text-xs font-medium text-zinc-300 bg-white/[0.04] border border-white/[0.08] px-2.5 py-0.5 rounded">
                    {result.page_or_slide}
                  </span>
                )}
              </div>

              {/* Metadata row */}
              <div className="flex items-center gap-3 text-sm text-zinc-300 mt-2 flex-wrap font-mono">
                <span className="flex items-center gap-1.5">
                  <Calendar className="w-4 h-4 text-zinc-400" />
                  {formatDate(result.modified_at)}
                </span>
                <span className="text-zinc-600">•</span>
                <span>{formatFileSize(result.file_size)}</span>
                <span className="text-zinc-600">•</span>
                <span className="truncate max-w-[240px] text-zinc-400" title={result.filepath}>
                  {result.filepath}
                </span>
              </div>
            </div>
          </div>

          {/* Match Score Badge */}
          <div className="flex flex-col items-end shrink-0">
            <div
              className={`flex items-center gap-2 px-3.5 py-1.5 rounded-full text-sm font-mono font-semibold border backdrop-blur-md ${
                result.score >= 0.7
                  ? "bg-indigo-950/40 text-indigo-300 border-indigo-500/40 shadow-[0_0_12px_rgba(99,102,241,0.2)]"
                  : result.score >= 0.5
                  ? "bg-emerald-950/40 text-emerald-300 border-emerald-500/40 shadow-[0_0_12px_rgba(16,185,129,0.15)]"
                  : "bg-white/[0.04] text-zinc-200 border-white/[0.1]"
              }`}
            >
              <span className="w-2 h-2 rounded-full bg-current shadow-[0_0_6px_currentColor]" />
              <span>{matchPercentage}% match</span>
            </div>
            <span className="text-xs text-zinc-400 mt-1 font-mono tracking-wider uppercase font-medium">
              {result.score_label}
            </span>
          </div>
        </div>

        {/* Snippet */}
        <div className="text-base text-zinc-200 bg-black/40 p-4 rounded-xl border border-white/[0.08] leading-relaxed font-sans">
          <p className="line-clamp-2">{result.snippet}</p>
        </div>

        {/* AI Grounded Explanation if present */}
        {result.ai_explanation && (
          <div className="flex items-start gap-3 p-3.5 rounded-xl bg-indigo-950/30 border border-indigo-500/25 text-sm text-indigo-100 leading-relaxed font-sans">
            <Sparkles className="w-4 h-4 text-indigo-400 shrink-0 mt-0.5" />
            <div>
              <span className="font-semibold text-indigo-300 font-mono text-xs uppercase tracking-wider block mb-1">
                Why this matched
              </span>
              <p>{result.ai_explanation}</p>
            </div>
          </div>
        )}

        {/* Matching Clues Checklist */}
        {result.matching_clues && result.matching_clues.length > 0 && (
          <div className="flex flex-col gap-2">
            <span className="text-xs font-mono uppercase tracking-wider text-zinc-400 font-medium">
              Matching memory clues:
            </span>
            <div className="flex flex-wrap items-center gap-2">
              {result.matching_clues.map((clue, idx) => (
                <span
                  key={idx}
                  className="inline-flex items-center gap-1.5 px-3 py-1 rounded-lg bg-emerald-950/30 text-emerald-300 border border-emerald-500/35 text-xs sm:text-sm font-mono font-medium"
                >
                  <Check className="w-3.5 h-3.5 text-emerald-400" />
                  {clue}
                </span>
              ))}
            </div>
          </div>
        )}

        {/* Detected Entities */}
        {result.detected_entities && result.detected_entities.length > 0 && (
          <div className="flex items-center gap-2 flex-wrap text-sm text-zinc-300">
            <span className="text-xs font-mono uppercase tracking-wider text-zinc-400 flex items-center gap-1.5 font-medium">
              <Layers className="w-3.5 h-3.5" />
              Entities:
            </span>
            {result.detected_entities.map((ent, idx) => (
              <span
                key={idx}
                className="px-2.5 py-1 rounded-md bg-white/[0.04] text-zinc-200 font-mono text-xs sm:text-sm border border-white/[0.08]"
              >
                {ent}
              </span>
            ))}
          </div>
        )}

        {/* Footer Actions */}
        <div className="pt-3 border-t border-white/[0.08] flex items-center justify-between gap-3">
          <div className="text-xs sm:text-sm text-zinc-400 font-mono">
            ID: {result.document_id.slice(0, 8)}
          </div>

          <div className="flex items-center gap-2.5">
            <a
              href={getDocumentDownloadUrl(result.document_id)}
              target="_blank"
              rel="noreferrer"
              className="flex items-center gap-2 px-4 py-2 rounded-xl bg-white/[0.05] hover:bg-white/[0.10] text-zinc-200 text-sm font-medium border border-white/[0.1] hover:border-white/[0.2] transition-all"
            >
              <Download className="w-4 h-4" />
              <span>Open File</span>
            </a>

            <button
              type="button"
              onClick={() => onShowContext(result)}
              className="flex items-center gap-2 px-4 py-2 rounded-xl bg-indigo-600/30 hover:bg-indigo-600/45 text-indigo-200 text-sm font-medium border border-indigo-500/40 hover:border-indigo-400/60 transition-all shadow-[0_0_15px_-3px_rgba(99,102,241,0.25)]"
            >
              <Info className="w-4 h-4" />
              <span>Show Context</span>
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
