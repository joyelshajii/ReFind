from pathlib import Path
from typing import Dict, Any, Callable
from app.processors.pdf_processor import process_pdf
from app.processors.docx_processor import process_docx
from app.processors.pptx_processor import process_pptx
from app.processors.txt_processor import process_txt
from app.processors.image_processor import process_image

SUPPORTED_EXTENSIONS = {
    ".pdf": "pdf",
    ".docx": "docx",
    ".pptx": "pptx",
    ".txt": "txt",
    ".md": "txt",
    ".png": "png",
    ".jpg": "jpg",
    ".jpeg": "jpeg",
    ".webp": "webp",
    ".gif": "gif",
    ".bmp": "bmp",
    ".tif": "tiff",
    ".tiff": "tiff",
    ".heic": "heic",
    ".heif": "heif",
    ".jfif": "jpeg",
}

PROCESSORS: Dict[str, Callable[[str], Dict[str, Any]]] = {
    "pdf": process_pdf,
    "docx": process_docx,
    "pptx": process_pptx,
    "txt": process_txt,
    "png": process_image,
    "jpg": process_image,
    "jpeg": process_image,
    "webp": process_image,
    "gif": process_image,
    "bmp": process_image,
    "tiff": process_image,
    "heic": process_image,
    "heif": process_image,
}

def get_file_type(file_path: str) -> str:
    ext = Path(file_path).suffix.lower()
    return SUPPORTED_EXTENSIONS.get(ext, "unknown")

def process_file(file_path: str) -> Dict[str, Any]:
    file_type = get_file_type(file_path)
    processor = PROCESSORS.get(file_type)
    if not processor:
        # Fallback to plain text processor
        return process_txt(file_path)
    return processor(file_path)
