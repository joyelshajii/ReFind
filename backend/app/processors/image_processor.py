import io
import json
import logging
import os
import re
from typing import Dict, Any, List
from pathlib import Path
from PIL import Image
from PIL.ExifTags import TAGS
from app.core.config import settings

logger = logging.getLogger("refind.processors.image")

# Register HEIF/HEIC opener support if pillow-heif is available
try:
    import pillow_heif
    pillow_heif.register_heif_opener()
except Exception:
    pass

_rapid_ocr = None

def _get_rapid_ocr():
    global _rapid_ocr
    if _rapid_ocr is None:
        try:
            from rapidocr_onnxruntime import RapidOCR
            _rapid_ocr = RapidOCR()
        except Exception:
            _rapid_ocr = False
    return _rapid_ocr if _rapid_ocr else None

def _clean_str(val: Any) -> str:
    """Removes null bytes and non-printable noise from strings (e.g. corrupted EXIF tags)."""
    if val is None:
        return ""
    if isinstance(val, bytes):
        try:
            val = val.decode("utf-8", errors="ignore")
        except Exception:
            return ""
    s = str(val).replace("\x00", "").strip()
    return s

def _parse_gemini_vision_output(raw_text: str) -> Dict[str, Any]:
    """Parses structured fields from Gemini Vision response."""
    result = {
        "visual_description": "",
        "detected_text": [],
        "entities": []
    }
    if not raw_text:
        return result

    # Extract Visual Description
    vd_match = re.search(r"Visual Description:\s*(.*?)(?=\n\s*(?:Detected Text|Key Entities):|$)", raw_text, re.DOTALL | re.IGNORECASE)
    if vd_match:
        result["visual_description"] = vd_match.group(1).strip()

    # Extract Detected Text
    dt_match = re.search(r"Detected Text:\s*(.*?)(?=\n\s*Key Entities:|$)", raw_text, re.DOTALL | re.IGNORECASE)
    if dt_match:
        dt_raw = dt_match.group(1).strip()
        if dt_raw.lower() not in ("none", "none.", "n/a", "no text", "no text detected"):
            for line in dt_raw.splitlines():
                clean_line = line.strip().lstrip("-*• ")
                if clean_line and clean_line.lower() != "none":
                    result["detected_text"].append(clean_line)

    # Extract Key Entities
    ke_match = re.search(r"Key Entities:\s*(.*?)$", raw_text, re.DOTALL | re.IGNORECASE)
    if ke_match:
        ke_raw = ke_match.group(1).strip()
        tags = [t.strip().lstrip("-*• ") for t in re.split(r"[,;\n]", ke_raw) if t.strip()]
        for tag in tags:
            if tag and len(tag) < 60 and tag.lower() not in ("none", "n/a"):
                result["entities"].append(tag)

    # Fallback if structure was slightly unaligned
    if not result["visual_description"] and not result["detected_text"]:
        result["visual_description"] = raw_text.strip()

    return result

def _analyze_image_with_gemini(img: Image.Image) -> Dict[str, Any]:
    """
    Uses Gemini Vision to produce an in-depth visual description, transcribe all text,
    and identify key scene entities. Resizes to max 1280px in memory for speed & efficiency.
    """
    if not settings.GEMINI_API_KEY:
        return {}

    try:
        from google import genai
        client = genai.Client(api_key=settings.GEMINI_API_KEY)

        # Scale down in-memory to max 1280px to make API payload fast (100-300KB)
        img_copy = img.copy().convert("RGB")
        img_copy.thumbnail((1280, 1280), Image.Resampling.LANCZOS)
        buf = io.BytesIO()
        img_copy.save(buf, format="JPEG", quality=85)
        image_bytes = buf.getvalue()

        prompt = """Analyze this image thoroughly for a personal search and memory indexing engine called ReFind.
Provide the output in exactly this format:

Visual Description:
[A detailed 2-4 sentence description of what is depicted in the image: the scene, subjects, people, actions, physical setting, appearance, clothing, colors, objects, diagrams, charts, UI elements, or documents]

Detected Text:
[Verbatim transcription of ALL text visible anywhere in the image, including headers, labels, captions, signs, handwriting, code, or UI text. If none, write: None]

Key Entities:
[Comma-separated list of 3 to 10 specific tags: topics, technologies, people, places, object categories, e.g. Rahul, BLE Beacon, Python, Architecture Diagram]
"""
        models_to_try = [settings.GEMINI_MODEL, "gemini-3.5-flash-lite", "gemini-3.8-flash"]
        for model_name in models_to_try:
            try:
                response = client.models.generate_content(
                    model=model_name,
                    contents=[
                        prompt,
                        genai.types.Part.from_bytes(data=image_bytes, mime_type="image/jpeg")
                    ]
                )
                if response and response.text:
                    return _parse_gemini_vision_output(response.text)
            except Exception as me:
                logger.warning(f"Gemini vision call failed with model {model_name}: {me}")
                continue

    except Exception as e:
        logger.warning(f"Gemini vision analysis failed: {e}")

    return {}

def process_image(file_path: str) -> Dict[str, Any]:
    """
    Extracts OCR text, visual description, and image metadata (dimensions, EXIF) from an image.
    Supports PNG, JPG, JPEG, WEBP, GIF, BMP, TIFF, HEIC, and HEIF.
    Integrates Gemini Multimodal Vision with local OCR fallback.
    """
    path = Path(file_path)
    metadata: Dict[str, Any] = {}
    ocr_lines: List[str] = []
    visual_description: str = ""
    discovered_entities: List[Dict[str, str]] = []

    try:
        with Image.open(str(path)) as img:
            metadata["dimensions"] = f"{img.width}x{img.height}"
            metadata["format"] = img.format or path.suffix.lstrip(".").upper()

            # Extract EXIF metadata if available (sanitized of null bytes)
            try:
                exif_data = img.getexif()
                if exif_data:
                    for tag_id, val in exif_data.items():
                        tag_name = TAGS.get(tag_id, str(tag_id))
                        if tag_name in ("DateTime", "DateTimeOriginal", "Make", "Model", "Software", "ImageDescription"):
                            clean_val = _clean_str(val)
                            if clean_val:
                                metadata[tag_name.lower()] = clean_val
                                if tag_name == "ImageDescription" and not visual_description:
                                    visual_description = clean_val
            except Exception as exif_err:
                logger.debug(f"EXIF extraction error for {path.name}: {exif_err}")

            # Check PNG info text chunks if present
            if hasattr(img, "info") and isinstance(img.info, dict):
                for k, v in img.info.items():
                    if isinstance(v, str) and len(v) < 1000:
                        clean_v = _clean_str(v)
                        if clean_v:
                            metadata[f"png_{k.lower()}"] = clean_v
                            if k.lower() in ("description", "comment", "title") and not visual_description:
                                visual_description = clean_v

            # 1. AI Multimodal Vision Analysis (Visual description + OCR + Entities)
            ai_result = _analyze_image_with_gemini(img)
            if ai_result:
                if ai_result.get("visual_description"):
                    visual_description = ai_result["visual_description"]
                if ai_result.get("detected_text"):
                    for line in ai_result["detected_text"]:
                        if line not in ocr_lines:
                            ocr_lines.append(line)
                if ai_result.get("entities"):
                    for tag in ai_result["entities"]:
                        discovered_entities.append({
                            "entity_type": "topic",
                            "entity_value": tag
                        })

            # 2. Local OCR Fallback if Gemini Vision is unavailable or detected no text
            if not ocr_lines:
                # Try OCR service (PaddleOCR / Tesseract)
                try:
                    from app.services.ocr_service import ocr_service
                    local_lines = ocr_service.extract_text_from_image(str(path))
                    for line in local_lines:
                        clean_line = _clean_str(line)
                        if clean_line and clean_line not in ocr_lines:
                            ocr_lines.append(clean_line)
                except Exception as local_ocr_err:
                    logger.debug(f"Local OCR service skipped for {path.name}: {local_ocr_err}")

                # RapidOCR fallback if available
                if not ocr_lines:
                    rapid_ocr = _get_rapid_ocr()
                    if rapid_ocr:
                        try:
                            ocr_result, _ = rapid_ocr(str(path))
                            for item in ocr_result or []:
                                if len(item) >= 2 and str(item[1]).strip():
                                    clean_line = _clean_str(item[1])
                                    if clean_line and clean_line not in ocr_lines:
                                        ocr_lines.append(clean_line)
                        except Exception as rapid_err:
                            logger.debug(f"RapidOCR skipped for {path.name}: {rapid_err}")

    except Exception as e:
        logger.error(f"Error opening image {file_path}: {e}")

    # Check companion metadata file if exists (e.g. for demo dataset: IMG_2384.png.meta.json)
    companion_meta = path.with_suffix(path.suffix + ".meta.json")
    if companion_meta.exists():
        try:
            with open(companion_meta, "r", encoding="utf-8") as f:
                comp = json.load(f)
                if "detected_text" in comp:
                    for item in comp["detected_text"]:
                        clean_item = _clean_str(item)
                        if clean_item and clean_item not in ocr_lines:
                            ocr_lines.append(clean_item)
                if "visual_description" in comp and not visual_description:
                    visual_description = _clean_str(comp["visual_description"])
                if "metadata" in comp:
                    for k, v in comp["metadata"].items():
                        clean_v = _clean_str(v)
                        if clean_v:
                            metadata[k] = clean_v
        except Exception as ce:
            logger.debug(f"Companion metadata read error: {ce}")

    # Include the filename/path
    metadata["filename"] = path.name
    metadata["source_path"] = str(path.parent)

    # Construct the rich searchable text representation
    text_blocks = []
    if visual_description:
        text_blocks.append(f"Visual Description:\n{visual_description}")
    if ocr_lines:
        text_blocks.append("Detected Text in Image:\n" + "\n".join(ocr_lines))
    if metadata:
        metadata_lines = [
            f"{key.replace('_', ' ').title()}: {value}"
            for key, value in metadata.items()
            if value is not None and str(value).strip()
        ]
        if metadata_lines:
            text_blocks.append("Image Metadata:\n" + "\n".join(metadata_lines))

    extracted_text = "\n\n".join(text_blocks)
    if not extracted_text:
        extracted_text = f"Image file: {path.name}, Format: {metadata.get('format', 'Image')}, Dimensions: {metadata.get('dimensions', 'unknown')}"

    chunk = {
        "content": extracted_text,
        "page_number": 1,
        "slide_number": None
    }

    return {
        "extracted_text": extracted_text,
        "chunks": [chunk],
        "metadata": metadata,
        "entities": discovered_entities
    }
