"""Shared pytest fixtures.

Every test runs against an isolated temp SQLite database (offline, no external
services). The DATABASE_URL is set before any app module imports so the engine
binds to the throwaway file. Schema is recreated per test for isolation; the
`seeded_*` fixtures ingest the full demo corpus through the real pipeline.
"""
from __future__ import annotations

import os
import tempfile
from pathlib import Path

import pytest

# --- bind the engine to a throwaway DB BEFORE importing app modules ---------
_TMP = Path(tempfile.mkdtemp(prefix="graphintel_tests_"))
os.environ["DATABASE_URL"] = f"sqlite:///{(_TMP / 'test.sqlite3').as_posix()}"
os.environ.setdefault("LLM_PROVIDER", "deterministic")
os.environ.setdefault("EMBEDDING_PROVIDER", "deterministic")

from app.db import Base, SessionLocal, engine  # noqa: E402
from app.services.seed import seed_all  # noqa: E402


def _reset_schema() -> None:
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)


@pytest.fixture()
def session():
    """Fresh empty schema + a session, rolled back/closed after the test."""
    _reset_schema()
    s = SessionLocal()
    try:
        yield s
    finally:
        s.rollback()
        s.close()


@pytest.fixture()
def seeded_session():
    """Fresh schema seeded with the full demo corpus via the real pipeline."""
    _reset_schema()
    s = SessionLocal()
    seed_all(s, reset=False)
    s.commit()
    try:
        yield s
    finally:
        s.rollback()
        s.close()


@pytest.fixture()
def client():
    """TestClient with a fresh (empty) schema. Use POST /admin/seed to populate."""
    from app.main import app
    from fastapi.testclient import TestClient

    _reset_schema()
    with TestClient(app) as c:
        yield c


@pytest.fixture()
def seeded_client(client):
    """TestClient with the demo corpus already seeded."""
    resp = client.post("/admin/seed")
    assert resp.status_code == 200
    return client
