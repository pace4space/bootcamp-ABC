"""Shared fixtures for embeddings tests.

MockEmbeddingClient: deterministic, reproducible, unit-norm vectors per text.
- Same text → same vector (reproducibility tests pass)
- Different texts → distinct vectors (ranking tests meaningful)
- L2-normalized → cosine == dot product
"""
from __future__ import annotations

import hashlib
import math
import random


class MockEmbeddingClient:
    embed_model_id = "mock-titan"

    def embed(self, text: str) -> list[float]:
        return self.embed_with_usage(text)[0]

    def embed_with_usage(self, text: str) -> tuple[list[float], int]:
        seed = int(hashlib.sha256(text.encode()).hexdigest(), 16) % (2**32)
        rng = random.Random(seed)
        v = [rng.uniform(-1, 1) for _ in range(512)]
        norm = math.sqrt(sum(x * x for x in v)) or 1.0
        normalized = [x / norm for x in v]
        return normalized, len(text.split())

    def embed_batch(self, texts: list[str]) -> tuple[list[list[float]], int]:
        vectors: list[list[float]] = []
        total = 0
        for t in texts:
            v, n = self.embed_with_usage(t)
            vectors.append(v)
            total += n
        return vectors, total
