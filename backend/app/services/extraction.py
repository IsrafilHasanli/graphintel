"""Entity and relation extraction.

Two complementary strategies:

  * Structured extraction (method="structured", confidence 1.0): maps normalized
    source records (tickets, incidents, catalogs, SLA, runbooks, postmortems)
    into typed entities and relations. This is the deterministic backbone.
  * Rule-based mention linking (method="rule"): matches entity ids, names,
    aliases, and error-signature patterns inside chunk text to connect the text
    corpus to graph nodes for graph-anchored vector retrieval.

Extraction NEVER silently discards failures: unmapped or malformed records are
returned in ExtractionResult.errors so the ingestion job surfaces them.
"""
from __future__ import annotations

import json
import re

from app.domain import EntityType as ET
from app.domain import ExtractionMethod
from app.domain import RelationType as RT
from app.llm import LLMProvider, get_llm
from app.schemas import ExtractedEntity, ExtractedRelation, ExtractionResult

LLM_EXTRACTION_SYSTEM_PROMPT_V1 = (
    "You extract a strict knowledge graph for GraphIntel. Return JSON only. "
    "Use only the allowed entity and relation types. Every item must be grounded "
    "in the provided text. If uncertain, omit it or lower confidence."
)

_ENTITY_TYPES = {e.value for e in ET}
_RELATION_TYPES = {r.value for r in RT}


def _entity(eid, etype, name, *, aliases=None, attributes=None, confidence=1.0,
            method=ExtractionMethod.STRUCTURED, doc=None) -> ExtractedEntity:
    return ExtractedEntity(
        id=eid, type=etype.value if hasattr(etype, "value") else etype,
        canonical_name=name, aliases=aliases or [], attributes=attributes or {},
        confidence=confidence, method=method.value if hasattr(method, "value") else method,
        source_document_id=doc,
    )


def _rel(rtype, src, tgt, *, confidence=1.0, method=ExtractionMethod.STRUCTURED, doc=None) -> ExtractedRelation:
    return ExtractedRelation(
        type=rtype.value if hasattr(rtype, "value") else rtype,
        source_id=src, target_id=tgt, confidence=confidence,
        method=method.value if hasattr(method, "value") else method,
        source_document_id=doc,
    )


def extract_structured(kind: str, records: list[dict], document_id: str | None = None) -> ExtractionResult:
    result = ExtractionResult()
    handler = _HANDLERS.get(kind)
    if handler is None:
        result.errors.append(f"no structured extractor for kind '{kind}'")
        return result
    for i, rec in enumerate(records):
        try:
            handler(rec, document_id, result)
        except (KeyError, TypeError, ValueError) as exc:
            result.errors.append(f"{kind}[{i}] extraction failed: {exc}")
    return result


def extract_llm_free_text(
    kind: str,
    chunks: list[tuple[str, str]],
    document_id: str | None = None,
    provider: LLMProvider | None = None,
) -> ExtractionResult:
    """Extract entities and relations from free-text chunks with an LLM.

    This path is opt-in via EXTRACTION_PROVIDER=llm. It keeps tests offline by
    accepting an injectable provider and by validating/parsing deterministic JSON
    rather than trusting arbitrary prose.
    """
    out = ExtractionResult()
    llm = provider or get_llm()
    if not llm.available:
        out.errors.append("llm extraction requested but provider is unavailable")
        return out
    for chunk_id, text in chunks:
        prompt = _llm_extraction_prompt(kind, chunk_id, text)
        try:
            raw = llm.complete(LLM_EXTRACTION_SYSTEM_PROMPT_V1, prompt, max_tokens=1200)
            parsed = _parse_llm_extraction_json(raw)
            _append_llm_payload(out, parsed, document_id=document_id, chunk_id=chunk_id)
        except (ValueError, TypeError, KeyError, json.JSONDecodeError) as exc:
            out.errors.append(f"{chunk_id} llm extraction failed: {exc}")
    return out


def _llm_extraction_prompt(kind: str, chunk_id: str, text: str) -> str:
    return f"""
Source kind: {kind}
Chunk id: {chunk_id}

Allowed entity types:
{sorted(_ENTITY_TYPES)}

Allowed relation types:
{sorted(_RELATION_TYPES)}

Return this JSON shape exactly:
{{
  "entities": [
    {{
      "id": "stable id, prefer existing ids if present",
      "type": "one allowed entity type",
      "canonical_name": "short display name",
      "aliases": ["optional aliases"],
      "attributes": {{"source_chunk_id": "{chunk_id}"}},
      "confidence": 0.0
    }}
  ],
  "relations": [
    {{
      "type": "one allowed relation type",
      "source_id": "entity id",
      "target_id": "entity id",
      "confidence": 0.0
    }}
  ]
}}

Text:
{text[:6000]}
""".strip()


def _parse_llm_extraction_json(raw: str) -> dict:
    raw = raw.strip()
    if raw.startswith("```"):
        raw = re.sub(r"^```(?:json)?\s*", "", raw)
        raw = re.sub(r"\s*```$", "", raw)
    start = raw.find("{")
    end = raw.rfind("}")
    if start < 0 or end < start:
        raise ValueError("LLM did not return a JSON object")
    return json.loads(raw[start:end + 1])


def _append_llm_payload(out: ExtractionResult, payload: dict, *,
                        document_id: str | None, chunk_id: str) -> None:
    seen_entities: set[str] = set()
    for item in payload.get("entities", []):
        eid = str(item["id"]).strip()
        etype = str(item["type"]).strip()
        if not eid or etype not in _ENTITY_TYPES:
            continue
        attrs = dict(item.get("attributes") or {})
        attrs.setdefault("source_chunk_id", chunk_id)
        out.entities.append(_entity(
            eid,
            etype,
            str(item.get("canonical_name") or eid),
            aliases=[str(a) for a in item.get("aliases", []) if a],
            attributes=attrs,
            confidence=float(item.get("confidence", 0.75)),
            method=ExtractionMethod.LLM,
            doc=document_id or chunk_id,
        ))
        seen_entities.add(eid)
    for item in payload.get("relations", []):
        rtype = str(item["type"]).strip()
        src = str(item["source_id"]).strip()
        tgt = str(item["target_id"]).strip()
        if rtype not in _RELATION_TYPES or not src or not tgt:
            continue
        # Relations to existing graph nodes may be valid even if not extracted
        # in this chunk, so do not require endpoints to be in seen_entities.
        out.relations.append(_rel(
            rtype,
            src,
            tgt,
            confidence=float(item.get("confidence", 0.7)),
            method=ExtractionMethod.LLM,
            doc=document_id or chunk_id,
        ))


# --- per-kind handlers -----------------------------------------------------
def _h_customers(rec, doc, out: ExtractionResult) -> None:
    out.entities.append(_entity(
        rec["id"], ET.CUSTOMER, rec["name"], aliases=rec.get("aliases", []),
        attributes={"tier": rec.get("tier")}, doc=doc,
    ))


def _h_services(rec, doc, out: ExtractionResult) -> None:
    # rec is the combined {teams, services} catalog.
    for team in rec.get("teams", []):
        out.entities.append(_entity(
            team["id"], ET.TEAM, team["name"],
            attributes={"contact": team.get("contact")}, doc=doc,
        ))
    for svc in rec.get("services", []):
        out.entities.append(_entity(
            svc["id"], ET.SERVICE, svc["name"],
            attributes={"tier": svc.get("tier")}, doc=doc,
        ))
        if svc.get("owning_team"):
            out.relations.append(_rel(RT.OWNED_BY, svc["id"], svc["owning_team"], doc=doc))


def _h_error_signatures(rec, doc, out: ExtractionResult) -> None:
    out.entities.append(_entity(
        rec["id"], ET.ERROR_SIGNATURE, rec["name"],
        aliases=rec.get("patterns", []),
        attributes={"patterns": rec.get("patterns", []), "severity": rec.get("severity")},
        doc=doc,
    ))


def _h_root_causes(rec, doc, out: ExtractionResult) -> None:
    out.entities.append(_entity(
        rec["id"], ET.ROOT_CAUSE, rec["title"],
        attributes={"description": rec.get("description")}, doc=doc,
    ))


def _h_incidents(rec, doc, out: ExtractionResult) -> None:
    out.entities.append(_entity(
        rec["id"], ET.INCIDENT, rec["title"],
        attributes={
            "severity": rec.get("severity"), "status": rec.get("status"),
            "started_at": rec.get("started_at"), "resolved_at": rec.get("resolved_at"),
            "service_id": rec.get("service_id"),
            "impacted_customers": rec.get("impacted_customers", []),
        }, doc=doc,
    ))
    if rec.get("service_id"):
        out.relations.append(_rel(RT.AFFECTED, rec["id"], rec["service_id"], doc=doc))
    if rec.get("root_cause"):
        out.relations.append(_rel(RT.CAUSED_BY, rec["id"], rec["root_cause"], confidence=0.9, doc=doc))
    if rec.get("error_signature"):
        out.relations.append(_rel(RT.EXHIBITS, rec["id"], rec["error_signature"], confidence=0.9, doc=doc))
    for upd in rec.get("updates", []):
        out.entities.append(_entity(
            upd["id"], ET.INCIDENT_UPDATE, upd.get("message", "")[:80],
            attributes={"status": upd.get("status"), "posted_at": upd.get("posted_at"),
                        "message": upd.get("message")}, doc=doc,
        ))
        out.relations.append(_rel(RT.HAS_UPDATE, rec["id"], upd["id"], doc=doc))


def _h_support_tickets(rec, doc, out: ExtractionResult) -> None:
    out.entities.append(_entity(
        rec["id"], ET.SUPPORT_TICKET, rec["subject"],
        attributes={
            "body": rec.get("body"), "priority": rec.get("priority"),
            "status": rec.get("status"), "created_at": rec.get("created_at"),
            "customer_id": rec.get("customer_id"), "service_id": rec.get("service_id"),
        }, doc=doc,
    ))
    if rec.get("customer_id"):
        out.relations.append(_rel(RT.REPORTED, rec["customer_id"], rec["id"], doc=doc))
    if rec.get("error_signature"):
        out.relations.append(_rel(RT.EXHIBITS, rec["id"], rec["error_signature"], confidence=0.9, doc=doc))
    related = rec.get("related_incident_id")
    if related:
        out.relations.append(_rel(RT.RELATED_TO, rec["id"], related, confidence=0.9, doc=doc))


def _h_sla(rec, doc, out: ExtractionResult) -> None:
    contract = rec["contract"]
    out.entities.append(_entity(
        contract["id"], ET.SLA_CONTRACT, contract["name"],
        attributes={"tier": contract.get("tier"), "customer_id": contract.get("customer_id")},
        confidence=rec.get("confidence", 1.0), doc=doc,
    ))
    if contract.get("customer_id"):
        out.relations.append(_rel(RT.APPLIES_TO, contract["id"], contract["customer_id"], doc=doc))
    for clause in rec.get("clauses", []):
        out.entities.append(_entity(
            clause["id"], ET.SLA_CLAUSE, clause.get("text", clause["id"])[:120],
            attributes={"kind": clause.get("kind"), "threshold": clause.get("threshold"),
                        "text": clause.get("text"),
                        "constrains_services": clause.get("constrains_services", [])},
            confidence=clause.get("confidence", 0.95), doc=doc,
        ))
        out.relations.append(_rel(RT.PART_OF, clause["id"], contract["id"], doc=doc))
        for svc in clause.get("constrains_services", []):
            out.relations.append(_rel(RT.CONSTRAINS, clause["id"], svc, confidence=0.9, doc=doc))


def _h_runbook(rec, doc, out: ExtractionResult) -> None:
    out.entities.append(_entity(
        rec["id"], ET.RUNBOOK, rec["title"],
        attributes={"steps": rec.get("steps", []), "service_id": rec.get("service_id")}, doc=doc,
    ))
    if rec.get("error_signature_id"):
        out.relations.append(_rel(RT.MITIGATES, rec["id"], rec["error_signature_id"], doc=doc))


def _h_postmortem(rec, doc, out: ExtractionResult) -> None:
    out.entities.append(_entity(
        rec["id"], ET.POSTMORTEM, rec["title"],
        attributes={"authored_at": rec.get("authored_at")}, doc=doc,
    ))
    if rec.get("incident_id"):
        out.relations.append(_rel(RT.ANALYZES, rec["id"], rec["incident_id"], doc=doc))


_HANDLERS = {
    "customers": _h_customers,
    "services": _h_services,
    "error_signatures": _h_error_signatures,
    "root_causes": _h_root_causes,
    "incidents": _h_incidents,
    "support_tickets": _h_support_tickets,
    "sla": _h_sla,
    "runbook": _h_runbook,
    "postmortem": _h_postmortem,
}


# --- rule-based mention linking -------------------------------------------
_ID_RE = re.compile(r"\b(?:INC|SUP|CUST|SVC|TEAM|SLA|CLAUSE|ERR|RC|RUN|PM)-[A-Za-z0-9\-]+")


class MentionIndex:
    """Index of entity ids/names/patterns for linking free text to graph nodes."""

    def __init__(self) -> None:
        # lowercased phrase -> entity_id
        self._by_id: dict[str, str] = {}
        self._by_phrase: dict[str, str] = {}

    def add(self, entity_id: str, names: list[str], patterns: list[str] | None = None) -> None:
        self._by_id[entity_id.lower()] = entity_id
        for n in names:
            if n and len(n) >= 3:
                self._by_phrase[n.lower()] = entity_id
        for p in patterns or []:
            if p and len(p) >= 4:
                self._by_phrase[p.lower()] = entity_id

    def find(self, text: str) -> list[str]:
        found: set[str] = set()
        low = text.lower()
        # Exact ids anywhere in text.
        for m in _ID_RE.findall(text):
            eid = self._by_id.get(m.lower())
            if eid:
                found.add(eid)
        # Known names / error patterns as substrings.
        for phrase, eid in self._by_phrase.items():
            if phrase in low:
                found.add(eid)
        return sorted(found)
