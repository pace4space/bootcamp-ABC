"""Small text helpers shared by the extraction pipeline and the query module."""
from __future__ import annotations

import re
from pathlib import Path


def strip_fences(raw: str) -> str:
    """Strip markdown code fences that LLMs emit despite 'no fences' instructions."""
    raw = raw.strip()
    raw = re.sub(r'^```(?:json|sql)?\s*', '', raw)
    raw = re.sub(r'\s*```$', '', raw)
    return raw.strip()


def load_prompt(prompts_dir: Path, version: str) -> tuple[str, str]:
    """Return (system_text, user_template) from a versioned [SYSTEM]/[USER] prompt file."""
    text = (prompts_dir / f"{version}.txt").read_text(encoding="utf-8")
    parts = text.split("[USER]", 1)
    system_text = parts[0].replace("[SYSTEM]", "").strip()
    user_template = parts[1].strip() if len(parts) > 1 else "{question}"
    return system_text, user_template
