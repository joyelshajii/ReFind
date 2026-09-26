from fastapi import APIRouter
from app.core.config import settings
from app.db.base import is_postgres_active, is_pgvector_active

router = APIRouter(prefix="/api/health", tags=["Health"])

@router.get("")
def health_check():
    return {
        "status": "healthy",
        "product": settings.PROJECT_NAME,
        "tagline": settings.TAGLINE,
        "team": settings.TEAM_NAME,
        "version": settings.VERSION,
        "database": {
            "postgres_connected": is_postgres_active,
            "pgvector_enabled": is_pgvector_active,
            "engine": "PostgreSQL with pgvector" if is_pgvector_active else "Local SQLite + Cosine Vector Engine"
        },
        "providers": {
            "embedding": settings.EMBEDDING_PROVIDER,
            "llm": settings.LLM_PROVIDER
        }
    }
