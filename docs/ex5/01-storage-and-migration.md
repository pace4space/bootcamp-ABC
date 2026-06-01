# Segment 01 — Storage & Migration (pgvector tables + the SQLite seam)

**Depends on:** nothing. **Blocks:** every other segment. **Do this first and prove the suite stays green.**

## Purpose

Stand up the vector storage with **zero blast radius** on the core schema. Two dedicated 1:1 tables hold
the embeddings; the Postgres-only `vector` type degrades to JSON under SQLite so the existing 100+ tests
keep passing. This segment is pure plumbing — no embedding generation yet.

## The critical risk (read before coding)

Tests run on `sqlite+aiosqlite` and build the schema with `Base.metadata.create_all` (`conftest.py:53`),
not Alembic. SQLite has no `vector` type. If the column is a bare `Vector(512)`, `create_all` throws at
fixture setup and **every test fails**. The fix mirrors the existing ARRAY→JSON handling
(`conftest.py:45-48`), but done *in the model* via `with_variant` so no per-test patch is needed:

```python
from pgvector.sqlalchemy import Vector
from sqlalchemy import JSON

EMBEDDING_DIM = 512
# real `vector(512)` on Postgres; JSON list-of-floats on SQLite
EmbeddingType = Vector(EMBEDDING_DIM).with_variant(JSON(), "sqlite")
```

`create_all` then builds a JSON column under SQLite and a `vector` column under Postgres — both round-trip a
`list[float]`. Verify this **before** writing any other segment.

## Public artifacts

### 1. ORM models (`api/app/models.py`, append after `QueryRun` at `models.py:419`)

Mirror the `QueryRun` style (scalar columns, explicit nullability). Both tables identical except the PK/FK name.

```python
class CandidateEmbedding(Base):
    __tablename__ = "candidate_embeddings"
    candidate_id: Mapped[str] = mapped_column(
        String(20), ForeignKey("candidates.id", ondelete="CASCADE"), primary_key=True
    )
    embedding: Mapped[list[float]] = mapped_column(EmbeddingType, nullable=False)
    embedding_text: Mapped[str] = mapped_column(Text, nullable=False)
    embedding_model: Mapped[str] = mapped_column(Text, nullable=False)
    text_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), nullable=False)

class PositionEmbedding(Base):
    __tablename__ = "position_embeddings"
    position_id: Mapped[str] = mapped_column(
        String(20), ForeignKey("positions.id", ondelete="CASCADE"), primary_key=True
    )
    # embedding / embedding_text / embedding_model / text_sha256 / updated_at  (identical)
```

- `EMBEDDING_DIM = 512` and `EmbeddingType` defined at module top near the other type imports
  (`ARRAY` is imported at `models.py:23` — add the `pgvector`/`JSON` imports alongside).
- **No `server_default="now()"`** on `updated_at` — the service supplies `datetime.now(timezone.utc)`
  explicitly (the SQLite lesson). Keep it `nullable=False` and always write it.
- FK `ondelete="CASCADE"` so re-ingest / candidate deletion cleans up the embedding row automatically.

### 2. Alembic migration (`api/alembic/versions/0004_embeddings.py`, `down_revision = "0003"`)

```python
def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    op.create_table(
        "candidate_embeddings",
        sa.Column("candidate_id", sa.String(20),
                  sa.ForeignKey("candidates.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("embedding", Vector(512), nullable=False),   # pgvector type in the migration
        sa.Column("embedding_text", sa.Text(), nullable=False),
        sa.Column("embedding_model", sa.Text(), nullable=False),
        sa.Column("text_sha256", sa.String(64), nullable=False),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), nullable=False),
    )
    op.create_table("position_embeddings", ...)  # identical with position_id FK -> positions.id

def downgrade() -> None:
    op.drop_table("position_embeddings")
    op.drop_table("candidate_embeddings")
    # leave the `vector` extension in place — dropping it could break other objects
```

- **No ANN index.** Document inline: at this scale exact cosine via sequential scan is sub-ms; when
  N > ~10k add `op.execute("CREATE INDEX ... USING hnsw (embedding vector_cosine_ops)")`.
- Guard `CREATE EXTENSION` to Postgres so a stray SQLite alembic run doesn't choke.

### 3. Infra / deps
- **`docker-compose.yml`:** change `db.image` from `postgres:16-alpine` to `pgvector/pgvector:pg16`.
  Same env, volume (`pgdata`), and `pg_isready` healthcheck. Note in a comment: the extension comes from
  migration `0004`, not the image — after the swap run `alembic upgrade head`.
- **`api/requirements.txt`:** add `pgvector` (provides `pgvector.sqlalchemy.Vector` + asyncpg adapter).

### 4. Register models in tests (`api/tests/conftest.py`)
- Add `CandidateEmbedding, PositionEmbedding` to the `from app.models import (...)` block at `conftest.py:25`
  so `create_all` builds the tables. **No new ARRAY-style patch is needed** — `with_variant(JSON, "sqlite")`
  handles the vector column itself. (If you instead defined a bare `Vector`, you'd be forced to patch here —
  don't; the variant is cleaner.)

## Reused utilities
- Model style + `server_default` discipline — `QueryRun` at `api/app/models.py:419`.
- ARRAY→JSON precedent (why `with_variant` works) — `api/tests/conftest.py:45-48`.
- Migration shape — `api/alembic/versions/0003_query_runs.py`.

## Tests (`api/tests/embeddings/test_models.py`) — test-first
1. `test_candidate_embedding_roundtrip` — insert a `CandidateEmbedding` with a 512-float list (seeded
   candidate id), commit, re-query → `embedding` equals the list; `text_sha256`/`embedding_text` persisted.
2. `test_position_embedding_roundtrip` — same for `PositionEmbedding`.
3. `test_cascade_delete` — delete a candidate → its `candidate_embeddings` row is gone.
4. `test_existing_suite_green` — implicit: run the full `pytest -q`; the 100+ existing tests still pass
   (proves the variant didn't break `create_all`).

## Demo / verify
- `cd api && .venv/bin/pytest -q tests/embeddings/test_models.py` green; full `pytest -q` green.
- On a pgvector Postgres: `docker compose up -d db` (new image) → `alembic upgrade head` → both tables +
  the `vector` extension exist (`\dx` shows `vector`; `\d candidate_embeddings` shows `embedding | vector(512)`).
