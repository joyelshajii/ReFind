import logging
from typing import Dict, Any, List
from pathlib import Path
from docx import Document

logger = logging.getLogger("refind.processors.docx")

def process_docx(file_path: str) -> Dict[str, Any]:
    """
    Extracts text, paragraphs, headings and sections from a DOCX file.
    """
    path = Path(file_path)
    chunks: List[Dict[str, Any]] = []
    full_text_parts: List[str] = []
    metadata: Dict[str, Any] = {}

    try:
        doc = Document(str(path))
        
        # Read core properties
        if doc.core_properties:
            cp = doc.core_properties
            if cp.title:
                metadata["title"] = cp.title
            if cp.author:
                metadata["author"] = cp.author
            if cp.created:
                metadata["created_date"] = str(cp.created)

        current_chunk_lines: List[str] = []
        chunk_idx = 1

        for p in doc.paragraphs:
            text = p.text.strip()
            if not text:
                continue
            
            full_text_parts.append(text)
            current_chunk_lines.append(text)

            # Chunk every ~4 paragraphs or on headings
            if len(current_chunk_lines) >= 4 or p.style.name.startswith("Heading"):
                chunk_content = "\n".join(current_chunk_lines)
                chunks.append({
                    "content": chunk_content,
                    "page_number": chunk_idx,
                    "slide_number": None
                })
                current_chunk_lines = []
                chunk_idx += 1

        if current_chunk_lines:
            chunks.append({
                "content": "\n".join(current_chunk_lines),
                "page_number": chunk_idx,
                "slide_number": None
            })

    except Exception as e:
        logger.error(f"Error processing DOCX {file_path}: {e}")

    extracted_text = "\n\n".join(full_text_parts)
    return {
        "extracted_text": extracted_text,
        "chunks": chunks,
        "metadata": metadata
    }
