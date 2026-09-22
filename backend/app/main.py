"""GraphIntel FastAPI application.

Wires the routers, configures logging, initializes the database schema on
startup, and exposes health/readiness endpoints. Runs fully offline with the
default settings (SQLite + in-process graph + deterministic embeddings/LLM).
"""
from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routers import admin, ask, evaluation, graph, ingestion
from app.config import get_settings
from app.db import init_db
from app.logging_config import configure_logging, get_logger

configure_logging()
log = get_logger("api")


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    init_db()
    log.info("startup", env=settings.env, sqlite=settings.is_sqlite,
             graph_backend=settings.graph_backend, llm=settings.llm_provider,
             extraction=settings.extraction_provider, embeddings=settings.embedding_provider)
    yield
    log.info("shutdown")


app = FastAPI(
    title="GraphIntel API",
    version="0.1.0",
    description="Graph RAG platform for support & incident intelligence.",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=get_settings().cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health", tags=["meta"])
def health() -> dict:
    return {"status": "ok"}


@app.get("/ready", tags=["meta"])
def ready() -> dict:
    settings = get_settings()
    safety_errors = settings.production_safety_errors()
    return {
        "status": "not_ready" if safety_errors else "ready",
        "database": "sqlite" if settings.is_sqlite else "postgres",
        "graph": "neptune" if settings.use_neptune else "sql",
        "llm": settings.llm_provider,
        "extraction": settings.extraction_provider,
        "embeddings": settings.embedding_provider,
        "production_safety_errors": safety_errors,
    }


for _router in (ingestion.router, graph.router, ask.router, evaluation.router, admin.router):
    app.include_router(_router)
