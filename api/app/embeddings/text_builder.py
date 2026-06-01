"""Standardized, deterministic text builders for Titan embeddings.

The composed text is the #1 design lever for retrieval quality — Titan is a
black box; only this text is under our control.  Same row → byte-identical
string → identical vector (Principle 1: reproducibility).

Design rules baked in:
- Include semantic substance; exclude noise (PII, URLs, years, filenames).
- Drop empty sections entirely (no dangling headers).
- Deterministic ordering: skills/requirements by sort_order, experience by
  start_year desc.
- Standardized wording across both entity types keeps candidate/position
  vectors geometrically close to their matches.
"""
from __future__ import annotations

import hashlib
import re


def build_candidate_text(candidate) -> str:
    """Compose embedding text from a Candidate ORM object with eager-loaded children."""
    lines: list[str] = []

    if candidate.headline:
        lines.append(f"Role: {candidate.headline}")
    if candidate.summary:
        lines.append(f"Summary: {candidate.summary}")

    skills = sorted(candidate.skills or [], key=lambda s: s.sort_order)
    if skills:
        lines.append("Skills: " + ", ".join(s.name for s in skills))

    exp = sorted(candidate.experience or [], key=lambda e: -e.start_year)
    if exp:
        lines.append("Experience:")
        for e in exp:
            end = str(e.end_year) if e.end_year else "present"
            entry = f"- {e.role} at {e.company} ({e.start_year}–{end})"
            if e.highlights:
                entry += ": " + "; ".join(e.highlights)
            lines.append(entry)

    education = sorted(candidate.education or [], key=lambda e: e.sort_order)
    if education:
        edu_parts = [f"{e.degree}, {e.institution}" for e in education]
        lines.append("Education: " + "; ".join(edu_parts))

    languages = sorted(candidate.languages or [], key=lambda l: l.sort_order)
    if languages:
        lines.append("Languages: " + ", ".join(l.name for l in languages))

    return _normalize("\n".join(lines))


def build_position_text(position) -> str:
    """Compose embedding text from a Position ORM object with eager-loaded requirements."""
    lines: list[str] = []

    lines.append(f"Title: {position.title}")
    if position.seniority:
        lines.append(f"Seniority: {position.seniority}")
    if position.description:
        lines.append(f"Description: {position.description}")

    requirements = sorted(position.requirements or [], key=lambda r: r.sort_order)
    must_have = [r.text for r in requirements if r.type == "must_have"]
    nice_to_have = [r.text for r in requirements if r.type == "nice_to_have"]

    if must_have:
        lines.append("Must-have: " + ", ".join(must_have))
    if nice_to_have:
        lines.append("Nice-to-have: " + ", ".join(nice_to_have))

    return _normalize("\n".join(lines))


def text_sha256(text: str) -> str:
    """Hex digest of text; the skip-if-unchanged / drift-detection signal."""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _normalize(text: str) -> str:
    """Collapse internal whitespace runs; strip trailing whitespace per line."""
    lines = [re.sub(r" {2,}", " ", line).rstrip() for line in text.splitlines()]
    return "\n".join(line for line in lines if line)
