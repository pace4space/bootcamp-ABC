# Ex3 — Module 3: LLM Extraction

## Problem

After heuristics have locked in high-confidence fields, use an LLM to extract the
remaining fields that require semantic understanding: full name, headline, skills list,
experience entries (role, company, years, highlights), education, certifications, summary.

## Model Choice: Amazon Nova Lite via Bedrock

**Model ID:** `amazon.nova-lite-v1:0`

**Why Nova Lite?**
- Exercise default: "Nova by default, Nova 2 Lite v1 suggested"
- Optimized for structured extraction: low cost, fast latency, strong JSON adherence
- Bedrock gives native AWS integration (IAM, CloudWatch) — relevant for Ex6+
- Cost observability built into every response (`usage.inputTokens`, `usage.outputTokens`)

**Configurable via environment variables:**
```
BEDROCK_MODEL_ID=amazon.nova-lite-v1:0   (default)
BEDROCK_REGION=us-east-1                 (default)
```

## Why `converse()` vs `invoke_model()`

`converse()` is Bedrock's standardized multi-turn API with explicit `system` / `user`
message separation. This maps directly to our prompt structure (system = rules + schema,
user = document content) and works identically across all Bedrock providers. Swapping
Nova for Claude or Titan only changes `modelId`.

```python
response = client.converse(
    modelId=self.model_id,
    system=[{"text": system_prompt}],
    messages=[{"role": "user", "content": [{"text": user_message}]}],
)
reply   = response["output"]["message"]["content"][0]["text"]
in_tok  = response["usage"]["inputTokens"]
out_tok = response["usage"]["outputTokens"]
```

## Prompt Versioning

Each prompt is a plain text file in `pipeline/prompts/`. Filename = version slug.
Slug is stored in every `extraction_runs.prompt_version` row.

**Rule:** To change a prompt, create `cv-v2.txt`. Never overwrite `cv-v1.txt`.
Old extraction runs still reference the prompt that produced them. The rendered prompt
text is also stored in `extraction_runs.prompt_text` (immutable, self-contained).

**Prompt file format** (split on `[SYSTEM]` / `[USER]` markers):

```
[SYSTEM]
You are a structured HR data extractor. Return ONLY valid JSON.
No markdown fences. No explanation. No commentary.

Rules:
1. Omit optional fields entirely if absent (do not include null values).
2. All years are integers. "Present"/"current" as end_year → omit end_year entirely.
3. Skills: alphabetical order.
4. Experience: preserve CV order (do not sort by year).
5. Pre-extracted HIGH CONFIDENCE fields — use verbatim, do not re-extract:
   {heuristic_hints_json}

Return JSON matching this structure:
{schema_description}

[USER]
{raw_text}
```

`{heuristic_hints_json}` — JSON object of locked heuristic fields.
`{schema_description}` — compact field reference (required vs optional, types).

## Async Wrapper (boto3 is synchronous)

boto3 has no native async. A direct call blocks the FastAPI event loop.

```python
async def call_llm_for_cv(
    doc: RawDocument, hints: HeuristicHints,
    client: BedrockClient, prompt_version: str = "cv-v1"
) -> LLMResponse:
    t0 = time.monotonic()
    loop = asyncio.get_event_loop()
    reply, in_tok, out_tok = await loop.run_in_executor(
        None,
        lambda: client.converse(system_prompt, user_message)
    )
    elapsed_ms = int((time.monotonic() - t0) * 1000)
    return LLMResponse(
        model_id=client.model_id, prompt_version=prompt_version,
        prompt_text=full_prompt, raw_json_str=reply,
        input_tokens=in_tok, output_tokens=out_tok, latency_ms=elapsed_ms
    )
```

## Cost Observability

Every Bedrock response includes token counts → `LLMResponse` → `extraction_runs`.

```sql
-- Total cost by model
SELECT model_id, COUNT(*) runs,
       SUM(input_tokens) total_input, SUM(output_tokens) total_output,
       ROUND(SUM(input_tokens * 0.00006 + output_tokens * 0.00024) / 1000, 4) est_usd
FROM extraction_runs GROUP BY model_id;
```

Nova Lite pricing (2025): ~$0.00006/1K input, ~$0.00024/1K output.
2000-token CV extraction ≈ $0.0006. Full 270 CVs ≈ $0.16.

## Public Interface

```python
# api/app/pipeline/llm.py

class BedrockError(Exception): ...

class BedrockClient:
    def __init__(self, model_id: str = "amazon.nova-lite-v1:0", region: str = "us-east-1")
    def converse(self, system_prompt: str, user_message: str) -> tuple[str, int, int]

async def call_llm_for_cv(
    doc: RawDocument, hints: HeuristicHints, client: BedrockClient,
    prompt_version: str = "cv-v1"
) -> LLMResponse

async def call_llm_for_position(
    doc: RawDocument, hints: HeuristicHints, client: BedrockClient,
    prompt_version: str = "position-v1"
) -> LLMResponse
```

## Interview Talking Point

> "Why store the full rendered prompt in the DB and not just the version slug?"

Because the prompt file may be deleted, renamed, or the repo unavailable at inspection
time. The rendered prompt in the DB is immutable and self-contained. It also captures
the interpolated values (`raw_text`, `heuristic_hints_json`) that the version file alone
cannot reconstruct. Any run can be replayed with `SELECT prompt_text FROM extraction_runs WHERE id = N`.
