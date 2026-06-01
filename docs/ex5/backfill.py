#!/usr/bin/env python
"""One-time (idempotent) embedding backfill for all candidates + positions.

Usage:
  cd api && .venv/bin/python ../docs/ex5/backfill.py

Requires DATABASE_URL and AWS credentials in the environment (same as the API).
A second run skips everything (all sha256 digests match) — safe to re-run after
any profile edit.
"""
import asyncio
import sys
import os

# Allow imports from the api/app package when run from repo root or docs/ex5/
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "api"))

from app.db import AsyncSessionLocal
from app.embeddings.service import backfill_all
from app.ingest.llm import BedrockClient


async def main() -> None:
    client = BedrockClient()
    async with AsyncSessionLocal() as db:
        report = await backfill_all(db, client)
        await db.commit()

    print(
        f"embedded {report.candidates_embedded} candidates, "
        f"{report.positions_embedded} positions, "
        f"skipped {report.skipped}, "
        f"total_tokens {report.total_tokens}"
    )


if __name__ == "__main__":
    asyncio.run(main())
