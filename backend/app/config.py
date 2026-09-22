"""Centralized settings for GraphIntel.

All configuration is environment-driven with safe local defaults so the platform
can boot fully offline (SQLite + SQL-backed graph + deterministic embeddings)
with zero external services, and scale up to Postgres + Neptune + real LLMs by
changing environment variables only.
"""
from __future__ import annotations

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    env: str = Field(default="local", alias="GRAPHINTEL_ENV")
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")
    cors_allow_origins: str = Field(default="*", alias="CORS_ALLOW_ORIGINS")

    # --- PostgreSQL ---
    postgres_host: str = Field(default="localhost", alias="POSTGRES_HOST")
    postgres_port: int = Field(default=5432, alias="POSTGRES_PORT")
    postgres_db: str = Field(default="graphintel", alias="POSTGRES_DB")
    postgres_user: str = Field(default="graphintel", alias="POSTGRES_USER")
    postgres_password: str = Field(default="graphintel", alias="POSTGRES_PASSWORD")
    database_url_override: str | None = Field(default=None, alias="DATABASE_URL")

    # --- Graph backends ---
    # Local/test defaults use the SQL-backed graph mirror. AWS staging/prod
    # should set GRAPH_BACKEND=neptune and provide the Neptune endpoint.
    graph_backend: str = Field(default="sql", alias="GRAPH_BACKEND")
    neptune_endpoint: str = Field(default="", alias="NEPTUNE_ENDPOINT")
    neptune_port: int = Field(default=8182, alias="NEPTUNE_PORT")
    neptune_use_iam_auth: bool = Field(default=True, alias="NEPTUNE_USE_IAM_AUTH")

    # --- Vector / embeddings ---
    embedding_provider: str = Field(default="deterministic", alias="EMBEDDING_PROVIDER")
    embedding_dim: int = Field(default=256, alias="EMBEDDING_DIM")
    voyage_api_key: str = Field(default="", alias="VOYAGE_API_KEY")
    voyage_embedding_model: str = Field(default="voyage-3-large", alias="VOYAGE_EMBEDDING_MODEL")
    fastembed_embedding_model: str = Field(
        default="BAAI/bge-small-en-v1.5",
        alias="FASTEMBED_EMBEDDING_MODEL",
    )
    bedrock_embedding_model: str = Field(
        default="amazon.titan-embed-text-v2:0",
        alias="BEDROCK_EMBEDDING_MODEL",
    )
    aws_region: str = Field(default="us-east-1", alias="AWS_REGION")

    # --- LLM ---
    llm_provider: str = Field(default="deterministic", alias="LLM_PROVIDER")
    extraction_provider: str = Field(default="deterministic", alias="EXTRACTION_PROVIDER")
    anthropic_api_key: str = Field(default="", alias="ANTHROPIC_API_KEY")
    llm_model: str = Field(default="claude-opus-4-8", alias="LLM_MODEL")

    # --- Retrieval tuning ---
    retrieval_top_k: int = Field(default=8, alias="RETRIEVAL_TOP_K")
    graph_max_hops: int = Field(default=3, alias="GRAPH_MAX_HOPS")
    min_answer_confidence: float = Field(default=0.35, alias="MIN_ANSWER_CONFIDENCE")

    @property
    def database_url(self) -> str:
        if self.database_url_override:
            return self.database_url_override
        return (
            f"postgresql+psycopg://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    @property
    def use_neptune(self) -> bool:
        return self.graph_backend == "neptune" and bool(self.neptune_endpoint.strip())

    @property
    def is_sqlite(self) -> bool:
        return self.database_url.startswith("sqlite")

    @property
    def is_managed_env(self) -> bool:
        return self.env.lower() in {"staging", "prod", "production"}

    @property
    def cors_origins(self) -> list[str]:
        return [origin.strip() for origin in self.cors_allow_origins.split(",") if origin.strip()]

    def production_safety_errors(self) -> list[str]:
        if not self.is_managed_env:
            return []
        errors: list[str] = []
        placeholder_markers = {"change_me", "your_", "example", "placeholder"}

        def is_placeholder(value: str) -> bool:
            normalized = value.strip().lower()
            return not normalized or any(marker in normalized for marker in placeholder_markers)

        if self.is_sqlite:
            errors.append("DATABASE_URL must point to RDS PostgreSQL, not SQLite")
        if not self.database_url_override and is_placeholder(self.postgres_password):
            errors.append("POSTGRES_PASSWORD must be set to a non-placeholder value")
        if not self.use_neptune:
            errors.append("GRAPH_BACKEND must be neptune with NEPTUNE_ENDPOINT set")
        if self.llm_provider == "deterministic":
            errors.append("LLM_PROVIDER must use a real provider")
        if self.extraction_provider != "llm":
            errors.append("EXTRACTION_PROVIDER must be llm")
        if self.embedding_provider == "deterministic":
            errors.append("EMBEDDING_PROVIDER must use a real provider")
        if "*" in self.cors_origins:
            errors.append("CORS_ALLOW_ORIGINS must list explicit origins in managed environments")
        if self.llm_provider == "anthropic" and is_placeholder(self.anthropic_api_key):
            errors.append("ANTHROPIC_API_KEY must be set to a non-placeholder value")
        if self.embedding_provider == "voyage" and is_placeholder(self.voyage_api_key):
            errors.append("VOYAGE_API_KEY must be set to a non-placeholder value")
        return errors


@lru_cache
def get_settings() -> Settings:
    return Settings()
