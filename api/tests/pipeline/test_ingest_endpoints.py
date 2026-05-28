"""Integration tests for POST /api/ingest/cv and POST /api/ingest/position.

Bedrock is mocked via monkeypatch so no AWS credentials are needed.
The PDF parser is also patched to avoid real file parsing in these tests.
All other pipeline stages (heuristics, validator, persister, logger) run real code.
"""
from __future__ import annotations

import io
import json

import pytest
from httpx import AsyncClient, ASGITransport

from app.db import get_db
from app.main import app

# ---------------------------------------------------------------------------
# Canned LLM response fixtures
# ---------------------------------------------------------------------------

CANNED_CV_JSON = json.dumps({
    "full_name": "Ingested Candidate",
    "headline": "Software Engineer",
    "summary": "Experienced engineer.",
    "email": "ingested@example.com",
    "skills": ["Python", "FastAPI"],
    "experience": [{"role": "SWE", "company": "Acme", "start_year": 2020}],
    "education": [],
    "certifications": [],
    "languages": [],
})

CANNED_POSITION_JSON = json.dumps({
    "title": "Ingested Position",
    "description": "Build great software.",
    "requirements": [{"type": "must_have", "text": "Python"}],
})


class _MockBedrockClient:
    model_id = "test-model"

    def __init__(self, reply: str = CANNED_CV_JSON):
        self.reply = reply

    def converse(self, system: str, user: str) -> tuple[str, int, int]:
        return self.reply, 100, 50


class _ErrorMockClient:
    model_id = "test-model"

    def converse(self, system: str, user: str) -> tuple[str, int, int]:
        raise Exception("Bedrock service unavailable")


# ---------------------------------------------------------------------------
# Shared HTTP client fixture wired to seeded_db
# ---------------------------------------------------------------------------

@pytest.fixture
async def http_client(seeded_db):
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
        yield ac
    app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# Auth header helpers
# ---------------------------------------------------------------------------

@pytest.fixture
async def admin_token(seeded_db):
    from sqlalchemy import select
    from app.auth import create_access_token
    from app.models import User
    async with seeded_db() as db:
        result = await db.execute(select(User).where(User.email == "admin@hellio.com"))
        user = result.scalar_one()
    return {"Authorization": f"Bearer {create_access_token({'sub': str(user.id), 'role': user.role})}"}


@pytest.fixture
async def viewer_token(seeded_db):
    from sqlalchemy import select
    from app.auth import create_access_token
    from app.models import User
    async with seeded_db() as db:
        result = await db.execute(select(User).where(User.email == "viewer@hellio.com"))
        user = result.scalar_one()
    return {"Authorization": f"Bearer {create_access_token({'sub': str(user.id), 'role': user.role})}"}


def _pdf_upload(filename: str = "cv.pdf") -> dict:
    """Multipart file payload — b'%PDF-1.4' is sufficient with parser monkeypatched."""
    return {"file": (filename, io.BytesIO(b"%PDF-1.4"), "application/pdf")}


# ---------------------------------------------------------------------------
# POST /api/ingest/cv — success path
# ---------------------------------------------------------------------------

async def test_ingest_cv_returns_201_with_cv_entity_id(
    http_client, admin_token, monkeypatch
):
    monkeypatch.setattr("app.pipeline.parsers._extract_pdf", lambda _: "Alice Smith\nalice@example.com")
    monkeypatch.setattr("app.pipeline.BedrockClient", lambda: _MockBedrockClient(CANNED_CV_JSON))

    resp = await http_client.post(
        "/api/ingest/cv",
        headers=admin_token,
        files=_pdf_upload("cv.pdf"),
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["entityId"].startswith("cv_")
    assert body["status"] == "success"
    assert body["runId"] > 0


async def test_ingested_candidate_retrievable(http_client, admin_token, monkeypatch):
    monkeypatch.setattr("app.pipeline.parsers._extract_pdf", lambda _: "Bob Jones\nbob@example.com")
    monkeypatch.setattr("app.pipeline.BedrockClient", lambda: _MockBedrockClient(CANNED_CV_JSON))

    ingest_resp = await http_client.post(
        "/api/ingest/cv",
        headers=admin_token,
        files=_pdf_upload("cv.pdf"),
    )
    entity_id = ingest_resp.json()["entityId"]

    get_resp = await http_client.get(f"/api/candidates/{entity_id}", headers=admin_token)
    assert get_resp.status_code == 200
    assert get_resp.json()["fullName"] == "Ingested Candidate"


# ---------------------------------------------------------------------------
# POST /api/ingest/cv — error paths
# ---------------------------------------------------------------------------

async def test_ingest_cv_bedrock_error_returns_422(http_client, admin_token, monkeypatch):
    monkeypatch.setattr("app.pipeline.parsers._extract_pdf", lambda _: "Jane Doe\njane@example.com")
    monkeypatch.setattr("app.pipeline.BedrockClient", lambda: _ErrorMockClient())

    resp = await http_client.post(
        "/api/ingest/cv",
        headers=admin_token,
        files=_pdf_upload("cv.pdf"),
    )
    assert resp.status_code == 422


async def test_ingest_cv_txt_extension_returns_422(http_client, admin_token):
    """parse_cv raises ParseError for .txt files — no monkeypatch needed."""
    resp = await http_client.post(
        "/api/ingest/cv",
        headers=admin_token,
        files={"file": ("resume.txt", io.BytesIO(b"Plain text CV"), "text/plain")},
    )
    assert resp.status_code == 422


# ---------------------------------------------------------------------------
# Auth guards
# ---------------------------------------------------------------------------

async def test_ingest_cv_unauthenticated_returns_401(http_client):
    resp = await http_client.post("/api/ingest/cv", files=_pdf_upload())
    assert resp.status_code == 401


async def test_ingest_cv_viewer_role_returns_403(http_client, viewer_token, monkeypatch):
    monkeypatch.setattr("app.pipeline.parsers._extract_pdf", lambda _: "Some text")
    resp = await http_client.post(
        "/api/ingest/cv",
        headers=viewer_token,
        files=_pdf_upload("cv.pdf"),
    )
    assert resp.status_code == 403
