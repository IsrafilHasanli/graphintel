"""Admin / operational endpoints.

Contract
--------
POST /admin/seed     ?reset= -> seed summary   (ingest the demo corpus)
GET  /admin/stats    -> corpus + graph counts
GET  /audits         ?action= -> [audit records]  (correction trail)
"""
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app import models
from app.api.deps import get_db
from app.services.seed import seed_all

router = APIRouter(tags=["admin"])


@router.post("/admin/seed")
def seed(reset: bool = True, db: Session = Depends(get_db)) -> dict:
    return seed_all(db, reset=reset)


@router.get("/admin/stats")
def stats(db: Session = Depends(get_db)) -> dict:
    def count(model, *where) -> int:
        stmt = select(func.count()).select_from(model)
        for w in where:
            stmt = stmt.where(w)
        return db.scalar(stmt) or 0

    job_states = dict(db.execute(
        select(models.IngestionJob.state, func.count(models.IngestionJob.id))
        .group_by(models.IngestionJob.state)
    ).all())
    entity_types = dict(db.execute(
        select(models.Entity.type, func.count(models.Entity.id))
        .where(models.Entity.merged_into.is_(None))
        .group_by(models.Entity.type)
    ).all())
    return {
        "documents": count(models.Document),
        "chunks": count(models.Chunk),
        "jobs": count(models.IngestionJob),
        "entities": count(models.Entity, models.Entity.merged_into.is_(None)),
        "relations": count(models.Relation, models.Relation.deleted.is_(False)),
        "answers": count(models.Answer),
        "job_states": job_states,
        "entity_types": entity_types,
    }


@router.get("/audits")
def list_audits(action: str | None = None, limit: int = 100,
                db: Session = Depends(get_db)) -> list[dict]:
    stmt = select(models.Audit).order_by(models.Audit.created_at.desc()).limit(limit)
    if action:
        stmt = stmt.where(models.Audit.action == action)
    return [
        {"id": a.id, "action": a.action, "entity_type": a.entity_type,
         "target_id": a.target_id, "detail": a.detail, "actor": a.actor,
         "created_at": a.created_at.isoformat()}
        for a in db.execute(stmt).scalars()
    ]
