import os
import re
import hashlib
import logging
from datetime import datetime
from typing import List, Dict, Any, Optional
from pathlib import Path
from sqlalchemy.orm import Session
from app.db.base import SessionLocal
from app.db.models import Document, Chunk, Entity
from app.schemas.index import IndexProgressStatus
from app.processors.factory import process_file, get_file_type
from app.connectors.local_source import LocalFileSource
from app.services.embedding_service import get_embedding
from app.services.query_parser import COMMON_TECH, COMMON_TOPICS

logger = logging.getLogger("refind.services.indexer")

indexing_status = IndexProgressStatus()

def compute_file_hash(filepath: str) -> str:
    """
    Computes SHA-256 hash of a file to detect whether it has changed.
    """
    h = hashlib.sha256()
    try:
        with open(filepath, "rb") as f:
            while chunk := f.read(65536):
                h.update(chunk)
        return h.hexdigest()
    except Exception as e:
        logger.warning(f"Error computing hash for {filepath}: {e}")
        return ""

def extract_entities_from_text(text: str) -> List[Dict[str, str]]:
    """
    Extracts high-value domain entities (technologies, people, topics) from document text.
    """
    entities: List[Dict[str, str]] = []
    lower = text.lower()

    # Technologies
    for tech in COMMON_TECH:
        pattern = r"\b" + re.escape(tech) + r"\b"
        if re.search(pattern, lower):
            entities.append({
                "entity_type": "technology",
                "entity_value": tech.upper() if tech in ("ble", "iot", "api", "rest") else tech.title()
            })

    # Topics
    for top in COMMON_TOPICS:
        pattern = r"\b" + re.escape(top) + r"\b"
        if re.search(pattern, lower):
            entities.append({
                "entity_type": "topic",
                "entity_value": top.title()
            })

    # People detection
    name_patterns = [
        r"\b(?:Author|Sent by|Shared by|Presenter|Owner):\s*([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)\b",
        r"\b([A-Z][a-z]+)\s+sent\s+this\b",
        r"\b(?:with|from)\s+([A-Z][a-z]+)\b",
    ]
    for np in name_patterns:
        matches = re.findall(np, text)
        for m in matches:
            if m.lower() not in ("the", "find", "document", "architecture"):
                entities.append({
                    "entity_type": "person",
                    "entity_value": m.strip()
                })

    # Deduplicate
    unique = []
    seen = set()
    for e in entities:
        key = (e["entity_type"], e["entity_value"].lower())
        if key not in seen:
            seen.add(key)
            unique.append(e)

    return unique

def index_folder_background(folder_path: str):
    """
    Background worker that runs the multi-stage indexing workflow:
    Reading -> Extracting -> Understanding -> Indexing
    Includes caching: if a file has not changed (same hash/mtime), skips re-indexing.
    """
    global indexing_status
    indexing_status.is_indexing = True
    indexing_status.current_stage = "Reading"
    indexing_status.total_files = 0
    indexing_status.processed_files = 0
    indexing_status.documents_count = 0
    indexing_status.images_count = 0
    indexing_status.other_count = 0
    indexing_status.error_message = None

    db: Session = SessionLocal()
    try:
        source = LocalFileSource()
        files = source.scan(folder_path)
        indexing_status.total_files = len(files)

        for f in files:
            ftype = f["file_type"]
            if ftype in ("pdf", "docx", "pptx", "txt"):
                indexing_status.documents_count += 1
            elif ftype in ("png", "jpg", "jpeg", "webp", "gif", "bmp", "tiff", "heic", "heif"):
                indexing_status.images_count += 1
            else:
                indexing_status.other_count += 1

        for idx, file_info in enumerate(files):
            filepath = file_info["filepath"]
            filename = file_info["filename"]
            indexing_status.current_file = filename

            # Compute hash to detect if unchanged
            current_hash = compute_file_hash(filepath)
            existing_doc = db.query(Document).filter(Document.filepath == filepath).first()

            if existing_doc and existing_doc.file_hash == current_hash and current_hash:
                is_image = file_info["file_type"] in ("png", "jpg", "jpeg", "webp", "gif", "bmp", "tiff", "heic", "heif")
                needs_enrichment = is_image and ("Visual Description:" not in (existing_doc.extracted_text or "") and "Detected Text" not in (existing_doc.extracted_text or ""))
                if not needs_enrichment:
                    logger.info(f"Skipping unchanged document: {filename} (hash match)")
                    indexing_status.processed_files = idx + 1
                    continue

            # Stage 2: Extracting
            indexing_status.current_stage = "Extracting"
            try:
                extracted_data = process_file(filepath)
                extracted_text = extracted_data.get("extracted_text", "")
                raw_chunks = extracted_data.get("chunks", [])
            except Exception as file_error:
                logger.error("Failed to process %s: %s", filepath, file_error, exc_info=True)
                indexing_status.error_message = f"{filename}: {file_error}"
                indexing_status.processed_files = idx + 1
                continue

            # Stage 3: Understanding
            indexing_status.current_stage = "Understanding"
            doc_embedding = get_embedding(extracted_text[:1500] if extracted_text else filename)
            entities_data = extract_entities_from_text(extracted_text)
            if "entities" in extracted_data:
                for ent in extracted_data["entities"]:
                    if ent not in entities_data:
                        entities_data.append(ent)

            if existing_doc:
                db.delete(existing_doc)
                db.flush()

            # Stage 4: Indexing
            indexing_status.current_stage = "Indexing"
            doc = Document(
                filename=filename,
                filepath=filepath,
                file_type=file_info["file_type"],
                file_size=file_info["file_size"],
                file_hash=current_hash,
                created_at=file_info["created_at"],
                modified_at=file_info["modified_at"],
                source="local",
                extracted_text=extracted_text,
                summary=extracted_text[:300] if extracted_text else "",
                indexed_at=datetime.utcnow()
            )
            doc.set_embedding(doc_embedding)
            db.add(doc)
            db.flush()

            for chunk_idx, c in enumerate(raw_chunks):
                chunk_text = c.get("content", "").strip()
                if not chunk_text:
                    continue
                c_emb = get_embedding(chunk_text)
                chunk_model = Chunk(
                    document_id=doc.id,
                    chunk_index=chunk_idx,
                    content=chunk_text,
                    page_number=c.get("page_number"),
                    slide_number=c.get("slide_number")
                )
                chunk_model.set_embedding(c_emb)
                db.add(chunk_model)

            for ent in entities_data:
                e_model = Entity(
                    document_id=doc.id,
                    entity_type=ent["entity_type"],
                    entity_value=ent["entity_value"]
                )
                db.add(e_model)

            db.commit()
            indexing_status.processed_files = idx + 1

        indexing_status.current_stage = "Complete"
        indexing_status.last_indexed_at = datetime.utcnow()
        indexing_status.is_indexing = False
        indexing_status.current_file = None
        logger.info(f"Indexing completed: {len(files)} files processed.")

    except Exception as e:
        logger.error(f"Indexing failed: {e}", exc_info=True)
        indexing_status.error_message = str(e)
        indexing_status.is_indexing = False
        indexing_status.current_stage = "Error"
    finally:
        db.close()

def index_single_file(filepath: str, db: Session) -> Document:
    """
    Synchronously indexes a single uploaded or new file.
    Includes unchanged-file check: does not regenerate embeddings if unchanged.
    """
    path = Path(filepath)
    file_type = get_file_type(filepath)
    stat = path.stat()
    current_hash = compute_file_hash(filepath)

    existing_doc = db.query(Document).filter(Document.filepath == str(path.resolve())).first()
    if existing_doc and existing_doc.file_hash == current_hash and current_hash:
        is_image = file_type in ("png", "jpg", "jpeg", "webp", "gif", "bmp", "tiff", "heic", "heif")
        needs_enrichment = is_image and ("Visual Description:" not in (existing_doc.extracted_text or "") and "Detected Text" not in (existing_doc.extracted_text or ""))
        if not needs_enrichment:
            logger.info(f"File {path.name} is unchanged. Returning existing indexed document.")
            return existing_doc
    
    extracted_data = process_file(filepath)
    extracted_text = extracted_data.get("extracted_text", "")
    raw_chunks = extracted_data.get("chunks", [])

    doc_embedding = get_embedding(extracted_text[:1500] if extracted_text else path.name)
    entities_data = extract_entities_from_text(extracted_text)
    if "entities" in extracted_data:
        for ent in extracted_data["entities"]:
            if ent not in entities_data:
                entities_data.append(ent)

    if existing_doc:
        db.delete(existing_doc)
        db.flush()

    doc = Document(
        filename=path.name,
        filepath=str(path.resolve()),
        file_type=file_type,
        file_size=stat.st_size,
        file_hash=current_hash,
        created_at=datetime.fromtimestamp(stat.st_ctime),
        modified_at=datetime.fromtimestamp(stat.st_mtime),
        source="local",
        extracted_text=extracted_text,
        summary=extracted_text[:300] if extracted_text else "",
        indexed_at=datetime.utcnow()
    )
    doc.set_embedding(doc_embedding)
    db.add(doc)
    db.flush()

    for chunk_idx, c in enumerate(raw_chunks):
        c_text = c.get("content", "").strip()
        if not c_text:
            continue
        c_emb = get_embedding(c_text)
        chunk = Chunk(
            document_id=doc.id,
            chunk_index=chunk_idx,
            content=c_text,
            page_number=c.get("page_number"),
            slide_number=c.get("slide_number")
        )
        chunk.set_embedding(c_emb)
        db.add(chunk)

    for ent in entities_data:
        e = Entity(
            document_id=doc.id,
            entity_type=ent["entity_type"],
            entity_value=ent["entity_value"]
        )
        db.add(e)

    db.commit()
    db.refresh(doc)
    return doc
