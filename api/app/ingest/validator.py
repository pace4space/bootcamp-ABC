"""LLM output validation — parse raw JSON string into typed payload dataclasses.

Two failure modes:
  - Structural (malformed JSON, missing required fields) → ValidationError raised
  - Semantic (wrong type on optional field) → field cast, warning appended, PARTIAL status
"""
from __future__ import annotations

import json
from dataclasses import asdict
from typing import Any, Optional

from .types import (
    CandidatePayload,
    CertificationPayload,
    EducationPayload,
    ExperiencePayload,
    ExtractionStatus,
    HeuristicHints,
    LanguagePayload,
    LLMResponse,
    PositionPayload,
    RequirementPayload,
)


class ValidationError(Exception):
    """Raised when LLM output is structurally invalid (bad JSON or missing required fields)."""


from app.text_utils import strip_fences as _strip_fences


def _apply_hints(payload_dict: dict, hints: HeuristicHints) -> dict:
    overrides = {k: v for k, v in asdict(hints).items() if v is not None}
    return {**payload_dict, **overrides}


def _coerce_int(value: Any, field_name: str, warnings: list[str]) -> Optional[int]:
    """Attempt int cast; always appends a warning (cast was needed). Returns None on failure."""
    try:
        warnings.append(f"{field_name}: coerced from {type(value).__name__} '{value}' to int")
        return int(value)
    except (ValueError, TypeError):
        warnings.append(f"{field_name}: cannot coerce '{value}' to int; set to None")
        return None


def _parse_experience(raw: Any, warnings: list[str]) -> list[ExperiencePayload]:
    result = []
    if not isinstance(raw, list):
        return result
    for i, item in enumerate(raw):
        if not isinstance(item, dict):
            warnings.append(f"experience[{i}]: expected dict, skipped")
            continue
        role = str(item.get("role") or "")
        company = str(item.get("company") or "")
        sy = item.get("start_year")
        if sy is None:
            warnings.append(f"experience[{i}].start_year: missing, entry skipped")
            continue
        if not isinstance(sy, int):
            sy = _coerce_int(sy, f"experience[{i}].start_year", warnings)
            if sy is None:
                continue
        ey = item.get("end_year")
        if ey is not None and not isinstance(ey, int):
            ey = _coerce_int(ey, f"experience[{i}].end_year", warnings)
        result.append(ExperiencePayload(
            role=role,
            company=company,
            start_year=sy,
            end_year=ey,
            location=item.get("location"),
            highlights=item.get("highlights") or [],
        ))
    return result


def _parse_education(raw: Any, warnings: list[str]) -> list[EducationPayload]:
    result = []
    if not isinstance(raw, list):
        return result
    for i, item in enumerate(raw):
        if not isinstance(item, dict):
            continue
        degree = str(item.get("degree") or "")
        institution = str(item.get("institution") or "")
        sy = item.get("start_year")
        ey = item.get("end_year")
        if not isinstance(sy, int):
            sy = _coerce_int(sy, f"education[{i}].start_year", warnings)
        if not isinstance(ey, int):
            ey = _coerce_int(ey, f"education[{i}].end_year", warnings)
        if sy is None or ey is None:
            continue
        result.append(EducationPayload(degree=degree, institution=institution, start_year=sy, end_year=ey))
    return result


def _parse_certifications(raw: Any, warnings: list[str]) -> list[CertificationPayload]:
    result = []
    if not isinstance(raw, list):
        return result
    for i, item in enumerate(raw):
        if not isinstance(item, dict):
            continue
        name = str(item.get("name") or "")
        year = item.get("year")
        if year is not None and not isinstance(year, int):
            year = _coerce_int(year, f"certifications[{i}].year", warnings)
        result.append(CertificationPayload(name=name, year=year))
    return result


def _parse_languages(raw: Any) -> list[LanguagePayload]:
    result = []
    if not isinstance(raw, list):
        return result
    for item in raw:
        if not isinstance(item, dict):
            continue
        result.append(LanguagePayload(
            name=str(item.get("name") or ""),
            proficiency=str(item.get("proficiency") or ""),
        ))
    return result


def validate_cv_payload(
    llm_response: LLMResponse,
    hints: HeuristicHints,
) -> tuple[CandidatePayload, list[str], ExtractionStatus]:
    """Parse LLM JSON string → CandidatePayload with heuristic overrides.

    Returns (payload, warnings, status). Raises ValidationError on structural failure.
    """
    try:
        d = json.loads(_strip_fences(llm_response.raw_json_str))
    except json.JSONDecodeError as e:
        raise ValidationError(f"JSON parse failed: {e}") from e

    if not d.get("full_name"):
        raise ValidationError("full_name is required but missing or empty")

    d = _apply_hints(d, hints)

    warnings: list[str] = []
    experience = _parse_experience(d.get("experience", []), warnings)
    education = _parse_education(d.get("education", []), warnings)
    certifications = _parse_certifications(d.get("certifications", []), warnings)
    languages = _parse_languages(d.get("languages", []))

    skills_raw = d.get("skills", [])
    skills: list[str] = skills_raw if isinstance(skills_raw, list) else []

    payload = CandidatePayload(
        full_name=str(d["full_name"]),
        summary=str(d.get("summary") or ""),
        skills=skills,
        experience=experience,
        education=education,
        certifications=certifications,
        languages=languages,
        headline=d.get("headline"),
        email=d.get("email"),
        phone=d.get("phone"),
        city=d.get("city"),
        linkedin_url=d.get("linkedin_url"),
        github_url=d.get("github_url"),
    )

    status = ExtractionStatus.PARTIAL if warnings else ExtractionStatus.SUCCESS
    return payload, warnings, status


def validate_position_payload(
    llm_response: LLMResponse,
    hints: HeuristicHints,
) -> tuple[PositionPayload, list[str], ExtractionStatus]:
    """Parse LLM JSON string → PositionPayload with heuristic overrides.

    Returns (payload, warnings, status). Raises ValidationError on structural failure.
    """
    try:
        d = json.loads(_strip_fences(llm_response.raw_json_str))
    except json.JSONDecodeError as e:
        raise ValidationError(f"JSON parse failed: {e}") from e

    if not d.get("title"):
        raise ValidationError("title is required but missing or empty")

    d = _apply_hints(d, hints)

    warnings: list[str] = []
    reqs_raw = d.get("requirements", [])
    requirements: list[RequirementPayload] = []
    for i, req in enumerate(reqs_raw if isinstance(reqs_raw, list) else []):
        if not isinstance(req, dict):
            warnings.append(f"requirements[{i}]: expected dict, skipped")
            continue
        requirements.append(RequirementPayload(
            type=str(req.get("type") or "must_have"),
            text=str(req.get("text") or ""),
        ))

    payload = PositionPayload(
        title=str(d["title"]),
        requirements=requirements,
        description=d.get("description"),
        location=d.get("location"),
        seniority=d.get("seniority"),
        salary_range=d.get("salary_range"),
        hiring_manager_email=d.get("hiring_manager_email"),
    )

    status = ExtractionStatus.PARTIAL if warnings else ExtractionStatus.SUCCESS
    return payload, warnings, status
