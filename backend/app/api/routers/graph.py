"""Entity/relation review + correction + graph explorer endpoints.

Contract
--------
GET    /entities                 ?type=&q=&include_merged= -> [EntityOut]
GET    /entities/{id}            -> EntityOut | 404
PATCH  /entities/{id}            EditEntityRequest -> EntityOut
POST   /entities/merge           MergeEntitiesRequest -> {merged, target}
GET    /relations                ?type=&entity=&include_deleted= -> [RelationOut]
POST   /relations                AddRelationRequest -> RelationOut  (ontology-validated)
DELETE /relations/{id}           DeleteRelationRequest -> {deleted}
GET    /graph                    ?types=&rel_types=&limit= -> GraphView   (subgraph)
GET    /graph/expand             ?seed=&hops=&rel_types= -> GraphView      (neighborhood)
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app import models
from app.api.deps import get_db
from app.api.serializers import entity_out, relation_out
from app.graph import SQLGraphStore
from app.schemas import (
    AddRelationRequest,
    DeleteRelationRequest,
    EditEntityRequest,
    EntityOut,
    GraphEdge,
    GraphNode,
    GraphView,
    MergeEntitiesRequest,
    RelationOut,
)

router = APIRouter(tags=["graph"])


# --- entities --------------------------------------------------------------
@router.get("/entities", response_model=list[EntityOut])
def list_entities(type: str | None = None, q: str | None = None,
                  include_merged: bool = False, limit: int = 200,
                  db: Session = Depends(get_db)) -> list[EntityOut]:
    stmt = select(models.Entity)
    if type:
        stmt = stmt.where(models.Entity.type == type)
    if not include_merged:
        stmt = stmt.where(models.Entity.merged_into.is_(None))
    if q:
        stmt = stmt.where(models.Entity.canonical_name.ilike(f"%{q}%"))
    stmt = stmt.order_by(models.Entity.type, models.Entity.id).limit(limit)
    return [entity_out(e) for e in db.execute(stmt).scalars()]


@router.get("/entities/{entity_id}", response_model=EntityOut)
def get_entity(entity_id: str, db: Session = Depends(get_db)) -> EntityOut:
    ent = db.get(models.Entity, entity_id)
    if ent is None:
        raise HTTPException(status_code=404, detail="entity not found")
    return entity_out(ent)


@router.patch("/entities/{entity_id}", response_model=EntityOut)
def edit_entity(entity_id: str, req: EditEntityRequest,
                db: Session = Depends(get_db)) -> EntityOut:
    graph = SQLGraphStore(db)
    ok = graph.edit_entity(entity_id, canonical_name=req.canonical_name,
                           aliases=req.aliases, attributes=req.attributes, actor=req.actor)
    if not ok:
        raise HTTPException(status_code=404, detail="entity not found")
    db.flush()
    return entity_out(db.get(models.Entity, entity_id))


@router.post("/entities/merge")
def merge_entities(req: MergeEntitiesRequest, db: Session = Depends(get_db)) -> dict:
    graph = SQLGraphStore(db)
    ok = graph.merge_entities(req.source_id, req.target_id, actor=req.actor)
    if not ok:
        raise HTTPException(status_code=400,
                            detail="merge failed: unknown entity or identical ids")
    return {"merged": req.source_id, "target": req.target_id}


# --- relations -------------------------------------------------------------
@router.get("/relations", response_model=list[RelationOut])
def list_relations(type: str | None = None, entity: str | None = None,
                   include_deleted: bool = False, limit: int = 300,
                   db: Session = Depends(get_db)) -> list[RelationOut]:
    stmt = select(models.Relation)
    if type:
        stmt = stmt.where(models.Relation.type == type)
    if entity:
        stmt = stmt.where(or_(models.Relation.source_id == entity,
                              models.Relation.target_id == entity))
    if not include_deleted:
        stmt = stmt.where(models.Relation.deleted.is_(False))
    stmt = stmt.limit(limit)
    return [relation_out(r) for r in db.execute(stmt).scalars()]


@router.post("/relations", response_model=RelationOut, status_code=201)
def add_relation(req: AddRelationRequest, db: Session = Depends(get_db)) -> RelationOut:
    graph = SQLGraphStore(db)
    rid = graph.add_relation_manual(req.type, req.source_id, req.target_id,
                                    confidence=req.confidence, actor=req.actor)
    if rid is None:
        raise HTTPException(status_code=422,
                            detail="relation rejected: ontology violation or missing endpoint")
    db.flush()
    return relation_out(db.get(models.Relation, rid))


@router.delete("/relations/{relation_id}")
def delete_relation(relation_id: str, req: DeleteRelationRequest,
                    db: Session = Depends(get_db)) -> dict:
    graph = SQLGraphStore(db)
    ok = graph.delete_relation(relation_id, reason=req.reason, actor=req.actor)
    if not ok:
        raise HTTPException(status_code=404, detail="relation not found or already deleted")
    return {"deleted": relation_id}


# --- explorer --------------------------------------------------------------
@router.get("/graph", response_model=GraphView)
def get_graph(types: list[str] | None = Query(default=None),
              rel_types: list[str] | None = Query(default=None),
              limit: int = 300, db: Session = Depends(get_db)) -> GraphView:
    graph = SQLGraphStore(db)
    nodes, edges = graph.subgraph(etypes=types, rel_types=rel_types, limit_nodes=limit)
    node_ids = {n.id for n in nodes}
    return GraphView(
        nodes=[GraphNode(id=n.id, type=n.type, label=n.label, attributes=n.attributes) for n in nodes],
        edges=[GraphEdge(id=e.id, type=e.type, source=e.source_id, target=e.target_id,
                         confidence=e.confidence) for e in edges
               if e.source_id in node_ids and e.target_id in node_ids],
    )


@router.get("/graph/expand", response_model=GraphView)
def expand_graph(seed: list[str] = Query(...), hops: int = 2,
                 rel_types: list[str] | None = Query(default=None),
                 db: Session = Depends(get_db)) -> GraphView:
    graph = SQLGraphStore(db)
    nodes, edges = graph.expand(seed, max_hops=hops, rel_types=rel_types)
    return GraphView(
        nodes=[GraphNode(id=n.id, type=n.type, label=n.label, attributes=n.attributes) for n in nodes],
        edges=[GraphEdge(id=e.relation_id or f"{e.relation}:{e.source_id}->{e.target_id}",
                         type=e.relation, source=e.source_id, target=e.target_id) for e in edges],
    )
