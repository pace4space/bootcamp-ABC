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
