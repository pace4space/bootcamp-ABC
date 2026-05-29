# Ex4 — Segment 03: SQL Generation

**Depends on:** 01 (types), 02 (`sql-v1.txt`). **Blocks:** 07 (orchestrator calls `generate_sql`).

## Goal

`query/generator.py` turns a natural-language question (+ optional history) into a candidate SQL
string by calling the LLM with the schema-bearing system prompt. Reuse the Ex3 Bedrock wrapper
and fence-stripper — write no new LLM client, no new regex.

This segment also performs a **tiny shared refactor**: extract `strip_fences` (and a prompt
loader) into `api/app/text_utils.py` so both the pipeline and the query module use one copy.

## Step A — create `api/app/text_utils.py`

Move the two reusable, dependency-free helpers here.

```python
"""Small text helpers shared by the extraction pipeline and the query module."""
from __future__ import annotations

import re
from pathlib import Path


def strip_fences(raw: str) -> str:
    """Strip markdown code fences that LLMs emit despite 'no fences' instructions."""
    raw = raw.strip()
    raw = re.sub(r'^```(?:json|sql)?\s*', '', raw)   # note: also strips ```sql for SQL output
    raw = re.sub(r'\s*```$', '', raw)
    return raw.strip()


def load_prompt(prompts_dir: Path, version: str) -> tuple[str, str]:
    """Return (system_text, user_template) from a versioned [SYSTEM]/[USER] prompt file.

    Mirrors api/app/pipeline/llm.py:_load_prompt, generalized over the prompts dir.
    """
    text = (prompts_dir / f"{version}.txt").read_text(encoding="utf-8")
    parts = text.split("[USER]", 1)
    system_text = parts[0].replace("[SYSTEM]", "").strip()
    user_template = parts[1].strip() if len(parts) > 1 else "{question}"
    return system_text, user_template
```

**Shim so Ex3 stays green (minimal churn):** in `api/app/pipeline/validator.py`, replace the
`_strip_fences` *definition* (lines 32–37) with a re-export alias so every existing call site
keeps working:

```python
from app.text_utils import strip_fences as _strip_fences
```

Remove the now-unused `import re` from validator.py **only if** nothing else there uses it
(grep first — it may still be used by other helpers). Leave `pipeline/llm.py:_load_prompt` as-is
(don't refactor the pipeline loader; the query module uses the new `text_utils.load_prompt`).

## Step B — `api/app/query/generator.py`

```python
from __future__ import annotations

import asyncio
import os
import time
from pathlib import Path

from app.pipeline.llm import BedrockClient   # reuse the model-agnostic converse() wrapper
from app.text_utils import load_prompt, strip_fences

from .types import ChatTurn, GeneratedSQL

_PROMPTS_DIR = Path(__file__).parent / "prompts"
_NOVA_LITE = "amazon.nova-lite-v1:0"        # default (Bedrock billing; cheap)
# _CLAUDE = "us.anthropic.claude-..."       # one-line swap; NOT surfaced in UI (see 00)
_DEFAULT_MODEL = os.getenv("BEDROCK_MODEL_ID", _NOVA_LITE)
_MAX_HISTORY_TURNS = 6


def _render_user(question: str, history: list[ChatTurn]) -> str:
    """Fold a short transcript before the question so references like 'those' resolve."""
    recent = history[-_MAX_HISTORY_TURNS:]
    if not recent:
        return question
    lines = [f"{t.role}: {t.content}" for t in recent]
    return "Previous turns:\n" + "\n".join(lines) + f"\n\nCurrent question: {question}"


async def generate_sql(
    question: str,
    history: list[ChatTurn] | None = None,
    bedrock_client: BedrockClient | None = None,
    model: str | None = None,
    prompt_version: str = "sql-v1",
) -> GeneratedSQL:
    client = bedrock_client or BedrockClient(model_id=model or _DEFAULT_MODEL)
    system_text, user_template = load_prompt(_PROMPTS_DIR, prompt_version)

    user_rendered = user_template.replace("{question}", _render_user(question, history or []))

    loop = asyncio.get_event_loop()
    start = time.monotonic()
    reply, in_tok, out_tok = await loop.run_in_executor(
        None, lambda: client.converse(system_text, user_rendered)
    )
    latency_ms = int((time.monotonic() - start) * 1000)

    return GeneratedSQL(
        sql=strip_fences(reply),
        model_id=client.model_id,
        prompt_version=prompt_version,
        prompt_text=f"[SYSTEM]\n{system_text}\n\n[USER]\n{user_rendered}",
        input_tokens=in_tok,
        output_tokens=out_tok,
        latency_ms=latency_ms,
    )
```

**Design notes**
- **Reuses, does not rebuild:** `BedrockClient.converse` (`api/app/pipeline/llm.py:33`) is the
  same call Ex3 uses; `run_in_executor` keeps the sync boto3 call off the event loop (same pattern
  as `pipeline/llm.py:_call_llm`).
- **Model routing:** `model` param → `BedrockClient(model_id=...)`. `converse()` is provider-agnostic,
  so passing a Claude inference-profile id is the entire "comparison" feature. Default stays Nova.
- **Single-turn SQL gen, multi-turn answer:** SQL generation folds history into the user text
  (cheap, deterministic). The *answer* step (06) uses real conversation entries. This split is
  intentional — SQL gen benefits from a compact reference, not a full chat replay.
- **Fence-stripping matters:** Nova non-deterministically wraps output in ```sql fences despite the
  prompt; `strip_fences` (now also matching ```sql) removes them before the guard sees the string.
- `generated.sql` is **unvalidated** — the guard (04) is the only thing that may bless it.

## Tests (`api/tests/query/test_generator.py`) — write first

Use a fake client so no network/credentials are needed (same approach as Ex3's `test_llm.py`).

```python
class FakeBedrock:
    model_id = "amazon.nova-lite-v1:0"
    def __init__(self, reply): self._reply = reply
    def converse(self, system, user): return self._reply, 11, 7
```

| Test | Assertion |
|------|-----------|
| `test_strips_sql_fences` | client returns ```\n```sql\nSELECT 1\n```\n``` → `generated.sql == "SELECT 1"`. |
| `test_passes_through_plain_sql` | reply `"SELECT id FROM candidates"` → `sql` equals it; tokens 11/7 captured. |
| `test_prompt_text_contains_system_and_user` | `generated.prompt_text` contains `[SYSTEM]` and the question. |
| `test_history_folded_into_user` | with `history=[ChatTurn('user','show open positions'), ChatTurn('assistant','...')]`, the captured `user` arg (spy the FakeBedrock) contains `Previous turns:` and `Current question:`. |
| `test_model_param_sets_model_id` | inject client built from `model="x"`? Simpler: assert `generate_sql(..., bedrock_client=FakeBedrock(...))` returns `model_id` from the client. |

(Inject `FakeBedrock` via the `bedrock_client=` param — no monkeypatch needed at this layer. The
monkeypatch-the-imported-name technique is only needed for the endpoint test in 09.)

## Verification
- `cd api && .venv/bin/pytest tests/query/test_generator.py -q` → green.
- `cd api && .venv/bin/pytest tests/pipeline/test_validator.py -q` → still green (the `strip_fences`
  shim didn't break Ex3). Run the full suite too: `.venv/bin/pytest -q`.
