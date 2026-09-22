"""Evaluation harness and release gate regression."""
from __future__ import annotations

from app.services.evaluation import EvaluationService


def test_all_golden_questions_pass(seeded_session):
    run = EvaluationService(seeded_session).run(persist=False)
    assert run.summary["total"] == 5
    assert run.summary["passed"] == 5, [r.question_id for r in run.results if not r.passed]
    assert run.summary["refusals"] == 0
    assert run.summary["avg_entity_recall"] == 1.0
    assert run.summary["avg_reasoning_recall"] == 1.0


def test_release_gate_passes_on_seeded_corpus(seeded_session):
    ev = EvaluationService(seeded_session)
    run = ev.run(persist=False)
    gate = ev.release_gate(run)
    assert gate.status == "PASS"
    assert not gate.blockers


def test_release_gate_fails_without_data(session):
    """With no corpus every golden question is refused -> gate FAIL."""
    ev = EvaluationService(session)
    run = ev.run(persist=False)
    assert run.summary["refusals"] == 5
    gate = ev.release_gate(run)
    assert gate.status == "FAIL"
    assert gate.blockers


def test_eval_run_persists(seeded_session):
    from app import models

    ev = EvaluationService(seeded_session)
    ev.run(persist=True)
    seeded_session.flush()
    assert seeded_session.query(models.EvalRun).count() == 1
    assert seeded_session.query(models.EvalResult).count() == 5
    latest = ev.latest_run()
    assert latest is not None and len(latest.results) == 5
