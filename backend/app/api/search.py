import time
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.db.base import get_db
from app.schemas.search import SearchRequest, SearchResponse
from app.services.query_parser import parse_query
from app.services.hybrid_search import search_documents

router = APIRouter(prefix="/api/search", tags=["Search"])

@router.post("", response_model=SearchResponse)
def execute_search(payload: SearchRequest, db: Session = Depends(get_db)):
    """
    Decomposes natural language query into structured memory clues,
    performs hybrid retrieval across semantic, keyword, metadata, and entity vectors,
    and returns ranked results with verified match evidence.
    """
    start_time = time.time()
    
    if not payload.query or not payload.query.strip():
        raise HTTPException(status_code=400, detail="Query string cannot be empty.")

    # 1. Natural Language Query Understanding
    clues = parse_query(payload.query)

    # 2. Hybrid Retrieval & Ranking
    results = search_documents(
        query=payload.query,
        clues=clues,
        db=db,
        top_k=payload.top_k
    )

    elapsed_ms = round((time.time() - start_time) * 1000, 2)

    return SearchResponse(
        query=payload.query,
        clues=clues,
        total_results=len(results),
        results=results,
        processing_time_ms=elapsed_ms
    )
