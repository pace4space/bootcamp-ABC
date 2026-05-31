"""Type contracts for the SQL-RAG query module.

Every stage communicates only through these types. No stage imports from
another stage except via this module.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional


class ChatStatus(str, Enum):
    SUCCESS = "success"
    UNSAFE = "unsafe"
    SQL_ERROR = "sql_error"
    LLM_ERROR = "llm_error"


@dataclass
class ChatTurn:
    """One prior turn of the conversation. role ∈ {'user', 'assistant'}."""
    role: str
    content: str


@dataclass
class GeneratedSQL:
    """Output of generator.py — the raw model proposal, pre-guard."""
    sql: str
    model_id: str
    prompt_version: str
    prompt_text: str
    input_tokens: int
    output_tokens: int
    latency_ms: int


@dataclass
class QueryExecution:
    """Output of executor.py. ok=False carries the DB error; no exception leaks."""
    ok: bool
    columns: list[str] = field(default_factory=list)
    rows: list[dict[str, Any]] = field(default_factory=list)
    row_count: int = 0
    error: Optional[str] = None


@dataclass
class ChatResult:
    """The orchestrator's final return value → mapped to ChatResponse in the router."""
    status: ChatStatus
    answer: str
    sql: str
    execution: QueryExecution
    model_id: str
    run_id: int = -1
    input_tokens: int = 0
    output_tokens: int = 0
    error: Optional[str] = None
    suggestion: Optional[str] = None
