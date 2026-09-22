"""Embedding provider adapter tests stay offline by mocking provider clients."""
from __future__ import annotations

import json
import sys
import types

from app.vector import BedrockEmbeddingProvider, FastEmbedProvider, VoyageEmbeddingProvider


def test_voyage_embedding_provider_posts_expected_payload(monkeypatch):
    captured = {}

    class Resp:
        def raise_for_status(self):
            return None

        def json(self):
            return {
                "data": [
                    {"index": 1, "embedding": [0.0, 1.0]},
                    {"index": 0, "embedding": [1.0, 0.0]},
                ]
            }

    def fake_post(url, headers, json, timeout):
        captured.update({"url": url, "headers": headers, "json": json, "timeout": timeout})
        return Resp()

    monkeypatch.setattr("app.vector.httpx.post", fake_post)
    provider = VoyageEmbeddingProvider("voy-key", "voyage-3-large")

    vectors = provider.embed_batch(["alpha", "beta"])

    assert vectors == [[1.0, 0.0], [0.0, 1.0]]
    assert captured["url"].endswith("/v1/embeddings")
    assert captured["headers"]["Authorization"] == "Bearer voy-key"
    assert captured["json"] == {"model": "voyage-3-large", "input": ["alpha", "beta"]}


def test_bedrock_embedding_provider_invokes_model(monkeypatch):
    class Body:
        def read(self):
            return json.dumps({"embedding": [0.1, 0.2]}).encode()

    class Client:
        def invoke_model(self, **kwargs):
            assert kwargs["modelId"] == "amazon.titan-embed-text-v2:0"
            assert kwargs["contentType"] == "application/json"
            return {"body": Body()}

    provider = BedrockEmbeddingProvider("amazon.titan-embed-text-v2:0", "us-east-1")
    provider._client = Client()

    assert provider.embed("hello") == [0.1, 0.2]


def test_fastembed_provider_uses_configured_model(monkeypatch):
    captured = {}

    class TextEmbedding:
        def __init__(self, model_name):
            captured["model_name"] = model_name

        def embed(self, texts):
            captured["texts"] = texts
            return ([0.5, 0.6] for _ in texts)

    monkeypatch.setitem(sys.modules, "fastembed", types.SimpleNamespace(TextEmbedding=TextEmbedding))

    provider = FastEmbedProvider("BAAI/bge-small-en-v1.5")

    assert provider.embed("hello") == [0.5, 0.6]
    assert captured == {
        "model_name": "BAAI/bge-small-en-v1.5",
        "texts": ["hello"],
    }


def test_bedrock_embedding_provider_retries_throttling(monkeypatch):
    sleeps = []

    class ThrottleError(Exception):
        response = {"Error": {"Code": "ThrottlingException"}}

    class Body:
        def read(self):
            return json.dumps({"embedding": [0.3, 0.4]}).encode()

    class Client:
        calls = 0

        def invoke_model(self, **kwargs):
            self.calls += 1
            if self.calls == 1:
                raise ThrottleError("too many requests")
            return {"body": Body()}

    monkeypatch.setattr("app.vector.time.sleep", lambda delay: sleeps.append(delay))
    provider = BedrockEmbeddingProvider(
        "amazon.titan-embed-text-v2:0",
        "us-east-1",
        max_retries=2,
        min_interval_seconds=0,
    )
    provider._client = Client()

    assert provider.embed("hello") == [0.3, 0.4]
    assert sleeps == [1]
