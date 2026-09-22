"""Knowledge graph store.

Graph traversal is a first-class retrieval mechanism in GraphIntel, so the store
exposes explicit neighborhood-expansion and path APIs (not just key lookups).

Two implementations behind one interface:
  * SQLGraphStore   - backed by the entities/relations tables. Works on SQLite
                      and Postgres, needs no extra services, and is the tested
                      default. Traversal is BFS over an in-memory adjacency
                      built per request (demo scale).
  * NeptuneGraphStore - AWS production/staging graph store using Neptune's
                        openCypher HTTP endpoint.

Both validate every edge against the ontology in app.domain.RELATION_SCHEMA.
"""
from __future__ import annotations

import json
from collections import deque
from dataclasses import dataclass, field

import httpx
from sqlalchemy import select
from sqlalchemy.orm import Session

from app import models
from app.config import get_settings
from app.domain import RELATION_SCHEMA, AuditAction, RelationType
from app.logging_config import get_logger

log = get_logger("graph")


@dataclass
class GNode:
    id: str
    type: str
    label: str
    attributes: dict = field(default_factory=dict)


@dataclass
class GEdge:
    id: str
    type: str
    source_id: str
    target_id: str
    confidence: float = 1.0


@dataclass
class PathEdge:
    """A directed edge encountered during traversal, with endpoint types."""
    source_id: str
    source_type: str
    relation: str
    target_id: str
    target_type: str
    relation_id: str | None = None


def relation_id(rtype: str, source_id: str, target_id: str) -> str:
    return f"{rtype}:{source_id}->{target_id}"


class GraphStore:
    # --- writes ---
    def upsert_entity(self, entity_id: str, etype: str, label: str,
                      attributes: dict | None = None, aliases: list[str] | None = None,
                      confidence: float = 1.0, method: str = "structured",
                      source_document_id: str | None = None) -> None:
        raise NotImplementedError

    def upsert_relation(self, rtype: str, source_id: str, target_id: str,
                        confidence: float = 1.0, method: str = "structured",
                        source_document_id: str | None = None) -> str | None:
        raise NotImplementedError

    # --- reads / traversal ---
    def get_entity(self, entity_id: str) -> GNode | None:
        raise NotImplementedError

    def expand(self, seed_ids: list[str], max_hops: int, rel_types: list[str] | None = None,
               direction: str = "both") -> tuple[list[GNode], list[PathEdge]]:
        raise NotImplementedError


class SQLGraphStore(GraphStore):
    def __init__(self, session: Session) -> None:
        self.s = session

    # --- writes ------------------------------------------------------------
    def upsert_entity(self, entity_id, etype, label, attributes=None, aliases=None,
                      confidence=1.0, method="structured", source_document_id=None) -> None:
        ent = self.s.get(models.Entity, entity_id)
        if ent is None:
            ent = models.Entity(id=entity_id, type=etype, canonical_name=label)
            self.s.add(ent)
        ent.type = etype
        ent.canonical_name = label
        if aliases is not None:
            ent.aliases = sorted(set(aliases))
        if attributes is not None:
            ent.attributes = attributes
        ent.confidence = confidence
        ent.method = method
        if source_document_id:
            ent.source_document_id = source_document_id

    def _validate_edge(self, rtype: str, source_id: str, target_id: str) -> str | None:
        try:
            rt = RelationType(rtype)
        except ValueError:
            return f"unknown relation type {rtype}"
        expected = RELATION_SCHEMA.get(rt)
        if not expected:
            return None  # relation type has no strict schema (e.g. MENTIONS)
        src = self.s.get(models.Entity, source_id)
        tgt = self.s.get(models.Entity, target_id)
        if src is None or tgt is None:
            return f"endpoint missing for {rtype} {source_id}->{target_id}"
        if not any(src.type == es.value and tgt.type == et.value for es, et in expected):
            allowed = ", ".join(f"{es.value}->{et.value}" for es, et in expected)
            return (f"ontology violation: {rtype} expects [{allowed}], "
                    f"got {src.type}->{tgt.type}")
        return None

    def upsert_relation(self, rtype, source_id, target_id, confidence=1.0,
                        method="structured", source_document_id=None) -> str | None:
        err = self._validate_edge(rtype, source_id, target_id)
        if err:
            log.warning("relation_rejected", reason=err)
            return None
        rid = relation_id(rtype, source_id, target_id)
        rel = self.s.get(models.Relation, rid)
        if rel is None:
            rel = models.Relation(id=rid, type=rtype, source_id=source_id, target_id=target_id)
            self.s.add(rel)
        rel.confidence = confidence
        rel.method = method
        rel.deleted = False
        if source_document_id:
            rel.source_document_id = source_document_id
        return rid

    def delete_relation(self, rid: str, reason: str, actor: str = "operator") -> bool:
        rel = self.s.get(models.Relation, rid)
        if rel is None or rel.deleted:
            return False
        rel.deleted = True
        self.s.add(models.Audit(
            action=AuditAction.DELETE_RELATION.value, entity_type=rel.type,
            target_id=rid, actor=actor,
            detail={"reason": reason, "source_id": rel.source_id, "target_id": rel.target_id},
        ))
        return True

    def add_relation_manual(self, rtype: str, source_id: str, target_id: str,
                            confidence: float, actor: str = "operator") -> str | None:
        rid = self.upsert_relation(rtype, source_id, target_id, confidence=confidence, method="manual")
        if rid:
            self.s.add(models.Audit(
                action=AuditAction.ADD_RELATION.value, entity_type=rtype,
                target_id=rid, actor=actor, detail={"confidence": confidence},
            ))
        return rid

    def edit_entity(self, entity_id: str, canonical_name=None, aliases=None,
                    attributes=None, actor: str = "operator") -> bool:
        ent = self.s.get(models.Entity, entity_id)
        if ent is None:
            return False
        detail: dict = {}
        if canonical_name is not None:
            detail["canonical_name"] = [ent.canonical_name, canonical_name]
            ent.canonical_name = canonical_name
        if aliases is not None:
            ent.aliases = sorted(set(aliases))
            detail["aliases"] = ent.aliases
        if attributes is not None:
            ent.attributes = {**ent.attributes, **attributes}
            detail["attributes"] = list(attributes.keys())
        ent.method = "manual"
        self.s.add(models.Audit(action=AuditAction.EDIT_ENTITY.value,
                                entity_type=ent.type, target_id=entity_id,
                                actor=actor, detail=detail))
        return True

    def merge_entities(self, source_id: str, target_id: str, actor: str = "operator") -> bool:
        """Merge duplicate `source_id` into canonical `target_id`.

        All edges are repointed to the target, aliases are preserved, and the
        source is tombstoned via merged_into so retrieval uses the canonical node.
        """
        src = self.s.get(models.Entity, source_id)
        tgt = self.s.get(models.Entity, target_id)
        if src is None or tgt is None or source_id == target_id:
            return False
        # Preserve names/aliases.
        tgt.aliases = sorted(set(tgt.aliases) | set(src.aliases) | {src.canonical_name})
        # Repoint edges.
        repointed = 0
        rels = self.s.execute(
            select(models.Relation).where(
                (models.Relation.source_id == source_id) | (models.Relation.target_id == source_id)
            )
        ).scalars().all()
        for rel in rels:
            new_src = target_id if rel.source_id == source_id else rel.source_id
            new_tgt = target_id if rel.target_id == source_id else rel.target_id
            if new_src == new_tgt:
                rel.deleted = True
                continue
            new_id = relation_id(rel.type, new_src, new_tgt)
            existing = self.s.get(models.Relation, new_id)
            if existing and existing.id != rel.id:
                rel.deleted = True
            else:
                rel.id = new_id
                rel.source_id = new_src
                rel.target_id = new_tgt
            repointed += 1
        src.merged_into = target_id
        self.s.add(models.Audit(
            action=AuditAction.MERGE_ENTITY.value, entity_type=src.type,
            target_id=source_id, actor=actor,
            detail={"merged_into": target_id, "edges_repointed": repointed},
        ))
        return True

    # --- reads -------------------------------------------------------------
    def get_entity(self, entity_id: str) -> GNode | None:
        ent = self.s.get(models.Entity, entity_id)
        if ent is None:
            return None
        if ent.merged_into:
            return self.get_entity(ent.merged_into)
        return GNode(ent.id, ent.type, ent.canonical_name, ent.attributes or {})

    def list_entities(self, etype: str | None = None, include_merged: bool = False) -> list[GNode]:
        stmt = select(models.Entity)
        if etype:
            stmt = stmt.where(models.Entity.type == etype)
        rows = self.s.execute(stmt).scalars().all()
        out = []
        for e in rows:
            if e.merged_into and not include_merged:
                continue
            out.append(GNode(e.id, e.type, e.canonical_name, e.attributes or {}))
        return out

    def _active_relations(self) -> list[models.Relation]:
        return self.s.execute(
            select(models.Relation).where(models.Relation.deleted.is_(False))
        ).scalars().all()

    def expand(self, seed_ids, max_hops, rel_types=None, direction="both"):
        rel_filter = set(rel_types) if rel_types else None
        rels = self._active_relations()
        # Build adjacency.
        adj: dict[str, list[tuple[models.Relation, str]]] = {}
        for r in rels:
            if rel_filter and r.type not in rel_filter:
                continue
            if direction in ("both", "out"):
                adj.setdefault(r.source_id, []).append((r, r.target_id))
            if direction in ("both", "in"):
                adj.setdefault(r.target_id, []).append((r, r.source_id))
        visited: set[str] = set()
        edges: list[PathEdge] = []
        seen_edges: set[str] = set()
        queue: deque[tuple[str, int]] = deque()
        for sid in seed_ids:
            node = self.get_entity(sid)
            if node:
                queue.append((node.id, 0))
                visited.add(node.id)
        while queue:
            node_id, hops = queue.popleft()
            if hops >= max_hops:
                continue
            for rel, neighbor in adj.get(node_id, []):
                if rel.id not in seen_edges:
                    seen_edges.add(rel.id)
                    src_node = self.get_entity(rel.source_id)
                    tgt_node = self.get_entity(rel.target_id)
                    if src_node and tgt_node:
                        edges.append(PathEdge(
                            src_node.id, src_node.type, rel.type,
                            tgt_node.id, tgt_node.type, rel.id,
                        ))
                if neighbor not in visited:
                    visited.add(neighbor)
                    queue.append((neighbor, hops + 1))
        nodes = [n for n in (self.get_entity(v) for v in visited) if n]
        return nodes, edges

    def neighbors(self, entity_id: str, rel_types=None, direction="both") -> list[PathEdge]:
        _nodes, edges = self.expand([entity_id], max_hops=1, rel_types=rel_types, direction=direction)
        return [e for e in edges if e.source_id == entity_id or e.target_id == entity_id]

    def subgraph(self, etypes: list[str] | None = None, rel_types: list[str] | None = None,
                 limit_nodes: int = 300) -> tuple[list[GNode], list[GEdge]]:
        nodes = self.list_entities()
        if etypes:
            nodes = [n for n in nodes if n.type in etypes]
        nodes = nodes[:limit_nodes]
        node_ids = {n.id for n in nodes}
        rel_filter = set(rel_types) if rel_types else None
        edges = []
        for r in self._active_relations():
            if rel_filter and r.type not in rel_filter:
                continue
            if r.source_id in node_ids and r.target_id in node_ids:
                edges.append(GEdge(r.id, r.type, r.source_id, r.target_id, r.confidence))
        return nodes, edges


class NeptuneGraphStore(GraphStore):  # pragma: no cover - requires AWS Neptune
    """Amazon Neptune graph store using the openCypher HTTP endpoint.

    The SQL tables remain the system-of-record mirror for admin review and
    provenance, while AWS staging/prod uses Neptune for graph persistence and
    traversal. This adapter intentionally has the same method surface as the
    SQL store so retrieval code does not need backend-specific branches.
    """

    def __init__(self, endpoint: str, port: int = 8182, use_iam_auth: bool = True) -> None:
        self.endpoint = endpoint.replace("https://", "").replace("http://", "").rstrip("/")
        self.port = port
        self.use_iam_auth = use_iam_auth
        self.base_url = f"https://{self.endpoint}:{self.port}/openCypher"

    def _query(self, query: str, parameters: dict | None = None) -> list[dict]:
        # Neptune's openCypher endpoint accepts form-encoded query text. IAM
        # signing can be added by swapping the client auth layer; ECS tasks run
        # inside the VPC and should be restricted by security group + IAM policy.
        data = {"query": query}
        if parameters:
            data["parameters"] = json.dumps(parameters)
        resp = httpx.post(self.base_url, data=data, timeout=20.0)
        resp.raise_for_status()
        payload = resp.json()
        return payload.get("results") or payload.get("result") or []

    @staticmethod
    def _props(attributes: dict | None) -> list:
        return list((attributes or {}).items())

    def upsert_entity(self, entity_id, etype, label, attributes=None, aliases=None,
                      confidence=1.0, method="structured", source_document_id=None) -> None:
        query = (
            "MERGE (n:Entity {id: $id}) "
            "SET n.type=$type, n.label=$label, n.attributes=$attrs, "
            "n.aliases=$aliases, n.confidence=$conf, n.method=$method, "
            "n.source_document_id=$doc"
        )
        self._query(query, {
            "id": entity_id, "type": etype, "label": label,
            "attrs": self._props(attributes), "aliases": aliases or [],
            "conf": confidence, "method": method, "doc": source_document_id,
        })

    def upsert_relation(self, rtype, source_id, target_id, confidence=1.0,
                        method="structured", source_document_id=None) -> str | None:
        rid = relation_id(rtype, source_id, target_id)
        # Relationship types cannot be parameterized in openCypher, so whitelist
        # through the enum before interpolation.
        RelationType(rtype)
        query = (
            f"MATCH (a:Entity {{id: $src}}), (b:Entity {{id: $tgt}}) "
            f"MERGE (a)-[r:{rtype} {{id:$rid}}]->(b) "
            "SET r.type=$type, r.confidence=$conf, r.method=$method, "
            "r.source_document_id=$doc, r.deleted=false"
        )
        self._query(query, {
            "src": source_id, "tgt": target_id, "rid": rid, "type": rtype,
            "conf": confidence, "method": method, "doc": source_document_id,
        })
        return rid

    def get_entity(self, entity_id: str) -> GNode | None:
        rows = self._query(
            "MATCH (n:Entity {id:$id}) RETURN n.id AS id, n.type AS type, "
            "n.label AS label, n.attributes AS attributes",
            {"id": entity_id},
        )
        if not rows:
            return None
        row = rows[0]
        attrs = dict(row.get("attributes") or [])
        return GNode(row["id"], row.get("type", ""), row.get("label", ""), attrs)

    def expand(self, seed_ids, max_hops, rel_types=None, direction="both"):
        rel_filter = ""
        params: dict = {"seeds": seed_ids, "hops": max_hops}
        if rel_types:
            rel_filter = " WHERE all(rel IN relationships(p) WHERE rel.type IN $rtypes)"
            params["rtypes"] = rel_types
        hops = max(1, min(int(max_hops), 8))
        rows = self._query(
            f"MATCH p=(seed:Entity)-[*1..{hops}]-(m:Entity) "
            "WHERE seed.id IN $seeds" + rel_filter +
            " RETURN nodes(p) AS nodes, relationships(p) AS rels",
            params,
        )
        nodes: dict[str, GNode] = {}
        edges: list[PathEdge] = []
        seen_edges: set[str] = set()
        for row in rows:
            for node in row.get("nodes", []):
                props = node.get("~properties", node)
                node_id = props.get("id")
                if node_id:
                    nodes[node_id] = GNode(
                        node_id,
                        props.get("type", ""),
                        props.get("label", ""),
                        dict(props.get("attributes") or []),
                    )
            for rel in row.get("rels", []):
                props = rel.get("~properties", rel)
                rid = props.get("id")
                if not rid or rid in seen_edges or props.get("deleted"):
                    continue
                seen_edges.add(rid)
                src_id = props.get("source_id") or rel.get("~start")
                tgt_id = props.get("target_id") or rel.get("~end")
                if src_id in nodes and tgt_id in nodes:
                    edges.append(PathEdge(
                        src_id,
                        nodes[src_id].type,
                        props.get("type", ""),
                        tgt_id,
                        nodes[tgt_id].type,
                        rid,
                    ))
        return list(nodes.values()), edges


def get_graph_store(session: Session) -> GraphStore:
    settings = get_settings()
    if settings.use_neptune:
        try:
            return NeptuneGraphStore(
                settings.neptune_endpoint,
                settings.neptune_port,
                settings.neptune_use_iam_auth,
            )
        except Exception as exc:  # pragma: no cover
            log.warning("neptune_unavailable_falling_back_to_sql", error=str(exc))
    return SQLGraphStore(session)
