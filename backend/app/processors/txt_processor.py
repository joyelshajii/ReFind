import logging
from typing import Dict, Any, List
from pathlib import Path

logger = logging.getLogger("refind.processors.txt")

def process_txt(file_path: str) -> Dict[str, Any]:
    """
    Extracts text from TXT or Markdown files with encoding fallbacks and paragraph chunking.
    """
    path = Path(file_path)
    chunks: List[Dict[str, Any]] = []
    text_content = ""

    encodings = ["utf-8", "utf-8-sig", "latin-1", "cp1252"]
    for enc in encodings:
        try:
            with open(path, "r", encoding=enc) as f:
                text_content = f.read()
            break
        except Exception:
            continue

    paragraphs = [p.strip() for p in text_content.split("\n\n") if p.strip()]
    
    current_chunk: List[str] = []
    chunk_idx = 1
    for p in paragraphs:
        current_chunk.append(p)
        if len("\n".join(current_chunk)) > 500:
            chunks.append({
                "content": "\n\n".join(current_chunk),
                "page_number": chunk_idx,
                "slide_number": None
            })
            current_chunk = []
            chunk_idx += 1
            
    if current_chunk:
        chunks.append({
            "content": "\n\n".join(current_chunk),
            "page_number": chunk_idx,
            "slide_number": None
        })

    return {
        "extracted_text": text_content,
        "chunks": chunks if chunks else [{"content": text_content, "page_number": 1, "slide_number": None}],
        "metadata": {}
    }
