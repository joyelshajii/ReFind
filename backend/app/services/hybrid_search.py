import re
import logging
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any, Tuple, Optional
from sqlalchemy.orm import Session
from sqlalchemy import or_, func
from app.db.models import Document, Chunk, Entity
from app.schemas.search import QueryClues, SearchResultItem, EvidenceItem
from app.services.embedding_service import get_embedding, cosine_similarity
from app.services.reranker_service import reranker_service
from app.services.gemini_service import gemini_service
from app.core.config import settings

logger = logging.getLogger("refind.services.hybrid_search")

def _extract_snippet(text: str, keywords: List[str], max_len: int = 220) -> str:
    """
    Finds the most relevant snippet of text containing search keywords.
    """
    if not text:
        return "No text available."

    clean = " ".join(text.split())
    if len(clean) <= max_len:
        return clean

    lower = clean.lower()
    best_pos = -1
    for kw in keywords:
        pos = lower.find(kw.lower())
        if pos != -1:
            best_pos = pos
            break

    if best_pos == -1:
        return clean[:max_len] + "..."

    start = max(0, best_pos - 60)
    end = min(len(clean), start + max_len)
    
    if start > 0:
        space_before = clean.rfind(" ", 0, start)
        if space_before != -1:
            start = space_before + 1
    if end < len(clean):
        space_after = clean.find(" ", end)
        if space_after != -1:
            end = space_after

    snippet = clean[start:end].strip()
    if start > 0:
        snippet = "..." + snippet
    if end < len(clean):
        snippet = snippet + "..."
    return snippet

def search_documents(
    query: str,
    clues: QueryClues,
    db: Session,
    top_k: int = 10
) -> List[SearchResultItem]:
    """
    Full AI-Powered Hybrid Search Pipeline:
    1. Query Understanding (provided via clues)
    2. Candidate Retrieval:
       - Semantic Vector Search (top candidates via pgvector/embeddings)
       - Keyword / Full-Text Search (top candidates via text search & ilike)
       - Filename & Metadata matching
    3. Merge candidates and deduplicate (up to RETRIEVAL_CANDIDATE_LIMIT)
    4. Compute initial 5-signal scores (semantic, keyword, filename, metadata)
    5. Jina Reranker across candidates (falls back gracefully to hybrid scores if unavailable)
    6. Grounded Gemini match explanations for top results
    7. Return top ranked results
    """
    raw_docs = db.query(Document).all()
    if not raw_docs:
        return []

    # Guard: do not search files that no longer exist on disk
    documents = []
    seen_paths = set()
    for doc in raw_docs:
        if not Path(doc.filepath).exists():
            continue
        canon = str(Path(doc.filepath).resolve()).lower()
        if canon in seen_paths:
            continue
        seen_paths.add(canon)
        documents.append(doc)

    if not documents:
        return []

    # 1. Generate query embedding for vector retrieval
    query_vec = get_embedding(query, task="retrieval.query")

    # Candidate Retrieval Pool (Deduplicated by document id)
    candidate_map: Dict[str, Document] = {}

    # Keyword tokens
    search_keywords = list(dict.fromkeys(clues.keywords + (clues.topics or [])))

    # Semantic candidate retrieval
    scored_by_vec: List[Tuple[float, Document]] = []
    for doc in documents:
        doc_vec = doc.get_embedding()
        best_sem = cosine_similarity(query_vec, doc_vec) if doc_vec else 0.0
        for chunk in doc.chunks:
            c_vec = chunk.get_embedding()
            if c_vec:
                c_sem = cosine_similarity(query_vec, c_vec)
                if c_sem > best_sem:
                    best_sem = c_sem
        scored_by_vec.append((best_sem, doc))

    scored_by_vec.sort(key=lambda x: x[0], reverse=True)
    # Take top 20 semantic candidates
    for score, doc in scored_by_vec[:20]:
        candidate_map[doc.id] = doc

    # Keyword / Filename candidate retrieval
    for doc in documents:
        doc_lower = (doc.extracted_text or "").lower()
        fn_lower = doc.filename.lower()
        if any(kw.lower() in fn_lower or kw.lower() in doc_lower for kw in search_keywords):
            candidate_map[doc.id] = doc
        if clues.file_type and doc.file_type.lower() == clues.file_type.lower():
            candidate_map[doc.id] = doc

    # If candidates are few, include all available documents up to candidate limit
    candidate_docs = list(candidate_map.values())
    if len(candidate_docs) < settings.RETRIEVAL_CANDIDATE_LIMIT:
        for doc in documents:
            if doc.id not in candidate_map:
                candidate_docs.append(doc)
            if len(candidate_docs) >= settings.RETRIEVAL_CANDIDATE_LIMIT:
                break

    # Month mapping for date matching
    month_names = {
        "january": 1, "jan": 1,
        "february": 2, "feb": 2,
        "march": 3, "mar": 3,
        "april": 4, "apr": 4,
        "may": 5,
        "june": 6, "jun": 6,
        "july": 7, "jul": 7,
        "august": 8, "aug": 8,
        "september": 9, "sep": 9,
        "october": 10, "oct": 10,
        "november": 11, "nov": 11,
        "december": 12, "dec": 12
    }

    scored_candidates: List[Dict[str, Any]] = []

    for doc in candidate_docs:
        doc_text = doc.extracted_text or ""
        doc_lower = doc_text.lower()
        filename_lower = doc.filename.lower()

        # 1. Semantic Similarity (document + best chunk)
        doc_vec = doc.get_embedding()
        best_sem = cosine_similarity(query_vec, doc_vec) if doc_vec else 0.0
        best_chunk_loc = None
        best_chunk_text = ""

        for chunk in doc.chunks:
            chunk_vec = chunk.get_embedding()
            if chunk_vec:
                chunk_sem = cosine_similarity(query_vec, chunk_vec)
                if chunk_sem > best_sem:
                    best_sem = chunk_sem
                    best_chunk_text = chunk.content
                    if chunk.page_number:
                        best_chunk_loc = f"Page {chunk.page_number}"
                    elif chunk.slide_number:
                        best_chunk_loc = f"Slide {chunk.slide_number}"

        # 2. Keyword Relevance (supporting singular/plural and stem matching)
        kw_matches = 0
        total_kws = len(search_keywords)
        if total_kws > 0:
            for kw in search_keywords:
                kw_l = kw.lower().rstrip("s") # Stem trailing 's' for simple plural matching
                pattern = r"\b" + re.escape(kw_l)
                if re.search(pattern, doc_lower) or re.search(pattern, filename_lower):
                    kw_matches += 1
            kw_score = kw_matches / total_kws
        else:
            kw_score = 0.5

        # 3. Filename Relevance
        fn_score = 0.0
        if search_keywords:
            fn_matches = sum(1 for kw in search_keywords if kw.lower().rstrip("s") in filename_lower)
            fn_score = min(1.0, fn_matches / max(1, len(search_keywords)))

        # 4. Metadata Relevance (file_type and date/time)
        meta_score = 0.0
        meta_checks = 0

        matching_clues: List[str] = []
        detected_entities: List[str] = []
        evidence_list: List[EvidenceItem] = []

        image_types = {"png", "jpg", "jpeg", "webp", "gif", "bmp", "tiff"}
        if clues.file_type:
            meta_checks += 1
            type_matches = (
                doc.file_type.lower() in image_types
                if clues.file_type.lower() == "image"
                else doc.file_type.lower() == clues.file_type.lower()
            )
            if type_matches:
                meta_score += 1.0
                clue_label = "IMAGE" if clues.file_type.lower() == "image" else doc.file_type.upper()
                matching_clues.append(clue_label)
                evidence_list.append(EvidenceItem(
                    clue_name=clue_label,
                    clue_type="file_type",
                    matched_text=f"Document format matches requested '{clue_label}' type.",
                    location=f"File extension ({doc.file_type})",
                    verified=True
                ))

        if clues.time_clues:
            meta_checks += 1
            time_matched = False
            for tc in clues.time_clues:
                tc_lower = tc.lower()
                if tc_lower in month_names:
                    target_month = month_names[tc_lower]
                    if (doc.modified_at and doc.modified_at.month == target_month) or \
                       (doc.created_at and doc.created_at.month == target_month):
                        time_matched = True
                        matching_clues.append(tc.title())
                        date_str = (doc.modified_at or datetime.utcnow()).strftime("%B %d, %Y")
                        evidence_list.append(EvidenceItem(
                            clue_name=tc.title(),
                            clue_type="date",
                            matched_text=f"Document modification timestamp matches ({date_str}).",
                            location="File Metadata: modified_at",
                            verified=True
                        ))
                        break
                if tc.isdigit() and len(tc) == 4:
                    target_year = int(tc)
                    if (doc.modified_at and doc.modified_at.year == target_year) or \
                       (doc.created_at and doc.created_at.year == target_year):
                        time_matched = True
                        break
                if tc_lower in doc_lower:
                    time_matched = True
                    break
            if time_matched:
                meta_score += 1.0

        # Entities (People, Technologies, Topics)
        for person in clues.people:
            pattern = r"\b" + re.escape(person.lower()) + r"\b"
            if re.search(pattern, doc_lower) or re.search(pattern, filename_lower):
                matching_clues.append(person)
                evidence_list.append(EvidenceItem(
                    clue_name=person,
                    clue_type="person",
                    matched_text=f"Referenced person '{person}' verified in document content.",
                    location=best_chunk_loc or "Content",
                    verified=True
                ))

        for tech in clues.technologies:
            pattern = r"\b" + re.escape(tech.lower()) + r"\b"
            if re.search(pattern, doc_lower) or re.search(pattern, filename_lower):
                matching_clues.append(tech)
                detected_entities.append(tech)
                evidence_list.append(EvidenceItem(
                    clue_name=tech,
                    clue_type="technology",
                    matched_text=f"Technology '{tech}' identified in document text/architecture.",
                    location=best_chunk_loc or "Content",
                    verified=True
                ))

        for topic in clues.topics:
            pattern = r"\b" + re.escape(topic.lower()) + r"\b"
            if re.search(pattern, doc_lower) or re.search(pattern, filename_lower):
                matching_clues.append(topic)
                evidence_list.append(EvidenceItem(
                    clue_name=topic,
                    clue_type="topic",
                    matched_text=f"Topic '{topic}' detected.",
                    location=best_chunk_loc or "Document",
                    verified=True
                ))

        # Do not return unrelated documents for queries that have specific search keywords but zero matches
        if total_kws > 0 and kw_matches == 0:
            continue

        final_meta = (meta_score / meta_checks) if meta_checks > 0 else 0.5
        snippet = _extract_snippet(doc_text, search_keywords)

        # Baseline hybrid score (weights configurable in settings)
        # initial weights: semantic 0.45, reranker 0.20, keyword 0.15, metadata 0.10, filename 0.10
        scored_candidates.append({
            "doc": doc,
            "best_sem": best_sem,
            "kw_score": kw_score,
            "fn_score": fn_score,
            "meta_score": final_meta,
            "reranker_score": 0.0,
            "best_chunk_loc": best_chunk_loc,
            "snippet": snippet,
            "matching_clues": list(dict.fromkeys(matching_clues)),
            "detected_entities": list(dict.fromkeys(detected_entities)),
            "evidence": evidence_list,
            "repr_text": (best_chunk_text or doc_text)[:800] or doc.filename
        })

    # 5. Jina Reranking Stage
    candidate_texts = [c["repr_text"] for c in scored_candidates]
    jina_results = None
    if settings.JINA_API_KEY:
        try:
            jina_results = reranker_service.rerank(
                query=query,
                documents=candidate_texts,
                top_n=min(len(candidate_texts), settings.RERANKER_TOP_K)
            )
        except Exception as je:
            logger.warning(f"Jina reranker failed: {je}. Falling back to standard hybrid.")

    # Apply reranker score if returned
    if jina_results:
        for item in jina_results:
            idx = item.get("index")
            rel = item.get("relevance_score", 0.0)
            if idx is not None and 0 <= idx < len(scored_candidates):
                scored_candidates[idx]["reranker_score"] = float(rel)
    else:
        # Fallback: distribute reranker weight proportionally onto semantic and keyword
        for c in scored_candidates:
            c["reranker_score"] = c["best_sem"]

    # Compute final composite score
    w_sem = settings.WEIGHT_SEMANTIC
    w_rerank = settings.WEIGHT_RERANKER
    w_kw = settings.WEIGHT_KEYWORD
    w_meta = settings.WEIGHT_METADATA
    w_fn = settings.WEIGHT_FILENAME

    final_results: List[Tuple[float, SearchResultItem]] = []

    for c in scored_candidates:
        doc = c["doc"]
        composite = (
            w_sem * c["best_sem"] +
            w_rerank * c["reranker_score"] +
            w_kw * c["kw_score"] +
            w_meta * c["meta_score"] +
            w_fn * c["fn_score"]
        )
        clamped_score = round(max(0.05, min(0.98, composite)), 2)

        unique_clues = c["matching_clues"]
        if clamped_score >= 0.70 or len(unique_clues) >= 4:
            score_label = "Strong match"
        elif clamped_score >= 0.50 or len(unique_clues) >= 2:
            score_label = "Good match"
        elif clamped_score >= 0.30 or len(unique_clues) >= 1:
            score_label = "Relevant"
        else:
            score_label = "Partial match"

        item = SearchResultItem(
            document_id=doc.id,
            filename=doc.filename,
            filepath=doc.filepath,
            file_type=doc.file_type,
            file_size=doc.file_size or 0,
            modified_at=doc.modified_at or datetime.utcnow(),
            score=clamped_score,
            score_label=score_label,
            snippet=c["snippet"],
            page_or_slide=c["best_chunk_loc"],
            matching_clues=unique_clues,
            detected_entities=c["detected_entities"],
            evidence=c["evidence"],
            ai_explanation=None # Will enrich top results below
        )
        final_results.append((clamped_score, item))

    final_results.sort(key=lambda x: x[0], reverse=True)
    top_items = [r[1] for r in final_results[:top_k]]

    # 6. Generate grounded Gemini result explanations for top 3 results
    if settings.LLM_PROVIDER == "gemini" and settings.GEMINI_API_KEY:
        for item in top_items[:3]:
            try:
                # Find matching doc chunks
                matched_doc = next((d for d in candidate_docs if d.id == item.document_id), None)
                if matched_doc:
                    chunks_text = [ch.content for ch in matched_doc.chunks[:3]]
                    explanation = gemini_service.explain_match(
                        query=query,
                        filename=item.filename,
                        file_type=item.file_type,
                        relevant_chunks=chunks_text
                    )
                    item.ai_explanation = explanation
            except Exception as ee:
                logger.debug(f"AI explanation generation skipped: {ee}")

    return top_items

# Backward-compatible alias
search_hybrid = search_documents
