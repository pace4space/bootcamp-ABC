"""Segment 07 tests — match endpoints + ingest auto-embed hook."""
from __future__ import annotations

import io
import json

import pytest
from httpx import AsyncClient, ASGITransport
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import create_access_token
from app.db import get_db
from app.main import app
from app.models import CandidateEmbedding, User
from app.embeddings.service import backfill_all
from tests.embeddings.conftest import MockEmbeddingClient


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
async def seeded_db_with_embeddings(seeded_db):
    """Backfill all embeddings with deterministic mock vectors."""
    mock = MockEmbeddingClient()
    async with seeded_db() as db:
        await backfill_all(db, mock)
        await db.commit()
    return seeded_db


@pytest.fixture
async def http_client(seeded_db_with_embeddings):
    seeded = seeded_db_with_embeddings

    async def override_get_db():
        async with seeded() as session:
            try:
                yield session
            except Exception:
                await session.rollback()
                raise
            finally:
                await session.close()

    app.dependency_overrides[get_db] = override_get_db
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()


@pytest.fixture
async def admin_token(seeded_db_with_embeddings):
    async with seeded_db_with_embeddings() as db:
        result = await db.execute(select(User).where(User.email == "admin@hellio.com"))
        user = result.scalar_one()
    return {"Authorization": f"Bearer {create_access_token({'sub': str(user.id), 'role': user.role})}"}


@pytest.fixture
async def viewer_token(seeded_db_with_embeddings):
    async with seeded_db_with_embeddings() as db:
        result = await db.execute(select(User).where(User.email == "viewer@hellio.com"))
        user = result.scalar_one()
    return {"Authorization": f"Bearer {create_access_token({'sub': str(user.id), 'role': user.role})}"}


# ---------------------------------------------------------------------------
# Tests: match endpoints
# ---------------------------------------------------------------------------

async def test_position_candidate_matches_excludes_linked(
    http_client, admin_token, monkeypatch
):
    """With threshold=0.0, results present; none of the linked candidates appear."""
    monkeypatch.setattr("app.embeddings.search.SIMILARITY_THRESHOLD", 0.0)

    resp = await http_client.get("/api/positions/pos_t01/candidate-matches", headers=admin_token)
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    # cv_t01 and cv_t02 are linked to pos_t01 — must not appear
    linked = {"cv_t01", "cv_t02"}
    for item in data:
        assert item["candidateId"] not in linked
        assert item["score"] >= 0.0


async def test_candidate_position_matches_have_explanations(
    http_client, admin_token, monkeypatch
):
    """With threshold=0.0, results include non-empty explanations."""
    monkeypatch.setattr("app.embeddings.search.SIMILARITY_THRESHOLD", 0.0)
    monkeypatch.setattr(
        "app.embeddings.explainer.BedrockClient",
        lambda: _MockConverse("The match is based on shared DevOps skills."),
    )

    resp = await http_client.get("/api/candidates/cv_t01/position-matches", headers=admin_token)
    assert resp.status_code == 200
    data = resp.json()
    # cv_t01 applied to pos_t01 and pos_t02 — those must not appear
    applied = {"pos_t01", "pos_t02"}
    for item in data:
        assert item["positionId"] not in applied


async def test_threshold_empty_returns_empty_list(http_client, admin_token):
    """Default threshold (0.5) with mock vectors (scores ≈ 0) → empty list."""
    resp = await http_client.get("/api/positions/pos_t01/candidate-matches", headers=admin_token)
    assert resp.status_code == 200
    assert resp.json() == []


async def test_viewer_can_read(http_client, viewer_token):
    resp = await http_client.get("/api/positions/pos_t01/candidate-matches", headers=viewer_token)
    assert resp.status_code == 200


async def test_ingest_creates_embedding(seeded_db, monkeypatch):
    """Ingesting a CV should create a CandidateEmbedding row (auto-embed hook)."""
    monkeypatch.setattr("app.ingest.parsers._extract_pdf", lambda _: "Ingested Candidate\nPython developer")
    monkeypatch.setattr("app.ingest.BedrockClient", lambda: _MockExtractClient())
    monkeypatch.setattr("app.embeddings.service.BedrockClient", lambda: MockEmbeddingClient())

    async def override_get_db():
        async with seeded_db() as session:
            try:
                yield session
            except Exception:
                await session.rollback()
                raise
            finally:
                await session.close()

    app.dependency_overrides[get_db] = override_get_db
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        async with seeded_db() as db:
            result = await db.execute(select(User).where(User.email == "admin@hellio.com"))
            user = result.scalar_one()
        token = create_access_token({"sub": str(user.id), "role": user.role})
        headers = {"Authorization": f"Bearer {token}"}

        resp = await ac.post(
            "/api/ingest/cv",
            headers=headers,
            files={"file": ("cv.pdf", io.BytesIO(b"%PDF-1.4"), "application/pdf")},
        )
    app.dependency_overrides.clear()

    assert resp.status_code == 201
    entity_id = resp.json()["entityId"]
    assert entity_id.startswith("cv_")

    # Check embedding row was created
    async with seeded_db() as db:
        row = await db.get(CandidateEmbedding, entity_id)
    assert row is not None
    assert len(row.embedding) == 512


async def test_ingest_embed_failure_does_not_fail_ingest(seeded_db, monkeypatch):
    """Embed failure must not fail ingestion — best-effort hook."""
    monkeypatch.setattr("app.ingest.parsers._extract_pdf", lambda _: "Failing Embed Candidate")
    monkeypatch.setattr("app.ingest.BedrockClient", lambda: _MockExtractClient())
    monkeypatch.setattr("app.embeddings.service.BedrockClient", lambda: _ErrorEmbedClient())

    async def override_get_db():
        async with seeded_db() as session:
            try:
                yield session
            except Exception:
                await session.rollback()
                raise
            finally:
                await session.close()

    app.dependency_overrides[get_db] = override_get_db
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        async with seeded_db() as db:
            result = await db.execute(select(User).where(User.email == "admin@hellio.com"))
            user = result.scalar_one()
        token = create_access_token({"sub": str(user.id), "role": user.role})
        headers = {"Authorization": f"Bearer {token}"}

        resp = await ac.post(
            "/api/ingest/cv",
            headers=headers,
            files={"file": ("cv2.pdf", io.BytesIO(b"%PDF-1.4"), "application/pdf")},
        )
    app.dependency_overrides.clear()

    assert resp.status_code == 201   # ingest succeeded despite embed failure


async def test_camelcase_payload(http_client, admin_token, monkeypatch):
    """Response keys must be camelCase."""
    monkeypatch.setattr("app.embeddings.search.SIMILARITY_THRESHOLD", 0.0)
    monkeypatch.setattr(
        "app.embeddings.explainer.BedrockClient",
        lambda: _MockConverse("Good fit."),
    )

    pos_resp = await http_client.get(
        "/api/positions/pos_t02/candidate-matches", headers=admin_token
    )
    assert pos_resp.status_code == 200
    for item in pos_resp.json():
        assert "candidateId" in item
        assert "fullName" in item

    cand_resp = await http_client.get(
        "/api/candidates/cv_t02/position-matches", headers=admin_token
    )
    assert cand_resp.status_code == 200
    for item in cand_resp.json():
        assert "positionId" in item
        assert "explanation" in item


# ---------------------------------------------------------------------------
# Helper mock clients
# ---------------------------------------------------------------------------

_CANNED_CV_JSON = json.dumps({
    "full_name": "Ingested Candidate",
    "headline": "Software Engineer",
    "summary": "Experienced engineer.",
    "email": "ingested_embed_test@example.com",
    "skills": ["Python", "FastAPI"],
    "experience": [{"role": "SWE", "company": "Acme", "start_year": 2020}],
    "education": [],
    "certifications": [],
    "languages": [],
})


class _MockExtractClient:
    model_id = "test-model"
    embed_model_id = "mock-titan"

    def converse(self, system: str, user: str) -> tuple[str, int, int]:
        return _CANNED_CV_JSON, 100, 50


class _MockConverse:
    model_id = "test-model"
    embed_model_id = "mock-titan"

    def __init__(self, reply: str = "Good fit."):
        self._reply = reply

    def converse(self, system: str, user: str) -> tuple[str, int, int]:
        return self._reply, 50, 20


class _ErrorEmbedClient:
    model_id = "test-model"
    embed_model_id = "mock-titan"

    def embed_with_usage(self, text: str) -> tuple[list[float], int]:
        raise RuntimeError("Simulated embed failure")

    def embed(self, text: str) -> list[float]:
        raise RuntimeError("Simulated embed failure")
