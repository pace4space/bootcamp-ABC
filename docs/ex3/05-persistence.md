# Ex3 — Module 5: Persistence

## Problem

Given a validated `CandidatePayload`, write a `Candidate` record and all its children
(skills, experience, education, certifications, languages) to Postgres in a single
atomic transaction.

## Atomicity Contract

The persister's contract: either the full candidate (parent + all children) is committed,
or nothing is. There is no intermediate state where a `Candidate` row exists without its
`CandidateSkill` rows.

```python
async def persist_candidate(
    payload: CandidatePayload, doc: RawDocument, db: AsyncSession
) -> str:
    candidate_id = f"cv_{uuid4().hex[:8]}"
    async with db.begin():
        db.add(Candidate(
            id=candidate_id,
            full_name=payload.full_name,
            headline=payload.headline,
            status="Active",
            email=payload.email,
            # ... all other fields
        ))
        for i, skill in enumerate(payload.skills):
            db.add(CandidateSkill(
                candidate_id=candidate_id, name=skill, sort_order=i
            ))
        for i, exp in enumerate(payload.experience):
            db.add(CandidateExperience(
                candidate_id=candidate_id, role=exp.role,
                company=exp.company, start_year=exp.start_year,
                end_year=exp.end_year, sort_order=i
            ))
        # education, certifications, languages follow same pattern
    return candidate_id
```

If any `db.add()` triggers a constraint violation (e.g., duplicate email), `db.begin()`'s
context manager rolls back the entire block before re-raising. No partial state reaches DB.

## ID Generation Strategy

The seeded data uses `cv_001` through `cv_012`. We cannot continue that sequence safely
(concurrent requests, re-ingestion of same file). Pipeline-generated IDs use `cv_` + 8 hex
chars from `uuid4()`:

- Never collides with seeded records (`cv_001` is not 8 hex chars)
- Never collides with concurrent ingestions (UUID4 guarantee)
- Still readable and searchable

Example: `cv_3f7a1b2e`

**What the persister does NOT do:** generate IDs from filenames (`cv_013.pdf → cv_013`).
That pattern breaks when filenames change or the same file is ingested twice. UUID-based
IDs decouple identity from provenance.

## Public Interface

```python
# api/app/pipeline/persister.py

async def persist_candidate(
    payload: CandidatePayload,
    doc: RawDocument,
    db: AsyncSession,
) -> str:
    """
    Insert Candidate + all child rows in one transaction.
    Returns candidate_id (cv_XXXXXXXX).
    Raises sqlalchemy.exc.IntegrityError on constraint violation.
    """

async def persist_position(
    payload: PositionPayload,
    doc: RawDocument,
    db: AsyncSession,
) -> str:
    """
    Insert Position + requirements in one transaction.
    Returns position_id (pos_XXXXXXXX).
    """
```

## Test Cases

```python
# tests/pipeline/test_persister.py

async def test_persist_candidate_creates_all_rows(seeded_db):
    payload = CandidatePayload(
        full_name="Test Candidate", summary="A summary",
        skills=["Docker", "Kubernetes"],
        experience=[ExperiencePayload(role="SRE", company="Acme", start_year=2021)],
        education=[], certifications=[], languages=[]
    )
    doc = RawDocument(filename="test.pdf", format=ParseFormat.PDF,
                      kind=DocumentKind.CV, raw_text="...", char_count=3)
    async with seeded_db() as db:
        candidate_id = await persist_candidate(payload, doc, db)

    assert candidate_id.startswith("cv_")
    assert len(candidate_id) == 11  # "cv_" + 8 hex

async def test_duplicate_email_raises_integrity_error(seeded_db):
    # cv_001 in seed data has email aarav.hayes@email.com
    payload = CandidatePayload(
        full_name="Duplicate", email="aarav.hayes@email.com",
        summary="...", skills=[], experience=[], education=[],
        certifications=[], languages=[]
    )
    async with seeded_db() as db:
        with pytest.raises(IntegrityError):
            await persist_candidate(payload, doc, db)

async def test_candidate_with_no_children_still_created(seeded_db):
    payload = CandidatePayload(
        full_name="Empty Candidate", summary="...",
        skills=[], experience=[], education=[],
        certifications=[], languages=[]
    )
    async with seeded_db() as db:
        candidate_id = await persist_candidate(payload, doc, db)
    assert candidate_id.startswith("cv_")
```

## Interview Talking Point

> "Why put all child inserts inside the same `async with db.begin()` as the parent, rather
> than committing the parent first and adding children separately?"

Because a `Candidate` with no skills and no experience is a valid but useless record from
a data quality perspective — we'd have to clean it up manually. Atomicity means either the
complete record exists or nothing does. The UI never shows an incomplete candidate.
