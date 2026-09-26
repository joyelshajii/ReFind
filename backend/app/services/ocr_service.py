import logging
from typing import List, Dict, Any, Optional
from pathlib import Path
from PIL import Image
from app.core.config import settings

logger = logging.getLogger("refind.services.ocr")

class OCRService:
    def __init__(self):
        self._paddleocr = None
        self._paddleocr_failed = False

    def _get_paddleocr(self):
        if self._paddleocr is None and not self._paddleocr_failed:
            try:
                from paddleocr import PaddleOCR
                # Initialize local paddleocr for English / multilingual text
                self._paddleocr = PaddleOCR(use_angle_cls=True, lang="en")
                logger.info("PaddleOCR initialized successfully.")
            except Exception as e:
                logger.warning(f"PaddleOCR initialization failed: {e}. Will fall back to pytesseract / other methods.")
                self._paddleocr_failed = True
        return self._paddleocr

    def extract_text_from_image(self, image_path: str) -> List[str]:
        """
        Extracts text locally from an image file (PNG, JPG, JPEG, screenshots).
        Uses PaddleOCR first, then falls back to pytesseract if needed.
        Never sends user documents to Gemini for text extraction.
        """
        lines: List[str] = []
        path = Path(image_path)
        if not path.exists():
            return lines

        # 1. Try PaddleOCR
        ocr = self._get_paddleocr()
        if ocr is not None:
            try:
                result = ocr.ocr(str(path), cls=True)
                if result:
                    for line_group in result:
                        if line_group:
                            for line_info in line_group:
                                if len(line_info) > 1 and len(line_info[1]) > 0:
                                    text = line_info[1][0].strip()
                                    if text:
                                        lines.append(text)
                if lines:
                    return lines
            except Exception as pe:
                logger.warning(f"PaddleOCR extraction failed on {path.name}: {pe}")

        # 2. Fallback to pytesseract if available
        try:
            import pytesseract
            with Image.open(str(path)) as img:
                raw_text = pytesseract.image_to_string(img)
                if raw_text and raw_text.strip():
                    for line in raw_text.splitlines():
                        if line.strip():
                            lines.append(line.strip())
        except Exception as te:
            logger.debug(f"Pytesseract fallback skipped/failed on {path.name}: {te}")

        return lines

    def extract_text_from_scanned_pdf_page(self, page_pixmap) -> str:
        """
        Extracts OCR text from a rendered PyMuPDF Pixmap.
        """
        try:
            import numpy as np
            import io
            img_bytes = page_pixmap.tobytes("png")
            img = Image.open(io.BytesIO(img_bytes))
            
            ocr = self._get_paddleocr()
            if ocr is not None:
                img_np = np.array(img)
                result = ocr.ocr(img_np, cls=True)
                extracted = []
                if result:
                    for line_group in result:
                        if line_group:
                            for line_info in line_group:
                                if len(line_info) > 1 and len(line_info[1]) > 0:
                                    t = line_info[1][0].strip()
                                    if t:
                                        extracted.append(t)
                if extracted:
                    return "\n".join(extracted)

            # Fallback
            import pytesseract
            return pytesseract.image_to_string(img).strip()
        except Exception as e:
            logger.debug(f"Pixmap OCR failed: {e}")
            return ""

ocr_service = OCRService()
