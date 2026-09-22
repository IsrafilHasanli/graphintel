"""Evaluation harness and release gate.

Runs the golden Graph RAG questions through the *real* answer service and scores
each on four grounding dimensions that matter for this product:

  * entity recall     - were the expected graph entities linked/cited?
  * evidence recall    - were the expected evidence ids present in the context?
  * reasoning coverage - did the graph reasoning path contain the expected edges
                         (e.g. "Incident AFFECTED Service")?
  * theme coverage     - did the answer text mention the expected themes?

plus refusal correctness (answerable golden questions must not be refused) and
citation presence (every answer must be cited).

The release gate turns the aggregate into PASS / CONDITIONAL PASS / FAIL so CI
and operators get a single readiness signal.
"""
from __future__ import annotations

import json
import re
import uuid
from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from app import models
from app.config import get_settings
from app.logging_config import get_logger
from app.schemas import EvalResultOut, EvalRunOut, ReleaseGateOut
from app.services.answer import AnswerService

log = get_logger("evaluation")

REPO_ROOT = Path(__file__).resolve().parents[3]
GOLDEN_PATH = REPO_ROOT / "data" / "fixtures" / "golden_questions.json"

# Per-question pass thresholds.
MIN_ENTITY_RECALL = 1.0        # all expected entities must be grounded
MIN_EVIDENCE_RECALL = 0.5      # at least half the expected evidence ids present
MIN_REASONING_RECALL = 1.0     # every expected reasoning edge must appear
MIN_THEME_COVERAGE = 0.5       # at least half the expected themes surfaced

# Release-gate thresholds.
GATE_PASS_RATE = 1.0           # all golden questions pass -> PASS
GATE_CONDITIONAL_RATE = 0.8    # >= this (but < PASS) -> CONDITIONAL PASS

_ID_RE = re.compile(r"\b(?:INC|SUP|CUST|SVC|TEAM|SLA|CLAUSE|ERR|RC|RUN|PM)-[A-Za-z0-9\-]+")


def _utcnow() -> datetime:
    return datetime.now(UTC)


def load_golden_questions(path: Path | None = None) -> list[dict]:
    p = path or GOLDEN_PATH
    return json.loads(p.read_text(encoding="utf-8"))["questions"]


class EvaluationService:
    def __init__(self, session: Session) -> None:
        self.s = session
        self.settings = get_settings()
        self.answers = AnswerService(session)

    # --- scoring helpers ---------------------------------------------------
    @staticmethod
    def _found_ids(out) -> set[str]:
        ids: set[str] = set(out.plan.entities if out.plan else [])
        ids.update(_ID_RE.findall(out.answer))
        for c in out.citations:
            ids.add(c.ref_id)
            if c.source_document_id:
                ids.add(c.source_document_id)
        for e in out.reasoning_path:
            ids.add(e.source_id)
            ids.add(e.target_id)
        return ids

    @staticmethod
    def _reasoning_triples(out) -> set[tuple[str, str, str]]:
        return {(e.source_type, e.relation, e.target_type) for e in out.reasoning_path}

    @staticmethod
    def _parse_expected_edge(text: str) -> tuple[str, str, str] | None:
        # "Customer REPORTED SupportTicket" -> ("Customer", "REPORTED", "SupportTicket")
        parts = text.split()
        if len(parts) != 3:
            return None
        return parts[0], parts[1], parts[2]

    def _evaluate_one(self, q: dict) -> EvalResultOut:
        out = self.answers.ask(q["question"], persist=False)
        found = self._found_ids(out)

        exp_ent = set(q.get("expected_entities", []))
        entity_hits = exp_ent & found
        entity_recall = len(entity_hits) / len(exp_ent) if exp_ent else 1.0

        exp_ev = set(q.get("expected_evidence_ids", []))
        ev_hits = exp_ev & found
        evidence_recall = len(ev_hits) / len(exp_ev) if exp_ev else 1.0

        triples = self._reasoning_triples(out)
        exp_edges = [self._parse_expected_edge(e) for e in q.get("expected_reasoning_edges", [])]
        exp_edges = [e for e in exp_edges if e]
        edge_hits = [e for e in exp_edges if e in triples]
        reasoning_recall = len(edge_hits) / len(exp_edges) if exp_edges else 1.0

        themes = q.get("expected_answer_themes", [])
        low = out.answer.lower()
        theme_hits = [t for t in themes if _theme_present(t, low)]
        theme_coverage = len(theme_hits) / len(themes) if themes else 1.0

        refused = out.confidence == "insufficient"
        has_citations = len(out.citations) > 0

        passed = (
            not refused
            and has_citations
            and entity_recall >= MIN_ENTITY_RECALL
            and evidence_recall >= MIN_EVIDENCE_RECALL
            and reasoning_recall >= MIN_REASONING_RECALL
            and theme_coverage >= MIN_THEME_COVERAGE
        )

        metrics = {
            "entity_recall": round(entity_recall, 3),
            "evidence_recall": round(evidence_recall, 3),
            "reasoning_recall": round(reasoning_recall, 3),
            "theme_coverage": round(theme_coverage, 3),
            "confidence": out.confidence,
            "confidence_score": out.confidence_score,
            "refused": refused,
            "citation_count": len(out.citations),
            "reasoning_edges": len(out.reasoning_path),
        }
        return EvalResultOut(
            question_id=q["id"], question=q["question"], passed=passed, metrics=metrics,
            expected={
                "entities": sorted(exp_ent), "evidence_ids": sorted(exp_ev),
                "reasoning_edges": q.get("expected_reasoning_edges", []),
                "themes": themes,
            },
            actual={
                "answer": out.answer,
                "linked_entities": out.plan.entities if out.plan else [],
                "entity_hits": sorted(entity_hits),
                "evidence_hits": sorted(ev_hits),
                "reasoning_edge_hits": [" ".join(e) for e in edge_hits],
                "theme_hits": theme_hits,
            },
        )

    # --- run ---------------------------------------------------------------
    def run(self, persist: bool = True, path: Path | None = None) -> EvalRunOut:
        questions = load_golden_questions(path)
        started = _utcnow()
        results = [self._evaluate_one(q) for q in questions]
        finished = _utcnow()

        total = len(results)
        passed = sum(1 for r in results if r.passed)
        pass_rate = passed / total if total else 0.0
        summary = {
            "total": total, "passed": passed, "failed": total - passed,
            "pass_rate": round(pass_rate, 3),
            "avg_entity_recall": round(_avg(results, "entity_recall"), 3),
            "avg_evidence_recall": round(_avg(results, "evidence_recall"), 3),
            "avg_reasoning_recall": round(_avg(results, "reasoning_recall"), 3),
            "avg_theme_coverage": round(_avg(results, "theme_coverage"), 3),
            "refusals": sum(1 for r in results if r.metrics.get("refused")),
        }
        run_id = f"EVAL-{uuid.uuid4().hex[:12]}"
        run_out = EvalRunOut(id=run_id, started_at=started, finished_at=finished,
                             summary=summary, results=results)
        if persist:
            self._persist(run_out)
        log.info("eval_run_complete", **summary)
        return run_out

    def _persist(self, run: EvalRunOut) -> None:
        row = models.EvalRun(id=run.id, started_at=run.started_at,
                             finished_at=run.finished_at, summary=run.summary)
        self.s.add(row)
        for r in run.results:
            self.s.add(models.EvalResult(
                run_id=run.id, question_id=r.question_id, question=r.question,
                passed=r.passed, metrics=r.metrics, expected=r.expected, actual=r.actual,
            ))
        self.s.flush()

    def latest_run(self) -> EvalRunOut | None:
        row = self.s.execute(
            select(models.EvalRun).order_by(models.EvalRun.started_at.desc())
        ).scalars().first()
        if row is None:
            return None
        results = [
            EvalResultOut(question_id=r.question_id, question=r.question, passed=r.passed,
                          metrics=r.metrics, expected=r.expected, actual=r.actual)
            for r in row.results
        ]
        return EvalRunOut(id=row.id, started_at=row.started_at, finished_at=row.finished_at,
                          summary=row.summary, results=results)

    # --- release gate ------------------------------------------------------
    def release_gate(self, run: EvalRunOut | None = None) -> ReleaseGateOut:
        run = run or self.latest_run() or self.run(persist=False)
        blockers: list[str] = []
        warnings: list[str] = []
        summary = run.summary
        pass_rate = summary.get("pass_rate", 0.0)

        if summary.get("refusals", 0) > 0:
            blockers.append(f"{summary['refusals']} golden question(s) were refused")
        for r in run.results:
            if not r.passed:
                warnings.append(f"{r.question_id} failed: {self._why_failed(r)}")

        if pass_rate >= GATE_PASS_RATE and not blockers:
            status = "PASS"
        elif pass_rate >= GATE_CONDITIONAL_RATE and not blockers:
            status = "CONDITIONAL PASS"
        else:
            status = "FAIL"
            if pass_rate < GATE_CONDITIONAL_RATE:
                blockers.append(f"pass rate {pass_rate:.0%} below "
                                f"conditional threshold {GATE_CONDITIONAL_RATE:.0%}")

        checks = {
            "golden_questions": summary.get("total", 0),
            "passed": summary.get("passed", 0),
            "pass_rate": pass_rate,
            "refusals": summary.get("refusals", 0),
            "avg_entity_recall": summary.get("avg_entity_recall"),
            "avg_reasoning_recall": summary.get("avg_reasoning_recall"),
        }
        return ReleaseGateOut(status=status, blockers=blockers, warnings=warnings, checks=checks)

    @staticmethod
    def _why_failed(r: EvalResultOut) -> str:
        m = r.metrics
        reasons = []
        if m.get("refused"):
            reasons.append("refused")
        if m.get("entity_recall", 0) < MIN_ENTITY_RECALL:
            reasons.append(f"entity_recall={m.get('entity_recall')}")
        if m.get("evidence_recall", 0) < MIN_EVIDENCE_RECALL:
            reasons.append(f"evidence_recall={m.get('evidence_recall')}")
        if m.get("reasoning_recall", 0) < MIN_REASONING_RECALL:
            reasons.append(f"reasoning_recall={m.get('reasoning_recall')}")
        if m.get("theme_coverage", 0) < MIN_THEME_COVERAGE:
            reasons.append(f"theme_coverage={m.get('theme_coverage')}")
        return ", ".join(reasons) or "unknown"


def _avg(results: list[EvalResultOut], key: str) -> float:
    if not results:
        return 0.0
    return sum(r.metrics.get(key, 0.0) for r in results) / len(results)


def _stem(token: str) -> str:
    for suffix in ("ing", "ed", "s"):
        if len(token) > len(suffix) + 2 and token.endswith(suffix):
            return token[:-len(suffix)]
    return token


def _theme_present(theme: str, answer_lower: str) -> bool:
    low = theme.lower()
    if low in answer_lower:
        return True
    answer_stems = {_stem(t) for t in re.findall(r"[a-z0-9]+", answer_lower)}
    theme_stems = [_stem(t) for t in re.findall(r"[a-z0-9]+", low)]
    return bool(theme_stems) and all(t in answer_stems for t in theme_stems)
