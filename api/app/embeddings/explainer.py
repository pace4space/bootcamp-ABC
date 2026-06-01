"""Match explainer: grounded 1–2 sentence explanation of why a position fits a candidate.

Reuses BedrockClient.converse with a versioned anti-hallucination prompt.
Grounding contract: may cite ONLY the candidate skills/experience and position
requirements supplied; when no concrete overlap exists, say the match is weak.

Cost shape: called at most top_n (≤3) times per candidate view, fired with
asyncio.gather in the endpoint.  The position view never calls this — scores only.
"""
from __future__ import annotations

import asyncio
import json
from pathlib import Path

from app.ingest.llm import BedrockClient
from app.text_utils import load_prompt, strip_fences

_PROMPTS_DIR = Path(__file__).parent / "prompts"


async def explain_match(
    candidate,
    position,
    score: float,
    client: BedrockClient | None = None,
    prompt_version: str = "explain-v1",
) -> tuple[str, int, int]:
    """Return (explanation, input_tokens, output_tokens).

    Builds a compact structured payload from the candidate and position fields
    that were also used for embedding — no PII, no noise.
    """
    system_text, user_template = load_prompt(_PROMPTS_DIR, prompt_version)

    candidate_data = {
        "headline": candidate.headline,
        "skills": [s.name for s in (candidate.skills or [])],
        "experience": [
            {"role": e.role, "company": e.company}
            for e in sorted(candidate.experience or [], key=lambda e: -e.start_year)
        ],
    }
    position_data = {
        "title": position.title,
        "must_have": [
            r.text for r in (position.requirements or []) if r.type == "must_have"
        ],
        "nice_to_have": [
            r.text for r in (position.requirements or []) if r.type == "nice_to_have"
        ],
    }

    user_message = (
        user_template
        .replace("{candidate_json}", json.dumps(candidate_data, ensure_ascii=False))
        .replace("{position_json}", json.dumps(position_data, ensure_ascii=False))
        .replace("{score}", f"{score:.3f}")
    )

    _client = client or BedrockClient()
    loop = asyncio.get_event_loop()
    reply, in_tok, out_tok = await loop.run_in_executor(
        None, lambda: _client.converse(system_text, user_message)
    )
    return strip_fences(reply), in_tok, out_tok
