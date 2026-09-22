"""Answer generation over the retrieval bundle.

Produces source-grounded answers with citations, an explicit graph reasoning
path, a confidence label/score, recommended actions, and stated limitations.
When evidence is too weak (below MIN_ANSWER_CONFIDENCE or no graph anchor) the
service REFUSES rather than guessing, per the product principle "source-grounded
answers only".

The deterministic provider builds the answer text from templates keyed on the
query intent so behavior is reproducible and testable offline. When
LLM_PROVIDER=anthropic, the same grounded context is handed to Claude with the
versioned ANSWER_SYSTEM_PROMPT; the citations/reasoning path/confidence are still
computed deterministically so grounding is enforced regardless of provider.
"""
from __future__ import annotations

import hashlib
from datetime import UTC, datetime

from sqlalchemy.orm import Session

from app import models
from app.config import get_settings
from app.domain import AnswerConfidence
from app.graph import GNode, PathEdge
from app.llm import ANSWER_SYSTEM_PROMPT_V1, get_llm
from app.logging_config import get_logger
from app.schemas import AnswerOut, ReasoningEdge
from app.services.retrieval import RetrievalBundle, RetrievalService

log = get_logger("answer")


def _utcnow() -> datetime:
    return datetime.now(UTC)


def _answer_id(question: str) -> str:
    return "ANS-" + hashlib.sha1(question.strip().lower().encode()).hexdigest()[:12]


def _label(score: float, settings) -> AnswerConfidence:
    if score < settings.min_answer_confidence:
        return AnswerConfidence.INSUFFICIENT
    if score >= 0.7:
        return AnswerConfidence.HIGH
    if score >= 0.5:
        return AnswerConfidence.MEDIUM
    return AnswerConfidence.LOW


class AnswerService:
    def __init__(self, session: Session) -> None:
        self.s = session
        self.settings = get_settings()
        self.retrieval = RetrievalService(session)
        self.llm = get_llm()

    def ask(self, question: str, top_k: int | None = None,
            as_of: datetime | None = None, persist: bool = True) -> AnswerOut:
        bundle = self.retrieval.retrieve(question, top_k=top_k, as_of=as_of)
        score = self._score(bundle)
        label = _label(score, self.settings)
        reasoning = [self._edge(e) for e in bundle.edges]

        if label is AnswerConfidence.INSUFFICIENT:
            out = self._refusal(question, bundle, score, reasoning)
        else:
            text, actions, limitations = self._compose(question, bundle)
            out = AnswerOut(
                id=_answer_id(question), question=question, answer=text,
                confidence=label.value, confidence_score=round(score, 4),
                citations=bundle.citations, reasoning_path=reasoning,
                actions=actions, limitations=limitations, plan=bundle.plan,
                created_at=_utcnow(),
            )
        if persist:
            self._persist(out)
        return out

    # --- scoring -----------------------------------------------------------
    def _score(self, bundle: RetrievalBundle) -> float:
        """Confidence blends graph anchoring and vector evidence strength.

        No linked entities OR no evidence chunks => effectively a refusal.
        """
        if not bundle.seed_ids or not bundle.chunks:
            return 0.0
        top = bundle.chunks[0].score if bundle.chunks else 0.0
        # Fraction of top chunks that are graph-anchored to linked entities.
        candidate = set(bundle.nodes) | set(bundle.seed_ids)
        anchored = sum(1 for c in bundle.chunks if candidate & set(c.mentions))
        anchor_ratio = anchored / len(bundle.chunks)
        # Did the graph produce a real reasoning path (>=1 edge)?
        path_bonus = 0.15 if bundle.edges else 0.0
        entity_bonus = 0.1 if bundle.seed_ids else 0.0
        raw = 0.45 * min(top, 1.0) + 0.3 * anchor_ratio + path_bonus + entity_bonus
        return max(0.0, min(raw, 1.0))

    def _edge(self, e: PathEdge) -> ReasoningEdge:
        return ReasoningEdge(source_id=e.source_id, source_type=e.source_type,
                             relation=e.relation, target_id=e.target_id,
                             target_type=e.target_type, relation_id=e.relation_id)

    # --- composition -------------------------------------------------------
    def _compose(self, question: str, bundle: RetrievalBundle) -> tuple[str, list[str], list[str]]:
        intent = bundle.plan.intent
        builder = {
            "impact_analysis": self._impact,
            "sla_risk": self._sla_risk,
            "ownership": self._ownership,
            "root_cause": self._root_cause,
            "runbook_lookup": self._runbook,
        }.get(intent, self._generic)
        text, actions, limitations = builder(bundle)

        if self.llm.name == "anthropic" and self.llm.available:  # pragma: no cover - network
            text = self._llm_answer(question, bundle, fallback=text)
        return text, actions, limitations

    def _names(self, nodes: list[GNode]) -> str:
        return ", ".join(f"{n.label} ({n.id})" for n in nodes) or "none found"

    def _cite_ids(self, bundle: RetrievalBundle, kinds=("chunk",)) -> str:
        ids = [c.ref_id for c in bundle.citations if c.kind in kinds]
        return ", ".join(ids[:6])

    def _impact(self, b: RetrievalBundle):
        customers = b.nodes_of_type("Customer")
        incidents = b.nodes_of_type("Incident")
        services = b.nodes_of_type("Service")
        window = f" in the last {b.plan.time_range_days} days" if b.plan.time_range_days else ""
        text = (
            f"Affected customers{window}: {self._names(customers)}. "
            f"This is derived from {len(incidents)} incident(s) "
            f"({self._names(incidents)}) on service(s) {self._names(services)}, "
            f"traced through AFFECTED / RELATED_TO / REPORTED edges. "
            f"Evidence: {self._cite_ids(b)}."
        )
        actions = ["Notify affected customer success owners",
                   "Confirm incident timelines against SLA windows"]
        limitations = []
        if not customers:
            limitations.append("No customer could be linked to the matched incidents.")
        return text, actions, limitations

    def _sla_risk(self, b: RetrievalBundle):
        clauses = b.nodes_of_type("SLAClause")
        incidents = b.nodes_of_type("Incident")
        customers = b.nodes_of_type("Customer")
        may_violate = [e for e in b.edges if e.relation == "MAY_VIOLATE"]
        risk = "AT RISK" if may_violate else "no clear breach found"
        text = (
            f"SLA assessment for {self._names(customers)}: {risk}. "
            f"{len(may_violate)} incident->clause MAY_VIOLATE link(s) detected across "
            f"clauses {self._names(clauses)}, driven by incidents {self._names(incidents)}. "
            f"Evidence: {self._cite_ids(b)}."
        )
        actions = ["Review breach thresholds on the flagged clauses",
                   "Escalate to the account team if within the SLA measurement window"]
        limitations = []
        if not may_violate:
            limitations.append("No MAY_VIOLATE edge was derived; risk is inferred from evidence only.")
        return text, actions, limitations

    def _ownership(self, b: RetrievalBundle):
        teams = b.nodes_of_type("Team")
        services = b.nodes_of_type("Service")
        incidents = b.nodes_of_type("Incident")
        text = (
            f"Owning team: {self._names(teams)}. "
            f"Path: incident {self._names(incidents)} AFFECTED service {self._names(services)}, "
            f"which is OWNED_BY {self._names(teams)}. Evidence: {self._cite_ids(b)}."
        )
        actions = ["Page the owning team's on-call for the affected service"]
        limitations = []
        if not teams:
            limitations.append("No owning team is recorded for the linked service.")
        return text, actions, limitations

    def _root_cause(self, b: RetrievalBundle):
        causes = b.nodes_of_type("RootCause")
        errors = b.nodes_of_type("ErrorSignature")
        incidents = b.nodes_of_type("Incident")
        text = (
            f"Likely root cause: {self._names(causes)}. "
            f"Recurring error signature(s) {self._names(errors)} across incidents "
            f"{self._names(incidents)} point to this cause via EXHIBITS / CAUSED_BY edges. "
            f"Evidence: {self._cite_ids(b)}."
        )
        actions = ["Validate the root cause against recent postmortems",
                   "Open a remediation task against the responsible service"]
        limitations = []
        if not causes:
            limitations.append("No RootCause node was linked; the answer relies on error-signature correlation.")
        return text, actions, limitations

    def _runbook(self, b: RetrievalBundle):
        runbooks = b.nodes_of_type("Runbook")
        errors = b.nodes_of_type("ErrorSignature")
        text = (
            f"Recommended runbook: {self._names(runbooks)}. "
            f"It MITIGATES the error signature(s) {self._names(errors)} referenced in the query. "
            f"Evidence: {self._cite_ids(b)}."
        )
        actions = ["Follow the runbook steps in order",
                   "Record the outcome on the active incident"]
        limitations = []
        if not runbooks:
            limitations.append("No runbook is linked to the referenced error signature.")
        return text, actions, limitations

    def _generic(self, b: RetrievalBundle):
        entities = list(b.nodes.values())[:8]
        text = (
            f"Based on the linked graph entities ({self._names(entities)}) and the "
            f"retrieved evidence ({self._cite_ids(b)}), here is what the sources support. "
            f"See citations for the grounding snippets and the reasoning path for the "
            f"graph relationships traversed."
        )
        return text, ["Refine the question with a specific entity or time range"], []

    def _llm_answer(self, question: str, bundle: RetrievalBundle, fallback: str) -> str:  # pragma: no cover
        context_lines = []
        for c in bundle.citations:
            context_lines.append(f"[{c.ref_id}] ({c.kind}) {c.snippet}")
        for e in bundle.edges[:20]:
            context_lines.append(f"[path] {e.source_id} {e.relation} {e.target_id}")
        prompt = (
            f"Question: {question}\n\nEvidence context (cite ids in square brackets):\n"
            + "\n".join(context_lines)
            + "\n\nAnswer using only this evidence and cite ids inline."
        )
        try:
            return self.llm.complete(ANSWER_SYSTEM_PROMPT_V1, prompt) or fallback
        except Exception as exc:
            log.warning("llm_answer_failed_using_template", error=str(exc))
            return fallback

    # --- refusal & persistence --------------------------------------------
    def _refusal(self, question: str, bundle: RetrievalBundle, score: float,
                 reasoning: list[ReasoningEdge]) -> AnswerOut:
        reasons = []
        if not bundle.seed_ids:
            reasons.append("no query entities could be linked to the knowledge graph")
        if not bundle.chunks:
            reasons.append("no supporting evidence chunks were retrieved")
        if not reasons:
            reasons.append("retrieved evidence was too weak to support a grounded answer")
        text = ("I don't have sufficient grounded evidence to answer confidently: "
                + "; ".join(reasons) + ". Please refine the question or ingest more sources.")
        return AnswerOut(
            id=_answer_id(question), question=question, answer=text,
            confidence=AnswerConfidence.INSUFFICIENT.value, confidence_score=round(score, 4),
            citations=bundle.citations, reasoning_path=reasoning, actions=[],
            limitations=reasons, plan=bundle.plan, created_at=_utcnow(),
        )

    def _persist(self, out: AnswerOut) -> None:
        row = self.s.get(models.Answer, out.id)
        payload = dict(
            question=out.question, answer_text=out.answer, confidence=out.confidence,
            confidence_score=out.confidence_score,
            citations=[c.model_dump() for c in out.citations],
            reasoning_path=[r.model_dump() for r in out.reasoning_path],
            actions=out.actions, limitations=out.limitations,
            meta={"intent": out.plan.intent if out.plan else None},
        )
        if row is None:
            self.s.add(models.Answer(id=out.id, **payload))
        else:
            for k, v in payload.items():
                setattr(row, k, v)
        self.s.flush()
