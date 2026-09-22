"""Embeddings + vector search.

Default embedding provider is 'deterministic': a hashed bag-of-words projection
into a fixed-dim unit vector. It is reproducible, offline, and dependency-free,
and captures lexical/semantic overlap well enough for the demo corpus.

Production providers are available behind the same interface:
  * voyage - Voyage embeddings via VOYAGE_API_KEY.
  * bedrock - Amazon Bedrock embeddings using the configured AWS credentials.
  * fastembed - local ONNX semantic embeddings, baked into the container image.

AWS production/staging should use a real provider, not deterministic hashes.

The VectorStore computes cosine similarity in Python (adequate for the demo
scale). In production the same interface is backed by a pgvector column; the
Postgres image ships with the extension enabled (see docker-compose.yml).
"""
from __future__ import annotations

import hashlib
import json
import math
import re
import time
from collections import Counter
from dataclasses import dataclass

import httpx

from app.config import get_settings
from app.logging_config import get_logger

log = get_logger("vector")

_TOKEN_RE = re.compile(r"[a-z0-9][a-z0-9\-_.]+")
_STOPWORDS = {
    "the", "a", "an", "and", "or", "of", "to", "in", "for", "on", "at", "is",
    "are", "was", "were", "be", "with", "by", "that", "this", "it", "as", "we",
    "our", "from", "has", "have", "will", "shall",
}


def tokenize(text: str) -> list[str]:
    return [t for t in _TOKEN_RE.findall(text.lower()) if t not in _STOPWORDS]


class EmbeddingProvider:
    def __init__(self, dim: int | None = None) -> None:
        self.dim = dim or get_settings().embedding_dim
        self.model = f"deterministic-hash-{self.dim}"

    def embed(self, text: str) -> list[float]:
        vec = [0.0] * self.dim
        counts = Counter(tokenize(text))
        if not counts:
            return vec
        for token, tf in counts.items():
            # Two hashed features per token for a denser, more stable projection.
            for salt in ("a", "b"):
                h = hashlib.sha1(f"{salt}:{token}".encode()).digest()
                idx = int.from_bytes(h[:4], "big") % self.dim
                sign = 1.0 if h[4] & 1 else -1.0
                vec[idx] += sign * (1.0 + math.log(tf))
        norm = math.sqrt(sum(v * v for v in vec))
        if norm > 0:
            vec = [v / norm for v in vec]
        return vec

    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        return [self.embed(t) for t in texts]


class VoyageEmbeddingProvider(EmbeddingProvider):
    def __init__(self, api_key: str, model: str, dim: int | None = None) -> None:
        super().__init__(dim)
        self.api_key = api_key
        self.model = model

    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        if not self.api_key:
            raise RuntimeError("VOYAGE_API_KEY is required for EMBEDDING_PROVIDER=voyage")
        resp = httpx.post(
            "https://api.voyageai.com/v1/embeddings",
            headers={"Authorization": f"Bearer {self.api_key}"},
            json={"model": self.model, "input": texts},
            timeout=30.0,
        )
        resp.raise_for_status()
        data = resp.json()["data"]
        return [item["embedding"] for item in sorted(data, key=lambda item: item["index"])]

    def embed(self, text: str) -> list[float]:
        return self.embed_batch([text])[0]


class FastEmbedProvider(EmbeddingProvider):
    def __init__(self, model: str) -> None:
        super().__init__(dim=None)
        self.model = model
        self._embedder = None

    @property
    def embedder(self):
        if self._embedder is None:
            try:
                from fastembed import TextEmbedding  # type: ignore
            except Exception as exc:  # pragma: no cover - env dependent
                raise RuntimeError("fastembed is required for EMBEDDING_PROVIDER=fastembed") from exc
            self._embedder = TextEmbedding(model_name=self.model)
        return self._embedder

    def embed_batch(self, texts: list[str]) -> list[list[float]]:  # pragma: no cover - model dependent
        return [list(map(float, vector)) for vector in self.embedder.embed(texts)]

    def embed(self, text: str) -> list[float]:  # pragma: no cover - model dependent
        return self.embed_batch([text])[0]


class BedrockEmbeddingProvider(EmbeddingProvider):
    def __init__(self, model: str, region: str, dim: int | None = None,
                 max_retries: int = 8, min_interval_seconds: float = 0.5) -> None:
        super().__init__(dim)
        self.model = model
        self.region = region
        self._client = None
        self.max_retries = max_retries
        self.min_interval_seconds = min_interval_seconds
        self._last_call_at = 0.0

    @property
    def client(self):
        if self._client is None:
            try:
                import boto3  # type: ignore
            except Exception as exc:  # pragma: no cover - env dependent
                raise RuntimeError("boto3 is required for EMBEDDING_PROVIDER=bedrock") from exc
            self._client = boto3.client("bedrock-runtime", region_name=self.region)
        return self._client

    def _throttle_if_needed(self) -> None:
        if self.min_interval_seconds <= 0:
            return
        elapsed = time.monotonic() - self._last_call_at
        if elapsed < self.min_interval_seconds:
            time.sleep(self.min_interval_seconds - elapsed)

    @staticmethod
    def _is_retryable(exc: Exception) -> bool:
        code = getattr(exc, "response", {}).get("Error", {}).get("Code", "")
        return code in {"ThrottlingException", "TooManyRequestsException", "ServiceQuotaExceededException"}

    def embed(self, text: str) -> list[float]:  # pragma: no cover - AWS dependent
        body = json.dumps({"inputText": text})
        for attempt in range(self.max_retries + 1):
            try:
                self._throttle_if_needed()
                resp = self.client.invoke_model(
                    modelId=self.model,
                    body=body,
                    accept="application/json",
                    contentType="application/json",
                )
                self._last_call_at = time.monotonic()
                break
            except Exception as exc:
                if attempt >= self.max_retries or not self._is_retryable(exc):
                    raise
                delay = min(2 ** attempt, 16)
                log.warning("bedrock_embedding_retry", attempt=attempt + 1, delay_seconds=delay)
                time.sleep(delay)
        payload = json.loads(resp["body"].read())
        return payload.get("embedding") or payload.get("embeddings", [{}])[0].get("embedding", [])


def get_embedding_provider() -> EmbeddingProvider:
    settings = get_settings()
    provider = settings.embedding_provider.lower()
    if provider == "voyage":
        return VoyageEmbeddingProvider(settings.voyage_api_key, settings.voyage_embedding_model)
    if provider == "fastembed":
        return FastEmbedProvider(settings.fastembed_embedding_model)
    if provider == "bedrock":
        return BedrockEmbeddingProvider(settings.bedrock_embedding_model, settings.aws_region)
    if settings.env in {"staging", "prod", "production"} and provider == "deterministic":
        log.warning("deterministic_embeddings_in_nonlocal_env", env=settings.env)
    return EmbeddingProvider()


def cosine(a: list[float], b: list[float]) -> float:
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b, strict=True))
    # vectors are pre-normalized, but guard anyway
    na = math.sqrt(sum(x * x for x in a)) or 1.0
    nb = math.sqrt(sum(y * y for y in b)) or 1.0
    return dot / (na * nb)


@dataclass
class VectorHit:
    chunk_id: str
    score: float


class VectorStore:
    """In-process cosine search over stored chunk embeddings.

    `items` maps chunk_id -> embedding. For the demo this is loaded from the
    Chunk table; the interface is intentionally minimal so a pgvector-backed
    implementation can replace it without touching retrieval code.
    """

    def __init__(self, embedder: EmbeddingProvider | None = None) -> None:
        self.embedder = embedder or get_embedding_provider()
        self._items: dict[str, list[float]] = {}

    def add(self, chunk_id: str, embedding: list[float]) -> None:
        self._items[chunk_id] = embedding

    def add_text(self, chunk_id: str, text: str) -> list[float]:
        emb = self.embedder.embed(text)
        self._items[chunk_id] = emb
        return emb

    def __len__(self) -> int:
        return len(self._items)

    def search(self, query: str, top_k: int = 8, allowed: set[str] | None = None) -> list[VectorHit]:
        q = self.embedder.embed(query)
        hits: list[VectorHit] = []
        for cid, emb in self._items.items():
            if allowed is not None and cid not in allowed:
                continue
            hits.append(VectorHit(cid, cosine(q, emb)))
        hits.sort(key=lambda h: h.score, reverse=True)
        return hits[:top_k]

    def search_vector(self, vec: list[float], top_k: int = 8,
                      allowed: set[str] | None = None) -> list[VectorHit]:
        hits = [
            VectorHit(cid, cosine(vec, emb))
            for cid, emb in self._items.items()
            if allowed is None or cid in allowed
        ]
        hits.sort(key=lambda h: h.score, reverse=True)
        return hits[:top_k]
