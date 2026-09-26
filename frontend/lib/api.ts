import {
  SearchResponse,
  ContextDetailResponse,
  IndexProgressStatus,
  IndexStats,
  IndexedDocumentItem
} from "@/types";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export async function searchDocuments(query: string, topK: number = 10): Promise<SearchResponse> {
  const res = await fetch(`${API_BASE_URL}/api/search`, {
    method: "POST",
    cache: "no-store",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ query, top_k: topK }),
  });
  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    throw new Error(errorData.detail || "Search request failed");
  }
  return res.json();
}

export async function getDocumentContext(
  documentId: string,
  query: string,
  score: number = 0.94,
  scoreLabel: string = "Strong match"
): Promise<ContextDetailResponse> {
  const params = new URLSearchParams({
    q: query,
    score: score.toString(),
    score_label: scoreLabel,
  });
  const res = await fetch(`${API_BASE_URL}/api/documents/${documentId}/context?${params.toString()}`);
  if (!res.ok) {
    throw new Error("Failed to load document context");
  }
  return res.json();
}

export async function getIndexStatus(): Promise<IndexProgressStatus> {
  const res = await fetch(`${API_BASE_URL}/api/index/status`, {
    cache: "no-store",
  });
  if (!res.ok) {
    throw new Error("Failed to fetch indexing status");
  }
  return res.json();
}

export async function getIndexStats(): Promise<IndexStats> {
  const res = await fetch(`${API_BASE_URL}/api/index/stats`, {
    cache: "no-store",
  });
  if (!res.ok) {
    throw new Error("Failed to fetch index stats");
  }
  return res.json();
}

export async function getIndexedDocuments(search?: string, fileType?: string): Promise<IndexedDocumentItem[]> {
  const params = new URLSearchParams();
  if (search && search.trim()) params.set("search", search.trim());
  if (fileType && fileType.trim() && fileType !== "all") params.set("file_type", fileType.trim());
  params.set("limit", "100");

  const url = `${API_BASE_URL}/api/documents${params.toString() ? `?${params.toString()}` : ""}`;
  const res = await fetch(url, { cache: "no-store" });
  if (!res.ok) {
    throw new Error("Failed to fetch indexed documents list");
  }
  return res.json();
}

export async function deleteDocument(documentId: string): Promise<{ status: string; message: string }> {
  const res = await fetch(`${API_BASE_URL}/api/documents/${documentId}`, {
    method: "DELETE",
  });
  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    throw new Error(errorData.detail || "Failed to remove document");
  }
  return res.json();
}

export async function deleteAllDocuments(): Promise<{
  status: string;
  removed_count: number;
  message: string;
}> {
  const res = await fetch(`${API_BASE_URL}/api/documents`, {
    method: "DELETE",
  });
  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    throw new Error(errorData.detail || "Failed to clear indexed files");
  }
  return res.json();
}

export async function triggerIndexing(folderPath?: string): Promise<{ status: string; message: string; files_found: number }> {
  const res = await fetch(`${API_BASE_URL}/api/index`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(folderPath ? { folder_path: folderPath } : {}),
  });
  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    throw new Error(errorData.detail || "Failed to trigger indexing");
  }
  return res.json();
}

export async function uploadFiles(formData: FormData): Promise<{ status: string; message: string }> {
  const res = await fetch(`${API_BASE_URL}/api/index/upload`, {
    method: "POST",
    body: formData,
  });
  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    throw new Error(errorData.detail || "Failed to upload files");
  }
  return res.json();
}

export async function seedDemoData(): Promise<{ status: string; message: string; demo_scenario: string }> {
  const res = await fetch(`${API_BASE_URL}/api/demo/seed`, {
    method: "POST",
  });
  if (!res.ok) {
    throw new Error("Failed to seed demo data");
  }
  return res.json();
}

export async function getHealth(): Promise<any> {
  try {
    const res = await fetch(`${API_BASE_URL}/api/health`, { cache: "no-store" });
    if (!res.ok) return null;
    return res.json();
  } catch {
    return null;
  }
}

export function getDocumentDownloadUrl(documentId: string): string {
  return `${API_BASE_URL}/api/documents/${documentId}/download`;
}
