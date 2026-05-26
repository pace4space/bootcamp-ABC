# Prompts (Exercise 1)

> **THROWAWAY — Exercise 1 only.** These prompts do semi-manual extraction of the
> source CVs/job emails into schema-valid JSON. They are **replaced by a real LLM
> extraction pipeline in Exercise 3** and should not be carried forward as code.

Prompts are versioned here (not pasted into chat) so the extraction is reproducible
and reviewable.

- `extract-candidate.md` — one CV (PDF/DOCX) → one `Candidate` JSON record.
- `extract-position.md` — one job email (`.txt`) → one `Position` JSON record.

The output contract is the `Candidate` / `Position` type in `src/lib/types.ts`.
Full prompt bodies are written in **commit 4**, once the types (commit 1) exist.
