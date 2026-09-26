"use client";

import { useEffect, useState, Suspense } from "react";
import { useSearchParams } from "next/navigation";
import Link from "next/link";
import { Search, Filter, AlertCircle, ArrowLeft } from "lucide-react";
import SearchBar from "@/components/SearchBar";
import ResultCard from "@/components/ResultCard";
import ContextModal from "@/components/ContextModal";
import { searchDocuments } from "@/lib/api";
import { SearchResponse, SearchResultItem } from "@/types";

function SearchResultsContent() {
  const searchParams = useSearchParams();
  const initialQuery = searchParams.get("q") || "";

  const [currentQuery, setCurrentQuery] = useState(initialQuery);
  const [response, setResponse] = useState<SearchResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [selectedResultForContext, setSelectedResultForContext] = useState<SearchResultItem | null>(null);

  const performSearch = async (queryText: string) => {
    if (!queryText.trim()) return;
    setLoading(true);
    setError(null);
    try {
      const data = await searchDocuments(queryText);
      setResponse(data);
    } catch (err: any) {
      console.error("Search failed:", err);
      setError(err.message || "Search failed to execute");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (initialQuery) {
      setCurrentQuery(initialQuery);
      performSearch(initialQuery);
    }
  }, [initialQuery]);

  return (
    <div className="max-w-4xl mx-auto px-4 py-8 space-y-6">
      {/* Top Search Bar & Back button */}
      <div className="space-y-4" data-grav-mass="1.3">
        <div className="flex items-center justify-between">
          <Link
            href="/"
            className="inline-flex items-center gap-2 text-sm text-zinc-300 hover:text-white transition-colors"
          >
            <ArrowLeft className="w-4 h-4" />
            <span>Back to Home</span>
          </Link>

          <span className="text-xs font-mono text-zinc-400 font-medium">
            ReFind Hybrid Retriever v0.1
          </span>
        </div>

        <SearchBar
          initialQuery={currentQuery}
          onSearch={(q) => {
            setCurrentQuery(q);
            performSearch(q);
          }}
          isLoading={loading}
        />
      </div>

      {/* Loading state with subtle progressive memory stages */}
      {loading && (
        <div className="p-8 rounded-2xl bg-black/50 border border-white/[0.08] backdrop-blur-xl flex flex-col items-center justify-center gap-3.5 text-center shadow-[0_8px_32px_rgba(0,0,0,0.6)]">
          <div className="w-7 h-7 border-2 border-indigo-500 border-t-transparent rounded-full animate-spin shadow-[0_0_12px_rgba(99,102,241,0.5)]" />
          <div className="space-y-1.5">
            <p className="text-base font-semibold text-zinc-100">Understanding your memory...</p>
            <p className="text-sm text-zinc-300 font-mono">
              Decomposing query clues → Searching indexed content → Ranking matches
            </p>
          </div>
        </div>
      )}

      {/* Error state */}
      {error && !loading && (
        <div className="p-4 rounded-xl bg-red-950/30 border border-red-800/40 text-sm text-red-200 backdrop-blur-md flex items-center gap-2.5">
          <AlertCircle className="w-5 h-5 text-red-400 shrink-0" />
          <span>{error}</span>
        </div>
      )}

      {/* Results view */}
      {response && !loading && (
        <div className="space-y-6">
          {/* Header & Clues pill breakdown */}
          <div className="flex flex-col gap-3.5 pb-4 border-b border-white/[0.08]">
            <div className="flex items-center justify-between flex-wrap gap-2">
              <div>
                <h2 className="text-xl sm:text-2xl font-semibold text-white">Search results</h2>
                <p className="text-sm text-zinc-300 font-mono mt-1">
                  <strong className="text-white font-semibold">{response.total_results}</strong> relevant{" "}
                  {response.total_results === 1 ? "result" : "results"} found in{" "}
                  <span className="text-indigo-300 font-semibold">{response.processing_time_ms}ms</span>
                </p>
              </div>

              <div className="text-xs sm:text-sm text-zinc-400 font-mono font-medium">
                Multimodal Hybrid Ranking
              </div>
            </div>

            {/* Inferred Clues Badges */}
            <div className="flex items-center gap-2 flex-wrap pt-1">
              <span className="text-xs sm:text-sm font-mono text-zinc-300 flex items-center gap-1.5 mr-1 font-medium">
                <Filter className="w-3.5 h-3.5 text-indigo-400" />
                Detected Clues:
              </span>
              {response.clues.file_type && (
                <span className="px-3 py-1 rounded-lg bg-white/[0.04] border border-white/[0.1] text-zinc-200 text-xs sm:text-sm font-mono">
                  Format: <strong className="text-indigo-400 uppercase font-semibold">{response.clues.file_type}</strong>
                </span>
              )}
              {response.clues.people.map((p, i) => (
                <span key={i} className="px-3 py-1 rounded-lg bg-white/[0.04] border border-white/[0.1] text-zinc-200 text-xs sm:text-sm font-mono">
                  Person: <strong className="text-indigo-400 font-semibold">{p}</strong>
                </span>
              ))}
              {response.clues.time_clues.map((t, i) => (
                <span key={i} className="px-3 py-1 rounded-lg bg-white/[0.04] border border-white/[0.1] text-zinc-200 text-xs sm:text-sm font-mono">
                  Time: <strong className="text-indigo-400 font-semibold">{t}</strong>
                </span>
              ))}
              {response.clues.technologies.map((tech, i) => (
                <span key={i} className="px-3 py-1 rounded-lg bg-white/[0.04] border border-white/[0.1] text-zinc-200 text-xs sm:text-sm font-mono">
                  Tech: <strong className="text-indigo-400 font-semibold">{tech}</strong>
                </span>
              ))}
              {response.clues.topics.map((top, i) => (
                <span key={i} className="px-3 py-1 rounded-lg bg-white/[0.04] border border-white/[0.1] text-zinc-200 text-xs sm:text-sm font-mono">
                  Topic: <strong className="text-indigo-400 font-semibold">{top}</strong>
                </span>
              ))}
            </div>
          </div>

          {/* Results List */}
          {response.results.length > 0 ? (
            <div className="space-y-4">
              {response.results.map((item, index) => (
                <ResultCard
                  key={item.document_id}
                  result={item}
                  rank={index + 1}
                  isBestMatch={index === 0}
                  onShowContext={(r) => setSelectedResultForContext(r)}
                />
              ))}
            </div>
          ) : (
            /* Empty State matching specifications */
            <div className="p-10 rounded-2xl bg-black/40 border border-white/[0.08] backdrop-blur-xl text-center space-y-4">
              <div className="w-12 h-12 rounded-xl bg-white/[0.04] border border-white/[0.1] text-zinc-300 flex items-center justify-center mx-auto">
                <Search className="w-6 h-6" />
              </div>
              <div className="space-y-1.5">
                <h3 className="text-lg font-semibold text-zinc-100">
                  We couldn't find a strong match.
                </h3>
                <p className="text-sm text-zinc-400 max-w-md mx-auto">
                  Try adjusting the clues in your memory or removing strict constraints.
                </p>
              </div>

              {/* Suggestions */}
              <div className="pt-2 text-left max-w-md mx-auto p-5 rounded-xl bg-black/60 border border-white/[0.08] space-y-2.5 text-sm text-zinc-300">
                <span className="font-semibold text-zinc-200">Suggestions:</span>
                <ul className="space-y-1.5 list-disc list-inside text-zinc-300">
                  <li>Try another memory or rephrase the query</li>
                  <li>Remove a date clue if not certain of the month</li>
                  <li>Try describing what the file contained</li>
                  <li>Search without specifying the exact file type</li>
                </ul>
              </div>
            </div>
          )}
        </div>
      )}

      {/* Signature Show Context Modal */}
      {selectedResultForContext && (
        <ContextModal
          result={selectedResultForContext}
          query={currentQuery}
          onClose={() => setSelectedResultForContext(null)}
        />
      )}
    </div>
  );
}

export default function SearchPage() {
  return (
    <Suspense
      fallback={
        <div className="p-12 text-center text-xs text-zinc-500 font-mono">
          Loading digital memory results...
        </div>
      }
    >
      <SearchResultsContent />
    </Suspense>
  );
}
