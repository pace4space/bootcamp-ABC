import pytest

from app.pipeline.heuristics import extract_hints
from app.pipeline.types import DocumentKind, ParseFormat, RawDocument


def _doc(text: str, kind: DocumentKind = DocumentKind.CV) -> RawDocument:
    return RawDocument(
        filename="test.txt",
        format=ParseFormat.TXT,
        kind=kind,
        raw_text=text,
        char_count=len(text),
    )


# ---------------------------------------------------------------------------
# Email
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("text,expected", [
    ("contact alice@example.com for details", "alice@example.com"),
    ("jane.doe+tag@sub.domain.co.il is my address", "jane.doe+tag@sub.domain.co.il"),
    ("no email in this text at all", None),
])
def test_email(text, expected):
    assert extract_hints(_doc(text)).email == expected


# ---------------------------------------------------------------------------
# Phone
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("text,expected", [
    ("call me at 050-1234567 anytime", "050-1234567"),
    ("mobile: 050-123-4567", "050-123-4567"),
    ("phone: +972-50-1234567", "+972-50-1234567"),
    ("intl: +1-800-555-1234 for support", "+1-800-555-1234"),
    ("no phone here", None),
])
def test_phone(text, expected):
    assert extract_hints(_doc(text)).phone == expected


# ---------------------------------------------------------------------------
# LinkedIn URL
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("text,expected", [
    ("profile: https://linkedin.com/in/johndoe", "https://linkedin.com/in/johndoe"),
    ("see https://www.linkedin.com/in/jane-smith-il", "https://www.linkedin.com/in/jane-smith-il"),
    ("no linkedin here", None),
])
def test_linkedin_url(text, expected):
    assert extract_hints(_doc(text)).linkedin_url == expected


# ---------------------------------------------------------------------------
# GitHub URL
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("text,expected", [
    ("code at https://github.com/alice", "https://github.com/alice"),
    ("https://www.github.com/bob-dev is my repo", "https://www.github.com/bob-dev"),
    ("no github here", None),
])
def test_github_url(text, expected):
    assert extract_hints(_doc(text)).github_url == expected


# ---------------------------------------------------------------------------
# Hiring manager email (position docs only)
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("text,expected", [
    ("From: hr@company.com\nWe are hiring", "hr@company.com"),
    ("From: Sarah Levi <sarah@hellio.io>\nSenior role", "Sarah Levi <sarah@hellio.io>"),
    ("No from header here\nalice@example.com", None),  # inline email, no From: prefix
])
def test_hiring_manager_email(text, expected):
    doc = _doc(text, kind=DocumentKind.POSITION)
    assert extract_hints(doc).hiring_manager_email == expected


# ---------------------------------------------------------------------------
# Multiple fields in one document
# ---------------------------------------------------------------------------

def test_all_fields_extracted():
    text = (
        "From: manager@hellio.io\n"
        "Candidate: Alice Levi\n"
        "Email: alice@example.com\n"
        "Phone: 052-9876543\n"
        "LinkedIn: https://linkedin.com/in/aliceli\n"
        "GitHub: https://github.com/alice-dev\n"
    )
    hints = extract_hints(_doc(text, kind=DocumentKind.POSITION))
    assert hints.email == "manager@hellio.io"  # first email found in text
    assert hints.phone == "052-9876543"
    assert hints.linkedin_url == "https://linkedin.com/in/aliceli"
    assert hints.github_url == "https://github.com/alice-dev"
    assert hints.hiring_manager_email == "manager@hellio.io"


def test_no_patterns_returns_all_none():
    hints = extract_hints(_doc("Senior Python developer wanted in Tel Aviv"))
    assert hints.email is None
    assert hints.phone is None
    assert hints.linkedin_url is None
    assert hints.github_url is None
    assert hints.hiring_manager_email is None
