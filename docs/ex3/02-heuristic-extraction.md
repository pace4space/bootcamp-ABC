# Ex3 — Module 2: Heuristic Extraction

## Problem

Before calling the LLM, extract fields that can be reliably captured with deterministic
patterns. These become "locked" values that override whatever the LLM returns.

## Why Heuristics Before LLM

LLMs are not always more accurate than regex for structured fields. For an email address
embedded in a CV, a regex is 100% accurate by definition — it extracts exactly what the
string contains. An LLM might hallucinate, truncate, or reformat the address.

The heuristics/LLM separation also has an audit benefit: when a candidate's email in the
DB is wrong, you can determine whether it came from the regex stage or the LLM stage by
reading the `extraction_runs` row. The `HeuristicHints` struct is included in the prompt
context, making the source of every field traceable.

## Fields Handled by Heuristics

| Field | Pattern strategy |
|-------|-----------------|
| `email` | RFC-5321 email regex: `[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}` |
| `phone` | Israeli mobile: `05x-xxx-xxxx` or `+972-5x-xxx-xxxx`, with optional hyphens/spaces; international: `+` followed by 9-16 digits/separators |
| `linkedin_url` | `https?://(?:www\.)?linkedin\.com/in/[^\s/"'<>]+` |
| `github_url` | `https?://(?:www\.)?github\.com/[^\s/"'<>]+` |
| `hiring_manager_email` | `^From:\s*(.+@[^\s]+)` on position docs — first matching line |

All fields are `Optional[str]`. Hints are opportunistic — never blocking. A document with
no regex matches returns a `HeuristicHints` with all fields `None`, which is valid.

LinkedIn and GitHub hints intentionally require an explicit `http://` or `https://`
scheme. Bare domains such as `linkedin.com/in/alice` are left to the LLM because the
current regex only treats full URLs as high-confidence structured fields.

For position documents, `email` is still the first email found anywhere in the text. If a
`From:` header appears first, `email` and `hiring_manager_email` can contain the same
address. `hiring_manager_email` captures the rest of the `From:` value, so display-name
headers such as `From: Sarah Levi <sarah@hellio.io>` are preserved.

## Trust Hierarchy in Practice

The validator applies heuristic overrides after receiving the LLM payload:

```python
def _apply_hints(payload_dict: dict, hints: HeuristicHints) -> dict:
    """Heuristic values override LLM values for the same field."""
    overrides = {k: v for k, v in asdict(hints).items() if v is not None}
    return {**payload_dict, **overrides}
```

Simple dict merge. Hints win. Explicit in code, logged in prompt context, explainable
in an interview.

## What Heuristics Do NOT Do

- Infer seniority from job titles → LLM task
- Extract skills from prose → LLM task
- Generate summaries → LLM task
- Parse varied date formats ("March 2019 – Present") → LLM task

The boundary rule: use a heuristic when the field is structurally deterministic (has a
known format) and correctness is binary (matches or it doesn't). Use the LLM when the
field requires reading comprehension.

## Public Interface

```python
# api/app/pipeline/heuristics.py

def extract_hints(doc: RawDocument) -> HeuristicHints:
    """Run regex patterns against raw_text. Returns HeuristicHints (all fields Optional)."""
```

## Test Cases

```python
# tests/pipeline/test_heuristics.py

@pytest.mark.parametrize("text,expected_email", [
    ("Contact: alice@example.com", "alice@example.com"),
    ("Email: user.name+tag@sub.domain.org", "user.name+tag@sub.domain.org"),
    ("No email here", None),
])
def test_email_extraction(text, expected_email):
    doc = RawDocument(filename="t.pdf", format=ParseFormat.PDF,
                      kind=DocumentKind.CV, raw_text=text, char_count=len(text))
    hints = extract_hints(doc)
    assert hints.email == expected_email

def test_israeli_phone():
    doc = _make_doc("Call me: 050-1234567")
    assert extract_hints(doc).phone == "050-1234567"

def test_linkedin_url():
    doc = _make_doc("https://linkedin.com/in/alice-smith")
    assert "alice-smith" in extract_hints(doc).linkedin_url

def test_github_url():
    doc = _make_doc("https://github.com/alicedev")
    assert extract_hints(doc).github_url is not None

def test_hiring_manager_from_position_doc():
    doc = RawDocument(..., kind=DocumentKind.POSITION,
                      raw_text="From: sarah.chen@company.com\n\nJob description...")
    hints = extract_hints(doc)
    assert hints.hiring_manager_email == "sarah.chen@company.com"

def test_no_patterns_returns_all_none():
    doc = _make_doc("Nothing structured here at all")
    hints = extract_hints(doc)
    assert hints.email is None
    assert hints.phone is None
    assert hints.linkedin_url is None
    assert hints.github_url is None
```

## Interview Talking Point

> "When would you add a new heuristic vs letting the LLM handle it?"

When the field is structurally deterministic (known format, binary correctness) and the
heuristic is always cheaper, always auditable, and always reproducible. Use it wherever it
works. The LLM handles ambiguity; heuristics handle structure.
