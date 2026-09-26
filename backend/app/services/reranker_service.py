import logging
import requests
from typing import List, Dict, Any, Optional
from app.core.config import settings

logger = logging.getLogger("refind.services.reranker")

class RerankerService:
    def __init__(self):
        self.api_url = "https://api.jina.ai/v1/rerank"
        self.model = "jina-reranker-v2-base-multilingual"

    def rerank(
        self,
        query: str,
        documents: List[str],
        top_n: Optional[int] = None
    ) -> Optional[List[Dict[str, Any]]]:
        """
        Calls Jina Reranker API to rerank retrieved candidate document texts against the query.
        Returns a list of dicts: [{"index": int, "relevance_score": float, "document": str}, ...]
        Returns None if Jina is unavailable or fails, allowing seamless fallback.
        """
        if not settings.JINA_API_KEY:
            logger.debug("Jina API key not set, skipping external reranker.")
            return None

        if not documents:
            return []

        top_n = top_n or min(len(documents), settings.RERANKER_TOP_K)

        headers = {
            "Authorization": f"Bearer {settings.JINA_API_KEY}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": self.model,
            "query": query,
            "documents": [d[:1000] for d in documents], # Truncate long chunks for speed and token limits
            "top_n": top_n
        }

        try:
            resp = requests.post(self.api_url, headers=headers, json=payload, timeout=8.0)
            if resp.status_code == 200:
                data = resp.json()
                results = data.get("results", [])
                logger.info(f"Jina reranked {len(documents)} candidates successfully.")
                return results
            else:
                logger.warning(f"Jina reranker returned status {resp.status_code}: {resp.text}")
                return None
        except Exception as e:
            logger.warning(f"Jina reranker request failed: {e}. Falling back to hybrid score.")
            return None

reranker_service = RerankerService()
