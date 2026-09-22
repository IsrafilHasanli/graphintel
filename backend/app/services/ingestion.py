"""Ingestion service: parse -> chunk -> extract -> graph -> index.

Handles CSV (tickets), JSON (incidents + catalogs), and Markdown (SLA, runbooks,
postmortems). Produces Document + Chunk records with source provenance, runs
extraction, writes entities/relations to the graph mirror, links chunks to graph
nodes (mentions), and embeds chunks. Job state advances through every stage and
every parse/extraction failure is recorded on the job (never silently dropped).
"""
from __future__ import annotations

import csv
import hashlib
import io
import json
import re
import uuid
from pathlib import PurePosixPath

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app import models
from app.config import get_settings
from app.domain import JobState
from app.graph import SQLGraphStore
from app.logging_config import get_logger
from app.services.extraction import MentionIndex, extract_llm_free_text, extract_structured
from app.vector import EmbeddingProvider, get_embedding_provider

log = get_logger("ingestion")

MAX_CHUNK_CHARS = 900


# --- helpers ---------------------------------------------------------------
def _sha256(data: str) -> str:
    return hashlib.sha256(data.encode("utf-8")).hexdigest()


def _doc_id(sha: str) -> str:
    return f"DOC-{sha[:12]}"


def infer_source_type(filename: str) -> str:
    ext = PurePosixPath(filename).suffix.lower()
    return {".csv": "csv", ".json": "json", ".md": "markdown",
            ".markdown": "markdown", ".txt": "txt"}.get(ext, "txt")


def infer_source_kind(filename: str, source_type: str) -> str:
    stem = PurePosixPath(filename).name.lower()
    if source_type == "csv" or "ticket" in stem:
        return "support_tickets"
    if stem.startswith("pm-") or "postmortem" in stem:
        return "postmortem"
    if stem.startswith("run-") or "runbook" in stem:
        return "runbook"
    if stem.startswith("sla-") or stem.startswith("clause"):
        return "sla"
    if "incident" in stem:
        return "incidents"
    if "customer" in stem:
        return "customers"
    if "service" in stem:
        return "services"
    if "error_signature" in stem or "error-signature" in stem:
        return "error_signatures"
    if "root_cause" in stem or "root-cause" in stem:
        return "root_causes"
    if source_type == "json":
        return "incidents"
    return "document"


def _dedupe_extraction_result(result) -> None:
    """Merge duplicate IDs produced by combining structured and LLM extraction."""
    entities = {}
    for ent in result.entities:
        existing = entities.get(ent.id)
        if existing is None:
            entities[ent.id] = ent
            continue
        existing.aliases = sorted(set(existing.aliases) | set(ent.aliases))
        existing.attributes = {**(existing.attributes or {}), **(ent.attributes or {})}
        existing.confidence = max(existing.confidence, ent.confidence)
        if existing.method != "structured" and ent.method == "structured":
            existing.type = ent.type
            existing.canonical_name = ent.canonical_name
            existing.method = ent.method
            existing.source_document_id = ent.source_document_id

    relations = {}
    for rel in result.relations:
        key = (rel.type, rel.source_id, rel.target_id)
        existing = relations.get(key)
        if existing is None:
            relations[key] = rel
            continue
        existing.confidence = max(existing.confidence, rel.confidence)
        if existing.method != "structured" and rel.method == "structured":
            existing.method = rel.method
            existing.source_document_id = rel.source_document_id

    result.entities = list(entities.values())
    result.relations = list(relations.values())


# --- parsers: return (records, chunk_texts, parse_errors, title) -----------
def _parse_tickets_csv(content: str) -> tuple[list[dict], list[tuple[str, str]], list[tuple[str, str]]]:
    records: list[dict] = []
    chunks: list[tuple[str, str]] = []      # (ref, text)
    errors: list[tuple[str, str]] = []      # (row_ref, reason)
    reader = csv.DictReader(io.StringIO(content))
    required = {"ticket_id", "customer_id", "subject"}
    for i, row in enumerate(reader, start=2):  # header is line 1
        missing = [c for c in required if not (row.get(c) or "").strip()]
        if missing or None in row.values():
            errors.append((f"row:{i}", f"missing/invalid columns: {missing or 'ragged row'}"))
            continue
        rec = {
            "id": row["ticket_id"].strip(),
            "customer_id": row["customer_id"].strip(),
            "subject": row.get("subject", "").strip(),
            "body": row.get("body", "").strip(),
            "service_id": (row.get("service_id") or "").strip() or None,
            "error_signature": (row.get("error_signature") or "").strip() or None,
            "priority": (row.get("priority") or "").strip(),
            "status": (row.get("status") or "").strip(),
            "created_at": (row.get("created_at") or "").strip(),
            "related_incident_id": (row.get("related_incident_id") or "").strip() or None,
        }
        records.append(rec)
        text = (f"[{rec['id']}] {rec['subject']} "
                f"(customer {rec['customer_id']}, priority {rec['priority']}, "
                f"status {rec['status']}). {rec['body']}")
        chunks.append((rec["id"], text))
    return records, chunks, errors


def _parse_incidents_json(content: str) -> tuple[list[dict], list[tuple[str, str]], list[tuple[str, str]]]:
    data = json.loads(content)
    records, chunks, errors = [], [], []
    for i, inc in enumerate(data):
        if "id" not in inc:
            errors.append((f"item:{i}", "incident missing id"))
            continue
        records.append(inc)
        updates = "; ".join(u.get("message", "") for u in inc.get("updates", []))
        text = (f"[{inc['id']}] {inc.get('title', '')} severity {inc.get('severity', '')} "
                f"on {inc.get('service_id', '')} error {inc.get('error_signature', '')}. "
                f"Impacted: {', '.join(inc.get('impacted_customers', []))}. Updates: {updates}")
        chunks.append((inc["id"], text))
    return records, chunks, errors


def _parse_catalog_json(content: str, kind: str) -> tuple[list[dict], list[tuple[str, str]], list[tuple[str, str]]]:
    data = json.loads(content)
    if kind == "services":
        # single combined record; one chunk per service/team
        chunks = []
        for t in data.get("teams", []):
            chunks.append((t["id"], f"[{t['id']}] Team {t['name']} contact {t.get('contact', '')}"))
        for s in data.get("services", []):
            chunks.append((s["id"], f"[{s['id']}] Service {s['name']} owned by {s.get('owning_team', '')}"))
        return [data], chunks, []
    # list catalogs
    records, chunks, errors = [], [], []
    for i, rec in enumerate(data):
        if "id" not in rec:
            errors.append((f"item:{i}", f"{kind} record missing id"))
            continue
        records.append(rec)
        name = rec.get("name") or rec.get("title") or rec["id"]
        chunks.append((rec["id"], f"[{rec['id']}] {name}"))
    return records, chunks, errors


_HEADING_RE = re.compile(r"^#\s+(.*)$", re.MULTILINE)
_CLAUSE_HDR_RE = re.compile(r"^###\s+(CLAUSE-[\w\-]+)\s+\((\w+)\)", re.MULTILINE)


def _chunk_markdown(text: str) -> list[str]:
    blocks, buf = [], []
    for para in re.split(r"\n\s*\n", text):
        para = para.strip()
        if not para:
            continue
        if sum(len(b) for b in buf) + len(para) > MAX_CHUNK_CHARS and buf:
            blocks.append("\n\n".join(buf))
            buf = []
        buf.append(para)
    if buf:
        blocks.append("\n\n".join(buf))
    return blocks or [text.strip()]


def _parse_runbook_md(filename, content):
    stem = PurePosixPath(filename).stem
    err_match = re.search(r"error signature:\s*(ERR-[\w\-]+)", content)
    svc_match = re.search(r"service:\s*(SVC-[\w\-]+)", content)
    steps = re.findall(r"^\d+\.\s+(.*)$", content, re.MULTILINE)
    title_match = _HEADING_RE.search(content)
    title = title_match.group(1) if title_match else stem
    rec = {"id": stem, "title": title.split("(")[0].strip(),
           "error_signature_id": err_match.group(1) if err_match else None,
           "service_id": svc_match.group(1) if svc_match else None, "steps": steps}
    return [rec]


def _parse_postmortem_md(filename, content):
    stem = PurePosixPath(filename).stem                # e.g. PM-INC-247
    incident_id = stem[3:] if stem.upper().startswith("PM-") else None
    if not incident_id:
        m = re.search(r"\b(INC-[\w\-]+)", content)
        incident_id = m.group(1) if m else None
    title_match = _HEADING_RE.search(content)
    title = title_match.group(1) if title_match else stem
    return [{"id": stem, "title": title, "incident_id": incident_id}]


def _parse_sla_md(filename, content):
    stem = PurePosixPath(filename).stem
    cust = re.search(r"Customer:\s*(CUST-[\w\-]+)", content)
    tier = re.search(r"Tier:\s*(\w+)", content)
    name_match = _HEADING_RE.search(content)
    name = name_match.group(1).split("(")[0].strip() if name_match else stem
    contract = {"id": stem, "name": name, "customer_id": cust.group(1) if cust else None,
                "tier": tier.group(1) if tier else None}
    clauses = []
    parts = list(_CLAUSE_HDR_RE.finditer(content))
    for idx, m in enumerate(parts):
        clause_id, kind = m.group(1), m.group(2)
        segment = content[m.end():parts[idx + 1].start() if idx + 1 < len(parts) else len(content)]
        text_line = next((ln.strip() for ln in segment.splitlines() if ln.strip()), "")
        threshold = re.search(r"Threshold:\s*(.+)", segment)
        constrains = re.search(r"Constrains services:\s*(.+)", segment)
        svcs = []
        if constrains and constrains.group(1).strip() != "n/a":
            svcs = [s.strip() for s in constrains.group(1).split(",") if s.strip()]
        clauses.append({"id": clause_id, "kind": kind, "text": text_line,
                        "threshold": threshold.group(1).strip() if threshold else None,
                        "constrains_services": svcs, "confidence": 0.95})
    return [{"contract": contract, "clauses": clauses, "confidence": 0.95}]


# --- main entry ------------------------------------------------------------
class IngestionService:
    def __init__(self, session: Session, embedder: EmbeddingProvider | None = None) -> None:
        self.s = session
        self.graph = SQLGraphStore(session)
        self.embedder = embedder or get_embedding_provider()

    def _new_job(self, source: str, kind: str, filename: str) -> models.IngestionJob:
        job = models.IngestionJob(id=f"JOB-{uuid.uuid4().hex[:12]}", source=source,
                                  source_kind=kind, filename=filename,
                                  state=JobState.QUEUED.value, stats={})
        self.s.add(job)
        self.s.flush()
        return job

    def _add_error(self, job: models.IngestionJob, scope: str, ref: str, reason: str) -> None:
        self.s.add(models.JobError(job_id=job.id, scope=scope, ref=ref, reason=reason))
        log.warning("ingestion_error", job=job.id, scope=scope, ref=ref, reason=reason)

    def ingest(self, *, filename: str, content: str, source: str = "upload",
               source_kind: str | None = None) -> models.IngestionJob:
        source_type = infer_source_type(filename)
        kind = source_kind or infer_source_kind(filename, source_type)
        job = self._new_job(source, kind, filename)

        # 1. PARSE
        job.state = JobState.PARSING.value
        self.s.flush()
        try:
            records, chunk_pairs, parse_errors, doc_records = self._parse(source_type, kind, filename, content)
        except (json.JSONDecodeError, csv.Error, ValueError) as exc:
            self._add_error(job, "file", filename, f"parse failed: {exc}")
            job.state = JobState.FAILED.value
            self.s.flush()
            return job
        for ref, reason in parse_errors:
            self._add_error(job, "row", ref, reason)

        # Persist document + chunks.
        sha = _sha256(content)
        doc_id = _doc_id(sha)
        self.s.execute(delete(models.Chunk).where(models.Chunk.document_id == doc_id))
        existing = self.s.get(models.Document, doc_id)
        title = PurePosixPath(filename).name
        if existing is None:
            self.s.add(models.Document(id=doc_id, job_id=job.id, source_type=source_type,
                                       source_kind=kind, filename=filename, sha256=sha,
                                       title=title, content=content[:20000], meta={}))
        else:
            existing.job_id = job.id

        # 2. CHUNKING
        job.state = JobState.CHUNKING.value
        self.s.flush()
        chunk_rows: list[models.Chunk] = []
        for ordinal, (ref, text) in enumerate(chunk_pairs):
            cid = f"{doc_id}::c{ordinal}"
            row = models.Chunk(id=cid, document_id=doc_id, ordinal=ordinal, text=text,
                               token_count=len(text.split()), meta={"ref": ref})
            self.s.add(row)
            chunk_rows.append(row)

        # 3. EXTRACTING
        job.state = JobState.EXTRACTING.value
        self.s.flush()
        result = extract_structured(kind, records if kind != "document" else doc_records, doc_id)
        settings = get_settings()
        if settings.extraction_provider == "llm" and source_type in {"markdown", "txt"}:
            llm_result = extract_llm_free_text(kind, [(c.id, c.text) for c in chunk_rows], doc_id)
            result.entities.extend(llm_result.entities)
            result.relations.extend(llm_result.relations)
            result.errors.extend(llm_result.errors)
        _dedupe_extraction_result(result)
        for e in result.errors:
            self._add_error(job, "extraction", filename, e)
        for ent in result.entities:
            self.graph.upsert_entity(ent.id, ent.type, ent.canonical_name,
                                     attributes=ent.attributes, aliases=ent.aliases,
                                     confidence=ent.confidence, method=ent.method,
                                     source_document_id=ent.source_document_id)
        self.s.flush()
        rejected = 0
        for rel in result.relations:
            rid = self.graph.upsert_relation(rel.type, rel.source_id, rel.target_id,
                                             confidence=rel.confidence, method=rel.method,
                                             source_document_id=rel.source_document_id)
            if rid is None:
                rejected += 1
                self._add_error(job, "extraction", f"{rel.type}",
                                f"relation rejected {rel.source_id}->{rel.target_id}")
        self.s.flush()

        # Link chunks to graph nodes (rule-based mentions).
        self._link_mentions(chunk_rows)

        # 4. INDEXING (embeddings)
        job.state = JobState.INDEXING.value
        self.s.flush()
        for row in chunk_rows:
            row.embedding = self.embedder.embed(row.text)
            row.embedding_model = self.embedder.model

        # Finalize state.
        n_errors = len(parse_errors) + len(result.errors) + rejected
        job.stats = {
            "records": len(records), "chunks": len(chunk_rows),
            "entities": len(result.entities), "relations": len(result.relations) - rejected,
            "parse_errors": len(parse_errors), "extraction_errors": len(result.errors),
            "rejected_relations": rejected,
        }
        if len(chunk_rows) == 0 and len(result.entities) == 0:
            job.state = JobState.FAILED.value
        elif n_errors > 0:
            job.state = JobState.PARTIAL.value
        else:
            job.state = JobState.COMPLETED.value
        self.s.flush()
        log.info("ingested", job=job.id, kind=kind, state=job.state, **job.stats)
        return job

    def _parse(self, source_type, kind, filename, content):
        doc_records: list[dict] = []
        if source_type == "csv":
            records, chunks, errors = _parse_tickets_csv(content)
        elif source_type == "json":
            if kind == "incidents":
                records, chunks, errors = _parse_incidents_json(content)
            else:
                records, chunks, errors = _parse_catalog_json(content, kind)
        elif source_type in ("markdown", "txt"):
            if kind == "runbook":
                records, errors = _parse_runbook_md(filename, content), []
            elif kind == "postmortem":
                records, errors = _parse_postmortem_md(filename, content), []
            elif kind == "sla":
                records, errors = _parse_sla_md(filename, content), []
            else:
                records, errors = [], []
                doc_records = []
            chunks = [(f"{PurePosixPath(filename).stem}#{i}", t)
                      for i, t in enumerate(_chunk_markdown(content))]
        else:
            records, chunks, errors = [], [], []
        return records, chunks, errors, doc_records

    def _link_mentions(self, chunk_rows: list[models.Chunk]) -> None:
        index = MentionIndex()
        for ent in self.s.execute(select(models.Entity)).scalars():
            patterns = (ent.attributes or {}).get("patterns", [])
            index.add(ent.id, [ent.canonical_name, *ent.aliases], patterns)
        for row in chunk_rows:
            mentions = index.find(row.text)
            row.meta = {**(row.meta or {}), "mentions": mentions}
