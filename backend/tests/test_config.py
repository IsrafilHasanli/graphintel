"""Configuration safety checks."""
from __future__ import annotations

from app.config import Settings


def test_staging_rejects_mock_backends():
    settings = Settings(
        GRAPHINTEL_ENV="staging",
        DATABASE_URL="sqlite:///bad.sqlite3",
        GRAPH_BACKEND="sql",
        LLM_PROVIDER="deterministic",
        EXTRACTION_PROVIDER="deterministic",
        EMBEDDING_PROVIDER="deterministic",
    )

    errors = settings.production_safety_errors()

    assert any("RDS PostgreSQL" in e for e in errors)
    assert any("GRAPH_BACKEND" in e for e in errors)
    assert any("LLM_PROVIDER" in e for e in errors)
    assert any("EXTRACTION_PROVIDER" in e for e in errors)
    assert any("EMBEDDING_PROVIDER" in e for e in errors)


def test_staging_accepts_real_neptune_bedrock_config():
    settings = Settings(
        GRAPHINTEL_ENV="staging",
        DATABASE_URL="postgresql+psycopg://u:p@db.example.com:5432/graphintel",
        GRAPH_BACKEND="neptune",
        NEPTUNE_ENDPOINT="graph.cluster-example.us-east-1.neptune.amazonaws.com",
        LLM_PROVIDER="anthropic",
        EXTRACTION_PROVIDER="llm",
        ANTHROPIC_API_KEY="test-key",
        EMBEDDING_PROVIDER="bedrock",
        CORS_ALLOW_ORIGINS="https://graphintel.example.com",
    )

    assert settings.production_safety_errors() == []


def test_staging_rejects_placeholder_provider_keys():
    settings = Settings(
        GRAPHINTEL_ENV="staging",
        DATABASE_URL="postgresql+psycopg://u:p@db.example.com:5432/graphintel",
        GRAPH_BACKEND="neptune",
        NEPTUNE_ENDPOINT="graph.cluster-example.us-east-1.neptune.amazonaws.com",
        LLM_PROVIDER="anthropic",
        EXTRACTION_PROVIDER="llm",
        ANTHROPIC_API_KEY="your_anthropic_api_key_here",
        EMBEDDING_PROVIDER="voyage",
        VOYAGE_API_KEY="your_voyage_api_key_here",
        CORS_ALLOW_ORIGINS="https://graphintel.example.com",
    )

    errors = settings.production_safety_errors()

    assert any("ANTHROPIC_API_KEY" in e for e in errors)
    assert any("VOYAGE_API_KEY" in e for e in errors)
