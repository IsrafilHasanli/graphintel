"""Ingestion & job-tracking endpoints.

Contract
--------
POST /ingest/upload      multipart file -> JobOut         (upload a document/dataset)
POST /ingest/text        {filename, content, source_kind} -> JobOut
GET  /jobs               -> [JobOut]                        (ingestion history + errors)
GET  /jobs/{job_id}      -> JobOut | 404
GET  /documents          -> [DocumentOut]
GET  /documents/{id}     -> DocumentOut | 404
GET  /documents/{id}/chunks -> [ChunkOut]
"""
from __future__ import annotations

from pathlib import PurePosixPath

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app import models
from app.api.deps import get_db
from app.api.serializers import chunk_out, document_out, job_out
from app.domain import SUPPORTED_UPLOAD_TYPES
from app.schemas import ChunkOut, DocumentOut, JobOut
from app.services.ingestion import IngestionService

router = APIRouter(tags=["ingestion"])


class IngestTextRequest(BaseModel):
    filename: str
    content: str
    source_kind: str | None = None


@router.post("/ingest/upload", response_model=JobOut)
async def ingest_upload(file: UploadFile = File(...), db: Session = Depends(get_db)) -> JobOut:
    suffix = PurePosixPath(file.filename or "").suffix.lower()
    if suffix not in SUPPORTED_UPLOAD_TYPES:
        raise HTTPException(status_code=415, detail=(
            f"unsupported file type '{suffix}'. Supported: {sorted(SUPPORTED_UPLOAD_TYPES)}"))
    raw = await file.read()
    try:
        content = raw.decode("utf-8")
    except UnicodeDecodeError as err:
        raise HTTPException(status_code=400, detail="file must be UTF-8 encoded text") from err
    svc = IngestionService(db)
    job = svc.ingest(filename=file.filename or "upload", content=content, source="upload")
    return job_out(job)


@router.post("/ingest/text", response_model=JobOut)
def ingest_text(req: IngestTextRequest, db: Session = Depends(get_db)) -> JobOut:
    if not req.content.strip():
        raise HTTPException(status_code=400, detail="content is empty")
    svc = IngestionService(db)
    job = svc.ingest(filename=req.filename, content=req.content, source="upload",
                     source_kind=req.source_kind)
    return job_out(job)


@router.get("/jobs", response_model=list[JobOut])
def list_jobs(state: str | None = None, limit: int = 100, db: Session = Depends(get_db)) -> list[JobOut]:
    stmt = select(models.IngestionJob).order_by(models.IngestionJob.created_at.desc()).limit(limit)
    if state:
        stmt = stmt.where(models.IngestionJob.state == state)
    return [job_out(j) for j in db.execute(stmt).scalars()]


@router.get("/jobs/{job_id}", response_model=JobOut)
def get_job(job_id: str, db: Session = Depends(get_db)) -> JobOut:
    job = db.get(models.IngestionJob, job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="job not found")
    return job_out(job)


@router.get("/documents", response_model=list[DocumentOut])
def list_documents(source_kind: str | None = None, limit: int = 200,
                   db: Session = Depends(get_db)) -> list[DocumentOut]:
    counts = dict(db.execute(
        select(models.Chunk.document_id, func.count(models.Chunk.id)).group_by(models.Chunk.document_id)
    ).all())
    stmt = select(models.Document).order_by(models.Document.created_at.desc()).limit(limit)
    if source_kind:
        stmt = stmt.where(models.Document.source_kind == source_kind)
    return [document_out(d, counts.get(d.id, 0)) for d in db.execute(stmt).scalars()]


@router.get("/documents/{document_id}", response_model=DocumentOut)
def get_document(document_id: str, db: Session = Depends(get_db)) -> DocumentOut:
    doc = db.get(models.Document, document_id)
    if doc is None:
        raise HTTPException(status_code=404, detail="document not found")
    count = db.scalar(select(func.count(models.Chunk.id)).where(models.Chunk.document_id == document_id))
    return document_out(doc, count or 0)


@router.get("/documents/{document_id}/chunks", response_model=list[ChunkOut])
def get_document_chunks(document_id: str, db: Session = Depends(get_db)) -> list[ChunkOut]:
    if db.get(models.Document, document_id) is None:
        raise HTTPException(status_code=404, detail="document not found")
    stmt = (select(models.Chunk).where(models.Chunk.document_id == document_id)
            .order_by(models.Chunk.ordinal))
    return [chunk_out(c) for c in db.execute(stmt).scalars()]
