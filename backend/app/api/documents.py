from pathlib import Path
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from app.db.base import get_db
from app.db.models import Document, Chunk, Entity
from app.schemas.document import DocumentSchema, DocumentDetailSchema
from app.schemas.search import ContextDetailResponse
from app.services.query_parser import parse_query
from app.services.context_explainer import generate_context_explanation

router = APIRouter(prefix="/api/documents", tags=["Documents"])

@router.get("", response_model=List[DocumentSchema])
def list_documents(
    search: Optional[str] = None,
    file_type: Optional[str] = None,
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db)
):
    """
    List all currently indexed files in the digital memory with search, filter, and pagination.
    """
    query = db.query(Document)
    if search:
        query = query.filter(Document.filename.ilike(f"%{search}%"))
    if file_type:
        query = query.filter(Document.file_type == file_type.lower())

    # Do not expose stale index rows for files that were moved or deleted.
    # Search already applies the same guard; the file browser must stay
    # consistent with search and download behavior.
    docs = [
        doc for doc in query.order_by(Document.indexed_at.desc()).all()
        if Path(doc.filepath).exists()
    ][offset:offset + limit]

    results = []
    for doc in docs:
        doc_dict = {
            "id": doc.id,
            "filename": doc.filename,
            "filepath": doc.filepath,
            "file_type": doc.file_type,
            "file_size": doc.file_size or 0,
            "created_at": doc.created_at,
            "modified_at": doc.modified_at,
            "source": doc.source,
            "summary": doc.summary or "",
            "indexed_at": doc.indexed_at,
            "entities": doc.entities,
            "chunk_count": len(doc.chunks)
        }
        results.append(DocumentSchema(**doc_dict))

    return results

@router.delete("", status_code=status.HTTP_200_OK)
@router.delete("/", status_code=status.HTTP_200_OK)
def delete_all_documents(db: Session = Depends(get_db)):
    """
    Clears the entire index without deleting the original files on disk.
    """
    from app.services.indexer import indexing_status

    documents = db.query(Document).all()
    removed_count = len(documents)
    
    # Delete entities and chunks then documents
    db.query(Entity).delete()
    db.query(Chunk).delete()
    db.query(Document).delete()
    db.commit()

    # Reset indexing status
    indexing_status.is_indexing = False
    indexing_status.total_files = 0
    indexing_status.processed_files = 0
    indexing_status.documents_count = 0
    indexing_status.images_count = 0
    indexing_status.other_count = 0
    indexing_status.current_file = ""
    indexing_status.current_stage = "Idle"
    indexing_status.error_message = None
    indexing_status.last_indexed_at = None

    return {
        "status": "success",
        "removed_count": removed_count,
        "message": (
            f"Removed {removed_count} indexed file"
            f"{'' if removed_count == 1 else 's'} from memory. "
            "Original files were not deleted."
        ),
    }

@router.delete("/{document_id}", status_code=status.HTTP_200_OK)
def delete_document(document_id: str, db: Session = Depends(get_db)):
    """
    Removes a document and all its chunks and entities from the index.
    """
    from app.services.indexer import indexing_status

    doc = db.query(Document).filter(Document.id == document_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found.")

    filename = doc.filename
    db.delete(doc)
    db.commit()

    # Update real-time counts
    total_docs = db.query(Document).count()
    indexing_status.processed_files = total_docs
    indexing_status.total_files = total_docs
    docs = db.query(Document.file_type).all()
    doc_count = sum(1 for d in docs if d[0] in ("pdf", "docx", "pptx", "txt"))
    img_count = sum(1 for d in docs if d[0] in ("png", "jpg", "jpeg", "webp", "gif", "bmp", "tiff", "heic", "heif"))
    indexing_status.documents_count = doc_count
    indexing_status.images_count = img_count
    indexing_status.other_count = max(0, total_docs - doc_count - img_count)

    return {
        "status": "success",
        "message": f"Successfully removed '{filename}' from digital memory index."
    }

@router.get("/{document_id}", response_model=DocumentDetailSchema)
def get_document_detail(document_id: str, db: Session = Depends(get_db)):
    doc = db.query(Document).filter(Document.id == document_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found.")

    return DocumentDetailSchema(
        id=doc.id,
        filename=doc.filename,
        filepath=doc.filepath,
        file_type=doc.file_type,
        file_size=doc.file_size or 0,
        created_at=doc.created_at,
        modified_at=doc.modified_at,
        source=doc.source,
        extracted_text=doc.extracted_text or "",
        summary=doc.summary or "",
        indexed_at=doc.indexed_at,
        entities=doc.entities,
        chunks=doc.chunks,
        chunk_count=len(doc.chunks)
    )

@router.get("/{document_id}/context", response_model=ContextDetailResponse)
def get_document_context(
    document_id: str,
    q: str = Query("", description="Original search query to ground context against"),
    score: float = Query(0.94, description="Calculated match score"),
    score_label: str = Query("Strong match", description="Calculated match label"),
    db: Session = Depends(get_db)
):
    """
    Signature 'Show Context' feature.
    Returns side-by-side verified evidence comparing remembered clues to actual document content.
    """
    doc = db.query(Document).filter(Document.id == document_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found.")

    clues = parse_query(q) if q else parse_query(doc.filename)
    return generate_context_explanation(doc, clues, score, score_label)

@router.get("/{document_id}/download")
def download_document(document_id: str, db: Session = Depends(get_db)):
    """
    Allows user to open/download the original indexed file.
    """
    doc = db.query(Document).filter(Document.id == document_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found.")

    file_path = Path(doc.filepath)
    if not file_path.exists():
        raise HTTPException(status_code=404, detail=f"File not found on disk: {doc.filepath}")

    return FileResponse(
        path=str(file_path),
        filename=doc.filename,
        media_type="application/octet-stream"
    )
