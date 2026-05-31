"""SQL generation: natural-language question → validated SQL string via LLM."""
from __future__ import annotations

import asyncio
import os
import time
from pathlib import Path

from app.ingest.llm import BedrockClient
from app.text_utils import load_prompt, strip_fences

from .types import ChatTurn, GeneratedSQL

_PROMPTS_DIR = Path(__file__).parent / "prompts"
_NOVA_LITE = "amazon.nova-lite-v1:0"
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
