import pytest

from app.ingest.llm import BedrockError, call_llm_for_cv, call_llm_for_position
from app.ingest.types import DocumentKind, HeuristicHints, ParseFormat, RawDocument

CANNED_CV_JSON = '{"full_name": "Alice Levi", "skills": ["python", "sql"]}'
CANNED_POSITION_JSON = '{"title": "Backend Engineer", "requirements": [{"type": "must", "text": "Python"}]}'


class MockBedrockClient:
    model_id = "test-model"

    def __init__(self, reply: str = CANNED_CV_JSON, raise_error: bool = False) -> None:
        self.reply = reply
        self.raise_error = raise_error
        self.calls: list[tuple[str, str]] = []

    def converse(self, system: str, user: str) -> tuple[str, int, int]:
        self.calls.append((system, user))
        if self.raise_error:
            raise BedrockError("AWS credentials not found")
        return self.reply, 100, 50


def _cv_doc(text: str = "Alice Levi\nalice@example.com\nPython developer") -> RawDocument:
    return RawDocument(
        filename="cv.pdf",
        format=ParseFormat.PDF,
        kind=DocumentKind.CV,
        raw_text=text,
        char_count=len(text),
    )


def _position_doc(text: str = "Hiring Python Backend Engineer in Tel Aviv") -> RawDocument:
    return RawDocument(
        filename="job.txt",
        format=ParseFormat.TXT,
        kind=DocumentKind.POSITION,
        raw_text=text,
        char_count=len(text),
    )


def _no_hints() -> HeuristicHints:
    return HeuristicHints()


def _hints_with_email(email: str = "alice@example.com") -> HeuristicHints:
    return HeuristicHints(email=email)


# ---------------------------------------------------------------------------
# call_llm_for_cv — basic shape
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_cv_returns_llm_response():
    result = await call_llm_for_cv(_cv_doc(), _no_hints(), MockBedrockClient())
    assert result.model_id == "test-model"
    assert result.prompt_version == "cv-v1"
    assert result.raw_json_str == CANNED_CV_JSON
    assert result.input_tokens == 100
    assert result.output_tokens == 50
    assert result.latency_ms >= 0


@pytest.mark.asyncio
async def test_cv_raw_text_in_user_section():
    mock = MockBedrockClient()
    await call_llm_for_cv(_cv_doc("Jane Doe senior developer"), _no_hints(), mock)
    _, user_msg = mock.calls[0]
    assert "Jane Doe senior developer" in user_msg


@pytest.mark.asyncio
async def test_cv_heuristic_hints_in_system_prompt():
    mock = MockBedrockClient()
    await call_llm_for_cv(_cv_doc(), _hints_with_email("alice@example.com"), mock)
    system_msg, _ = mock.calls[0]
    assert "alice@example.com" in system_msg


@pytest.mark.asyncio
async def test_cv_empty_hints_injects_empty_json():
    mock = MockBedrockClient()
    await call_llm_for_cv(_cv_doc(), _no_hints(), mock)
    system_msg, _ = mock.calls[0]
    # All-None hints → injected as {} so the LLM gets no spurious fields
    assert "{}" in system_msg


@pytest.mark.asyncio
async def test_cv_prompt_text_contains_both_sections():
    result = await call_llm_for_cv(_cv_doc(), _no_hints(), MockBedrockClient())
    assert "[SYSTEM]" in result.prompt_text
    assert "[USER]" in result.prompt_text


# ---------------------------------------------------------------------------
# call_llm_for_cv — error path
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_cv_bedrock_error_propagates():
    with pytest.raises(BedrockError, match="AWS credentials"):
        await call_llm_for_cv(_cv_doc(), _no_hints(), MockBedrockClient(raise_error=True))


# ---------------------------------------------------------------------------
# call_llm_for_position — basic shape
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_position_returns_llm_response():
    mock = MockBedrockClient(reply=CANNED_POSITION_JSON)
    result = await call_llm_for_position(_position_doc(), _no_hints(), mock)
    assert result.prompt_version == "position-v1"
    assert result.raw_json_str == CANNED_POSITION_JSON


@pytest.mark.asyncio
async def test_position_raw_text_in_user_section():
    mock = MockBedrockClient(reply=CANNED_POSITION_JSON)
    await call_llm_for_position(_position_doc("Senior DevOps role"), _no_hints(), mock)
    _, user_msg = mock.calls[0]
    assert "Senior DevOps role" in user_msg
