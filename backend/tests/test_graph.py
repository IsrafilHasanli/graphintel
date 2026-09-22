"""Graph store: ontology validation, traversal, and correction workflows."""
from __future__ import annotations

from app import models
from app.graph import SQLGraphStore, relation_id


def _mini_graph(session) -> SQLGraphStore:
    g = SQLGraphStore(session)
    g.upsert_entity("CUST-a", "Customer", "Acme")
    g.upsert_entity("SUP-1", "SupportTicket", "Ticket 1")
    g.upsert_entity("INC-1", "Incident", "Incident 1", attributes={"service_id": "SVC-x"})
    g.upsert_entity("SVC-x", "Service", "Payment API")
    g.upsert_entity("TEAM-x", "Team", "Payments")
    session.flush()
    g.upsert_relation("REPORTED", "CUST-a", "SUP-1")
    g.upsert_relation("RELATED_TO", "SUP-1", "INC-1")
    g.upsert_relation("AFFECTED", "INC-1", "SVC-x")
    g.upsert_relation("OWNED_BY", "SVC-x", "TEAM-x")
    session.flush()
    return g


def test_ontology_rejects_invalid_edge(session):
    g = _mini_graph(session)
    # Customer OWNED_BY Team is not in the ontology.
    rid = g.upsert_relation("OWNED_BY", "CUST-a", "TEAM-x")
    assert rid is None


def test_ontology_accepts_valid_edge(session):
    g = _mini_graph(session)
    rid = g.upsert_relation("AFFECTED", "INC-1", "SVC-x")
    assert rid == relation_id("AFFECTED", "INC-1", "SVC-x")


def test_expand_returns_multi_hop_path(session):
    g = _mini_graph(session)
    nodes, edges = g.expand(["CUST-a"], max_hops=4)
    ids = {n.id for n in nodes}
    assert {"CUST-a", "SUP-1", "INC-1", "SVC-x", "TEAM-x"} <= ids
    relations = {e.relation for e in edges}
    assert {"REPORTED", "RELATED_TO", "AFFECTED", "OWNED_BY"} <= relations


def test_expand_respects_rel_type_filter(session):
    g = _mini_graph(session)
    nodes, _ = g.expand(["INC-1"], max_hops=3, rel_types=["AFFECTED", "OWNED_BY"])
    ids = {n.id for n in nodes}
    assert "SVC-x" in ids and "TEAM-x" in ids
    assert "CUST-a" not in ids  # REPORTED/RELATED_TO not traversed


def test_delete_relation_tombstones_and_audits(session):
    g = _mini_graph(session)
    rid = relation_id("AFFECTED", "INC-1", "SVC-x")
    assert g.delete_relation(rid, reason="wrong") is True
    session.flush()
    assert session.get(models.Relation, rid).deleted is True
    assert session.query(models.Audit).filter_by(action="delete_relation").count() == 1
    # Deleting again is a no-op.
    assert g.delete_relation(rid, reason="again") is False


def test_merge_repoints_edges(session):
    g = _mini_graph(session)
    # Duplicate customer that also reported a ticket.
    g.upsert_entity("CUST-a-dup", "Customer", "ACME Inc")
    g.upsert_entity("SUP-2", "SupportTicket", "Ticket 2")
    session.flush()
    g.upsert_relation("REPORTED", "CUST-a-dup", "SUP-2")
    session.flush()

    assert g.merge_entities("CUST-a-dup", "CUST-a") is True
    session.flush()
    dup = session.get(models.Entity, "CUST-a-dup")
    assert dup.merged_into == "CUST-a"
    # The edge now points at the canonical customer.
    assert session.get(models.Relation, relation_id("REPORTED", "CUST-a", "SUP-2")) is not None
    # get_entity follows the tombstone.
    assert g.get_entity("CUST-a-dup").id == "CUST-a"


def test_add_relation_manual_records_audit(session):
    g = _mini_graph(session)
    g.upsert_entity("RC-1", "RootCause", "Latency")
    session.flush()
    rid = g.add_relation_manual("CAUSED_BY", "INC-1", "RC-1", confidence=0.9)
    assert rid is not None
    session.flush()
    assert session.query(models.Audit).filter_by(action="add_relation").count() == 1
