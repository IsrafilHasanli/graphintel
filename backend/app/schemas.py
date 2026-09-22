"""Pydantic schemas: API contracts and internal typed payloads.

These are the typed models used for ingestion, extraction, graph writes, and
retrieval. Grouped by concern.
"""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


# --- Extraction (internal) -------------------------------------------------
class ExtractedEntity(BaseModel):
    id: str
    type: str
    canonical_name: str
    aliases: list[str] = Field(default_factory=list)
    attributes: dict = Field(default_factory=dict)
    confidence: float = 1.0
    method: str = "structured"
    source_document_id: str | None = None


class ExtractedRelation(BaseModel):
    type: str
    source_id: str
    target_id: str
    confidence: float = 1.0
    method: str = "structured"
    source_document_id: str | None = None


class ExtractionResult(BaseModel):
    entities: list[ExtractedEntity] = Field(default_factory=list)
    relations: list[ExtractedRelation] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)


# --- Ingestion / jobs ------------------------------------------------------
class JobErrorOut(BaseModel):
    scope: str
    ref: str
    reason: str


class JobOut(BaseModel):
    id: str
    source: str
    source_kind: str
    filename: str
    state: str
    stats: dict
    errors: list[JobErrorOut] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime


class DocumentOut(BaseModel):
    id: str
    source_type: str
    source_kind: str
    filename: str
    title: str | None = None
    sha256: str
    chunk_count: int = 0
    created_at: datetime


class ChunkOut(BaseModel):
    id: str
    document_id: str
    ordinal: int
    text: str
    meta: dict = Field(default_factory=dict)


# --- Entities / relations (review) -----------------------------------------
class EntityOut(BaseModel):
    id: str
    type: str
    canonical_name: str
    aliases: list[str] = Field(default_factory=list)
    attributes: dict = Field(default_factory=dict)
    confidence: float
    method: str
    merged_into: str | None = None


class RelationOut(BaseModel):
    id: str
    type: str
    source_id: str
    target_id: str
    confidence: float
    method: str
    deleted: bool = False


class MergeEntitiesRequest(BaseModel):
    source_id: str = Field(..., description="Duplicate entity that will be merged away")
    target_id: str = Field(..., description="Canonical entity that survives")
    actor: str = "operator"


class EditEntityRequest(BaseModel):
    canonical_name: str | None = None
    aliases: list[str] | None = None
    attributes: dict | None = None
    actor: str = "operator"


class DeleteRelationRequest(BaseModel):
    reason: str = "operator correction"
    actor: str = "operator"


class AddRelationRequest(BaseModel):
    type: str
    source_id: str
    target_id: str
    confidence: float = 1.0
    actor: str = "operator"


# --- Ask / answers ---------------------------------------------------------
class AskRequest(BaseModel):
    question: str
    top_k: int | None = None
    as_of: datetime | None = Field(
        default=None,
        description="Pin 'now' for time-bounded queries; defaults to the dataset reference date.",
    )


class Citation(BaseModel):
    ref_id: str                       # document/chunk/entity id
    kind: str                         # chunk|document|entity
    entity_type: str | None = None
    snippet: str = ""
    source_document_id: str | None = None
    score: float = 0.0


class ReasoningEdge(BaseModel):
    source_id: str
    source_type: str
    relation: str
    target_id: str
    target_type: str
    relation_id: str | None = None


class QueryPlan(BaseModel):
    intent: str
    entities: list[str] = Field(default_factory=list)
    entity_types: list[str] = Field(default_factory=list)
    time_range_days: int | None = None
    required_evidence_types: list[str] = Field(default_factory=list)
    keywords: list[str] = Field(default_factory=list)


class AnswerOut(BaseModel):
    id: str
    question: str
    answer: str
    confidence: str
    confidence_score: float
    citations: list[Citation] = Field(default_factory=list)
    reasoning_path: list[ReasoningEdge] = Field(default_factory=list)
    actions: list[str] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)
    plan: QueryPlan | None = None
    created_at: datetime | None = None


# --- Graph explorer --------------------------------------------------------
class GraphNode(BaseModel):
    id: str
    type: str
    label: str
    attributes: dict = Field(default_factory=dict)


class GraphEdge(BaseModel):
    id: str
    type: str
    source: str
    target: str
    confidence: float = 1.0


class GraphView(BaseModel):
    nodes: list[GraphNode] = Field(default_factory=list)
    edges: list[GraphEdge] = Field(default_factory=list)


# --- Evaluation ------------------------------------------------------------
class EvalResultOut(BaseModel):
    question_id: str
    question: str
    passed: bool
    metrics: dict
    expected: dict
    actual: dict


class EvalRunOut(BaseModel):
    id: str
    started_at: datetime
    finished_at: datetime | None = None
    summary: dict
    results: list[EvalResultOut] = Field(default_factory=list)


class ReleaseGateOut(BaseModel):
    status: str                       # PASS|CONDITIONAL PASS|FAIL
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    checks: dict = Field(default_factory=dict)
