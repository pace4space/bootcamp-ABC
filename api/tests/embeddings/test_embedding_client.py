"""Segment 03 tests — BedrockClient.embed + MockEmbeddingClient."""
from __future__ import annotations

import io
import json
import math
from unittest.mock import MagicMock, patch

import pytest

from app.ingest.llm import BedrockClient, BedrockError, EMBEDDING_DIM
from tests.embeddings.conftest import MockEmbeddingClient


def _make_client() -> BedrockClient:
    """BedrockClient wired to a mock boto3 client; no real AWS calls."""
    c = BedrockClient.__new__(BedrockClient)
    c.model_id = "amazon.nova-lite-v1:0"
    c.embed_model_id = "amazon.titan-embed-text-v2:0"
    c._client = MagicMock()
    return c


def _invoke_ok(floats: list[float]) -> dict:
    payload = json.dumps({"embedding": floats, "inputTextTokenCount": 7}).encode()
    return {"body": io.BytesIO(payload)}


def test_embed_returns_vector():
    c = _make_client()
    vec = [0.1] * EMBEDDING_DIM
    c._client.invoke_model.return_value = _invoke_ok(vec)
    result = c.embed("test text")
    assert len(result) == EMBEDDING_DIM
    assert result == vec


def test_embed_wrong_dim_raises():
    c = _make_client()
    c._client.invoke_model.return_value = _invoke_ok([0.1] * 256)
    with pytest.raises(BedrockError, match="256"):
        c.embed("test text")


def test_embed_with_usage_tokens():
    c = _make_client()
    vec = [0.2] * EMBEDDING_DIM
    c._client.invoke_model.return_value = _invoke_ok(vec)
    result_vec, tokens = c.embed_with_usage("hello world")
    assert tokens == 7
    assert result_vec == vec


def test_invoke_model_failure_raises():
    c = _make_client()
    c._client.invoke_model.side_effect = RuntimeError("timeout")
    with pytest.raises(BedrockError, match="timeout"):
        c.embed("anything")


def test_mock_deterministic():
    m = MockEmbeddingClient()
    v1 = m.embed("hello")
    v2 = m.embed("hello")
    vy = m.embed("world")
    assert v1 == v2                              # stable
    assert v1 != vy                              # distinct per text
    norm = math.sqrt(sum(x * x for x in v1))
    assert abs(norm - 1.0) < 1e-9               # L2-normalized


def test_converse_unchanged():
    """Additive embed change must not break the converse path."""
    c = _make_client()
    response = {
        "output": {"message": {"content": [{"text": "ok"}]}},
        "usage": {"inputTokens": 5, "outputTokens": 2},
    }
    c._client.converse.return_value = response
    reply, in_tok, out_tok = c.converse("sys", "user msg")
    assert reply == "ok"
    assert in_tok == 5
    assert out_tok == 2
