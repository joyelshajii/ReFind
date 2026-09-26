"use client";

import { CheckCircle2, Loader2, FileText, Image as ImageIcon, Files, AlertCircle } from "lucide-react";
import { IndexProgressStatus } from "@/types";

interface IndexProgressProps {
  status: IndexProgressStatus;
}

const STAGES = ["Reading", "Extracting", "Understanding", "Indexing"];

export default function IndexProgress({ status }: IndexProgressProps) {
  const getStageIndex = (stage: string) => {
    return STAGES.indexOf(stage);
  };

  const currentStageIdx = getStageIndex(status.current_stage);
  const isComplete = status.current_stage.toLowerCase() === "complete";
  const isError = status.current_stage.toLowerCase() === "error";

  const percent = status.total_files > 0
    ? Math.min(100, Math.round((status.processed_files / status.total_files) * 100))
    : isComplete ? 100 : 0;

  return (
    <div
      data-grav-mass="1.2"
      className="w-full p-5 sm:p-6 rounded-2xl bg-black/50 border border-white/[0.08] backdrop-blur-xl shadow-[0_8px_32px_rgba(0,0,0,0.7)] flex flex-col gap-5"
    >
      {/* Header and Stage title */}
      <div className="flex items-center justify-between flex-wrap gap-2">
        <div className="flex items-center gap-2.5">
          {status.is_indexing ? (
            <Loader2 className="w-5 h-5 text-indigo-400 animate-spin shadow-[0_0_8px_rgba(99,102,241,0.5)]" />
          ) : isComplete ? (
            <CheckCircle2 className="w-5 h-5 text-emerald-400 shadow-[0_0_8px_rgba(16,185,129,0.4)]" />
          ) : isError ? (
            <AlertCircle className="w-5 h-5 text-red-400" />
          ) : (
            <Files className="w-5 h-5 text-zinc-400" />
          )}
          <h3 className="text-base sm:text-lg font-semibold text-zinc-100">
            {status.is_indexing
              ? "Indexing your digital memory..."
              : isComplete
              ? "Digital memory indexing complete"
              : isError
              ? "Indexing error encountered"
              : "Digital Memory Status"}
          </h3>
        </div>

        <div className="text-sm font-mono text-zinc-300">
          <span className="text-white font-semibold">{status.processed_files}</span> /{" "}
          <span>{status.total_files} files</span>
        </div>
      </div>

      {/* 4-Stage visual pipeline */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-2.5">
        {STAGES.map((stage, idx) => {
          const isActive = status.is_indexing && status.current_stage === stage;
          const isDone = isComplete || (status.is_indexing && currentStageIdx > idx);

          return (
            <div
              key={stage}
              className={`p-3.5 rounded-xl border flex flex-col gap-1.5 transition-all ${
                isActive
                  ? "bg-indigo-950/30 border-indigo-500/50 shadow-[0_0_15px_-3px_rgba(99,102,241,0.3)]"
                  : isDone
                  ? "bg-white/[0.03] border-emerald-500/30 text-emerald-300"
                  : "bg-black/30 border-white/[0.06] text-zinc-500"
              }`}
            >
              <div className="flex items-center justify-between">
                <span className="text-xs font-mono uppercase tracking-wider text-zinc-400 font-medium">
                  Stage 0{idx + 1}
                </span>
                {isActive ? (
                  <Loader2 className="w-4 h-4 text-indigo-400 animate-spin" />
                ) : isDone ? (
                  <CheckCircle2 className="w-4 h-4 text-emerald-400" />
                ) : null}
              </div>
              <span className={`text-sm font-semibold ${isActive ? "text-indigo-200" : isDone ? "text-zinc-200" : "text-zinc-500"}`}>
                {stage}
              </span>
            </div>
          );
        })}
      </div>

      {/* Progress Bar */}
      <div className="w-full flex flex-col gap-2">
        <div className="w-full h-2 rounded-full bg-white/[0.08] overflow-hidden">
          <div
            className={`h-full transition-all duration-300 ${
              isComplete
                ? "bg-emerald-400 shadow-[0_0_8px_#34d399]"
                : "bg-gradient-to-r from-indigo-500 to-indigo-400 shadow-[0_0_10px_rgba(99,102,241,0.6)]"
            }`}
            style={{ width: `${percent}%` }}
          />
        </div>
        {status.current_file && (
          <p className="text-xs sm:text-sm text-zinc-400 font-mono truncate">
            Processing: <span className="text-zinc-200">{status.current_file}</span>
          </p>
        )}
      </div>

      {/* Useful Statistics Breakdown */}
      <div className="pt-3.5 border-t border-white/[0.08] grid grid-cols-3 gap-3 text-center">
        <div className="p-3.5 rounded-xl bg-white/[0.02] border border-white/[0.06] flex flex-col items-center">
          <span className="text-sm text-zinc-300 flex items-center gap-1.5 font-mono font-medium">
            <FileText className="w-4 h-4 text-indigo-400" />
            Documents
          </span>
          <span className="text-lg sm:text-xl font-bold text-white mt-1">
            {status.documents_count}
          </span>
        </div>

        <div className="p-3.5 rounded-xl bg-white/[0.02] border border-white/[0.06] flex flex-col items-center">
          <span className="text-sm text-zinc-300 flex items-center gap-1.5 font-mono font-medium">
            <ImageIcon className="w-4 h-4 text-emerald-400" />
            Images
          </span>
          <span className="text-lg sm:text-xl font-bold text-white mt-1">
            {status.images_count}
          </span>
        </div>

        <div className="p-3.5 rounded-xl bg-white/[0.02] border border-white/[0.06] flex flex-col items-center">
          <span className="text-sm text-zinc-300 flex items-center gap-1.5 font-mono font-medium">
            <Files className="w-4 h-4 text-zinc-400" />
            Other
          </span>
          <span className="text-lg sm:text-xl font-bold text-white mt-1">
            {status.other_count}
          </span>
        </div>
      </div>

      {status.error_message && (
        <div className="p-3.5 rounded-xl bg-red-950/30 border border-red-800/40 text-sm text-red-200">
          {status.error_message}
        </div>
      )}
    </div>
  );
}
