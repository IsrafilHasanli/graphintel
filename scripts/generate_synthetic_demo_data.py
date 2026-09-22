"""Generate the deterministic synthetic demo dataset for GraphIntel.

Run: python scripts/generate_synthetic_demo_data.py

Produces canonical entity + relation JSON under data/synthetic/. Everything is
deterministic (fixed reference date, no randomness) and carries provenance
markers (synthetic/source_rule/created_by_script). The data is intentionally
shaped so the five golden Graph RAG questions are answerable:

  1. Which customers were affected by Payment API incidents in the last 30 days?
  2. Is Acme Corp at SLA risk because of checkout or payment incidents?
  3. Which engineering team owns the service involved in INC-247?
  4. What is the likely root cause of recurring checkout timeout tickets?
  5. Which runbook should be used for payment gateway timeout errors?
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from _dataset_common import (  # noqa: E402
    SYNTHETIC_DIR,
    days_ago,
    ensure_dirs,
    synthetic_meta,
    write_json,
)

# --- Base reference tables -------------------------------------------------

CUSTOMERS = [
    ("CUST-acme", "Acme Corp", ["Acme", "Acme Corporation", "ACME"], "enterprise"),
    ("CUST-globex", "Globex Inc", ["Globex", "Globex Incorporated"], "enterprise"),
    ("CUST-initech", "Initech", ["Initech LLC"], "business"),
    ("CUST-umbrella", "Umbrella LLC", ["Umbrella", "Umbrella Corp"], "business"),
    ("CUST-hooli", "Hooli", ["Hooli Inc"], "enterprise"),
]

TEAMS = [
    ("TEAM-backend-payments", "Payments Platform", "payments-oncall@graphintel.example"),
    ("TEAM-checkout", "Checkout Experience", "checkout-oncall@graphintel.example"),
    ("TEAM-platform-infra", "Platform Infrastructure", "infra-oncall@graphintel.example"),
    ("TEAM-data-platform", "Data Platform", "data-oncall@graphintel.example"),
]

# (id, name, owning_team, tier)
SERVICES = [
    ("SVC-payment-api", "Payment API", "TEAM-backend-payments", "critical"),
    ("SVC-payment-gateway", "Payment Gateway", "TEAM-backend-payments", "critical"),
    ("SVC-checkout", "Checkout Service", "TEAM-checkout", "critical"),
    ("SVC-cart", "Cart Service", "TEAM-checkout", "high"),
    ("SVC-auth", "Auth Service", "TEAM-platform-infra", "critical"),
    ("SVC-search", "Search Service", "TEAM-data-platform", "medium"),
    ("SVC-notifications", "Notification Service", "TEAM-platform-infra", "medium"),
    ("SVC-billing", "Billing Service", "TEAM-backend-payments", "high"),
]

# (id, name, patterns, severity)
ERROR_SIGNATURES = [
    ("ERR-payment-gateway-timeout", "Payment gateway timeout",
     ["payment gateway timeout", "gateway timed out", "PaymentGatewayTimeoutException",
      "payment gateway timed out"], "high"),
    ("ERR-checkout-timeout", "Checkout timeout",
     ["checkout timeout", "checkout timed out", "checkout request timed out"], "high"),
    ("ERR-db-connection-exhausted", "Database connection pool exhausted",
     ["connection pool exhausted", "too many connections", "PoolTimeout"], "critical"),
    ("ERR-auth-5xx", "Auth service 5xx errors",
     ["auth 500", "token service unavailable", "authentication failed 5xx"], "critical"),
    ("ERR-search-slow-query", "Search slow query",
     ["slow query", "search latency", "query timeout"], "medium"),
]

# (id, title, description)
ROOT_CAUSES = [
    ("RC-connection-pool-exhaustion", "Database connection pool exhaustion",
     "Payment API exhausted its database connection pool under load, so gateway "
     "calls queued and timed out."),
    ("RC-downstream-payment-latency", "Downstream payment latency",
     "Elevated Payment API latency propagated to Checkout, causing checkout "
     "requests to time out."),
    ("RC-deploy-regression", "Bad deployment regression",
     "A regression introduced in a recent deploy increased error rates."),
    ("RC-auth-cert-expiry", "Expired TLS certificate",
     "An expired certificate caused auth token validation to fail."),
    ("RC-search-index-bloat", "Search index bloat",
     "An unpruned search index increased query latency."),
]

# (id, title, service, error_sig, root_cause, days_ago, severity, status, impacted_customers)
INCIDENTS = [
    ("INC-247", "Payment API elevated gateway timeouts", "SVC-payment-api",
     "ERR-payment-gateway-timeout", "RC-connection-pool-exhaustion", 3, "SEV1",
     "resolved", ["CUST-acme", "CUST-globex"]),
    ("INC-0248", "Checkout timeouts during peak traffic", "SVC-checkout",
     "ERR-checkout-timeout", "RC-downstream-payment-latency", 10, "SEV2",
     "resolved", ["CUST-acme", "CUST-initech"]),
    ("INC-0249", "Payment API 5xx spike after deploy", "SVC-payment-api",
     "ERR-payment-gateway-timeout", "RC-deploy-regression", 18, "SEV2",
     "resolved", ["CUST-globex"]),
    ("INC-0250", "Checkout errors after release", "SVC-checkout",
     "ERR-checkout-timeout", "RC-deploy-regression", 25, "SEV3",
     "resolved", ["CUST-hooli"]),
    ("INC-0251", "Payment gateway timeouts", "SVC-payment-gateway",
     "ERR-payment-gateway-timeout", "RC-connection-pool-exhaustion", 8, "SEV2",
     "resolved", ["CUST-acme"]),
    ("INC-0252", "Auth service outage", "SVC-auth",
     "ERR-auth-5xx", "RC-auth-cert-expiry", 40, "SEV1",
     "resolved", ["CUST-umbrella", "CUST-hooli"]),
    ("INC-0253", "Search latency degradation", "SVC-search",
     "ERR-search-slow-query", "RC-search-index-bloat", 55, "SEV3",
     "resolved", ["CUST-initech"]),
    ("INC-0254", "Notification delivery delays", "SVC-notifications",
     "ERR-db-connection-exhausted", "RC-connection-pool-exhaustion", 60, "SEV3",
     "resolved", ["CUST-globex"]),
    ("INC-0255", "Billing sync failure", "SVC-billing",
     "ERR-db-connection-exhausted", "RC-connection-pool-exhaustion", 20, "SEV2",
     "resolved", ["CUST-acme"]),
    ("INC-0256", "Cart service errors", "SVC-cart",
     "ERR-checkout-timeout", "RC-downstream-payment-latency", 12, "SEV3",
     "resolved", ["CUST-initech"]),
]

# Ticket themes drive both text content and graph links.
# (theme, subject, body, service, error_sig, candidate_incidents)
TICKET_THEMES = {
    "checkout-timeout": (
        "Checkout keeps timing out at the payment step",
        "Multiple customers report the checkout request timed out when applying "
        "payment. We keep seeing 'checkout timeout' errors at peak hours.",
        "SVC-checkout", "ERR-checkout-timeout", ["INC-0248", "INC-0250", "INC-0256"]),
    "payment-gateway-timeout": (
        "Payment gateway timeout on transactions",
        "Payments are failing with PaymentGatewayTimeoutException; the payment "
        "gateway timed out repeatedly during checkout.",
        "SVC-payment-api", "ERR-payment-gateway-timeout", ["INC-247", "INC-0249", "INC-0251"]),
    "auth": (
        "Users cannot log in",
        "Authentication is failing with 'token service unavailable' (auth 500).",
        "SVC-auth", "ERR-auth-5xx", ["INC-0252"]),
    "search": (
        "Search is very slow",
        "Search latency is high and queries time out for large catalogs.",
        "SVC-search", "ERR-search-slow-query", ["INC-0253"]),
    "billing": (
        "Billing amounts are not syncing",
        "Billing sync is failing; logs show connection pool exhausted errors.",
        "SVC-billing", "ERR-db-connection-exhausted", ["INC-0255"]),
    "notifications": (
        "Delayed email notifications",
        "Notification delivery is delayed significantly for our customers.",
        "SVC-notifications", "ERR-db-connection-exhausted", ["INC-0254"]),
    "cart": (
        "Cart is not updating",
        "Cart service throws errors when adding items and checkout timed out.",
        "SVC-cart", "ERR-checkout-timeout", ["INC-0256"]),
}

# Deterministic theme frequency (sums to 50). checkout-timeout and
# payment-gateway-timeout are intentionally recurring for golden questions.
TICKET_PLAN = (
    ["checkout-timeout"] * 14
    + ["payment-gateway-timeout"] * 12
    + ["auth"] * 5
    + ["search"] * 5
    + ["billing"] * 5
    + ["notifications"] * 4
    + ["cart"] * 5
)

PRIORITIES = ["P1", "P2", "P3", "P4"]
TICKET_STATUSES = ["resolved", "closed", "open", "pending"]


def build_customers() -> list[dict]:
    out = []
    for cid, name, aliases, tier in CUSTOMERS:
        out.append({
            "id": cid, "type": "Customer", "name": name, "aliases": aliases,
            "tier": tier, **synthetic_meta("customer_catalog"),
        })
    return out


def build_teams() -> list[dict]:
    return [
        {"id": tid, "type": "Team", "name": name, "contact": contact,
         **synthetic_meta("team_catalog")}
        for tid, name, contact in TEAMS
    ]


def build_services() -> list[dict]:
    return [
        {"id": sid, "type": "Service", "name": name, "owning_team": team, "tier": tier,
         **synthetic_meta("service_catalog")}
        for sid, name, team, tier in SERVICES
    ]


def build_error_signatures() -> list[dict]:
    return [
        {"id": eid, "type": "ErrorSignature", "name": name, "patterns": patterns,
         "severity": sev, **synthetic_meta("error_signature_catalog")}
        for eid, name, patterns, sev in ERROR_SIGNATURES
    ]


def build_root_causes() -> list[dict]:
    return [
        {"id": rid, "type": "RootCause", "title": title, "description": desc,
         **synthetic_meta("root_cause_catalog")}
        for rid, title, desc in ROOT_CAUSES
    ]


def build_incidents() -> tuple[list[dict], list[dict]]:
    incidents, updates = [], []
    for (iid, title, svc, err, rc, ago, sev, status, impacted) in INCIDENTS:
        incidents.append({
            "id": iid, "type": "Incident", "title": title, "service_id": svc,
            "error_signature_id": err, "root_cause_id": rc, "severity": sev,
            "status": status, "started_at": days_ago(ago),
            "resolved_at": days_ago(max(ago - 1, 0)), "impacted_customers": impacted,
            **synthetic_meta("incident_catalog"),
        })
        # Two lifecycle updates per incident (>= 20 total).
        updates.append({
            "id": f"{iid}-U1", "type": "IncidentUpdate", "incident_id": iid,
            "status": "identified", "posted_at": days_ago(ago),
            "message": f"We identified elevated errors on {title.lower()} and are investigating.",
            **synthetic_meta("incident_update_catalog"),
        })
        updates.append({
            "id": f"{iid}-U2", "type": "IncidentUpdate", "incident_id": iid,
            "status": "resolved", "posted_at": days_ago(max(ago - 1, 0)),
            "message": f"Mitigation applied for {title.lower()}; service recovered.",
            **synthetic_meta("incident_update_catalog"),
        })
    return incidents, updates


def build_sla() -> tuple[list[dict], list[dict]]:
    contracts, clauses = [], []
    for cid, name, _aliases, tier in CUSTOMERS:
        slug = cid.replace("CUST-", "")
        contract_id = f"SLA-{slug}-{tier}"
        # Acme's clauses constrain the payment + checkout critical services so
        # SLA risk from payment/checkout incidents is reasoned over (golden Q2).
        if cid == "CUST-acme":
            avail_services = ["SVC-payment-api", "SVC-checkout"]
            latency_services = ["SVC-payment-api"]
        else:
            avail_services = ["SVC-payment-api"]
            latency_services = ["SVC-payment-api"]
        contracts.append({
            "id": contract_id, "type": "SLAContract", "customer_id": cid,
            "name": f"{name} {tier.title()} SLA", "tier": tier,
            **synthetic_meta("sla_contract_catalog"),
        })
        clauses.append({
            "id": f"CLAUSE-{slug}-availability-99-9", "type": "SLAClause",
            "contract_id": contract_id, "kind": "availability",
            "text": f"Monthly availability of {', '.join(avail_services)} shall be at "
                    f"least 99.9% for {name}.",
            "threshold": "99.9%", "constrains_services": avail_services,
            **synthetic_meta("sla_clause_catalog"),
        })
        clauses.append({
            "id": f"CLAUSE-{slug}-latency-p95", "type": "SLAClause",
            "contract_id": contract_id, "kind": "latency",
            "text": f"P95 latency of {', '.join(latency_services)} shall remain under "
                    f"800ms for {name}.",
            "threshold": "800ms", "constrains_services": latency_services,
            **synthetic_meta("sla_clause_catalog"),
        })
        clauses.append({
            "id": f"CLAUSE-{slug}-response-15m", "type": "SLAClause",
            "contract_id": contract_id, "kind": "response_time",
            "text": f"SEV1 incidents impacting {name} shall be acknowledged within "
                    f"15 minutes.",
            "threshold": "15m", "constrains_services": [],
            **synthetic_meta("sla_clause_catalog"),
        })
    return contracts, clauses


def build_runbooks() -> list[dict]:
    specs = [
        ("RUN-payment-gateway-timeout", "Payment gateway timeout mitigation",
         "ERR-payment-gateway-timeout", "SVC-payment-api",
         ["Check Payment API connection pool saturation and DB connection counts.",
          "Increase pool size or shed load; enable circuit breaker to the gateway.",
          "Verify gateway health and retry budget; roll back the last deploy if error rate spiked.",
          "Confirm recovery via the payment success-rate dashboard."]),
        ("RUN-checkout-timeout", "Checkout timeout mitigation",
         "ERR-checkout-timeout", "SVC-checkout",
         ["Inspect Payment API latency feeding the checkout flow.",
          "Enable checkout request hedging and raise the downstream timeout budget.",
          "Scale checkout workers; verify cart and payment dependencies.",
          "Watch checkout completion rate until stable."]),
        ("RUN-db-connection-pool", "Database connection pool exhaustion",
         "ERR-db-connection-exhausted", "SVC-billing",
         ["Identify the service holding connections open.",
          "Raise max pool size temporarily and kill idle-in-transaction sessions.",
          "Deploy the query fix; add connection leak monitoring."]),
        ("RUN-auth-outage", "Auth service outage response",
         "ERR-auth-5xx", "SVC-auth",
         ["Check TLS certificate validity and token service health.",
          "Rotate the expired certificate and restart token validators.",
          "Confirm login success rate recovery."]),
        ("RUN-search-latency", "Search latency mitigation",
         "ERR-search-slow-query", "SVC-search",
         ["Inspect slow query logs and index size.",
          "Prune or reindex the bloated search index.",
          "Verify P95 query latency returns to baseline."]),
    ]
    out = []
    for rid, title, err, svc, steps in specs:
        out.append({
            "id": rid, "type": "Runbook", "title": title, "error_signature_id": err,
            "service_id": svc, "steps": steps, **synthetic_meta("runbook_catalog"),
        })
    return out


def build_postmortems() -> list[dict]:
    incident_by_id = {i[0]: i for i in INCIDENTS}
    rc_by_id = {r[0]: r for r in ROOT_CAUSES}
    targets = ["INC-247", "INC-0248", "INC-0249", "INC-0251", "INC-0255"]
    out = []
    for iid in targets:
        _, title, svc, err, rc, ago, sev, _status, impacted = incident_by_id[iid]
        rc_title = rc_by_id[rc][1]
        rc_desc = rc_by_id[rc][2]
        body = (
            f"# Postmortem: {title} ({iid})\n\n"
            f"**Severity:** {sev}  \n**Service:** {svc}  \n"
            f"**Impacted customers:** {', '.join(impacted)}\n\n"
            f"## Summary\n{title}. Root cause: {rc_title}. {rc_desc}\n\n"
            f"## Root Cause\n{rc_desc}\n\n"
            f"## Resolution\nMitigation was applied following the relevant runbook and the "
            f"service recovered. Error signature observed: {err}.\n\n"
            f"## Follow-ups\n- Add alerting for the {err} signature.\n"
            f"- Track SLA impact for affected customers.\n"
        )
        out.append({
            "id": f"PM-{iid}", "type": "Postmortem", "incident_id": iid,
            "title": f"Postmortem: {title}", "body": body, "authored_at": days_ago(max(ago - 2, 0)),
            **synthetic_meta("postmortem_catalog"),
        })
    return out


def build_tickets() -> list[dict]:
    tickets = []
    for i, theme in enumerate(TICKET_PLAN):
        subject, body, svc, err, incidents = TICKET_THEMES[theme]
        customer = CUSTOMERS[i % len(CUSTOMERS)][0]
        # Link ~65% of tickets to a concrete incident (cycled deterministically).
        related_incident = incidents[i % len(incidents)] if (i % 3 != 2) else None
        ago = 1 + (i * 2) % 60
        tickets.append({
            "id": f"SUP-{i + 1:04d}", "type": "SupportTicket", "subject": subject,
            "body": f"{body} (ref {customer})", "customer_id": customer,
            "service_id": svc, "error_signature_id": err, "theme": theme,
            "related_incident_id": related_incident, "priority": PRIORITIES[i % len(PRIORITIES)],
            "status": TICKET_STATUSES[i % len(TICKET_STATUSES)], "created_at": days_ago(ago),
            **synthetic_meta("support_ticket_catalog"),
        })
    return tickets


def build_relations(tickets: list[dict], incidents: list[dict], contracts: list[dict],
                    clauses: list[dict], runbooks: list[dict], postmortems: list[dict]) -> list[dict]:
    rels: list[dict] = []

    def add(rtype: str, src: str, tgt: str, rule: str, confidence: float = 1.0) -> None:
        rels.append({
            "id": f"REL-{len(rels) + 1:05d}", "type": rtype, "source_id": src,
            "target_id": tgt, "confidence": round(confidence, 3), "method": "structured",
            "created_at": days_ago(0), **synthetic_meta(rule),
        })

    # Service ownership.
    for sid, _n, team, _t in SERVICES:
        add("OWNED_BY", sid, team, "service_ownership")
    # SLA contract -> customer, clause -> contract, clause -> service.
    for c in contracts:
        add("APPLIES_TO", c["id"], c["customer_id"], "sla_applies_to")
    for cl in clauses:
        add("PART_OF", cl["id"], cl["contract_id"], "sla_part_of")
        for svc in cl["constrains_services"]:
            add("CONSTRAINS", cl["id"], svc, "sla_constrains")
    # Incidents.
    clause_by_service_customer: dict[tuple[str, str], list[str]] = {}
    for cl in clauses:
        contract = next(c for c in contracts if c["id"] == cl["contract_id"])
        for svc in cl["constrains_services"]:
            clause_by_service_customer.setdefault((svc, contract["customer_id"]), []).append(cl["id"])
    for inc in incidents:
        add("AFFECTED", inc["id"], inc["service_id"], "incident_affected")
        add("CAUSED_BY", inc["id"], inc["root_cause_id"], "incident_caused_by")
        add("EXHIBITS", inc["id"], inc["error_signature_id"], "incident_exhibits")
        add("HAS_UPDATE", inc["id"], f"{inc['id']}-U1", "incident_has_update")
        add("HAS_UPDATE", inc["id"], f"{inc['id']}-U2", "incident_has_update")
        # MAY_VIOLATE: an incident on a constrained service risks the customer's clause.
        for cust in inc["impacted_customers"]:
            for clause_id in clause_by_service_customer.get((inc["service_id"], cust), []):
                add("MAY_VIOLATE", inc["id"], clause_id, "incident_may_violate", 0.8)
    # Tickets.
    for t in tickets:
        add("REPORTED", t["customer_id"], t["id"], "customer_reported")
        add("EXHIBITS", t["id"], t["error_signature_id"], "ticket_exhibits", 0.9)
        if t["related_incident_id"]:
            add("RELATED_TO", t["id"], t["related_incident_id"], "ticket_related_to", 0.9)
    # Runbooks mitigate error signatures.
    for rb in runbooks:
        add("MITIGATES", rb["id"], rb["error_signature_id"], "runbook_mitigates")
    # Postmortems analyze incidents.
    for pm in postmortems:
        add("ANALYZES", pm["id"], pm["incident_id"], "postmortem_analyzes")
    return rels


def main() -> int:
    ensure_dirs()
    customers = build_customers()
    teams = build_teams()
    services = build_services()
    error_signatures = build_error_signatures()
    root_causes = build_root_causes()
    incidents, incident_updates = build_incidents()
    sla_contracts, sla_clauses = build_sla()
    runbooks = build_runbooks()
    postmortems = build_postmortems()
    tickets = build_tickets()
    relations = build_relations(tickets, incidents, sla_contracts, sla_clauses,
                                runbooks, postmortems)

    tables = {
        "customers": customers,
        "teams": teams,
        "services": services,
        "error_signatures": error_signatures,
        "root_causes": root_causes,
        "incidents": incidents,
        "incident_updates": incident_updates,
        "sla_contracts": sla_contracts,
        "sla_clauses": sla_clauses,
        "runbooks": runbooks,
        "postmortems": postmortems,
        "support_tickets": tickets,
        "relations": relations,
    }
    for name, rows in tables.items():
        write_json(SYNTHETIC_DIR / f"{name}.json", rows)

    print("Synthetic dataset generated in", SYNTHETIC_DIR)
    for name, rows in tables.items():
        print(f"  {name:20s} {len(rows):4d}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
