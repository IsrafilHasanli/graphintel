"""Prepare the full local demo dataset for GraphIntel.

Pipeline:
  1. Attempt public downloads (best-effort, logged, never fatal).
  2. Generate the deterministic synthetic dataset.
  3. Convert canonical synthetic entities into source-shaped import files
     (CSV / JSON / Markdown) under data/processed/import so the *real* ingestion
     pipeline parses them like customer-provided files.
  4. Emit test fixtures and the golden question set under data/fixtures.
  5. Print a clear summary of which sources were real vs synthetic.

Run: python scripts/prepare_demo_data.py
"""
from __future__ import annotations

import csv
import io
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import download_datasets  # noqa: E402
import generate_synthetic_demo_data as gen  # noqa: E402
from _dataset_common import (  # noqa: E402
    DATASET_REFERENCE_DATE,
    FIXTURES_DIR,
    IMPORT_DIR,
    RAW_DIR,
    SYNTHETIC_DIR,
    ensure_dirs,
    read_json,
    write_json,
    write_text,
)


def _load(name: str) -> list[dict]:
    return read_json(SYNTHETIC_DIR / f"{name}.json")  # type: ignore[return-value]


def build_tickets_csv(tickets: list[dict]) -> None:
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow([
        "ticket_id", "customer_id", "subject", "body", "service_id",
        "error_signature", "priority", "status", "created_at", "related_incident_id",
    ])
    for t in tickets:
        writer.writerow([
            t["id"], t["customer_id"], t["subject"], t["body"], t["service_id"],
            t["error_signature_id"], t["priority"], t["status"], t["created_at"],
            t["related_incident_id"] or "",
        ])
    write_text(IMPORT_DIR / "support_tickets.csv", buf.getvalue())


def build_incidents_json(incidents: list[dict], updates: list[dict]) -> None:
    updates_by_incident: dict[str, list[dict]] = {}
    for u in updates:
        updates_by_incident.setdefault(u["incident_id"], []).append({
            "id": u["id"], "status": u["status"], "posted_at": u["posted_at"],
            "message": u["message"],
        })
    payload = []
    for inc in incidents:
        payload.append({
            "id": inc["id"], "title": inc["title"], "service_id": inc["service_id"],
            "error_signature": inc["error_signature_id"], "root_cause": inc["root_cause_id"],
            "severity": inc["severity"], "status": inc["status"],
            "started_at": inc["started_at"], "resolved_at": inc["resolved_at"],
            "impacted_customers": inc["impacted_customers"],
            "updates": updates_by_incident.get(inc["id"], []),
        })
    write_json(IMPORT_DIR / "incidents.json", payload)


def build_catalog_json(customers, teams, services, error_signatures, root_causes) -> None:
    write_json(IMPORT_DIR / "customers.json", customers)
    write_json(IMPORT_DIR / "services.json", {"teams": teams, "services": services})
    write_json(IMPORT_DIR / "error_signatures.json", error_signatures)
    write_json(IMPORT_DIR / "root_causes.json", root_causes)


def build_sla_markdown(contracts: list[dict], clauses: list[dict]) -> None:
    clauses_by_contract: dict[str, list[dict]] = {}
    for cl in clauses:
        clauses_by_contract.setdefault(cl["contract_id"], []).append(cl)
    sla_dir = IMPORT_DIR / "sla"
    for c in contracts:
        lines = [f"# {c['name']} ({c['id']})", "", f"Customer: {c['customer_id']}",
                 f"Tier: {c['tier']}", "", "## Clauses", ""]
        for cl in clauses_by_contract.get(c["id"], []):
            constrains = ", ".join(cl["constrains_services"]) or "n/a"
            lines.append(f"### {cl['id']} ({cl['kind']})")
            lines.append("")
            lines.append(cl["text"])
            lines.append("")
            lines.append(f"- Threshold: {cl['threshold']}")
            lines.append(f"- Constrains services: {constrains}")
            lines.append("")
        write_text(sla_dir / f"{c['id']}.md", "\n".join(lines) + "\n")


def build_runbook_markdown(runbooks: list[dict]) -> None:
    rb_dir = IMPORT_DIR / "runbooks"
    for rb in runbooks:
        lines = [f"# {rb['title']} ({rb['id']})", "",
                 f"Mitigates error signature: {rb['error_signature_id']}",
                 f"Primary service: {rb['service_id']}", "", "## Steps", ""]
        for i, step in enumerate(rb["steps"], start=1):
            lines.append(f"{i}. {step}")
        write_text(rb_dir / f"{rb['id']}.md", "\n".join(lines) + "\n")


def build_postmortem_markdown(postmortems: list[dict]) -> None:
    pm_dir = IMPORT_DIR / "postmortems"
    for pm in postmortems:
        write_text(pm_dir / f"{pm['id']}.md", pm["body"])


def build_graph_seed(tables: dict[str, list[dict]]) -> None:
    """A single file that lets the graph service seed nodes + edges directly."""
    write_json(IMPORT_DIR / "graph_seed.json", {
        "reference_date": DATASET_REFERENCE_DATE.isoformat(),
        "entities": {k: v for k, v in tables.items() if k != "relations"},
        "relations": tables["relations"],
    })


def build_golden_questions() -> None:
    golden = [
        {
            "id": "GQ-1",
            "question": "Which customers were affected by Payment API incidents in the last 30 days?",
            "intent": "impact_analysis",
            "time_range_days": 30,
            "required_evidence_types": ["incident", "support_ticket"],
            "expected_entities": ["CUST-acme", "CUST-globex"],
            "expected_evidence_ids": ["INC-247", "INC-0249", "SVC-payment-api"],
            "expected_answer_themes": ["Payment API", "affected customers", "last 30 days"],
            "expected_reasoning_edges": [
                "Customer REPORTED SupportTicket",
                "SupportTicket RELATED_TO Incident",
                "Incident AFFECTED Service",
            ],
        },
        {
            "id": "GQ-2",
            "question": "Is Acme Corp at SLA risk because of checkout or payment incidents?",
            "intent": "sla_risk",
            "time_range_days": None,
            "required_evidence_types": ["incident", "sla_clause", "support_ticket"],
            "expected_entities": ["CUST-acme", "CLAUSE-acme-availability-99-9"],
            "expected_evidence_ids": ["INC-247", "INC-0248", "CLAUSE-acme-availability-99-9"],
            "expected_answer_themes": ["SLA risk", "availability", "Acme"],
            "expected_reasoning_edges": [
                "SLAContract APPLIES_TO Customer",
                "SLAClause PART_OF SLAContract",
                "SLAClause CONSTRAINS Service",
                "Incident MAY_VIOLATE SLAClause",
            ],
        },
        {
            "id": "GQ-3",
            "question": "Which engineering team owns the service involved in INC-247?",
            "intent": "ownership",
            "time_range_days": None,
            "required_evidence_types": ["incident", "service", "team"],
            "expected_entities": ["TEAM-backend-payments"],
            "expected_evidence_ids": ["INC-247", "SVC-payment-api", "TEAM-backend-payments"],
            "expected_answer_themes": ["Payments Platform", "owns", "Payment API"],
            "expected_reasoning_edges": [
                "Incident AFFECTED Service",
                "Service OWNED_BY Team",
            ],
        },
        {
            "id": "GQ-4",
            "question": "What is the likely root cause of recurring checkout timeout tickets?",
            "intent": "root_cause",
            "time_range_days": None,
            "required_evidence_types": ["support_ticket", "incident", "root_cause"],
            "expected_entities": ["RC-downstream-payment-latency"],
            "expected_evidence_ids": ["INC-0248", "RC-downstream-payment-latency"],
            "expected_answer_themes": ["downstream payment latency", "checkout timeout", "root cause"],
            "expected_reasoning_edges": [
                "SupportTicket RELATED_TO Incident",
                "Incident CAUSED_BY RootCause",
            ],
        },
        {
            "id": "GQ-5",
            "question": "Which runbook should be used for payment gateway timeout errors?",
            "intent": "runbook_lookup",
            "time_range_days": None,
            "required_evidence_types": ["error_signature", "runbook"],
            "expected_entities": ["RUN-payment-gateway-timeout"],
            "expected_evidence_ids": ["ERR-payment-gateway-timeout", "RUN-payment-gateway-timeout"],
            "expected_answer_themes": ["payment gateway timeout", "runbook", "mitigation"],
            "expected_reasoning_edges": [
                "Runbook MITIGATES ErrorSignature",
            ],
        },
    ]
    write_json(FIXTURES_DIR / "golden_questions.json", {
        "reference_date": DATASET_REFERENCE_DATE.isoformat(),
        "questions": golden,
    })


def build_fixtures(tables: dict[str, list[dict]]) -> None:
    # Expected counts (used by validate + tests).
    write_json(FIXTURES_DIR / "expected_counts.json",
               {name: len(rows) for name, rows in tables.items()})
    # A tiny CSV fixture for ingestion unit tests (first 3 tickets + 1 malformed row).
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(["ticket_id", "customer_id", "subject", "body", "service_id",
                     "error_signature", "priority", "status", "created_at", "related_incident_id"])
    for t in tables["support_tickets"][:3]:
        writer.writerow([t["id"], t["customer_id"], t["subject"], t["body"], t["service_id"],
                         t["error_signature_id"], t["priority"], t["status"], t["created_at"],
                         t["related_incident_id"] or ""])
    # Intentionally malformed row (missing columns) to exercise error reporting.
    writer.writerow(["SUP-BAD", "CUST-acme", "broken row"])
    write_text(FIXTURES_DIR / "tickets_sample.csv", buf.getvalue())
    build_golden_questions()


def main() -> int:
    ensure_dirs()

    # 1. Public downloads (best effort).
    download_datasets.main()

    # 2. Synthetic generation.
    gen.main()

    # 3. Load synthetic tables.
    tables = {
        name: _load(name)
        for name in [
            "customers", "teams", "services", "error_signatures", "root_causes",
            "incidents", "incident_updates", "sla_contracts", "sla_clauses",
            "runbooks", "postmortems", "support_tickets", "relations",
        ]
    }

    # 4. Convert to import-shaped source files.
    build_tickets_csv(tables["support_tickets"])
    build_incidents_json(tables["incidents"], tables["incident_updates"])
    build_catalog_json(tables["customers"], tables["teams"], tables["services"],
                       tables["error_signatures"], tables["root_causes"])
    build_sla_markdown(tables["sla_contracts"], tables["sla_clauses"])
    build_runbook_markdown(tables["runbooks"])
    build_postmortem_markdown(tables["postmortems"])
    build_graph_seed(tables)

    # 5. Fixtures + golden questions.
    build_fixtures(tables)

    # Summary of real vs synthetic.
    download_manifest = read_json(RAW_DIR / "download_manifest.json")
    real = download_manifest.get("downloaded", 0)
    failed = download_manifest.get("failed", 0)

    print("\n=== GraphIntel demo data ready ===")
    print(f"Reference date : {DATASET_REFERENCE_DATE.isoformat()}")
    print(f"Public sources : {real} downloaded, {failed} failed -> synthetic fallback")
    print(f"Synthetic dir  : {SYNTHETIC_DIR}")
    print(f"Import dir      : {IMPORT_DIR}")
    print(f"Fixtures dir    : {FIXTURES_DIR}")
    print("Entity/relation counts:")
    for name, rows in tables.items():
        print(f"  {name:20s} {len(rows):4d}")
    print("\nAll domain data is synthetic (provenance-stamped). Run "
          "validate_demo_data.py to verify golden-question readiness.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
