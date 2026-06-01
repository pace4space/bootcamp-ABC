"""Segment 02 tests — deterministic embedding text builders.

Golden strings are the tripwire: any wording change forces a conscious re-embed.
"""
from __future__ import annotations

import types

import pytest

from app.embeddings.text_builder import (
    build_candidate_text,
    build_position_text,
    text_sha256,
)


# ---------------------------------------------------------------------------
# Helpers: build lightweight stand-in objects from the conftest seed data
# ---------------------------------------------------------------------------

def _skill(name, sort_order=0):
    return types.SimpleNamespace(name=name, sort_order=sort_order)

def _exp(role, company, start_year, end_year=None, highlights=None, sort_order=0):
    return types.SimpleNamespace(
        role=role, company=company, start_year=start_year,
        end_year=end_year, highlights=highlights or [], sort_order=sort_order,
    )

def _edu(degree, institution, sort_order=0):
    return types.SimpleNamespace(degree=degree, institution=institution, sort_order=sort_order)

def _lang(name, sort_order=0):
    return types.SimpleNamespace(name=name, sort_order=sort_order)

def _req(text, req_type, sort_order=0):
    return types.SimpleNamespace(text=text, type=req_type, sort_order=sort_order)

def _candidate(**kw):
    defaults = dict(headline=None, summary=None, skills=[], experience=[],
                    education=[], certifications=[], languages=[])
    defaults.update(kw)
    return types.SimpleNamespace(**defaults)

def _position(**kw):
    defaults = dict(title="", seniority=None, description=None, requirements=[])
    defaults.update(kw)
    return types.SimpleNamespace(**defaults)


# ---------------------------------------------------------------------------
# Golden strings (tripwire tests)
# ---------------------------------------------------------------------------

_ALICE = _candidate(
    headline="Senior DevOps Engineer",
    summary="Experienced DevOps.",
    skills=[_skill("Docker", 0)],
    experience=[
        _exp("Senior DevOps", "ACME", 2022, sort_order=0),
        _exp("DevOps Engineer", "Corp", 2020, 2021, sort_order=1),
    ],
    languages=[_lang("English", 0)],
)

_ALICE_GOLDEN = (
    "Role: Senior DevOps Engineer\n"
    "Summary: Experienced DevOps.\n"
    "Skills: Docker\n"
    "Experience:\n"
    "- Senior DevOps at ACME (2022–present)\n"
    "- DevOps Engineer at Corp (2020–2021)\n"
    "Languages: English"
)

_POS_A = _position(
    title="Test Position Open A",
    description="Open position A.",
    requirements=[
        _req("Docker", "must_have", 0),
        _req("Kubernetes", "nice_to_have", 0),
    ],
)

_POS_A_GOLDEN = (
    "Title: Test Position Open A\n"
    "Description: Open position A.\n"
    "Must-have: Docker\n"
    "Nice-to-have: Kubernetes"
)


def test_candidate_text_golden():
    assert build_candidate_text(_ALICE) == _ALICE_GOLDEN


def test_position_text_golden():
    assert build_position_text(_POS_A) == _POS_A_GOLDEN


# ---------------------------------------------------------------------------
# PII exclusion
# ---------------------------------------------------------------------------

def test_excludes_pii():
    c = _candidate(
        headline="Engineer",
        skills=[_skill("Python")],
        experience=[_exp("Dev", "Corp", 2020)],
    )
    # Inject noise via a custom object that has a __str__ with PII
    text = build_candidate_text(c)
    assert "@" not in text       # no email
    assert "http" not in text    # no URLs
    assert "+1" not in text      # no phone


# ---------------------------------------------------------------------------
# Empty section suppression
# ---------------------------------------------------------------------------

def test_empty_sections_dropped():
    c = _candidate(headline="Engineer")  # no skills, no experience, no languages
    text = build_candidate_text(c)
    assert "Skills:" not in text
    assert "Experience:" not in text
    assert "Languages:" not in text
    assert "Education:" not in text


# ---------------------------------------------------------------------------
# Determinism
# ---------------------------------------------------------------------------

def test_deterministic():
    assert build_candidate_text(_ALICE) == build_candidate_text(_ALICE)
    assert build_position_text(_POS_A) == build_position_text(_POS_A)


# ---------------------------------------------------------------------------
# sha256 stability and sensitivity
# ---------------------------------------------------------------------------

def test_sha256_stable_and_sensitive():
    s = "hello world"
    h1 = text_sha256(s)
    h2 = text_sha256(s)
    assert h1 == h2                         # stable
    assert len(h1) == 64                    # hex sha256
    h3 = text_sha256(s + "x")
    assert h1 != h3                         # sensitive to change
