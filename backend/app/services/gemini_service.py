import os
import json
import logging
from typing import Optional, Dict, Any, List
from pydantic import BaseModel
from app.core.config import settings

logger = logging.getLogger("refind.services.gemini")

class StructuredIntent(BaseModel):
    semantic_query: str
    keywords: List[str] = []
    file_type: Optional[str] = None
    date_hint: Optional[str] = None
    topics: List[str] = []
    people: List[str] = []
    technologies: List[str] = []

class GeminiService:
    def __init__(self):
        self._client = None

    def _get_client(self):
        if self._client is None and settings.GEMINI_API_KEY:
            try:
                from google import genai
                self._client = genai.Client(api_key=settings.GEMINI_API_KEY)
            except Exception as e:
                logger.error(f"Failed to initialize Gemini client: {e}")
                self._client = None
        return self._client

    def parse_query_intent(self, query: str) -> Optional[StructuredIntent]:
        """
        Uses Gemini (gemini-2.5-flash-lite / fallback) to analyze the user query
        and extract structured search intent.
        Strict validation applied: returns None on failure so caller can fall back.
        """
        client = self._get_client()
        if not client:
            return None

        prompt = f"""You are a search query parser for a personal search engine called ReFind.
Analyze this user search query and output ONLY valid JSON matching this schema:
{{
  "semantic_query": "core search terms focused purely on the document meaning/subject (exclude words like 'document', 'file', 'find')",
  "keywords": ["specific subject-matter keywords only (DO NOT include 'document', 'file', 'wrote', 'find', 'me')"],
  "file_type": "pdf" or "docx" or "pptx" or "txt" or "png" or null,
  "date_hint": "relative or absolute date clue (e.g. 'last month', 'September 2026') or null",
  "topics": ["specific", "topics"],
  "people": ["person names mentioned if any"],
  "technologies": ["technologies mentioned if any"]
}}

User Query: "{query}"

Output ONLY raw JSON. No markdown code blocks, no backticks, no explanations.
"""
        working_model = getattr(self, "_working_chat_model", None)
        models_to_try = [working_model] if working_model else []
        for m in [settings.GEMINI_MODEL, "gemini-3.5-flash-lite", "gemini-3.8-flash"]:
            if m and m not in models_to_try:
                models_to_try.append(m)

        for model_name in models_to_try:
            try:
                response = client.models.generate_content(
                    model=model_name,
                    contents=prompt,
                )
                text = response.text.strip() if response and response.text else ""
                if text.startswith("```"):
                    text = text.strip("`")
                    if text.startswith("json"):
                        text = text[4:].strip()
                
                data = json.loads(text)
                self._working_chat_model = model_name
                return StructuredIntent(
                    semantic_query=str(data.get("semantic_query") or query).strip(),
                    keywords=[str(k).strip() for k in data.get("keywords", []) if str(k).strip()],
                    file_type=data.get("file_type") if data.get("file_type") in ("pdf", "docx", "pptx", "txt", "png", "jpg", "jpeg", "webp", "gif", "bmp", "tiff", "heic", "heif", "image") else None,
                    date_hint=str(data.get("date_hint")).strip() if data.get("date_hint") else None,
                    topics=[str(t).strip() for t in data.get("topics", []) if str(t).strip()],
                    people=[str(p).strip() for p in data.get("people", []) if str(p).strip()],
                    technologies=[str(t).strip() for t in data.get("technologies", []) if str(t).strip()],
                )
            except Exception as e:
                logger.warning(f"Gemini query parsing failed with model {model_name}: {e}")
                continue

        return None

    def explain_match(
        self,
        query: str,
        filename: str,
        file_type: str,
        relevant_chunks: List[str]
    ) -> Optional[str]:
        """
        Generates a concise, 1-2 sentence explanation of why this document matches the query,
        strictly grounded in the retrieved chunks.
        PRIVACY: Only relevant retrieved chunks and metadata are sent. Never the whole document.
        """
        client = self._get_client()
        if not client:
            return None

        context_excerpt = "\n---\n".join([c[:400] for c in relevant_chunks[:3]])
        prompt = f"""You are a search explanation engine. Given the user search query, the document filename, and a few retrieved chunks from that document, write a concise 1-2 sentence explanation starting with 'Matched because...' explaining why this document satisfies the query.
Ground your explanation STRICTLY on the excerpt below. Never invent details or assume anything outside this excerpt.

Query: "{query}"
Document: "{filename}" ({file_type})
Retrieved Excerpts:
{context_excerpt}

Provide only the 1-2 sentence explanation.
"""
        working_model = getattr(self, "_working_chat_model", None)
        models_to_try = [working_model] if working_model else []
        for m in [settings.GEMINI_MODEL, "gemini-3.5-flash-lite", "gemini-3.8-flash"]:
            if m and m not in models_to_try:
                models_to_try.append(m)

        for model_name in models_to_try:
            try:
                response = client.models.generate_content(
                    model=model_name,
                    contents=prompt,
                )
                if response and response.text:
                    self._working_chat_model = model_name
                    return response.text.strip()
            except Exception as e:
                logger.warning(f"Gemini match explanation failed with model {model_name}: {e}")
                continue

        return None

gemini_service = GeminiService()
