# Segment 06 — Match Explainer (grounded "why it fits")

**Depends on:** 02 (field selection), 03 (`converse`). **Blocks:** 07 (candidate-view endpoint).

## Purpose

For the candidate→positions view, generate a short, **grounded** explanation of why a position fits the
candidate. Reuses the existing text-generation path (`BedrockClient.converse`) with a versioned,
anti-hallucination prompt. The explainer is the Ex5 analog of Ex4's grounded answerer: it may cite **only**
the candidate skills/experience and position requirements it is given.

## Public artifacts

### `api/app/embeddings/explainer.py`
```python
_PROMPTS_DIR = Path(__file__).parent / "prompts"

async def explain_match(candidate, position, score: float,
                        client: BedrockClient | None = None,
                        prompt_version: str = "explain-v1") -> tuple[str, int, int]:
    """Return (explanation, input_tokens, output_tokens). 1–2 sentences, grounded in the
    structured fields below. Runs the sync client via run_in_executor."""
```

- Load the prompt with the shared loader: `load_prompt(_PROMPTS_DIR, prompt_version)` (`text_utils.py:16`).
- Build a **compact structured payload** (not raw CV prose) — exactly the field set the embedding builder used,
  so the explanation is grounded in what was actually matched:
  - candidate: `headline`, `skills` (names), `experience` (role @ company) — no PII.
  - position: `title`, `must_have` + `nice_to_have` requirement texts.
- Render into the `[USER]` template as JSON or a tight key:value block; call `client.converse(system, user)`
  via `loop.run_in_executor` (the `_call_llm` pattern, `llm.py:91-96`). Optionally `strip_fences` the reply.

### `api/app/embeddings/prompts/explain-v1.txt` (`[SYSTEM]` / `[USER]` split)
System prompt rules (the grounding contract):
- "You explain why a job position fits a candidate, for a recruiter. Use ONLY the provided candidate skills/
  experience and position requirements. Cite the specific overlapping skill or requirement by name."
- "If you cannot find a concrete overlap, say the match is weak and why — do NOT invent skills, employers, or
  requirements that are not in the input."
- "One or two sentences. No preamble, no markdown."

User template: `{candidate_json}` + `{position_json}` (+ optional `{score}` for hedging language).

## Why grounding is tested via the prompt, not the output
The model output is non-deterministic, but the **contract** is deterministic: the prompt must contain the
candidate's skills and the position's requirements, and must forbid invention. Tests assert the *rendered
prompt* (grounding contract) + that a mocked reply is returned with token counts — not the model's words.

## Cost shape
- Called only on the candidate view, capped at `top_n` (≤3) short generations. The endpoint (segment 07)
  fires them with `asyncio.gather`. The position view never calls this — scores only.

## Reused utilities
- `BedrockClient.converse` — `api/app/ingest/llm.py:42`.
- `load_prompt(prompts_dir, version)` + `strip_fences` — `api/app/text_utils.py:16,8`.
- Prompt `[SYSTEM]`/`[USER]` file convention — `api/app/chat/prompts/answer-v1.txt` (Ex4).
- `run_in_executor` for the sync client — `api/app/ingest/llm.py:91-96`.
- `MockBedrockClient` (canned reply) — `api/tests/ingest/test_llm.py`.

## Tests (`api/tests/embeddings/test_explainer.py`) — test-first
1. `test_prompt_contains_candidate_skills` — rendered user prompt includes the candidate's skill names.
2. `test_prompt_contains_position_requirements` — rendered prompt includes the position's must-have texts.
3. `test_system_prompt_forbids_invention` — system text contains the anti-hallucination instruction.
4. `test_returns_explanation_and_tokens` — with `MockBedrockClient`, returns the canned reply + (in,out) tokens.
5. `test_no_overlap_still_returns_sentence` — a candidate/position with no shared terms still yields a non-empty
   (weak-match) explanation (the model is asked to say "weak", not to error).

## Demo / verify
- `cd api && .venv/bin/pytest -q tests/embeddings/test_explainer.py` green.
- Live: `explain_match(candidate, position, 0.71)` returns a sentence that names a real shared skill/requirement
  from the inputs — record one in the validation checklist as a hallucination spot-check.
