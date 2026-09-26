import json
import uuid
import hashlib
from datetime import datetime
from typing import List, Optional
from sqlalchemy import Column, String, Integer, BigInteger, Text, DateTime, ForeignKey, Index
from sqlalchemy.orm import relationship
from app.db.base import Base, is_pgvector_active
from app.core.config import settings

def generate_uuid() -> str:
    return str(uuid.uuid4())

class Document(Base):
    __tablename__ = "documents"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    filename = Column(String(512), nullable=False, index=True)
    filepath = Column(String(1024), nullable=False, unique=True, index=True)
    file_type = Column(String(64), nullable=False, index=True) # pdf, docx, pptx, txt, png, etc.
    file_size = Column(BigInteger, default=0)
    file_hash = Column(String(64), default="", index=True) # SHA-256 hash for unchanged-document caching
    created_at = Column(DateTime, default=datetime.utcnow)
    modified_at = Column(DateTime, default=datetime.utcnow)
    source = Column(String(128), default="local") # local, upload, etc.
    extracted_text = Column(Text, default="")
    summary = Column(Text, default="")
    embedding_json = Column(Text, default="[]") # JSON list of floats for universal compatibility
    indexed_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    chunks = relationship("Chunk", back_populates="document", cascade="all, delete-orphan")
    entities = relationship("Entity", back_populates="document", cascade="all, delete-orphan")

    def get_embedding(self) -> List[float]:
        try:
            return json.loads(self.embedding_json) if self.embedding_json else []
        except Exception:
            return []

    def set_embedding(self, vec: List[float]):
        self.embedding_json = json.dumps(vec)

class Chunk(Base):
    __tablename__ = "chunks"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    document_id = Column(String(36), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, index=True)
    chunk_index = Column(Integer, default=0)
    content = Column(Text, nullable=False)
    page_number = Column(Integer, nullable=True) # For PDF
    slide_number = Column(Integer, nullable=True) # For PPTX
    embedding_json = Column(Text, default="[]")

    document = relationship("Document", back_populates="chunks")

    def get_embedding(self) -> List[float]:
        try:
            return json.loads(self.embedding_json) if self.embedding_json else []
        except Exception:
            return []

    def set_embedding(self, vec: List[float]):
        self.embedding_json = json.dumps(vec)

class Entity(Base):
    __tablename__ = "entities"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    document_id = Column(String(36), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, index=True)
    entity_type = Column(String(64), nullable=False, index=True) # person, technology, topic, date, organization
    entity_value = Column(String(256), nullable=False, index=True)

    document = relationship("Document", back_populates="entities")
