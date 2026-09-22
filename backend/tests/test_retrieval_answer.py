"""Retrieval + answer generation, including golden-question regression."""
from __future__ import annotations

import json
from pathlib import Path

import pytest
from app.db import SessionLocal
from app.services.answer import AnswerService
from app.services.retrieval import RetrievalService

GOLDEN = json.loads(
    (Path(__file__).resolve().parents[2] / "data" / "fixtures" / "golden_questions.json")
    .read_text(encoding="utf-8")
)["questions"]


@pytest.mark.parametrize("gq", GOLDEN, ids=[q["id"] for q in GOLDEN])
def test_golden_question_is_answered_and_grounded(seeded_session, gq):
    out = AnswerService(seeded_session).ask(gq["question"], persist=False)
    # Not refused.
    assert out.confidence != "insufficient", out.answer
    # Grounded: has citations and a graph reasoning path.
    assert out.citations, "answer must expose citations"
    assert out.reasoning_path, "answer must expose a graph reasoning path"
    # Expected entities are surfaced (linked or cited).
    found = set(out.plan.entities) | {c.ref_id for c in out.citations}
    for e in gq["expected_entities"]:
        assert e in found, f"{gq['id']} missing expected entity {e}"
    # Expected reasoning edges appear in the path.
    triples = {(x.source_type, x.relation, x.target_type) for x in out.reasoning_path}
    for edge in gq["expected_reasoning_edges"]:
        st, rel, tt = edge.split()
        assert (st, rel, tt) in triples, f"{gq['id']} missing edge {edge}"


def test_refusal_on_out_of_domain(seeded_session):
    out = AnswerService(seeded_session).ask("What is the capital of France?", persist=False)
    assert out.confidence == "insufficient"
    assert out.limitations
    assert not out.actions


def test_retrieval_is_deterministic_cold_vs_warm(seeded_session):
    """A cold service (first call) and a warm one must score identically."""
    q = "Which engineering team owns the service involved in INC-247?"
    # Warm: reuse the service across two calls.
    warm = RetrievalService(seeded_session)
    b1 = warm.retrieve(q)
    b2 = warm.retrieve(q)
    # Cold: brand-new service in a separate session.
    s2 = SessionLocal()
    try:
        cold = RetrievalService(s2).retrieve(q)
    finally:
        s2.close()
    ids1 = [c.chunk_id for c in b1.chunks]
    ids2 = [c.chunk_id for c in b2.chunks]
    ids_cold = [c.chunk_id for c in cold.chunks]
    assert ids1 == ids2 == ids_cold
    scores1 = [round(c.score, 6) for c in b1.chunks]
    scores_cold = [round(c.score, 6) for c in cold.chunks]
    assert scores1 == scores_cold


def test_answer_persist_roundtrip(seeded_session):
    from app import models

    svc = AnswerService(seeded_session)
    out = svc.ask("Which runbook should be used for payment gateway timeout errors?", persist=True)
    seeded_session.flush()
    row = seeded_session.get(models.Answer, out.id)
    assert row is not None
    assert row.confidence == out.confidence
    assert row.reasoning_path
