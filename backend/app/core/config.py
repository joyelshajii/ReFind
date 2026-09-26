import os
from pathlib import Path
from typing import List
from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parent.parent.parent
PROJECT_ROOT = BASE_DIR.parent if BASE_DIR.name == "backend" else BASE_DIR

class Settings(BaseSettings):
    PROJECT_NAME: str = "ReFind"
    TAGLINE: str = "Find what you remember."
    TEAM_NAME: str = "BitByBit"
    VERSION: str = "0.1.0"
    
    # Server
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    CORS_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:8000",
    ]
    
    # Database (PostgreSQL with pgvector or fallback SQLite)
    DATABASE_URL: str = ""
    SQLITE_FALLBACK_PATH: str = str(BASE_DIR / "refind_local.db")
    
    # Storage
    STORAGE_DIR: str = str(BASE_DIR / "storage")
    UPLOAD_DIR: str = str(BASE_DIR / "storage" / "uploads")
    DEMO_DATA_DIR: str = str(BASE_DIR / "demo_data")
    
    # AI & Embeddings
    EMBEDDING_PROVIDER: str = "gemini" # local, gemini, openai, jina
    EMBEDDING_DIMENSION: int = 768     # 768 for gemini-embedding-2
    LLM_PROVIDER: str = "gemini"       # local, gemini, openai
    JINA_API_KEY: str = ""
    JINA_EMBEDDING_MODEL: str = "jina-embeddings-v3"
    JINA_EMBEDDING_DIMENSION: int = 1024
    JINA_RERANKER_MODEL: str = "jina-reranker-v2-base-multilingual"
    JINA_TIMEOUT_SECONDS: float = 30.0
    
    GEMINI_API_KEY: str = ""
    GEMINI_MODEL: str = "gemini-3.5-flash-lite"
    GEMINI_REASONING_MODEL: str = "gemini-3.8-flash"
    GEMINI_EMBEDDING_MODEL: str = "gemini-embedding-2"
    OPENAI_API_KEY: str = ""
    
    # Chunking Configuration
    CHUNK_SIZE: int = 800
    CHUNK_OVERLAP: int = 150
    
    # Candidate Retrieval Limits
    RETRIEVAL_CANDIDATE_LIMIT: int = 40
    RERANKER_TOP_K: int = 10
    
    # Search Weights (Modular hybrid ranking: semantic, reranker, keyword, metadata, filename)
    WEIGHT_SEMANTIC: float = 0.45
    WEIGHT_RERANKER: float = 0.20
    WEIGHT_KEYWORD: float = 0.15
    WEIGHT_METADATA: float = 0.10
    WEIGHT_FILENAME: float = 0.10

    model_config = SettingsConfigDict(
        env_file=[str(PROJECT_ROOT / ".env"), str(BASE_DIR / ".env"), ".env"],
        extra="ignore"
    )

settings = Settings()

# Ensure required directories exist
os.makedirs(settings.STORAGE_DIR, exist_ok=True)
os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
os.makedirs(settings.DEMO_DATA_DIR, exist_ok=True)
