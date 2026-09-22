"""Validate the GraphIntel demo dataset.

Checks:
  * Minimum entity/relation counts (docs/DATASET_PLAN.md).
  * Provenance markers present on every synthetic record.
  * Referential integrity of relations (endpoints exist).
  * Each of the 5 golden questions is answerable by traversing the seeded graph.

Exits non-zero on failure so it can gate CI. Run:
  python scripts/validate_demo_data.py
"""
from __future__ import annotations

import sys
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from _dataset_common import (  # noqa: E402
    FIXTURES_DIR,
    MINIMUM_COUNTS,
    SYNTHETIC_DIR,
    read_json,
    reference_now,
)

TABLES = [
    "customers", "teams", "services", "error_signatures", "root_causes",
    "incidents", "incident_updates", "sla_contracts", "sla_clauses",
    "runbooks", "postmortems", "support_tickets", "relations",
]


class Validator:
    def __init__(self) -> None:
        self.errors: list[str] = []
        self.checks: list[str] = []
        self.data: dict[str, list[dict]] = {}

    def load(self) -> bool:
        for name in TABLES:
            path = SYNTHETIC_DIR / f"{name}.json"
            if not path.exists():
                self.errors.append(f"missing synthetic table: {name}.json (run prepare_demo_data.py)")
                return False
            self.data[name] = read_json(path)  # type: ignore[assignment]
        return True

    def ok(self, cond: bool, msg: str) -> None:
        self.checks.append(msg)
        if not cond:
            self.errors.append(msg)

    # --- checks -------------------------------------------------------------
    def check_counts(self) -> None:
        for name, minimum in MINIMUM_COUNTS.items():
            actual = len(self.data.get(name, []))
            self.ok(actual >= minimum, f"count {name}: {actual} >= {minimum}")

    def check_provenance(self) -> None:
        for name, rows in self.data.items():
            bad = [r.get("id") for r in rows
                   if not (r.get("synthetic") and r.get("source_rule") and r.get("created_by_script"))]
            self.ok(not bad, f"provenance markers present on all {name} "
                             f"({'missing: ' + ', '.join(map(str, bad[:3])) if bad else 'ok'})")

    def check_referential_integrity(self) -> None:
        ids: set[str] = set()
        for name, rows in self.data.items():
            if name == "relations":
                continue
            ids.update(r["id"] for r in rows)
        dangling = [
            f"{r['type']}({r['source_id']}->{r['target_id']})"
            for r in self.data["relations"]
            if r["source_id"] not in ids or r["target_id"] not in ids
        ]
        self.ok(not dangling, f"relation endpoints resolve "
                              f"({'dangling: ' + ', '.join(dangling[:3]) if dangling else 'ok'})")

    # --- golden question readiness -----------------------------------------
    def _rels(self, rtype: str) -> list[dict]:
        return [r for r in self.data["relations"] if r["type"] == rtype]

    def check_golden_questions(self) -> None:
        incidents = {i["id"]: i for i in self.data["incidents"]}
        now = reference_now()
        cutoff = now - timedelta(days=30)

        # GQ-1: customers affected by Payment API incidents in last 30 days.
        payment_api_recent = {
            iid for iid, inc in incidents.items()
            if inc["service_id"] == "SVC-payment-api"
            and datetime.fromisoformat(inc["started_at"]) >= cutoff
        }
        affected_customers = set()
        related = {(r["source_id"], r["target_id"]) for r in self._rels("RELATED_TO")}
        reported = {(r["source_id"], r["target_id"]) for r in self._rels("REPORTED")}
        for ticket, inc in related:
            if inc in payment_api_recent:
                for cust, tk in reported:
                    if tk == ticket:
                        affected_customers.add(cust)
        self.ok("INC-247" in payment_api_recent, "GQ-1: INC-247 is a recent Payment API incident")
        self.ok(len(affected_customers) >= 2,
                f"GQ-1: >=2 customers linked to recent Payment API incidents ({sorted(affected_customers)})")

        # GQ-2: Acme SLA risk from payment/checkout incidents.
        may_violate = self._rels("MAY_VIOLATE")
        applies = {(r["source_id"], r["target_id"]) for r in self._rels("APPLIES_TO")}
        part_of = {(r["source_id"], r["target_id"]) for r in self._rels("PART_OF")}
        acme_contracts = {c for c, cust in applies if cust == "CUST-acme"}
        acme_clauses = {cl for cl, contract in part_of if contract in acme_contracts}
        acme_risk = [r for r in may_violate if r["target_id"] in acme_clauses]
        self.ok(len(acme_risk) >= 1,
                f"GQ-2: Acme has >=1 incident MAY_VIOLATE clause ({len(acme_risk)} found)")

        # GQ-3: team owning service in INC-247.
        affected = {(r["source_id"], r["target_id"]) for r in self._rels("AFFECTED")}
        owned = {(r["source_id"], r["target_id"]) for r in self._rels("OWNED_BY")}
        inc247_services = {svc for inc, svc in affected if inc == "INC-247"}
        inc247_teams = {team for svc, team in owned if svc in inc247_services}
        self.ok("TEAM-backend-payments" in inc247_teams,
                f"GQ-3: INC-247 service owned by TEAM-backend-payments ({sorted(inc247_teams)})")

        # GQ-4: root cause of recurring checkout timeout tickets.
        checkout_tickets = [t for t in self.data["support_tickets"]
                            if t["theme"] == "checkout-timeout"]
        caused_by = {(r["source_id"], r["target_id"]) for r in self._rels("CAUSED_BY")}
        rc_counts: dict[str, int] = {}
        for t in checkout_tickets:
            inc = t["related_incident_id"]
            if not inc:
                continue
            for i, rc in caused_by:
                if i == inc:
                    rc_counts[rc] = rc_counts.get(rc, 0) + 1
        top_rc = max(rc_counts, key=rc_counts.get) if rc_counts else None
        self.ok(len(checkout_tickets) >= 5, f"GQ-4: recurring checkout tickets ({len(checkout_tickets)})")
        self.ok(top_rc == "RC-downstream-payment-latency",
                f"GQ-4: dominant checkout root cause is downstream-payment-latency (got {top_rc})")

        # GQ-5: runbook for payment gateway timeout.
        mitigates = {(r["source_id"], r["target_id"]) for r in self._rels("MITIGATES")}
        gateway_runbooks = {rb for rb, err in mitigates if err == "ERR-payment-gateway-timeout"}
        self.ok("RUN-payment-gateway-timeout" in gateway_runbooks,
                f"GQ-5: payment gateway timeout runbook exists ({sorted(gateway_runbooks)})")

    def check_fixtures(self) -> None:
        gq_path = FIXTURES_DIR / "golden_questions.json"
        self.ok(gq_path.exists(), "fixtures: golden_questions.json present")
        if gq_path.exists():
            payload = read_json(gq_path)
            self.ok(len(payload.get("questions", [])) >= 5,
                    "fixtures: >=5 golden questions defined")

    def run(self) -> int:
        if not self.load():
            _report(self)
            return 1
        self.check_counts()
        self.check_provenance()
        self.check_referential_integrity()
        self.check_golden_questions()
        self.check_fixtures()
        return _report(self)


def _report(v: Validator) -> int:
    print("GraphIntel dataset validation")
    print("-" * 60)
    for c in v.checks:
        mark = "FAIL" if c in v.errors else "ok  "
        print(f"  [{mark}] {c}")
    print("-" * 60)
    if v.errors:
        print(f"VALIDATION FAILED: {len(v.errors)} problem(s).")
        return 1
    print(f"VALIDATION PASSED: {len(v.checks)} checks, all golden questions answerable.")
    return 0


if __name__ == "__main__":
    raise SystemExit(Validator().run())
