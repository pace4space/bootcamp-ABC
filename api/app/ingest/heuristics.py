from __future__ import annotations

import re

from .types import HeuristicHints, RawDocument

_EMAIL_RE = re.compile(r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}")

# Israeli mobile: 05x-xxx-xxxx or +972-5x-xxx-xxxx (hyphens/spaces optional)
# Generic international: +E.164-style, no separator requirement
_PHONE_RE = re.compile(
    r"(?:\+972[-\s]?|0)5\d[-\s]?\d{3}[-\s]?\d{4}"
    r"|\+[1-9][\d\s\-\.]{7,14}\d"
)

_LINKEDIN_RE = re.compile(
    r"https?://(?:www\.)?linkedin\.com/in/[^\s/\"'<>]+",
    re.IGNORECASE,
)
_GITHUB_RE = re.compile(
    r"https?://(?:www\.)?github\.com/[^\s/\"'<>]+",
    re.IGNORECASE,
)

# Position docs: "From: manager@company.com" on its own line
_FROM_EMAIL_RE = re.compile(r"^From:\s*(.+@[^\s]+)", re.MULTILINE | re.IGNORECASE)


def extract_hints(doc: RawDocument) -> HeuristicHints:
    text = doc.raw_text

    email_m = _EMAIL_RE.search(text)
    phone_m = _PHONE_RE.search(text)
    linkedin_m = _LINKEDIN_RE.search(text)
    github_m = _GITHUB_RE.search(text)
    from_m = _FROM_EMAIL_RE.search(text)

    return HeuristicHints(
        email=email_m.group(0) if email_m else None,
        phone=phone_m.group(0).strip() if phone_m else None,
        linkedin_url=linkedin_m.group(0) if linkedin_m else None,
        github_url=github_m.group(0) if github_m else None,
        hiring_manager_email=from_m.group(1).strip() if from_m else None,
    )
