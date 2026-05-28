# Ex3 — Module 1: Document Parsing

## Problem

Given a PDF or DOCX file as bytes, produce a clean string of the document's text content.
Must work across 270 heterogeneous CVs: different layouts, fonts, encodings, and
directionality (some CVs contain Hebrew names and addresses).

## Why This Is Its Own Stage

Parsing is pure I/O. It has no business logic, no model calls, and no schema knowledge.
A function that both parses a PDF and extracts candidate fields is two functions pretending
to be one. Isolating parsing means:

- It can be tested independently (no mocking needed — just bytes in, string out)
- The rest of the pipeline can be tested with pre-constructed `RawDocument` objects
- Parse errors are a distinct failure mode from extraction errors

## Library Choice: pdfminer.six vs pypdf

### pypdf (rejected)
Simpler and lighter. However, it extracts characters in the order they appear in the PDF
byte stream, not in reading order. For right-to-left text (Hebrew, Arabic), this produces
scrambled output — characters appear in reverse. Our CVs include Hebrew names and addresses.

### pdfminer.six (chosen)
Performs layout analysis before text extraction. Groups characters into lines and paragraphs
using spatial positioning, which produces correct reading order even for bidirectional text.
More expensive to run but correct.

**Decision: pdfminer.six.** The Ex1 prompt documentation (rule 9 in `prompts/extract-candidate.md`)
already notes this pitfall. We follow the established learning.

## Failure Mode Design

A successful parse that returns empty string is a *parser failure*, not "no content found."
If `raw_text.strip() == ""` after parsing, raise `ParseError` — never return silently.

```python
class ParseError(Exception):
    """Raised when a file cannot be parsed or produces no extractable text."""

def parse_cv(file_bytes: bytes, filename: str) -> RawDocument:
    fmt = _detect_format(filename)  # raises ParseError for unknown extension
    if fmt == ParseFormat.PDF:
        raw_text = _extract_pdf(file_bytes)
    elif fmt == ParseFormat.DOCX:
        raw_text = _extract_docx(file_bytes)
    if not raw_text.strip():
        raise ParseError(f"{filename}: parsed successfully but produced no text")
    return RawDocument(
        filename=filename, format=fmt, kind=DocumentKind.CV,
        raw_text=raw_text, char_count=len(raw_text)
    )
```

## Public Interface

```python
# api/app/pipeline/parsers.py

class ParseError(Exception): ...

def parse_cv(file_bytes: bytes, filename: str) -> RawDocument:
    """Accept PDF or DOCX bytes. Returns RawDocument or raises ParseError."""

def parse_position(text: str, filename: str) -> RawDocument:
    """Accept plain text string. Returns RawDocument or raises ParseError."""
```

## Test Cases

```python
# tests/pipeline/test_parsers.py

def test_parse_pdf_returns_raw_document(minimal_pdf_bytes):
    doc = parse_cv(minimal_pdf_bytes, "test.pdf")
    assert isinstance(doc.raw_text, str)
    assert len(doc.raw_text.strip()) > 0
    assert doc.format == ParseFormat.PDF

def test_parse_docx_returns_raw_document(minimal_docx_bytes):
    doc = parse_cv(minimal_docx_bytes, "test.docx")
    assert doc.format == ParseFormat.DOCX

def test_empty_pdf_raises_parse_error():
    with pytest.raises(ParseError):
        parse_cv(b"%PDF-1.4", "empty.pdf")

def test_unknown_extension_raises_parse_error():
    with pytest.raises(ParseError, match="unsupported format"):
        parse_cv(b"rtf content", "test.rtf")

def test_parse_position_plain_text():
    doc = parse_position("From: mgr@co.com\n\nWe are hiring...", "job_001.txt")
    assert doc.kind == DocumentKind.POSITION
    assert "hiring" in doc.raw_text
```

## Interview Talking Point

> "Why does `parse_cv` raise an exception instead of returning an empty `RawDocument`?"

Because an empty `RawDocument` is indistinguishable from a valid empty document. Errors
should be explicit types, not sentinel values. If every caller has to check `if doc.raw_text`,
the parse function has failed to communicate its contract.
