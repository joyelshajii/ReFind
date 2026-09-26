import re
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from app.db.models import Document, Chunk, Entity
from app.schemas.search import QueryClues, ContextDetailResponse, EvidenceItem
from app.services.gemini_service import gemini_service

def generate_context_explanation(
    document: Document,
    clues: QueryClues,
    score: float,
    score_label: str
) -> ContextDetailResponse:
    """
    Constructs deterministic, verified evidence connecting the user's remembered clues
    to the actual document metadata, page/slide chunks, and extracted content.
    Optionally generates a grounded explanation via Gemini 2.5 Flash Lite.
    """
    memory_clues: List[str] = []
    document_evidence: List[EvidenceItem] = []
    relevant_snippets: List[str] = []

    doc_text = document.extracted_text or ""
    doc_lower = doc_text.lower()
    filename_lower = document.filename.lower()

    def excerpt_for(term: str):
        normalized = term.lower()
        if len(normalized) > 3 and normalized.endswith("s"):
            normalized = normalized[:-1]
        pattern = r"(?<!\w)" + re.escape(normalized) + r"s?(?!\w)"
        for chunk in document.chunks:
            content = " ".join((chunk.content or "").split())
            match = re.search(pattern, content, re.IGNORECASE)
            if match:
                start = max(0, match.start() - 75)
                end = min(len(content), start + 220)
                quote = ("..." if start else "") + content[start:end].strip()
                if end < len(content):
                    quote += "..."
                location = (
                    f"Page {chunk.page_number}" if chunk.page_number
                    else f"Slide {chunk.slide_number}" if chunk.slide_number
                    else "Content"
                )
                return quote, location
        return "", ""

    # 1. Topic Memory Clue
    if clues.topics:
        for topic in clues.topics:
            memory_clues.append(f"Topic: {topic}")
            if topic.lower() in doc_lower or topic.lower() in filename_lower:
                location = "Document content"
                for chunk in document.chunks:
                    if topic.lower() in chunk.content.lower():
                        if chunk.page_number:
                            location = f"Page {chunk.page_number}"
                        elif chunk.slide_number:
                            location = f"Slide {chunk.slide_number}"
                        break

                quote, quote_location = excerpt_for(topic)
                document_evidence.append(EvidenceItem(
                    clue_name=topic,
                    clue_type="topic",
                    matched_text=quote,
                    location=quote_location or location,
                    verified=True
                ))

    # 2. File Type Clue
    if clues.file_type:
        memory_clues.append(f"Format: {clues.file_type.upper()}")
        image_types = {"png", "jpg", "jpeg", "webp", "gif", "bmp", "tiff", "heic", "heif"}
        type_matches = document.file_type.lower() in image_types if clues.file_type.lower() == "image" else document.file_type.lower() == clues.file_type.lower()
        if type_matches:
            document_evidence.append(EvidenceItem(
                clue_name=f"{clues.file_type.upper()} format",
                clue_type="file_type",
                matched_text=f"File extension is .{document.file_type}, matching the requested {clues.file_type.upper()} type.",
                location=f"{document.filename}",
                verified=True
            ))

    # 3. Time Clue
    if clues.time_clues:
        for tc in clues.time_clues:
            memory_clues.append(f"Time: {tc}")
            month_names = {
                "january": 1, "february": 2, "march": 3, "april": 4, "may": 5, "june": 6,
                "july": 7, "august": 8, "september": 9, "october": 10, "november": 11, "december": 12
            }
            if tc.lower() in month_names:
                m_num = month_names[tc.lower()]
                if document.modified_at and document.modified_at.month == m_num:
                    date_display = document.modified_at.strftime('%B %d, %Y')
                    document_evidence.append(EvidenceItem(
                        clue_name=f"{tc.title()} timestamp",
                        clue_type="date",
                        matched_text=f"File last modified on {date_display}.",
                        location="Filesystem Metadata",
                        verified=True
                    ))
            elif tc.lower() in doc_lower:
                document_evidence.append(EvidenceItem(
                    clue_name=f"{tc.title()} mention",
                    clue_type="date",
                    matched_text=f"Date '{tc}' found in document text.",
                    location="Document body",
                    verified=True
                ))

    # 4. Person Clue
    if clues.people:
        for person in clues.people:
            memory_clues.append(f"Person: {person}")
            if person.lower() in doc_lower:
                sentences = re.split(r"(?<=[.!?]) +", doc_text)
                matched_sent = next((s.strip() for s in sentences if person.lower() in s.lower()), f"Mention of {person}")
                document_evidence.append(EvidenceItem(
                    clue_name=f"Shared by / references {person}",
                    clue_type="person",
                    matched_text=excerpt_for(person)[0] or matched_sent[:150],
                    location=excerpt_for(person)[1] or "Author / Header / Content",
                    verified=True
                ))

    # 5. Technology Clues
    if clues.technologies:
        for tech in clues.technologies:
            memory_clues.append(f"Tech: {tech}")
            if tech.lower() in doc_lower:
                loc = "System components"
                for chunk in document.chunks:
                    if tech.lower() in chunk.content.lower():
                        if chunk.page_number:
                            loc = f"Page {chunk.page_number}"
                        elif chunk.slide_number:
                            loc = f"Slide {chunk.slide_number}"
                        break

                document_evidence.append(EvidenceItem(
                    clue_name=tech,
                    clue_type="technology",
                    matched_text=excerpt_for(tech)[0],
                    location=excerpt_for(tech)[1] or loc,
                    verified=True
                ))

    for keyword in clues.keywords:
        quote, quote_location = excerpt_for(keyword)
        if quote and not any(ev.clue_name.lower() == keyword.lower() for ev in document_evidence):
            memory_clues.append(f"Keyword: {keyword}")
            document_evidence.append(EvidenceItem(
                clue_name=keyword,
                clue_type="keyword",
                matched_text=quote,
                location=quote_location,
                verified=True
            ))

    # Gather 2-3 key snippets from chunks
    chunk_contents = []
    for chunk in document.chunks[:3]:
        cleaned = " ".join(chunk.content.split())
        chunk_contents.append(cleaned)
        prefix = f"[Page {chunk.page_number}] " if chunk.page_number else (f"[Slide {chunk.slide_number}] " if chunk.slide_number else "")
        relevant_snippets.append(prefix + cleaned[:200] + ("..." if len(cleaned) > 200 else ""))

    # Grounded AI Explanation using Gemini 2.5 Flash Lite
    ai_explanation: Optional[str] = None
    try:
        ai_explanation = gemini_service.explain_match(
            query=clues.raw_query,
            filename=document.filename,
            file_type=document.file_type,
            relevant_chunks=chunk_contents
        )
    except Exception:
        ai_explanation = None

    return ContextDetailResponse(
        document_id=document.id,
        filename=document.filename,
        file_type=document.file_type,
        score=score,
        score_label=score_label,
        memory_clues=memory_clues,
        document_evidence=document_evidence,
        snippets=relevant_snippets,
        ai_explanation=ai_explanation
    )
