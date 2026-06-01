# Segment 03 — Embedding Client (Titan v2 on BedrockClient)

**Depends on:** nothing (additive to `BedrockClient`); logically follows 02. **Blocks:** 04, 06.

## Purpose

Give `BedrockClient` the ability to turn text into a 512-dim vector via Amazon Titan, **without touching**
the existing `converse`/`converse_messages` methods (so all Ex3/Ex4 tests stay green). Provide a deterministic
mock so retrieval/ranking tests are meaningful offline.

## The trap (read first)

Titan embeddings use a **different Bedrock API than Nova**. Do NOT copy the `converse` pattern:
- Call **`invoke_model`**, not `converse`.
- Request body: `{"inputText": text, "dimensions": 512, "normalize": true}`.
- Response body is a **streaming object** — `json.loads(resp["body"].read())`.
- Response shape: `{"embedding": [...512 floats...], "inputTextTokenCount": N}`.
- Pin `dimensions:512` + `normalize:true` for reproducibility (normalize → cosine == dot product, stable output).

## Public artifacts (`api/app/ingest/llm.py`, add to `BedrockClient` at `llm.py:33`)

```python
_DEFAULT_EMBED_MODEL_ID = os.getenv("BEDROCK_EMBED_MODEL_ID", "amazon.titan-embed-text-v2:0")
EMBEDDING_DIM = 512

class BedrockClient:
    def __init__(self, model_id=_DEFAULT_MODEL_ID, region=_DEFAULT_REGION,
                 embed_model_id: str = _DEFAULT_EMBED_MODEL_ID) -> None:
        ...
        self.embed_model_id = embed_model_id   # keep self.model_id for converse unchanged

    def embed(self, text: str) -> list[float]:
        vec, _ = self.embed_with_usage(text)
        return vec

    def embed_with_usage(self, text: str) -> tuple[list[float], int]:
        """Return (vector, input_token_count). Raises BedrockError on failure or wrong dim."""
        body = json.dumps({"inputText": text, "dimensions": EMBEDDING_DIM, "normalize": True})
        try:
            resp = self._client.invoke_model(modelId=self.embed_model_id, body=body)
            payload = json.loads(resp["body"].read())
        except Exception as exc:
            raise BedrockError(str(exc)) from exc
        vec = payload["embedding"]
        if len(vec) != EMBEDDING_DIM:
            raise BedrockError(f"expected {EMBEDDING_DIM} dims, got {len(vec)}")
        return vec, payload.get("inputTextTokenCount", 0)

    def embed_batch(self, texts: list[str]) -> tuple[list[list[float]], int]:
        """Titan has no batch endpoint — loop; return (vectors, total_tokens) for one cost summary."""
        vectors, total = [], 0
        for t in texts:
            v, n = self.embed_with_usage(t)
            vectors.append(v); total += n
        return vectors, total
```

- Reuse the existing `BedrockError` (`llm.py:19`) and the `boto3` `bedrock-runtime` client (`llm.py:40`).
- Callers run the sync client off the event loop via `loop.run_in_executor` (the `_call_llm` pattern at
  `llm.py:91-96`) — the service (segment 04) does this, not `embed` itself.

## Deterministic mock (`api/tests/embeddings/conftest.py`)

```python
class MockEmbeddingClient:
    embed_model_id = "mock-titan"
    def embed(self, text): return self.embed_with_usage(text)[0]
    def embed_with_usage(self, text):
        seed = int(hashlib.sha256(text.encode()).hexdigest(), 16) % (2**32)
        rng = random.Random(seed)
        v = [rng.uniform(-1, 1) for _ in range(512)]
        norm = math.sqrt(sum(x*x for x in v)) or 1.0
        return [x / norm for x in v], len(text.split())   # L2-normalized, reproducible per text
    def embed_batch(self, texts):
        vs, tot = [], 0
        for t in texts:
            v, n = self.embed_with_usage(t); vs.append(v); tot += n
        return vs, tot
```

This gives **distinct, reproducible, unit-norm vectors per distinct text** — same text always returns the same
vector (so reproducibility tests pass) and different texts cluster apart (so ranking tests are meaningful).
Patch it into the namespace that imported `BedrockClient` (segment 04/07), per the monkeypatch rule.

## Reused utilities
- `BedrockError`, `boto3` client, `self._client` — `api/app/ingest/llm.py:19,40`.
- `run_in_executor` pattern (used by callers) — `api/app/ingest/llm.py:91-96`.
- `MockBedrockClient` precedent — `api/tests/ingest/test_llm.py`.

## Tests (`api/tests/embeddings/test_embedding_client.py`) — test-first
1. `test_embed_returns_vector` — stub `_client.invoke_model` to return a body with 512 floats → `embed` returns them.
2. `test_embed_wrong_dim_raises` — body with 256 floats → `BedrockError`.
3. `test_embed_with_usage_tokens` — `inputTextTokenCount` surfaced in the tuple.
4. `test_invoke_model_failure_raises` — `_client.invoke_model` throws → `BedrockError`.
5. `test_mock_deterministic` — `MockEmbeddingClient().embed("x")` twice → identical; `embed("x") != embed("y")`; norm ≈ 1.
6. `test_converse_unchanged` — existing `converse` path still works (the additive change didn't break it).

## Demo / verify
- `cd api && .venv/bin/pytest -q tests/embeddings/test_embedding_client.py` green.
- Live (optional, real creds): `BedrockClient().embed("kubernetes platform engineer")` returns 512 floats; the
  same string twice returns the identical vector (reproducibility) — record this for the validation checklist.
