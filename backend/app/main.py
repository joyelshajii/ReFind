import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.db.base import init_db
from app.api import search, documents, index, demo, health

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("refind")

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Initializing ReFind database schema...")
    init_db()
    logger.info("ReFind backend started successfully.")
    yield
    logger.info("ReFind backend shutting down.")

app = FastAPI(
    title="ReFind API",
    description="Context-Aware Digital Memory Search System by BitByBit",
    version=settings.VERSION,
    lifespan=lifespan
)

# CORS setup for Next.js frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount API Routers
app.include_router(health.router)
app.include_router(search.router)
app.include_router(documents.router)
app.include_router(index.router)
app.include_router(demo.router)

@app.get("/")
def root():
    return {
        "product": settings.PROJECT_NAME,
        "tagline": settings.TAGLINE,
        "team": settings.TEAM_NAME,
        "docs": "/docs",
        "health": "/api/health"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host=settings.HOST, port=settings.PORT, reload=True)
