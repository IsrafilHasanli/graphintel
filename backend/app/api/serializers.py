"""ORM -> Pydantic serializers for API responses."""
from __future__ import annotations

from app import models
from app.schemas import (
    ChunkOut,
    DocumentOut,
    EntityOut,
    GraphEdge,
    GraphNode,
    JobErrorOut,
    JobOut,
    RelationOut,
)


def job_out(job: models.IngestionJob) -> JobOut:
    return JobOut(
        id=job.id, source=job.source, source_kind=job.source_kind, filename=job.filename,
        state=job.state, stats=job.stats or {},
        errors=[JobErrorOut(scope=e.scope, ref=e.ref, reason=e.reason) for e in job.errors],
        created_at=job.created_at, updated_at=job.updated_at,
    )


def document_out(doc: models.Document, chunk_count: int) -> DocumentOut:
    return DocumentOut(
        id=doc.id, source_type=doc.source_type, source_kind=doc.source_kind,
        filename=doc.filename, title=doc.title, sha256=doc.sha256,
        chunk_count=chunk_count, created_at=doc.created_at,
    )


def chunk_out(chunk: models.Chunk) -> ChunkOut:
    return ChunkOut(id=chunk.id, document_id=chunk.document_id, ordinal=chunk.ordinal,
                    text=chunk.text, meta=chunk.meta or {})


def entity_out(ent: models.Entity) -> EntityOut:
    return EntityOut(
        id=ent.id, type=ent.type, canonical_name=ent.canonical_name,
        aliases=ent.aliases or [], attributes=ent.attributes or {},
        confidence=ent.confidence, method=ent.method, merged_into=ent.merged_into,
    )


def relation_out(rel: models.Relation) -> RelationOut:
    return RelationOut(
        id=rel.id, type=rel.type, source_id=rel.source_id, target_id=rel.target_id,
        confidence=rel.confidence, method=rel.method, deleted=rel.deleted,
    )


def graph_node(ent: models.Entity) -> GraphNode:
    return GraphNode(id=ent.id, type=ent.type, label=ent.canonical_name,
                     attributes=ent.attributes or {})


def graph_edge(rel: models.Relation) -> GraphEdge:
    return GraphEdge(id=rel.id, type=rel.type, source=rel.source_id,
                     target=rel.target_id, confidence=rel.confidence)
