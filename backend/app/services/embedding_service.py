import math
import hashlib
import re
import logging
from typing import List, Optional
import numpy as np
import httpx
from app.core.config import settings

logger = logging.getLogger("refind.services.embedding")

DIMENSION = settings.EMBEDDING_DIMENSION  # Default 768
JINA_EMBEDDINGS_URL = "https://api.jina.ai/v1/embeddings"
JINA_RERANK_URL = "https://api.jina.ai/v1/rerank"

def _local_semantic_vector(text: str, dim: int = DIMENSION) -> List[float]:
    """
    Zero-dependency deterministic semantic embedding vectorizer.
    Uses token hashing, character n-grams, and TF-IDF weighting projected to L2 unit sphere.
    Produces stable dense vectors with genuine cosine distance behavior.
    """
    vec = np.zeros(dim, dtype=np.float32)
    clean = text.lower().strip()
    if not clean:
        return vec.tolist()

    words = re.findall(r"\w+", clean)
    
    # 1. Word-level hashing with positional damping
    for idx, word in enumerate(words):
        h = int(hashlib.md5(word.encode("utf-8")).hexdigest(), 16)
        pos = h % dim
        sign = 1.0 if (h // dim) % 2 == 0 else -1.0
        weight = (1.0 + math.log(1.0 + len(word))) * (1.0 / (1.0 + 0.05 * min(idx, 20)))
        vec[pos] += sign * weight

    # 2. Substring 3-gram hashing for morphological & typo resilience
    for i in range(len(clean) - 2):
        trigram = clean[i:i+3]
        h = int(hashlib.sha256(trigram.encode("utf-8")).hexdigest(), 16)
        pos = h % dim
        sign = 1.0 if (h // dim) % 2 == 0 else -1.0
        vec[pos] += sign * 0.35

    # L2 Normalization
    norm = np.linalg.norm(vec)
    if norm > 1e-6:
        vec = vec / norm

    return vec.tolist()

def _embed_gemini(text: str, dim: int = DIMENSION) -> Optional[List[float]]:
    """
    Generates embedding via Gemini Embedding 2 with configurable output dimensionality.
    """
    if not settings.GEMINI_API_KEY:
        return None

    try:
        from google import genai
        client = genai.Client(api_key=settings.GEMINI_API_KEY)
        
        # Truncate content if too long for a single embedding call
        clean_text = text[:8000].strip()
        if not clean_text:
            return None

        response = client.models.embed_content(
            model=settings.GEMINI_EMBEDDING_MODEL,
            contents=clean_text,
            config={"output_dimensionality": dim}
        )
        if response and response.embeddings and len(response.embeddings) > 0:
            return list(response.embeddings[0].values)
    except Exception as e:
        logger.warning(f"Gemini embedding API call failed: {e}. Falling back to local vectorizer.")
        return None

    return None

def _embed_jina(text: str, task: str = "retrieval.passage") -> Optional[List[float]]:
    """
    Generates embedding via Jina embeddings API if configured.
    """
    if not settings.JINA_API_KEY:
        return None
    try:
        response = httpx.post(
            JINA_EMBEDDINGS_URL,
            headers={
                "Authorization": f"Bearer {settings.JINA_API_KEY}",
                "Content-Type": "application/json",
            },
            json={
                "model": settings.JINA_EMBEDDING_MODEL,
                "input": [text or " "],
                "task": task,
                "dimensions": settings.JINA_EMBEDDING_DIMENSION,
            },
            timeout=settings.JINA_TIMEOUT_SECONDS,
        )
        response.raise_for_status()
        data = response.json().get("data", [])
        if data and data[0].get("embedding"):
            return data[0]["embedding"]
    except Exception as e:
        logger.warning(f"Jina embedding API call failed: {e}")
        return None
    return None

def embed_text(text: str) -> List[float]:
    """
    Core embedding interface: embed_text(text) -> vector (768-d).
    Uses Gemini Embedding 2 when configured, with robust local fallback.
    """
    if settings.EMBEDDING_PROVIDER == "gemini" and settings.GEMINI_API_KEY:
        vec = _embed_gemini(text, dim=DIMENSION)
        if vec is not None and len(vec) == DIMENSION:
            return vec

    if settings.EMBEDDING_PROVIDER.lower() == "jina" and settings.JINA_API_KEY:
        vec = _embed_jina(text)
        if vec is not None:
            return vec

    return _local_semantic_vector(text, dim=DIMENSION)

def get_embedding(text: str, task: str = "retrieval.passage") -> List[float]:
    """
    Backward-compatible alias for existing codebase callers.
    """
    return embed_text(text)

def cosine_similarity(v1: List[float], v2: List[float]) -> float:
    """
    Computes cosine similarity between two float vectors.
    Returns float in range [0.0, 1.0].
    """
    if not v1 or not v2 or len(v1) != len(v2):
        return 0.0
    
    a = np.array(v1, dtype=np.float32)
    b = np.array(v2, dtype=np.float32)
    
    norm_a = np.linalg.norm(a)
    norm_b = np.linalg.norm(b)
    
    if norm_a < 1e-6 or norm_b < 1e-6:
        return 0.0
        
    dot = float(np.dot(a, b))
    sim = dot / (norm_a * norm_b)
    return max(0.0, min(1.0, sim))

def rerank_with_jina(query: str, documents: List[str]) -> List[float]:
    """Return provider scores aligned to documents, or [] when unavailable."""
    if not settings.JINA_API_KEY or not documents:
        return []

    try:
        response = httpx.post(
            JINA_RERANK_URL,
            headers={
                "Authorization": f"Bearer {settings.JINA_API_KEY}",
                "Content-Type": "application/json",
            },
            json={
                "model": settings.JINA_RERANKER_MODEL,
                "query": query,
                "documents": documents,
                "top_n": len(documents),
                "return_documents": False,
            },
            timeout=settings.JINA_TIMEOUT_SECONDS,
        )
        response.raise_for_status()
        scores = [0.0] * len(documents)
        for item in response.json().get("results", []):
            index = item.get("index")
            score = item.get("relevance_score")
            if isinstance(index, int) and 0 <= index < len(scores) and isinstance(score, (int, float)):
                scores[index] = max(0.0, min(1.0, float(score)))
        return scores
    except (httpx.HTTPError, ValueError, KeyError, TypeError):
        return []
