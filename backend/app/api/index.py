import os
import shutil
from pathlib import Path
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, UploadFile, File
from sqlalchemy.orm import Session
from app.db.base import get_db, is_postgres_active, is_pgvector_active
from app.db.models import Document, Chunk
from app.schemas.index import IndexFolderRequest, IndexProgressStatus, IndexResponse
from app.connectors.local_source import LocalFileSource
from app.processors.factory import SUPPORTED_EXTENSIONS
from app.services.indexer import indexing_status, index_folder_background, index_single_file
from app.core.config import settings

router = APIRouter(prefix="/api/index", tags=["Indexing"])

@router.post("", response_model=IndexResponse)
def trigger_index(
    payload: Optional[IndexFolderRequest] = None,
    background_tasks: BackgroundTasks = BackgroundTasks()
):
    """
    Triggers indexing of a local directory. If no folder is provided,
    indexes the default uploads storage folder (or demo_data fallback).
    """
    global indexing_status
    if indexing_status.is_indexing:
        return IndexResponse(
            status="busy",
            message="Indexing is already in progress.",
            files_found=indexing_status.total_files
        )

    # Determine default target directory: prefer storage/uploads if populated, else demo_data
    if payload and payload.folder_path and payload.folder_path.strip():
        target_dir = payload.folder_path.strip()
    else:
        upload_path = Path(settings.UPLOAD_DIR)
        demo_path = Path(settings.DEMO_DATA_DIR)
        # Check if uploads directory has files
        if upload_path.exists() and any(upload_path.iterdir()):
            target_dir = str(upload_path)
        else:
            target_dir = str(demo_path)

    target_path = Path(target_dir).expanduser()
    if not target_path.exists():
        raise HTTPException(status_code=400, detail=f"Directory '{target_dir}' does not exist.")
    if not target_path.is_dir():
        raise HTTPException(status_code=400, detail=f"Path '{target_dir}' is not a directory.")

    discovered_files = LocalFileSource().scan(str(target_path))
    if not discovered_files:
        supported = ", ".join(sorted(SUPPORTED_EXTENSIONS.keys()))
        raise HTTPException(
            status_code=400,
            detail=f"No supported files found in '{target_dir}'. Supported formats: {supported}.",
        )

    # Start background processing
    background_tasks.add_task(index_folder_background, str(target_path.resolve()))

    return IndexResponse(
        status="started",
        message=f"Indexing initiated for '{target_dir}'",
        files_found=len(discovered_files)
    )

@router.get("/status", response_model=IndexProgressStatus)
def get_indexing_status(db: Session = Depends(get_db)):
    """
    Returns real-time progress status of the indexing pipeline.
    Always reflects real database numbers when indexing is idle or complete.
    """
    global indexing_status
    if not indexing_status.is_indexing:
        # Populate live counts directly from database
        total_docs = db.query(Document).count()
        indexing_status.processed_files = total_docs
        indexing_status.total_files = total_docs

        # Breakdown by file format
        docs = db.query(Document.file_type).all()
        doc_count = sum(1 for d in docs if d[0] in ("pdf", "docx", "pptx", "txt"))
        img_count = sum(1 for d in docs if d[0] in ("png", "jpg", "jpeg", "webp", "gif", "bmp", "tiff", "heic", "heif"))
        indexing_status.documents_count = doc_count
        indexing_status.images_count = img_count
        indexing_status.other_count = max(0, total_docs - doc_count - img_count)

        last_doc = db.query(Document).order_by(Document.indexed_at.desc()).first()
        if last_doc and last_doc.indexed_at:
            indexing_status.last_indexed_at = last_doc.indexed_at

    return indexing_status

@router.post("/upload")
def upload_and_index_files(
    files: List[UploadFile] = File(...),
    db: Session = Depends(get_db)
):
    """
    Accepts direct drag-and-drop file uploads and indexes them immediately.
    """
    global indexing_status
    indexed = []
    failed = []
    upload_dir = Path(settings.UPLOAD_DIR)
    upload_dir.mkdir(parents=True, exist_ok=True)

    for file in files:
        safe_filename = Path(file.filename).name
        dest_path = upload_dir / safe_filename
        try:
            with open(dest_path, "wb") as buffer:
                shutil.copyfileobj(file.file, buffer)

            doc = index_single_file(str(dest_path.resolve()), db)
            indexed.append({
                "id": doc.id,
                "filename": doc.filename,
                "file_type": doc.file_type,
                "file_size": doc.file_size
            })
        except Exception as upload_err:
            logger.error(f"Failed to index uploaded file {safe_filename}: {upload_err}", exc_info=True)
            failed.append({"filename": safe_filename, "error": str(upload_err)})

    # Update real-time status counts immediately
    total_docs = db.query(Document).count()
    indexing_status.processed_files = total_docs
    indexing_status.total_files = total_docs
    docs = db.query(Document.file_type).all()
    doc_count = sum(1 for d in docs if d[0] in ("pdf", "docx", "pptx", "txt"))
    img_count = sum(1 for d in docs if d[0] in ("png", "jpg", "jpeg", "webp", "gif", "bmp", "tiff", "heic", "heif"))
    indexing_status.documents_count = doc_count
    indexing_status.images_count = img_count
    indexing_status.other_count = max(0, total_docs - doc_count - img_count)
    indexing_status.current_stage = "Complete"

    return {
        "status": "success",
        "message": f"Successfully indexed {len(indexed)} files.",
        "files": indexed
    }

@router.get("/stats")
def get_index_stats(db: Session = Depends(get_db)):
    total_docs = db.query(Document).count()
    total_chunks = db.query(Chunk).count()
    last_doc = db.query(Document).order_by(Document.indexed_at.desc()).first()

    return {
        "total_documents": total_docs,
        "total_chunks": total_chunks,
        "last_indexed_at": last_doc.indexed_at if last_doc else None,
        "storage_source": "Local Files",
        "database_type": "PostgreSQL (pgvector)" if is_pgvector_active else "Local Vector Store (SQLite + Cosine)",
        "embedding_provider": settings.EMBEDDING_PROVIDER,
        "embedding_dimension": settings.EMBEDDING_DIMENSION
    }
