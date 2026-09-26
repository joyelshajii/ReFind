import logging
import json
from typing import Generator
from sqlalchemy import create_engine, text
from sqlalchemy.orm import declarative_base, sessionmaker, Session
from app.core.config import settings

logger = logging.getLogger("refind.db")

Base = declarative_base()

is_postgres_active = False
is_pgvector_active = False

def create_db_engine():
    global is_postgres_active, is_pgvector_active
    
    if settings.DATABASE_URL and settings.DATABASE_URL.startswith("postgres"):
        try:
            logger.info("Attempting to connect to PostgreSQL with pgvector...")
            pg_engine = create_engine(settings.DATABASE_URL, pool_pre_ping=True)
            with pg_engine.connect() as conn:
                conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector;"))
                conn.commit()
            is_postgres_active = True
            is_pgvector_active = True
            logger.info("Successfully connected to PostgreSQL with pgvector extension enabled.")
            return pg_engine
        except Exception as e:
            logger.warning(f"PostgreSQL connection failed: {e}. Falling back to local SQLite vector store.")
    
    # Fallback SQLite with 60s busy timeout and thread safety
    sqlite_url = f"sqlite:///{settings.SQLITE_FALLBACK_PATH}"
    logger.info(f"Using local database: {sqlite_url}")
    engine = create_engine(sqlite_url, connect_args={"check_same_thread": False, "timeout": 60})
    return engine

engine = create_db_engine()

from sqlalchemy import event

@event.listens_for(engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    if not is_postgres_active:
        try:
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA journal_mode=WAL;")
            cursor.execute("PRAGMA busy_timeout=60000;")
            cursor.execute("PRAGMA synchronous=NORMAL;")
            cursor.close()
        except Exception as pe:
            logger.debug(f"SQLite PRAGMA error: {pe}")

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def init_db():
    from app.db import models
    Base.metadata.create_all(bind=engine)
    
    # Safe lightweight migration for missing columns on existing SQLite/Postgres DB
    with engine.connect() as conn:
        try:
            conn.execute(text("ALTER TABLE documents ADD COLUMN file_hash VARCHAR(64) DEFAULT '';"))
            conn.commit()
        except Exception:
            pass # Already exists

        try:
            conn.execute(text("ALTER TABLE chunks ADD COLUMN chunk_index INTEGER DEFAULT 0;"))
            conn.commit()
        except Exception:
            pass # Already exists

    logger.info("Database tables and migration verified/created.")
