"""SQLAlchemy ORM models.

PostgreSQL is the system of record for documents, chunks, jobs, the entity/
relation mirror, answers, audits, and evaluation runs. Amazon Neptune is the
production graph traversal backend, while the SQL mirror supports offline dev
and tests. All column types are portable so the same schema runs on SQLite.

Embeddings are stored as JSON here for portability; the vector store layer
(app/vector) handles similarity and can be pointed at a pgvector column in
production.
"""
from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


def _utcnow() -> datetime:
    return datetime.now(UTC)


class Document(Base):
    __tablename__ = "documents"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    job_id: Mapped[str | None] = mapped_column(ForeignKey("ingestion_jobs.id"), nullable=True)
    source_type: Mapped[str] = mapped_column(String(32))          # csv|json|markdown|txt
    source_kind: Mapped[str] = mapped_column(String(32), default="unknown")  # tickets|incidents|sla|runbook|postmortem
    filename: Mapped[str] = mapped_column(String(512))
    uri: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    sha256: Mapped[str] = mapped_column(String(64), index=True)
    title: Mapped[str | None] = mapped_column(String(512), nullable=True)
    content: Mapped[str] = mapped_column(Text, default="")
    meta: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    chunks: Mapped[list[Chunk]] = relationship(back_populates="document", cascade="all, delete-orphan")


class Chunk(Base):
    __tablename__ = "chunks"

    id: Mapped[str] = mapped_column(String(80), primary_key=True)
    document_id: Mapped[str] = mapped_column(ForeignKey("documents.id"), index=True)
    ordinal: Mapped[int] = mapped_column(Integer, default=0)
    text: Mapped[str] = mapped_column(Text)
    token_count: Mapped[int] = mapped_column(Integer, default=0)
    meta: Mapped[dict] = mapped_column(JSON, default=dict)
    embedding: Mapped[list | None] = mapped_column(JSON, nullable=True)
    embedding_model: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    document: Mapped[Document] = relationship(back_populates="chunks")


class IngestionJob(Base):
    __tablename__ = "ingestion_jobs"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    source: Mapped[str] = mapped_column(String(64))               # upload|import
    source_kind: Mapped[str] = mapped_column(String(32), default="unknown")
    filename: Mapped[str] = mapped_column(String(512))
    state: Mapped[str] = mapped_column(String(24), default="queued", index=True)
    stats: Mapped[dict] = mapped_column(JSON, default=dict)       # counts by stage
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow)

    errors: Mapped[list[JobError]] = relationship(back_populates="job", cascade="all, delete-orphan")


class JobError(Base):
    __tablename__ = "job_errors"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    job_id: Mapped[str] = mapped_column(ForeignKey("ingestion_jobs.id"), index=True)
    scope: Mapped[str] = mapped_column(String(24))               # file|row|chunk|extraction
    ref: Mapped[str] = mapped_column(String(128), default="")    # row number / chunk id / filename
    reason: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    job: Mapped[IngestionJob] = relationship(back_populates="errors")


class Entity(Base):
    """SQL mirror of a graph node with provenance and merge bookkeeping."""

    __tablename__ = "entities"

    id: Mapped[str] = mapped_column(String(96), primary_key=True)
    type: Mapped[str] = mapped_column(String(32), index=True)
    canonical_name: Mapped[str] = mapped_column(String(512))
    aliases: Mapped[list] = mapped_column(JSON, default=list)
    attributes: Mapped[dict] = mapped_column(JSON, default=dict)
    confidence: Mapped[float] = mapped_column(Float, default=1.0)
    method: Mapped[str] = mapped_column(String(24), default="structured")
    source_document_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    merged_into: Mapped[str | None] = mapped_column(String(96), nullable=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)


class Relation(Base):
    __tablename__ = "relations"

    id: Mapped[str] = mapped_column(String(96), primary_key=True)
    type: Mapped[str] = mapped_column(String(32), index=True)
    source_id: Mapped[str] = mapped_column(String(96), index=True)
    target_id: Mapped[str] = mapped_column(String(96), index=True)
    confidence: Mapped[float] = mapped_column(Float, default=1.0)
    method: Mapped[str] = mapped_column(String(24), default="structured")
    source_document_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    deleted: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)


class Answer(Base):
    __tablename__ = "answers"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    question: Mapped[str] = mapped_column(Text)
    answer_text: Mapped[str] = mapped_column(Text)
    confidence: Mapped[str] = mapped_column(String(16))          # high|medium|low|insufficient
    confidence_score: Mapped[float] = mapped_column(Float, default=0.0)
    citations: Mapped[list] = mapped_column(JSON, default=list)
    reasoning_path: Mapped[list] = mapped_column(JSON, default=list)
    actions: Mapped[list] = mapped_column(JSON, default=list)
    limitations: Mapped[list] = mapped_column(JSON, default=list)
    meta: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)


class Audit(Base):
    __tablename__ = "audits"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    action: Mapped[str] = mapped_column(String(32), index=True)
    entity_type: Mapped[str | None] = mapped_column(String(32), nullable=True)
    target_id: Mapped[str] = mapped_column(String(128))
    detail: Mapped[dict] = mapped_column(JSON, default=dict)
    actor: Mapped[str] = mapped_column(String(64), default="operator")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)


class EvalRun(Base):
    __tablename__ = "eval_runs"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    summary: Mapped[dict] = mapped_column(JSON, default=dict)

    results: Mapped[list[EvalResult]] = relationship(back_populates="run", cascade="all, delete-orphan")


class EvalResult(Base):
    __tablename__ = "eval_results"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    run_id: Mapped[str] = mapped_column(ForeignKey("eval_runs.id"), index=True)
    question_id: Mapped[str] = mapped_column(String(32))
    question: Mapped[str] = mapped_column(Text)
    passed: Mapped[bool] = mapped_column(Boolean, default=False)
    metrics: Mapped[dict] = mapped_column(JSON, default=dict)
    expected: Mapped[dict] = mapped_column(JSON, default=dict)
    actual: Mapped[dict] = mapped_column(JSON, default=dict)

    run: Mapped[EvalRun] = relationship(back_populates="results")
