"""Request-scoped dependencies."""
from __future__ import annotations

from collections.abc import Iterator

from sqlalchemy.orm import Session

from app.db import SessionLocal


def get_db() -> Iterator[Session]:
    """Yield a session and commit on success (rollback on error).

    Write endpoints rely on this commit; read endpoints are unaffected.
    """
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
