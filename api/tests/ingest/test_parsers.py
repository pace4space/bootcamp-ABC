from pathlib import Path

import pytest

from app.ingest.parsers import ParseError, parse_cv, parse_position
from app.ingest.types import DocumentKind, ParseFormat

from .conftest import make_docx_bytes, make_empty_docx_bytes

_SAMPLE_PDF = Path(__file__).parents[3] / "public" / "cvs" / "cv_001.pdf"


# ---------------------------------------------------------------------------
# parse_cv — DOCX (hermetic, no filesystem)
# ---------------------------------------------------------------------------

def test_parse_cv_docx_returns_raw_document(minimal_docx):
    doc = parse_cv(minimal_docx, "resume.docx")
    assert doc.format == ParseFormat.DOCX
    assert doc.kind == DocumentKind.CV
    assert "Jane Doe" in doc.raw_text
    assert doc.char_count == len(doc.raw_text)
    assert doc.filename == "resume.docx"


def test_parse_cv_docx_empty_raises():
    with pytest.raises(ParseError, match="no extractable text"):
        parse_cv(make_empty_docx_bytes(), "empty.docx")


# ---------------------------------------------------------------------------
# parse_cv — format guards
# ---------------------------------------------------------------------------

def test_parse_cv_txt_extension_raises(minimal_docx):
    with pytest.raises(ParseError, match="not TXT"):
        parse_cv(minimal_docx, "resume.txt")


def test_parse_cv_unknown_extension_raises(minimal_docx):
    with pytest.raises(ParseError, match="Unsupported file extension"):
        parse_cv(minimal_docx, "resume.rtf")


# ---------------------------------------------------------------------------
# parse_cv — PDF (monkeypatched for unit test, real file for smoke)
# ---------------------------------------------------------------------------

def test_parse_cv_pdf_empty_raises(monkeypatch):
    monkeypatch.setattr("app.ingest.parsers._extract_pdf", lambda _: "   ")
    with pytest.raises(ParseError, match="no extractable text"):
        parse_cv(b"%PDF-1.4", "blank.pdf")


def test_parse_cv_pdf_returns_raw_document(monkeypatch):
    monkeypatch.setattr("app.ingest.parsers._extract_pdf", lambda _: "Alice Smith\nalice@example.com")
    doc = parse_cv(b"%PDF-1.4", "cv.pdf")
    assert doc.format == ParseFormat.PDF
    assert doc.kind == DocumentKind.CV
    assert "Alice" in doc.raw_text


@pytest.mark.skipif(not _SAMPLE_PDF.exists(), reason="CV corpus not present")
def test_parse_cv_pdf_smoke():
    doc = parse_cv(_SAMPLE_PDF.read_bytes(), "cv_001.pdf")
    assert doc.raw_text.strip(), "expected non-empty text from real CV"
    assert doc.format == ParseFormat.PDF
    assert doc.char_count > 100


# ---------------------------------------------------------------------------
# parse_position — TXT
# ---------------------------------------------------------------------------

def test_parse_position_txt_success():
    content = b"Senior Python Engineer\nRemote\nRequires 5 years experience"
    doc = parse_position(content, "job_001.txt")
    assert doc.format == ParseFormat.TXT
    assert doc.kind == DocumentKind.POSITION
    assert "Python" in doc.raw_text
    assert doc.char_count == len(doc.raw_text)


def test_parse_position_empty_raises():
    with pytest.raises(ParseError, match="no extractable text"):
        parse_position(b"   ", "job.txt")


def test_parse_position_pdf_raises():
    with pytest.raises(ParseError, match="must be TXT"):
        parse_position(b"%PDF-1.4", "job.pdf")


def test_parse_position_docx_raises(minimal_docx):
    with pytest.raises(ParseError, match="must be TXT"):
        parse_position(minimal_docx, "job.docx")


def test_parse_position_unknown_extension_raises():
    with pytest.raises(ParseError, match="Unsupported file extension"):
        parse_position(b"some text", "job.eml")
