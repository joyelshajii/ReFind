"use client";

import { useEffect, useState, useRef, ChangeEvent, DragEvent, useTransition } from "react";
import {
  FolderGit2,
  UploadCloud,
  Sparkles,
  RefreshCw,
  FolderOpen,
  CheckCircle2,
  HardDrive,
  FileText,
  FileCode,
  Image as ImageIcon,
  Presentation,
  Download,
  Trash2,
  Search,
  ExternalLink,
  Layers,
  Calendar,
  Clock,
  Filter,
  AlertTriangle
} from "lucide-react";
import IndexProgress from "@/components/IndexProgress";
import {
  getIndexStatus,
  triggerIndexing,
  uploadFiles,
  seedDemoData,
  getIndexedDocuments,
  deleteDocument,
  deleteAllDocuments,
  getDocumentDownloadUrl
} from "@/lib/api";
import { IndexProgressStatus, IndexedDocumentItem } from "@/types";

const SUPPORTED_FORMATS = ["PDF", "DOCX", "PPTX", "TXT", "PNG", "JPG", "JPEG", "WEBP", "GIF", "BMP", "TIFF", "HEIC", "HEIF"];

export default function IndexPage() {
  const [status, setStatus] = useState<IndexProgressStatus>({
    is_indexing: false,
    current_stage: "idle",
    total_files: 0,
    processed_files: 0,
    documents_count: 0,
    images_count: 0,
    other_count: 0,
  });

  const [folderPathInput, setFolderPathInput] = useState("");
  const [isUploading, setIsUploading] = useState(false);
  const [feedbackMessage, setFeedbackMessage] = useState<string | null>(null);
  const [dragActive, setDragActive] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  // Indexed files viewer state
  const [documents, setDocuments] = useState<IndexedDocumentItem[]>([]);
  const [isLoadingDocs, setIsLoadingDocs] = useState(false);
  const [docSearchQuery, setDocSearchQuery] = useState("");
  const [selectedFormat, setSelectedFormat] = useState("all");
  const [deletingId, setDeletingId] = useState<string | null>(null);
  const [isClearingIndex, setIsClearingIndex] = useState(false);
  const [backendConnected, setBackendConnected] = useState(true);

  // Fetch indexed documents list
  const loadDocuments = async () => {
    setIsLoadingDocs(true);
    try {
      const docs = await getIndexedDocuments(docSearchQuery, selectedFormat);
      setDocuments(docs);
      setBackendConnected(true);
    } catch (err) {
      setBackendConnected(false);
    } finally {
      setIsLoadingDocs(false);
    }
  };

  // Poll status while indexing is in progress
  useEffect(() => {
    const fetchStatus = () => {
      getIndexStatus()
        .then((data) => {
          setStatus(data);
          setBackendConnected(true);
          // If indexing has transitioned or completed, refresh documents list too
          if (!data.is_indexing && data.total_files > 0) {
            loadDocuments();
          }
        })
        .catch(() => {
          setBackendConnected(false);
        });
    };

    fetchStatus();
    loadDocuments();

    const interval = setInterval(fetchStatus, 3000);
    return () => clearInterval(interval);
  }, []);

  // Reload documents when filters change
  useEffect(() => {
    const timer = setTimeout(() => {
      loadDocuments();
    }, 250);
    return () => clearTimeout(timer);
  }, [docSearchQuery, selectedFormat]);

  const handleIndexFolder = async () => {
    try {
      setFeedbackMessage("Starting directory indexing...");
      const res = await triggerIndexing(folderPathInput.trim() || undefined);
      setFeedbackMessage(res.message);
      const updated = await getIndexStatus();
      setStatus(updated);
      loadDocuments();
    } catch (err: any) {
      setFeedbackMessage(err.message || "Failed to start indexing");
    }
  };

  const handleSeedDemo = async () => {
    try {
      setFeedbackMessage("Generating sample files & starting ingestion...");
      const res = await seedDemoData();
      setFeedbackMessage(res.message);
      const updated = await getIndexStatus();
      setStatus(updated);
      loadDocuments();
    } catch (err: any) {
      setFeedbackMessage(err.message || "Failed to seed demo data");
    }
  };

  const handleFileUpload = async (files: FileList | null) => {
    if (!files || files.length === 0) return;
    setIsUploading(true);
    setFeedbackMessage(`Uploading ${files.length} file(s)...`);

    try {
      const formData = new FormData();
      for (let i = 0; i < files.length; i++) {
        formData.append("files", files[i]);
      }
      const res = await uploadFiles(formData);
      setFeedbackMessage(res.message);
      // Refresh status and list
      const updated = await getIndexStatus();
      setStatus(updated);
      loadDocuments();
    } catch (err: any) {
      setFeedbackMessage(err.message || "Failed to upload files");
    } finally {
      setIsUploading(false);
    }
  };

  const handleDeleteDoc = async (id: string, name: string) => {
    if (!confirm(`Are you sure you want to remove "${name}" from indexed memory?`)) return;
    setDeletingId(id);
    try {
      await deleteDocument(id);
      setFeedbackMessage(`Removed "${name}" from index.`);
      const updated = await getIndexStatus();
      setStatus(updated);
      loadDocuments();
    } catch (err: any) {
      setFeedbackMessage(err.message || "Failed to delete document");
    } finally {
      setDeletingId(null);
    }
  };

  const handleClearIndex = async () => {
    if (documents.length === 0) {
      setFeedbackMessage("There are no indexed files to remove.");
      return;
    }
    if (!confirm(
      `Remove all ${documents.length} currently listed indexed files?\n\n` +
      "This clears them from ReFind's index but does not delete the original files."
    )) return;

    setIsClearingIndex(true);
    try {
      const res = await deleteAllDocuments();
      setDocuments([]);
      setFeedbackMessage(res.message);
      const updated = await getIndexStatus();
      setStatus(updated);
      await loadDocuments();
    } catch (err: any) {
      setFeedbackMessage(err.message || "Failed to clear indexed files");
    } finally {
      setIsClearingIndex(false);
    }
  };

  const handleDrop = (e: DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    setDragActive(false);
    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      handleFileUpload(e.dataTransfer.files);
    }
  };

  const getFileIcon = (type: string) => {
    switch (type.toLowerCase()) {
      case "pdf":
        return <FileText className="w-4 h-4 text-red-400/90" />;
      case "docx":
      case "doc":
        return <FileText className="w-4 h-4 text-blue-400/90" />;
      case "pptx":
      case "ppt":
        return <Presentation className="w-4 h-4 text-amber-400/90" />;
      case "png":
      case "jpg":
      case "jpeg":
      case "webp":
      case "gif":
      case "bmp":
      case "tiff":
      case "heic":
      case "heif":
        return <ImageIcon className="w-4 h-4 text-emerald-400/90" />;
      default:
        return <FileCode className="w-4 h-4 text-zinc-400" />;
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

  return (
    <div className="max-w-4xl mx-auto px-4 py-10 space-y-8">
      {/* Title Header */}
      <div className="space-y-2.5" data-grav-mass="1.2">
        <div className="inline-flex items-center gap-2 px-3.5 py-1.5 rounded-full bg-white/[0.04] border border-white/[0.1] backdrop-blur-md text-xs sm:text-sm text-indigo-400 font-mono font-medium">
          <HardDrive className="w-4 h-4" />
          Local Files Connector
        </div>
        <h1 className="text-2xl sm:text-3xl md:text-4xl font-bold tracking-tight text-white">
          Digital Memory Indexing
        </h1>
        <p className="text-base text-zinc-300">
          Index local files into the high-dimensional vector space and relational metadata store.
        </p>
      </div>

      {/* Main Live Progress Indicator */}
      <IndexProgress status={status} />

      {/* Indexing Actions Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Action 1: Select or Index Folder */}
        <div
          data-grav-mass="1.1"
          className="p-6 rounded-2xl bg-black/45 border border-white/[0.08] backdrop-blur-xl flex flex-col justify-between gap-5 hover:border-white/[0.16] transition-all shadow-[0_8px_32px_rgba(0,0,0,0.6)]"
        >
          <div className="space-y-3.5">
            <div className="flex items-center gap-2.5 text-zinc-100 font-semibold text-base">
              <FolderOpen className="w-4 h-4 text-indigo-400" />
              Index Local Directory
            </div>
            <p className="text-sm text-zinc-300 leading-relaxed">
              Scan a local folder on your computer. ReFind will recursively discover and index supported document and image formats.
            </p>

            <div className="space-y-2 pt-2">
              <label className="text-xs font-mono text-zinc-300 uppercase tracking-wider font-medium">
                Directory Path (optional, defaults to storage uploads):
              </label>
              <input
                type="text"
                value={folderPathInput}
                onChange={(e) => setFolderPathInput(e.target.value)}
                placeholder="e.g. C:\Users\YourName\Documents or leave blank"
                className="w-full px-4 py-2.5 rounded-xl bg-black/60 border border-white/[0.1] text-sm text-zinc-100 placeholder:text-zinc-500 focus:outline-none focus:border-indigo-400 font-mono transition-all"
              />
            </div>
          </div>

          <div className="flex items-center gap-2">
            <button
              onClick={handleIndexFolder}
              disabled={status.is_indexing}
              className="flex-1 flex items-center justify-center gap-2 px-5 py-2.5 rounded-xl bg-indigo-600/30 hover:bg-indigo-600/45 disabled:opacity-50 text-white text-sm font-medium border border-indigo-500/40 transition-all shadow-[0_0_15px_-3px_rgba(99,102,241,0.25)]"
            >
              <FolderGit2 className="w-4 h-4" />
              <span>{status.is_indexing ? "Indexing..." : "Scan & Index Folder"}</span>
            </button>
          </div>
        </div>

        {/* Action 2: Demo Quick-Seed */}
        <div
          data-grav-mass="1.1"
          className="p-6 rounded-2xl bg-black/45 border border-white/[0.08] backdrop-blur-xl flex flex-col justify-between gap-5 hover:border-white/[0.16] transition-all shadow-[0_8px_32px_rgba(0,0,0,0.6)]"
        >
          <div className="space-y-3.5">
            <div className="flex items-center gap-2.5 text-indigo-300 font-semibold text-base">
              <Sparkles className="w-4 h-4 text-indigo-400" />
              One-Click Demo Dataset (BitByBit)
            </div>
            <p className="text-sm text-zinc-300 leading-relaxed">
              Generate the canonical hackathon test set with messy, realistic filenames (
              <code className="text-indigo-300 font-mono">final2.pdf</code>,{" "}
              <code className="text-indigo-300 font-mono">IMG_2384.png</code>,{" "}
              <code className="text-indigo-300 font-mono">presentation2.pptx</code>) and immediately feed them to the indexer.
            </p>

            <div className="p-4 rounded-xl bg-black/60 border border-white/[0.08] text-xs sm:text-sm text-zinc-300 space-y-1.5">
              <strong className="text-indigo-300 block font-mono font-medium">Demonstration Scenario:</strong>
              <p className="italic text-zinc-300">
                “Find the architecture PDF Rahul sent me around February. It had PostgreSQL and BLE.”
              </p>
            </div>
          </div>

          <button
            onClick={handleSeedDemo}
            disabled={status.is_indexing}
            className="w-full flex items-center justify-center gap-2 px-5 py-2.5 rounded-xl bg-white/[0.05] hover:bg-white/[0.10] text-white text-sm font-medium border border-white/[0.1] hover:border-white/[0.2] transition-all"
          >
            <RefreshCw className={`w-4 h-4 ${status.is_indexing ? "animate-spin" : ""}`} />
            <span>Seed Demo Memory & Ingest</span>
          </button>
        </div>
      </div>

      {/* Drag & Drop File Ingestion Zone */}
      <div
        data-grav-mass="1.0"
        onDragOver={(e) => {
          e.preventDefault();
          setDragActive(true);
        }}
        onDragLeave={() => setDragActive(false)}
        onDrop={handleDrop}
        onClick={() => fileInputRef.current?.click()}
        className={`p-8 sm:p-10 rounded-2xl border-2 border-dashed cursor-pointer transition-all flex flex-col items-center justify-center gap-3.5 text-center backdrop-blur-md ${
          dragActive
            ? "border-indigo-400/80 bg-indigo-950/20 shadow-[0_0_30px_rgba(99,102,241,0.2)]"
            : "border-white/[0.12] hover:border-white/[0.24] bg-black/40 hover:bg-black/60"
        }`}
      >
        <input
          ref={fileInputRef}
          type="file"
          multiple
          className="hidden"
          onChange={(e: ChangeEvent<HTMLInputElement>) => handleFileUpload(e.target.files)}
        />
        <div className="w-14 h-14 rounded-2xl bg-white/[0.05] border border-white/[0.1] flex items-center justify-center text-indigo-400 shadow-[0_0_15px_-3px_rgba(99,102,241,0.2)]">
          <UploadCloud className="w-7 h-7" />
        </div>
        <div className="space-y-1">
          <p className="text-base sm:text-lg font-semibold text-zinc-100">
            {isUploading ? "Uploading & indexing..." : "Drag and drop local files here"}
          </p>
          <p className="text-sm text-zinc-400">
            or click to browse from your filesystem
          </p>
        </div>

        {/* Supported Formats Pills */}
        <div className="flex items-center gap-2 flex-wrap justify-center pt-2">
          <span className="text-xs text-zinc-400 uppercase tracking-wider font-mono mr-1 font-medium">
            Supported:
          </span>
          {SUPPORTED_FORMATS.map((fmt) => (
            <span
              key={fmt}
              className="px-2.5 py-1 rounded-md bg-white/[0.04] border border-white/[0.08] text-xs font-mono text-zinc-300"
            >
              {fmt}
            </span>
          ))}
        </div>
      </div>

      {feedbackMessage && (
        <div className="p-4 rounded-xl bg-black/60 border border-white/[0.1] backdrop-blur-md text-sm text-zinc-200 font-mono flex items-center justify-between gap-3">
          <div className="flex items-center gap-2.5">
            <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0" />
            <span>{feedbackMessage}</span>
          </div>
          <button
            onClick={() => setFeedbackMessage(null)}
            className="text-zinc-400 hover:text-white text-sm"
          >
            ✕
          </button>
        </div>
      )}

      {!backendConnected && (
        <div className="p-4 rounded-xl bg-amber-950/20 border border-amber-500/20 backdrop-blur-md text-sm text-amber-200 font-mono flex items-center gap-3">
          <AlertTriangle className="w-5 h-5 text-amber-400 shrink-0" />
          <span>Backend server at <code className="text-white font-semibold">http://localhost:8000</code> is currently unreachable. Make sure the FastAPI backend is running.</span>
        </div>
      )}

      {/* NEW: Indexed Documents Explorer Panel */}
      <div
        data-grav-mass="1.3"
        className="p-6 rounded-2xl bg-black/50 border border-white/[0.08] backdrop-blur-xl shadow-[0_8px_32px_rgba(0,0,0,0.7)] space-y-5"
      >
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-white/[0.08] pb-4">
          <div>
            <div className="flex items-center gap-2.5">
              <h2 className="text-lg font-semibold text-white">Indexed Memory Store</h2>
              <span className="px-2.5 py-0.5 rounded-full text-xs font-mono bg-white/[0.06] text-indigo-300 border border-white/[0.1] font-medium">
                {documents.length} files
              </span>
            </div>
            <p className="text-sm text-zinc-300 mt-1">
              Browse, search, inspect chunks & entities, or download indexed files.
            </p>
          </div>

          <div className="self-start sm:self-auto flex items-center gap-2">
            <button
              onClick={loadDocuments}
              disabled={isLoadingDocs || isClearingIndex}
              className="flex items-center gap-1.5 px-3.5 py-2 rounded-xl bg-white/[0.05] hover:bg-white/[0.10] text-sm font-mono text-zinc-200 border border-white/[0.1] transition-all disabled:opacity-50"
              title="Refresh files list"
            >
              <RefreshCw className={`w-4 h-4 ${isLoadingDocs ? "animate-spin" : ""}`} />
              <span>Refresh</span>
            </button>
            <button
              onClick={handleClearIndex}
              disabled={isLoadingDocs || isClearingIndex || documents.length === 0}
              className="flex items-center gap-1.5 px-3.5 py-2 rounded-xl bg-red-950/30 hover:bg-red-950/50 text-sm font-mono text-red-300 border border-red-800/40 transition-all disabled:opacity-50"
              title="Remove all indexed files without deleting originals"
            >
              <Trash2 className={`w-4 h-4 ${isClearingIndex ? "animate-pulse" : ""}`} />
              <span>{isClearingIndex ? "Clearing..." : "Clear Index"}</span>
            </button>
          </div>
        </div>

        {/* Filter & Search Bar for Files */}
        <div className="flex flex-col sm:flex-row items-center gap-3">
          <div className="relative flex-1 w-full">
            <Search className="w-4 h-4 text-zinc-400 absolute left-3.5 top-1/2 -translate-y-1/2" />
            <input
              type="text"
              value={docSearchQuery}
              onChange={(e) => setDocSearchQuery(e.target.value)}
              placeholder="Filter by filename..."
              className="w-full pl-10 pr-4 py-2.5 rounded-xl bg-black/60 border border-white/[0.1] text-sm text-zinc-100 placeholder:text-zinc-500 focus:outline-none focus:border-indigo-400 font-mono transition-all"
            />
          </div>

          <div className="flex items-center gap-1.5 w-full sm:w-auto overflow-x-auto pb-1 sm:pb-0">
            {["all", "pdf", "docx", "pptx", "png", "jpg", "webp", "gif", "bmp", "tiff", "txt"].map((fmt) => (
              <button
                key={fmt}
                onClick={() => setSelectedFormat(fmt)}
                className={`px-3 py-1.5 rounded-lg text-xs font-mono uppercase tracking-wider transition-all border font-medium ${
                  selectedFormat === fmt
                    ? "bg-indigo-600/30 text-indigo-200 border-indigo-500/45 shadow-[0_0_10px_rgba(99,102,241,0.2)]"
                    : "bg-white/[0.02] text-zinc-300 hover:text-white border-white/[0.06] hover:border-white/[0.14]"
                }`}
              >
                {fmt}
              </button>
            ))}
          </div>
        </div>

        {/* Files Grid / List */}
        {isLoadingDocs && documents.length === 0 ? (
          <div className="p-8 text-center text-sm text-zinc-400 font-mono flex items-center justify-center gap-2.5">
            <RefreshCw className="w-4 h-4 animate-spin text-indigo-400" />
            <span>Loading indexed files...</span>
          </div>
        ) : documents.length > 0 ? (
          <div className="space-y-3 max-h-[500px] overflow-y-auto pr-1">
            {documents.map((doc) => (
              <div
                key={doc.id}
                className="p-4 rounded-xl bg-white/[0.02] hover:bg-white/[0.05] border border-white/[0.06] hover:border-white/[0.14] transition-all flex flex-col sm:flex-row sm:items-center justify-between gap-3.5"
              >
                <div className="flex items-start gap-3.5 min-w-0">
                  <div className="p-2.5 rounded-lg bg-black/40 border border-white/[0.08] shrink-0 mt-0.5 sm:mt-0">
                    {getFileIcon(doc.file_type)}
                  </div>

                  <div className="flex flex-col min-w-0 space-y-1.5">
                    <div className="flex items-center gap-2 flex-wrap">
                      <span className="font-semibold text-sm sm:text-base text-zinc-100 truncate">
                        {doc.filename}
                      </span>
                      <span className="text-xs uppercase font-mono px-2.5 py-0.5 rounded bg-white/[0.06] text-zinc-200 border border-white/[0.1] font-medium">
                        {doc.file_type}
                      </span>
                      <span className="text-xs font-mono text-indigo-300 bg-indigo-950/40 border border-indigo-500/30 px-2.5 py-0.5 rounded font-medium">
                        {doc.chunk_count} chunk{doc.chunk_count !== 1 ? "s" : ""}
                      </span>
                    </div>

                    <div className="flex items-center gap-3 text-xs sm:text-sm text-zinc-300 font-mono flex-wrap">
                      <span className="flex items-center gap-1.5">
                        <Calendar className="w-3.5 h-3.5 text-zinc-400" />
                        {formatDate(doc.modified_at)}
                      </span>
                      <span className="text-zinc-600">•</span>
                      <span>{formatFileSize(doc.file_size)}</span>
                      <span className="text-zinc-600">•</span>
                      <span className="truncate max-w-[240px] text-zinc-400" title={doc.filepath}>
                        {doc.filepath}
                      </span>
                    </div>

                    {/* Entities if any */}
                    {doc.entities && doc.entities.length > 0 && (
                      <div className="flex items-center gap-1.5 flex-wrap pt-0.5">
                        <span className="text-xs text-zinc-400 font-mono font-medium">Entities:</span>
                        {doc.entities.slice(0, 4).map((ent, i) => (
                          <span
                            key={i}
                            className="text-xs font-mono px-2 py-0.5 rounded bg-white/[0.04] border border-white/[0.08] text-zinc-200"
                          >
                            {ent.entity_value}
                          </span>
                        ))}
                        {doc.entities.length > 4 && (
                          <span className="text-xs font-mono text-zinc-400">
                            +{doc.entities.length - 4} more
                          </span>
                        )}
                      </div>
                    )}
                  </div>
                </div>

                {/* Actions */}
                <div className="flex items-center gap-2 shrink-0 self-end sm:self-center">
                  <a
                    href={getDocumentDownloadUrl(doc.id)}
                    target="_blank"
                    rel="noreferrer"
                    className="p-2.5 rounded-lg bg-white/[0.05] hover:bg-white/[0.10] text-zinc-200 hover:text-white border border-white/[0.1] transition-all"
                    title="Open original file"
                  >
                    <Download className="w-4 h-4" />
                  </a>

                  <button
                    onClick={() => handleDeleteDoc(doc.id, doc.filename)}
                    disabled={deletingId === doc.id}
                    className="p-2.5 rounded-lg bg-red-950/25 hover:bg-red-950/45 text-red-300 hover:text-red-200 border border-red-800/35 transition-all disabled:opacity-50"
                    title="Remove from index"
                  >
                    <Trash2 className="w-4 h-4" />
                  </button>
                </div>
              </div>
            ))}
          </div>
        ) : (
          <div className="p-8 rounded-xl bg-black/40 border border-white/[0.06] text-center space-y-2">
            <p className="text-sm text-zinc-300">No indexed documents match your filter.</p>
            <p className="text-xs text-zinc-400 font-mono">
              Upload files above or click &ldquo;Seed Demo Memory & Ingest&rdquo;.
            </p>
          </div>
        )}
      </div>
    </div>
  );
}
