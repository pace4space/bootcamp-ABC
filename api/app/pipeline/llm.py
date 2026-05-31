from __future__ import annotations

import asyncio
import json
import os
import time
from dataclasses import asdict
from pathlib import Path

import boto3

from .types import HeuristicHints, LLMResponse, RawDocument

_PROMPTS_DIR = Path(__file__).parent / "prompts"
_DEFAULT_MODEL_ID = os.getenv("BEDROCK_MODEL_ID", "amazon.nova-lite-v1:0")
_DEFAULT_REGION = os.getenv("BEDROCK_REGION", "us-east-1")


class BedrockError(Exception):
    """Raised when the Bedrock API call fails."""


def _load_prompt(version: str) -> tuple[str, str]:
    """Return (system_text, user_template) parsed from a versioned prompt file."""
    path = _PROMPTS_DIR / f"{version}.txt"
    text = path.read_text(encoding="utf-8")
    parts = text.split("[USER]", 1)
    system_text = parts[0].replace("[SYSTEM]", "").strip()
    user_template = parts[1].strip() if len(parts) > 1 else "{raw_text}"
    return system_text, user_template


class BedrockClient:
    def __init__(
        self,
        model_id: str = _DEFAULT_MODEL_ID,
        region: str = _DEFAULT_REGION,
    ) -> None:
        self.model_id = model_id
        self._client = boto3.client("bedrock-runtime", region_name=region)

    def converse(self, system_prompt: str, user_message: str) -> tuple[str, int, int]:
        """Synchronous Bedrock call. Returns (reply_text, input_tokens, output_tokens)."""
        try:
            response = self._client.converse(
                modelId=self.model_id,
                system=[{"text": system_prompt}],
                messages=[{"role": "user", "content": [{"text": user_message}]}],
            )
        except Exception as exc:
            raise BedrockError(str(exc)) from exc
        reply = response["output"]["message"]["content"][0]["text"]
        usage = response.get("usage", {})
        return reply, usage.get("inputTokens", 0), usage.get("outputTokens", 0)

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


async def _call_llm(
    doc: RawDocument,
    hints: HeuristicHints,
    prompt_version: str,
    bedrock_client: BedrockClient | None,
) -> LLMResponse:
    client = bedrock_client or BedrockClient()
    system_text, user_template = _load_prompt(prompt_version)

    hints_json = json.dumps(
        {k: v for k, v in asdict(hints).items() if v is not None},
        ensure_ascii=False,
    )
    system_rendered = system_text.replace("{heuristic_hints_json}", hints_json)
    user_rendered = user_template.replace("{raw_text}", doc.raw_text)

    loop = asyncio.get_event_loop()
    start = time.monotonic()
    reply, in_tok, out_tok = await loop.run_in_executor(
        None,
        lambda: client.converse(system_rendered, user_rendered),
    )
    latency_ms = int((time.monotonic() - start) * 1000)

    return LLMResponse(
        model_id=client.model_id,
        prompt_version=prompt_version,
        prompt_text=f"[SYSTEM]\n{system_rendered}\n\n[USER]\n{user_rendered}",
        raw_json_str=reply,
        input_tokens=in_tok,
        output_tokens=out_tok,
        latency_ms=latency_ms,
    )


async def call_llm_for_cv(
    doc: RawDocument,
    hints: HeuristicHints,
    bedrock_client: BedrockClient | None = None,
    prompt_version: str = "cv-v1",
) -> LLMResponse:
    return await _call_llm(doc, hints, prompt_version, bedrock_client)


async def call_llm_for_position(
    doc: RawDocument,
    hints: HeuristicHints,
    bedrock_client: BedrockClient | None = None,
    prompt_version: str = "position-v1",
) -> LLMResponse:
    return await _call_llm(doc, hints, prompt_version, bedrock_client)
