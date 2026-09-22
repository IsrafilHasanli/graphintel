"""Seed the platform from the prepared demo import files.

Ingests the demo corpus through the *real* ingestion + extraction pipeline (so
the seeded graph is built by production code, not a shortcut), then runs a graph
enrichment pass to derive MAY_VIOLATE edges (Incident -> SLAClause) that require
cross-referencing incidents, impacted customers, SLA clauses, and constrained
services.
"""
from __future__ import annotations

from pathlib import Path

from sqlalchemy.orm import Session

from app import models
from app.graph import SQLGraphStore
from app.logging_config import get_logger
from app.services.ingestion import IngestionService

log = get_logger("seed")

REPO_ROOT = Path(__file__).resolve().parents[3]
IMPORT_DIR = REPO_ROOT / "data" / "processed" / "import"

# Dependency order: catalogs before things that reference them so relation
# endpoint validation passes.
INGEST_PLAN: list[tuple[str, str]] = [
    ("customers.json", "customers"),
    ("services.json", "services"),
    ("error_signatures.json", "error_signatures"),
    ("root_causes.json", "root_causes"),
    ("incidents.json", "incidents"),
    ("support_tickets.csv", "support_tickets"),
]


def _ingest_glob(svc: IngestionService, subdir: str, kind: str, jobs: list) -> None:
    d = IMPORT_DIR / subdir
    if not d.exists():
        return
    for path in sorted(d.glob("*.md")):
        job = svc.ingest(filename=f"{subdir}/{path.name}", content=path.read_text(encoding="utf-8"),
                         source="import", source_kind=kind)
        jobs.append(job)


def enrich_may_violate(session: Session) -> int:
    """Derive Incident MAY_VIOLATE SLAClause edges.

    An incident on service S impacting customer C may violate any clause of C's
    SLA contract that constrains S.
    """
    graph = SQLGraphStore(session)
    incidents = graph.list_entities("Incident")
    clauses = graph.list_entities("SLAClause")
    # customer -> contract ids
    applies = {r.target_id: r.source_id
               for r in session.query(models.Relation).filter_by(type="APPLIES_TO", deleted=False)}
    # clause -> contract
    part_of = {r.source_id: r.target_id
               for r in session.query(models.Relation).filter_by(type="PART_OF", deleted=False)}
    clauses_by_contract: dict[str, list] = {}
    for cl in clauses:
        contract = part_of.get(cl.id)
        if contract:
            clauses_by_contract.setdefault(contract, []).append(cl)

    added = 0
    for inc in incidents:
        service_id = inc.attributes.get("service_id")
        for cust in inc.attributes.get("impacted_customers", []):
            contract = applies.get(cust)
            if not contract:
                continue
            for cl in clauses_by_contract.get(contract, []):
                if service_id in (cl.attributes.get("constrains_services") or []):
                    rid = graph.upsert_relation("MAY_VIOLATE", inc.id, cl.id,
                                                confidence=0.8, method="rule")
                    if rid:
                        added += 1
    session.flush()
    log.info("may_violate_enriched", added=added)
    return added


def seed_all(session: Session, reset: bool = True) -> dict:
    if reset:
        for model in (models.EvalResult, models.EvalRun, models.Answer, models.Audit,
                      models.JobError, models.Chunk, models.Document, models.IngestionJob,
                      models.Relation, models.Entity):
            session.query(model).delete()
        session.flush()

    svc = IngestionService(session)
    jobs: list[models.IngestionJob] = []
    for filename, kind in INGEST_PLAN:
        path = IMPORT_DIR / filename
        if not path.exists():
            log.warning("seed_file_missing", file=filename)
            continue
        jobs.append(svc.ingest(filename=filename, content=path.read_text(encoding="utf-8"),
                               source="import", source_kind=kind))
    _ingest_glob(svc, "sla", "sla", jobs)
    _ingest_glob(svc, "runbooks", "runbook", jobs)
    _ingest_glob(svc, "postmortems", "postmortem", jobs)

    may_violate = enrich_may_violate(session)

    summary = {
        "jobs": len(jobs),
        "documents": session.query(models.Document).count(),
        "chunks": session.query(models.Chunk).count(),
        "entities": session.query(models.Entity).count(),
        "relations": session.query(models.Relation).filter_by(deleted=False).count(),
        "may_violate_derived": may_violate,
        "job_states": {},
    }
    for job in jobs:
        summary["job_states"][job.state] = summary["job_states"].get(job.state, 0) + 1
    return summary
