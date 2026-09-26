from datetime import datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel

class SearchRequest(BaseModel):
    query: str
    top_k: int = 10

class QueryClues(BaseModel):
    raw_query: str
    intent: str = "find_content"
    file_type: Optional[str] = None
    topics: List[str] = []
    people: List[str] = []
    technologies: List[str] = []
    time_clues: List[str] = []
    keywords: List[str] = []

class EvidenceItem(BaseModel):
    clue_name: str
    clue_type: str # person, date, tech, topic, file_type
    matched_text: str
    location: Optional[str] = None # e.g. "Page 1", "Metadata: modified_at", "Slide 3"
    verified: bool = True

class SearchResultItem(BaseModel):
    document_id: str
    filename: str
    filepath: str
    file_type: str
    file_size: int
    modified_at: datetime
    score: float # 0.0 to 1.0
    score_label: str # "Strong match", "Good match", "Relevant"
    snippet: str
    page_or_slide: Optional[str] = None
    matching_clues: List[str] = []
    detected_entities: List[str] = []
    evidence: List[EvidenceItem] = []
    ai_explanation: Optional[str] = None # Generated via Gemini 2.5 Flash Lite grounded in retrieved chunks

class SearchResponse(BaseModel):
    query: str
    clues: QueryClues
    total_results: int
    results: List[SearchResultItem]
    processing_time_ms: float

class ContextDetailResponse(BaseModel):
    document_id: str
    filename: str
    file_type: str
    score: float
    score_label: str
    memory_clues: List[str]
    document_evidence: List[EvidenceItem]
    snippets: List[str]
    ai_explanation: Optional[str] = None
