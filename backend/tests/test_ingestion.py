"""Ingestion happy-path and failure-path tests."""
from __future__ import annotations

from app import models
from app.domain import JobState
from app.services.ingestion import IngestionService

GOOD_CSV = (
    "ticket_id,customer_id,subject,body,service_id,error_signature,priority,status,created_at,related_incident_id\n"
    "SUP-1,CUST-acme,Checkout fails,Users cannot pay,SVC-payment-api,ERR-checkout-timeout,high,open,2026-09-20,\n"
    "SUP-2,CUST-globex,Timeout at pay,Gateway slow,SVC-payment-api,ERR-payment-gateway-timeout,medium,open,2026-09-19,\n"
)

# Second row is malformed (missing required customer_id + subject).
BAD_CSV = (
    "ticket_id,customer_id,subject,body\n"
    "SUP-10,CUST-acme,Works,fine\n"
    "SUP-11,,,\n"
)


def test_ingest_tickets_happy_path(session):
    svc = IngestionService(session)
    job = svc.ingest(filename="tickets.csv", content=GOOD_CSV, source="upload")
    session.flush()
    assert job.state in (JobState.COMPLETED.value, JobState.PARTIAL.value)
    assert job.stats["records"] == 2
    # Entities + chunks were created.
    assert session.query(models.Chunk).count() == 2
    tickets = session.query(models.Entity).filter_by(type="SupportTicket").count()
    assert tickets == 2
    # Chunks were embedded.
    assert all(c.embedding for c in session.query(models.Chunk))


def test_ingest_records_malformed_rows_without_dropping(session):
    svc = IngestionService(session)
    job = svc.ingest(filename="tickets.csv", content=BAD_CSV, source="upload")
    session.flush()
    # One valid ticket ingested, one row recorded as an error (never silent).
    assert job.stats["records"] == 1
    errors = session.query(models.JobError).filter_by(job_id=job.id).all()
    assert any(e.scope == "row" for e in errors)
    assert job.state == JobState.PARTIAL.value


def test_ingest_empty_content_fails_cleanly(session):
    svc = IngestionService(session)
    job = svc.ingest(filename="empty.csv", content="ticket_id,customer_id,subject\n", source="upload")
    session.flush()
    # Header only -> no records, no chunks -> failed, not a crash.
    assert job.state == JobState.FAILED.value


def test_ingest_invalid_json_fails_with_error(session):
    svc = IngestionService(session)
    job = svc.ingest(filename="incidents.json", content="{not valid json", source="upload",
                     source_kind="incidents")
    session.flush()
    assert job.state == JobState.FAILED.value
    assert session.query(models.JobError).filter_by(job_id=job.id, scope="file").count() == 1
