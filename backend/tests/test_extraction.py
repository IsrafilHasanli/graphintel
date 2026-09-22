"""Structured extraction and rule-based mention linking."""
from __future__ import annotations

from app.services.extraction import MentionIndex, extract_llm_free_text, extract_structured


class FakeLLM:
    name = "fake"
    available = True

    def complete(self, system: str, prompt: str, max_tokens: int = 700) -> str:
        assert "Allowed entity types" in prompt
        return """
        {
          "entities": [
            {
              "id": "SVC-checkout",
              "type": "Service",
              "canonical_name": "Checkout Service",
              "aliases": ["checkout"],
              "attributes": {"tier": "critical"},
              "confidence": 0.82
            },
            {
              "id": "ERR-checkout-timeout",
              "type": "ErrorSignature",
              "canonical_name": "Checkout timeout",
              "aliases": [],
              "attributes": {},
              "confidence": 0.78
            }
          ],
          "relations": [
            {
              "type": "EXHIBITS",
              "source_id": "SUP-123",
              "target_id": "ERR-checkout-timeout",
              "confidence": 0.66
            }
          ]
        }
        """


def test_extract_incidents_produces_entities_and_relations():
    records = [{
        "id": "INC-9", "title": "Payment outage", "severity": "SEV1",
        "service_id": "SVC-payment-api", "error_signature": "ERR-payment-gateway-timeout",
        "impacted_customers": ["CUST-acme"], "started_at": "2026-09-20T10:00:00Z",
        "updates": [{"id": "INC-9-u1", "message": "investigating", "status": "investigating"}],
    }]
    result = extract_structured("incidents", records, "DOC-1")
    types = {e.type for e in result.entities}
    assert "Incident" in types
    rels = {(r.type) for r in result.relations}
    assert "AFFECTED" in rels
    assert not result.errors


def test_extract_unknown_kind_reports_error():
    result = extract_structured("nonsense", [{"id": "X"}], "DOC-1")
    assert result.errors
    assert not result.entities


def test_mention_index_matches_ids_names_and_patterns():
    idx = MentionIndex()
    idx.add("SVC-payment-api", ["Payment API"], ["payment gateway timeout"])
    idx.add("INC-247", ["Payment API elevated timeouts"])
    found = idx.find("We saw INC-247 with a payment gateway timeout on the Payment API")
    assert "INC-247" in found
    assert "SVC-payment-api" in found


def test_mention_index_ignores_unknown_ids():
    idx = MentionIndex()
    idx.add("SVC-x", ["Payment API"])
    assert idx.find("Unrelated INC-999 text") == []


def test_llm_free_text_extraction_parses_json_and_marks_provenance():
    result = extract_llm_free_text(
        "document",
        [("DOC-1::c0", "Checkout service saw timeout errors.")],
        "DOC-1",
        provider=FakeLLM(),
    )
    assert not result.errors
    assert {e.id for e in result.entities} == {"SVC-checkout", "ERR-checkout-timeout"}
    assert all(e.method == "llm" for e in result.entities)
    assert result.entities[0].attributes["source_chunk_id"] == "DOC-1::c0"
    assert result.relations[0].method == "llm"


def test_llm_free_text_extraction_reports_bad_json():
    class BadLLM(FakeLLM):
        def complete(self, system: str, prompt: str, max_tokens: int = 700) -> str:
            return "not json"

    result = extract_llm_free_text("document", [("c1", "text")], "DOC-1", provider=BadLLM())
    assert result.errors
