#!/usr/bin/env python
"""Export embedding vectors + metadata for TensorFlow Embedding Projector (UMAP).

Writes two line-aligned files into docs/ex5/:
- vectors.tsv:  one row per record, tab-separated 512 floats, no header.
- metadata.tsv: header row + one data row per record (same order as vectors.tsv).
  Columns: id, kind, label, secondary, top_terms.

Order: all candidates first (sorted by id), then all positions (sorted by id).
This stable order ensures the two files stay aligned if re-exported.

Usage:
  cd api && python ../docs/ex5/export_embeddings.py
"""
import asyncio
import os
import sys
from pathlib import Path

# Allow imports from api/app
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "api"))

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.db import AsyncSessionLocal
from app.models import Candidate, CandidateEmbedding, Position, PositionEmbedding

_OUT_DIR = Path(__file__).parent


async def main() -> None:
    async with AsyncSessionLocal() as db:
        # Load embedding rows
        cand_emb_result = await db.execute(select(CandidateEmbedding))
        cand_embs = {row.candidate_id: row for row in cand_emb_result.scalars().all()}

        pos_emb_result = await db.execute(select(PositionEmbedding))
        pos_embs = {row.position_id: row for row in pos_emb_result.scalars().all()}

        # Load candidate metadata (with skills for top_terms)
        cand_result = await db.execute(
            select(Candidate)
            .options(selectinload(Candidate.skills))
            .where(Candidate.id.in_(cand_embs.keys()))
            .order_by(Candidate.id)
        )
        candidates = cand_result.scalars().all()

        # Load position metadata (with requirements for top_terms)
        pos_result = await db.execute(
            select(Position)
            .options(selectinload(Position.requirements))
            .where(Position.id.in_(pos_embs.keys()))
            .order_by(Position.id)
        )
        positions = pos_result.scalars().all()

    # Compose rows
    vectors_rows: list[str] = []
    metadata_rows: list[tuple[str, str, str, str, str]] = []

    for c in candidates:
        emb = cand_embs[c.id]
        vec_str = "\t".join(f"{v:.8f}" for v in emb.embedding)
        skill_names = ", ".join(s.name for s in sorted(c.skills, key=lambda s: s.sort_order)[:5])
        metadata_rows.append((
            c.id,
            "candidate",
            c.full_name,
            c.headline or "",
            skill_names,
        ))
        vectors_rows.append(vec_str)

    for p in positions:
        emb = pos_embs[p.id]
        vec_str = "\t".join(f"{v:.8f}" for v in emb.embedding)
        must_haves = ", ".join(
            r.text for r in sorted(p.requirements, key=lambda r: r.sort_order)
            if r.type == "must_have"
        )[:80]
        metadata_rows.append((
            p.id,
            "position",
            p.title,
            p.seniority or "",
            must_haves,
        ))
        vectors_rows.append(vec_str)

    # Write files
    vectors_path = _OUT_DIR / "vectors.tsv"
    metadata_path = _OUT_DIR / "metadata.tsv"

    vectors_path.write_text("\n".join(vectors_rows) + "\n", encoding="utf-8")

    meta_lines = ["id\tkind\tlabel\tsecondary\ttop_terms"]
    for row in metadata_rows:
        meta_lines.append("\t".join(row))
    metadata_path.write_text("\n".join(meta_lines) + "\n", encoding="utf-8")

    total = len(vectors_rows)
    n_candidates = len(candidates)
    n_positions = len(positions)
    print(
        f"Exported {total} rows ({n_candidates} candidates, {n_positions} positions)\n"
        f"  vectors.tsv  → {vectors_path}\n"
        f"  metadata.tsv → {metadata_path}"
    )
    assert len(vectors_rows) == len(metadata_rows), "line count mismatch!"


if __name__ == "__main__":
    asyncio.run(main())
