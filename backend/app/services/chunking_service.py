import re
from typing import List, Dict, Any, Optional
from app.core.config import settings

def chunk_text(
    text: str,
    chunk_size: Optional[int] = None,
    chunk_overlap: Optional[int] = None
) -> List[str]:
    """
    Splits text into chunks of roughly `chunk_size` characters with `chunk_overlap`
    while preserving sentence and paragraph boundaries.
    """
    size = chunk_size or settings.CHUNK_SIZE
    overlap = chunk_overlap or settings.CHUNK_OVERLAP

    if not text or not text.strip():
        return []

    clean_text = text.strip()
    if len(clean_text) <= size:
        return [clean_text]

    # Split into paragraphs first
    paragraphs = [p.strip() for p in clean_text.split("\n\n") if p.strip()]
    if not paragraphs:
        paragraphs = [clean_text]

    chunks: List[str] = []
    current_chunk: List[str] = []
    current_len = 0

    for para in paragraphs:
        para_len = len(para)
        
        # If single paragraph exceeds size, split on sentences
        if para_len > size:
            sentences = re.split(r"(?<=[.!?])\s+", para)
            for sent in sentences:
                sent = sent.strip()
                if not sent:
                    continue
                if current_len + len(sent) > size and current_chunk:
                    chunks.append("\n".join(current_chunk))
                    # Retain last piece for overlap
                    overlap_piece = current_chunk[-1] if len(current_chunk[-1]) <= overlap else current_chunk[-1][-overlap:]
                    current_chunk = [overlap_piece, sent]
                    current_len = len(overlap_piece) + len(sent)
                else:
                    current_chunk.append(sent)
                    current_len += len(sent)
        else:
            if current_len + para_len > size and current_chunk:
                chunks.append("\n\n".join(current_chunk))
                overlap_piece = current_chunk[-1] if len(current_chunk[-1]) <= overlap else current_chunk[-1][-overlap:]
                current_chunk = [overlap_piece, para]
                current_len = len(overlap_piece) + para_len
            else:
                current_chunk.append(para)
                current_len += para_len

    if current_chunk:
        chunks.append("\n\n".join(current_chunk))

    return [c.strip() for c in chunks if c.strip()]
