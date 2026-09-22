"""Hybrid Graph + Vector retrieval.

Implements the retrieval contract:
  1. Analyze the query (intent, entities, time range, evidence types).
  2. Link query mentions to graph nodes.
  3. Expand the graph neighborhood (first-class traversal).
  4. Vector-search chunks, anchored to graph candidates + a global pass.
  5. Merge & rerank graph and vector evidence.
  6. Build a context bundle with citations and an ordered reasoning path.

Deterministic and offline by default; every step is inspectable so answers can
expose why they were produced.
"""
from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app import models
from app.config import get_settings
from app.graph import GNode, PathEdge, SQLGraphStore
from app.schemas import Citation, QueryPlan
from app.services.extraction import MentionIndex
from app.vector import VectorStore, get_embedding_provider, tokenize

# Dataset reference "now" (mirrors scripts/_dataset_common.py) so time-bounded
# demo/eval queries are reproducible.
DATASET_REFERENCE_NOW = datetime(2026, 9, 21, tzinfo=UTC)

_ID_RE = re.compile(r"\b(?:INC|SUP|CUST|SVC|TEAM|SLA|CLAUSE|ERR|RC|RUN|PM)-[A-Za-z0-9\-]+")
_DAYS_RE = re.compile(r"last\s+(\d+)\s+day", re.IGNORECASE)
_FALLBACK_MIN_SCORE = 0.30

# Relation types worth traversing per intent (keeps reasoning paths focused).
INTENT_RELATIONS = {
    "impact_analysis": ["AFFECTED", "RELATED_TO", "REPORTED", "EXHIBITS"],
    "sla_risk": ["APPLIES_TO", "PART_OF", "CONSTRAINS", "MAY_VIOLATE", "AFFECTED", "REPORTED", "RELATED_TO"],
    "ownership": ["AFFECTED", "OWNED_BY"],
    "root_cause": ["EXHIBITS", "RELATED_TO", "CAUSED_BY", "ANALYZES"],
    "runbook_lookup": ["MITIGATES", "EXHIBITS"],
    "generic": ["AFFECTED", "OWNED_BY", "RELATED_TO", "REPORTED", "CAUSED_BY",
                "MITIGATES", "MAY_VIOLATE", "APPLIES_TO", "PART_OF", "CONSTRAINS", "EXHIBITS"],
}

# Entity-citation ordering per intent: the decisive answer node types first so
# they survive the citation cap regardless of neighborhood size.
ENTITY_CITATION_PRIORITY = {
    "impact_analysis": ["Customer", "Incident", "Service", "SupportTicket"],
    "sla_risk": ["SLAClause", "Customer", "Incident", "SLAContract", "Service"],
    "ownership": ["Team", "Service", "Incident"],
    "root_cause": ["RootCause", "ErrorSignature", "Incident", "SupportTicket"],
    "runbook_lookup": ["Runbook", "ErrorSignature", "Service"],
    "generic": [],
}

INTENT_KEYWORDS = [
    ("sla_risk", ("sla", "at risk", "risk", "breach", "violate")),
    ("runbook_lookup", ("runbook", "mitigat", "how do i fix", "playbook", "remediat")),
    ("ownership", ("who owns", "owns", "owned by", "which team", "team owns", "ownership")),
    ("root_cause", ("root cause", "why", "recurring", "caused")),
    ("impact_analysis", ("affected", "impact", "which customers", "blast radius")),
]


@dataclass
class ScoredChunk:
    chunk_id: str
    document_id: str
    text: str
    score: float
    mentions: list[str] = field(default_factory=list)


@dataclass
class RetrievalBundle:
    plan: QueryPlan
    seed_ids: list[str]
    nodes: dict[str, GNode]
    edges: list[PathEdge]
    chunks: list[ScoredChunk]
    citations: list[Citation]

    def nodes_of_type(self, etype: str) -> list[GNode]:
        return [n for n in self.nodes.values() if n.type == etype]


class QueryAnalyzer:
    def __init__(self, entity_index: MentionIndex) -> None:
        self.index = entity_index

    def analyze(self, question: str) -> QueryPlan:
        low = question.lower()
        intent = "generic"
        for name, kws in INTENT_KEYWORDS:
            if any(k in low for k in kws):
                intent = name
                break
        days = None
        m = _DAYS_RE.search(question)
        if m:
            days = int(m.group(1))
        entities = self.index.find(question)
        time_types = {
            "impact_analysis": ["incident", "support_ticket"],
            "sla_risk": ["incident", "sla_clause", "support_ticket"],
            "ownership": ["incident", "service", "team"],
            "root_cause": ["support_ticket", "incident", "root_cause"],
            "runbook_lookup": ["error_signature", "runbook"],
            "generic": ["incident", "support_ticket"],
        }
        keywords = [w for w in re.findall(r"[a-z0-9]+", low) if len(w) > 2]
        return QueryPlan(intent=intent, entities=entities, entity_types=[],
                         time_range_days=days, required_evidence_types=time_types[intent],
                         keywords=keywords)


class RetrievalService:
    def __init__(self, session: Session) -> None:
        self.s = session
        self.settings = get_settings()
        self.graph = SQLGraphStore(session)
        self.embedder = get_embedding_provider()
        self._entity_index: MentionIndex | None = None
        self._vector_store: VectorStore | None = None
        self._chunk_meta: dict[str, tuple[str, str, list[str]]] = {}  # cid -> (doc, text, mentions)

    # --- lazy caches -------------------------------------------------------
    def entity_index(self) -> MentionIndex:
        if self._entity_index is None:
            idx = MentionIndex()
            for e in self.s.execute(select(models.Entity)).scalars():
                if e.merged_into:
                    continue
                patterns = (e.attributes or {}).get("patterns", [])
                idx.add(e.id, [e.canonical_name, *e.aliases], patterns)
            self._entity_index = idx
        return self._entity_index

    def vector_store(self) -> VectorStore:
        if self._vector_store is None:
            store = VectorStore(self.embedder)
            for c in self.s.execute(select(models.Chunk)).scalars():
                emb = c.embedding or self.embedder.embed(c.text)
                store.add(c.id, emb)
                self._chunk_meta[c.id] = (c.document_id, c.text, (c.meta or {}).get("mentions", []))
            self._vector_store = store
        return self._vector_store

    # --- main --------------------------------------------------------------
    def retrieve(self, question: str, top_k: int | None = None,
                 as_of: datetime | None = None) -> RetrievalBundle:
        top_k = top_k or self.settings.retrieval_top_k
        as_of = as_of or DATASET_REFERENCE_NOW
        plan = QueryAnalyzer(self.entity_index()).analyze(question)

        # 2-3. Entity linking + graph expansion. If the query has no exact
        # entity mention, use vector hits to discover mentioned graph nodes and
        # seed traversal from those. This handles natural-language queries like
        # "checkout timeout tickets" that refer to entities by description.
        vstore = self.vector_store()
        rel_types = INTENT_RELATIONS.get(plan.intent, INTENT_RELATIONS["generic"])
        seeds = list(plan.entities)
        seed_types = {
            ent.type for entity_id in seeds
            if (ent := self.s.get(models.Entity, entity_id)) is not None
        }
        needs_semantic_seeds = not seeds or (
            plan.intent == "runbook_lookup"
            and not seed_types.intersection({"Runbook", "ErrorSignature"})
        )
        if needs_semantic_seeds:
            probe_hits = vstore.search(question, top_k=top_k * 3)
            discovered = self._fallback_seeds_from_hits(
                probe_hits, plan.intent, question=question, limit=8,
                min_score=_FALLBACK_MIN_SCORE,
            )
            seeds = list(dict.fromkeys([*seeds, *discovered]))
            plan.entities = seeds
        nodes: dict[str, GNode] = {}
        edges: list[PathEdge] = []
        if seeds:
            gnodes, gedges = self.graph.expand(seeds, self.settings.graph_max_hops,
                                               rel_types=rel_types)
            nodes = {n.id: n for n in gnodes}
            edges = gedges
        # Time filter: drop incidents outside the requested window.
        if plan.time_range_days:
            cutoff = as_of - timedelta(days=plan.time_range_days)
            for nid in list(nodes):
                n = nodes[nid]
                if n.type == "Incident":
                    started = n.attributes.get("started_at")
                    if started and _parse_dt(started) < cutoff:
                        nodes.pop(nid, None)
            edges = [e for e in edges if e.source_id in nodes and e.target_id in nodes]

        # 4. Vector search: graph-anchored + global.
        # Build the vector store first so _chunk_meta is populated before we
        # derive graph-anchored chunk ids (otherwise the first call on a fresh
        # service sees an empty anchor set and scoring becomes order-dependent).
        candidate_ids = set(nodes) | set(seeds)
        anchored_ids = {cid for cid, (_d, _t, mentions) in self._chunk_meta.items()
                        if candidate_ids & set(mentions)} if candidate_ids else set()
        hits = vstore.search(question, top_k=top_k * 2)
        scored: dict[str, ScoredChunk] = {}
        for h in hits:
            doc, text, mentions = self._chunk_meta[h.chunk_id]
            boost = 0.25 if h.chunk_id in anchored_ids else 0.0
            scored[h.chunk_id] = ScoredChunk(h.chunk_id, doc, text, h.score + boost, mentions)
        # Ensure anchored chunks are represented even if below global top-k.
        if anchored_ids:
            for h in vstore.search(question, top_k=top_k * 3, allowed=anchored_ids):
                if h.chunk_id not in scored:
                    doc, text, mentions = self._chunk_meta[h.chunk_id]
                    scored[h.chunk_id] = ScoredChunk(h.chunk_id, doc, text, h.score + 0.25, mentions)

        # 5-6. Rerank + build citations.
        ranked = sorted(scored.values(), key=lambda c: c.score, reverse=True)[:top_k]
        citations = self._build_citations(ranked, nodes, plan)
        return RetrievalBundle(plan=plan, seed_ids=seeds, nodes=nodes, edges=edges,
                               chunks=ranked, citations=citations)

    def _fallback_seeds_from_hits(self, hits, intent: str, question: str, limit: int,
                                  min_score: float = _FALLBACK_MIN_SCORE) -> list[str]:
        if not hits or hits[0].score < min_score:
            return []
        _doc, top_text, _mentions = self._chunk_meta.get(hits[0].chunk_id, ("", "", []))
        query_terms = set(tokenize(question))
        chunk_terms = set(tokenize(top_text))
        if not query_terms.intersection(chunk_terms):
            return []
        counts: Counter[str] = Counter()
        for hit in hits:
            _doc, _text, mentions = self._chunk_meta.get(hit.chunk_id, ("", "", []))
            counts.update(mentions)
        if not counts:
            return []
        priority = ENTITY_CITATION_PRIORITY.get(intent, [])
        rank = {t: i for i, t in enumerate(priority)}
        candidates = []
        for entity_id, count in counts.items():
            ent = self.s.get(models.Entity, entity_id)
            if ent is None or ent.merged_into:
                continue
            candidates.append((rank.get(ent.type, len(priority)), -count, entity_id))
        candidates.sort()
        return [entity_id for _rank, _count, entity_id in candidates[:limit]]

    def _build_citations(self, chunks: list[ScoredChunk], nodes: dict[str, GNode],
                         plan: QueryPlan) -> list[Citation]:
        cites: list[Citation] = []
        for c in chunks:
            snippet = c.text if len(c.text) <= 240 else c.text[:237] + "..."
            cites.append(Citation(ref_id=c.chunk_id, kind="chunk", snippet=snippet,
                                  source_document_id=c.document_id, score=round(c.score, 4)))
        # Add key graph entities as entity citations, prioritising the types this
        # intent is expected to answer with so the decisive nodes are always
        # cited (and traceable) even when the neighborhood is large.
        priority = ENTITY_CITATION_PRIORITY.get(plan.intent, [])
        rank = {t: i for i, t in enumerate(priority)}
        ordered = sorted(nodes.values(), key=lambda n: rank.get(n.type, len(priority)))
        for n in ordered[:14]:
            cites.append(Citation(ref_id=n.id, kind="entity", entity_type=n.type,
                                  snippet=n.label, score=0.0))
        return cites


def _parse_dt(value: str) -> datetime:
    try:
        dt = datetime.fromisoformat(value)
    except ValueError:
        return datetime.min.replace(tzinfo=UTC)
    return dt if dt.tzinfo else dt.replace(tzinfo=UTC)
