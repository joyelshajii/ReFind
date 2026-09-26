from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel

class EntitySchema(BaseModel):
    id: Optional[str] = None
    entity_type: str
    entity_value: str

    class Config:
        from_attributes = True

class ChunkSchema(BaseModel):
    id: Optional[str] = None
    document_id: Optional[str] = None
    content: str
    page_number: Optional[int] = None
    slide_number: Optional[int] = None

    class Config:
        from_attributes = True

class DocumentSchema(BaseModel):
    id: str
    filename: str
    filepath: str
    file_type: str
    file_size: int
    created_at: datetime
    modified_at: datetime
    source: str
    summary: Optional[str] = ""
    indexed_at: datetime
    entities: List[EntitySchema] = []
    chunk_count: Optional[int] = 0

    class Config:
        from_attributes = True

class DocumentDetailSchema(DocumentSchema):
    extracted_text: str
    chunks: List[ChunkSchema] = []
