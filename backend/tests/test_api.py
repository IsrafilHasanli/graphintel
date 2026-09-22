"""API contract tests (happy + failure paths) via TestClient."""
from __future__ import annotations


def test_health_and_ready(client):
    assert client.get("/health").json()["status"] == "ok"
    ready = client.get("/ready").json()
    assert ready["status"] == "ready"
    assert ready["database"] == "sqlite"
    assert ready["production_safety_errors"] == []


def test_seed_and_stats(seeded_client):
    stats = seeded_client.get("/admin/stats").json()
    assert stats["entities"] > 100
    assert stats["relations"] > 100
    assert stats["entity_types"]["SupportTicket"] == 50


def test_ask_endpoint_returns_grounded_answer(seeded_client):
    resp = seeded_client.post("/ask", json={
        "question": "Which engineering team owns the service involved in INC-247?"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["confidence"] != "insufficient"
    assert body["citations"]
    assert body["reasoning_path"]
    assert any("TEAM-backend-payments" in (c.get("ref_id") or "") for c in body["citations"])


def test_ask_refuses_out_of_domain(seeded_client):
    body = seeded_client.post("/ask", json={"question": "capital of France?"}).json()
    assert body["confidence"] == "insufficient"


def test_ask_empty_question_400(seeded_client):
    assert seeded_client.post("/ask", json={"question": "   "}).status_code == 400


def test_entities_list_and_get(seeded_client):
    ents = seeded_client.get("/entities", params={"type": "Team"}).json()
    assert ents
    one = seeded_client.get(f"/entities/{ents[0]['id']}").json()
    assert one["id"] == ents[0]["id"]
    assert seeded_client.get("/entities/DOES-NOT-EXIST").status_code == 404


def test_entity_edit_and_audit(seeded_client):
    resp = seeded_client.patch("/entities/CUST-acme", json={"aliases": ["Acme", "Acme Corp", "ACME"]})
    assert resp.status_code == 200
    assert "ACME" in resp.json()["aliases"]
    audits = seeded_client.get("/audits", params={"action": "edit_entity"}).json()
    assert audits


def test_relation_add_rejects_ontology_violation(seeded_client):
    # Customer OWNED_BY Team is invalid.
    resp = seeded_client.post("/relations", json={
        "type": "OWNED_BY", "source_id": "CUST-acme", "target_id": "TEAM-backend-payments"})
    assert resp.status_code == 422


def test_relation_delete(seeded_client):
    rels = seeded_client.get("/relations", params={"type": "AFFECTED", "limit": 1}).json()
    assert rels
    rid = rels[0]["id"]
    resp = seeded_client.request("DELETE", f"/relations/{rid}", json={"reason": "test"})
    assert resp.status_code == 200
    # Now excluded from active list.
    active = [r["id"] for r in seeded_client.get("/relations", params={"type": "AFFECTED"}).json()]
    assert rid not in active


def test_merge_entities_endpoint(seeded_client):
    resp = seeded_client.post("/entities/merge", json={
        "source_id": "CUST-globex", "target_id": "CUST-acme"})
    assert resp.status_code == 200
    assert resp.json() == {"merged": "CUST-globex", "target": "CUST-acme"}
    # The tombstoned entity is hidden from the default entity list.
    ids = [e["id"] for e in seeded_client.get("/entities", params={"type": "Customer"}).json()]
    assert "CUST-globex" not in ids


def test_graph_expand_endpoint(seeded_client):
    view = seeded_client.get("/graph/expand", params={"seed": "INC-247", "hops": 2}).json()
    assert view["nodes"] and view["edges"]
    assert any(n["id"] == "INC-247" for n in view["nodes"])


def test_upload_unsupported_type_415(client):
    resp = client.post("/ingest/upload",
                       files={"file": ("x.exe", b"data", "application/octet-stream")})
    assert resp.status_code == 415


def test_ingest_text_and_job_visible(client):
    csv = ("ticket_id,customer_id,subject\nSUP-1,CUST-acme,Hello\n")
    job = client.post("/ingest/text", json={
        "filename": "t.csv", "content": csv, "source_kind": "support_tickets"}).json()
    assert job["id"]
    listed = client.get("/jobs").json()
    assert any(j["id"] == job["id"] for j in listed)


def test_eval_run_and_release_gate(seeded_client):
    run = seeded_client.post("/eval/run").json()
    assert run["summary"]["passed"] == 5
    gate = seeded_client.get("/eval/release-gate").json()
    assert gate["status"] == "PASS"
