import logging
from typing import Dict, Any, List
from pathlib import Path
import fitz # PyMuPDF
from app.services.chunking_service import chunk_text
from app.services.ocr_service import ocr_service

logger = logging.getLogger("refind.processors.pdf")

def process_pdf(file_path: str) -> Dict[str, Any]:
    """
    Extracts text, metadata, and per-page chunks from a PDF file using PyMuPDF (fitz).
    If a page contains no digital text (e.g. scanned document), invokes local OCR via PaddleOCR.
    """
    path = Path(file_path)
    chunks: List[Dict[str, Any]] = []
    full_text_parts: List[str] = []
    metadata: Dict[str, Any] = {}

    try:
        doc = fitz.open(str(path))
        
        # Read PDF metadata
        pdf_meta = doc.metadata or {}
        if pdf_meta.get("title"):
            metadata["title"] = str(pdf_meta.get("title"))
        if pdf_meta.get("author"):
            metadata["author"] = str(pdf_meta.get("author"))
        if pdf_meta.get("creationDate"):
            metadata["creation_date"] = str(pdf_meta.get("creationDate"))

        for idx, page in enumerate(doc):
            page_num = idx + 1
            page_text = page.get_text() or ""
            cleaned = page_text.strip()

            # If page text is minimal, check if page is a scanned image
            if len(cleaned) < 30:
                try:
                    pix = page.get_pixmap(dpi=150)
                    ocr_res = ocr_service.extract_text_from_scanned_pdf_page(pix)
                    if ocr_res and len(ocr_res.strip()) > len(cleaned):
                        cleaned = ocr_res.strip()
                except Exception as oe:
                    logger.debug(f"OCR fallback on PDF page {page_num} error: {oe}")

            if cleaned:
                full_text_parts.append(cleaned)
                # Split large page into sensible chunks if needed
                page_chunks = chunk_text(cleaned)
                for pc in page_chunks:
                    chunks.append({
                        "content": pc,
                        "page_number": page_num,
                        "slide_number": None
                    })
        doc.close()
    except Exception as e:
        logger.error(f"PyMuPDF error processing PDF {file_path}: {e}")

    extracted_text = "\n\n".join(full_text_parts)
    return {
        "extracted_text": extracted_text,
        "chunks": chunks,
        "metadata": metadata
    }
