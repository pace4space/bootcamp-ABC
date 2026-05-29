# Ex4 — Segment 06: Answer Synthesis (grounded, multi-turn)

**Depends on:** 01 (types), 02 (`answer-v1.txt`), 03 (`text_utils.load_prompt`).
**Blocks:** 07 (orchestrator calls `synthesize_answer`).

## Goal

`query/answerer.py` turns the executor's rows into a natural-language answer that references **only
those rows** (grounding), using the chat history as **real conversation entries** (multi-turn) —
this is the "manipulate context via both system prompt and conversation entries" learning objective.

It requires one **additive** extension to the Bedrock wrapper: a `converse_messages()` method that
accepts a list of turns. The existing `converse(system, user)` (`api/app/pipeline/llm.py:42`) stays
untouched so Ex3 is unaffected.

## Step A — extend `api/app/pipeline/llm.py` (additive only)

Add a method to `BedrockClient` (do not modify `converse`):

```python
def converse_messages(
    self, system_prompt: str, messages: list[dict]
) -> tuple[str, int, int]:
    """Multi-turn variant. messages = [{'role': 'user'|'assistant', 'content': str}, ...].
    Bedrock requires turns to alternate and the first/last to be 'user'."""
    content = [{"role": m["role"], "content": [{"text": m["content"]}]} for m in messages]
    try:
        response = self._client.converse(
            modelId=self.model_id,
            system=[{"text": system_prompt}],
            messages=content,
        )
    except Exception as exc:
        raise BedrockError(str(exc)) from exc
    reply = response["output"]["message"]["content"][0]["text"]
    usage = response.get("usage", {})
    return reply, usage.get("inputTokens", 0), usage.get("outputTokens", 0)
```

## Step B — `api/app/query/answerer.py`

```python
from __future__ import annotations

import asyncio
import json
from pathlib import Path

from app.pipeline.llm import BedrockClient
from app.text_utils import load_prompt

from .types import ChatTurn, QueryExecution

_PROMPTS_DIR = Path(__file__).parent / "prompts"
_MAX_HISTORY_TURNS = 6
_NO_ROWS = "I couldn't find any matching records for that question."


async def synthesize_answer(
    question: str,
    execution: QueryExecution,
    history: list[ChatTurn] | None = None,
    bedrock_client: BedrockClient | None = None,
    prompt_version: str = "answer-v1",
) -> tuple[str, int, int]:
    """Return (answer, input_tokens, output_tokens). Assumes execution.ok is True."""
    # Deterministic, zero-cost grounding for the empty case (predictability NFR).
    if execution.row_count == 0:
        return _NO_ROWS, 0, 0

    client = bedrock_client or BedrockClient()
    system_text, user_template = load_prompt(_PROMPTS_DIR, prompt_version)
    rows_json = json.dumps(execution.rows, ensure_ascii=False)
    user_text = user_template.replace("{question}", question).replace("{rows_json}", rows_json)

    # Conversation entries: prior turns become real message turns; current turn carries the rows.
    messages = [{"role": t.role, "content": t.content} for t in (history or [])[-_MAX_HISTORY_TURNS:]]
    messages.append({"role": "user", "content": user_text})

    loop = asyncio.get_event_loop()
    reply, in_tok, out_tok = await loop.run_in_executor(
        None, lambda: client.converse_messages(system_text, messages)
    )
    return reply.strip(), in_tok, out_tok
```

## Design notes

- **Grounding lives in two places:** the system prompt (`answer-v1.txt`: "use ONLY the rows") and
  the data channel (`{rows_json}` is the *only* candidate/position data the model sees in this call).
  The model is never given the DB; it cannot invent a candidate that isn't in `rows`.
- **Empty-rows short-circuit** is deliberate: it's deterministic, costs zero tokens, and is trivially
  testable. The `answer-v1.txt` empty-rows rule remains a backstop if the path is ever reached with
  rows (it won't be, given this guard).
- **Two LLM calls per turn** (generate SQL in 03, synthesize answer here) is the standard SQL-RAG
  shape. The raw rows always appear in the trace (07/08), so a human can verify the answer against
  the data — predictability is preserved even though phrasing is generated.
- **Conversation entries vs folded history:** SQL generation (03) folds a compact transcript into the
  user text; answer synthesis uses *actual* alternating turns. Showing both techniques is the point of
  the learning objective. Bedrock requires turns to alternate and start/end on `user`; the UI history
  naturally alternates (user→assistant→…), and we append the final user turn.

## Tests (`api/tests/query/test_answerer.py`) — write first

```python
class FakeBedrock:
    model_id = "amazon.nova-lite-v1:0"
    def __init__(self, reply="Two candidates: Alice, Bob."):
        self.reply = reply; self.seen = None
    def converse_messages(self, system, messages):
        self.seen = (system, messages); return self.reply, 20, 9
```

| Test | Assertion |
|------|-----------|
| `test_empty_rows_short_circuits` | `QueryExecution(ok=True, columns=['id'], rows=[], row_count=0)` → returns `_NO_ROWS`, tokens 0/0, and the FakeBedrock was **not** called (`seen is None`). |
| `test_grounded_answer_returned` | rows=[{id:'cv_t01',full_name:'Alice'}] → returns FakeBedrock.reply; tokens 20/9. |
| `test_rows_json_in_user_turn` | the last message in `FakeBedrock.seen[1]` has role 'user' and its content contains `Alice` (the rows_json was interpolated). |
| `test_history_becomes_conversation_entries` | history=[ChatTurn('user','q1'), ChatTurn('assistant','a1')] → `seen[1]` starts with those two turns, then the new user turn (3 messages total). |
| `test_system_prompt_loaded` | `seen[0]` contains the grounding instruction text from `answer-v1.txt` ("only the rows" / "no matching records"). |

## Verification
- `cd api && .venv/bin/pytest tests/query/test_answerer.py -q` → green.
- `.venv/bin/pytest tests/pipeline -q` → Ex3 still green (you only *added* a method to BedrockClient).
