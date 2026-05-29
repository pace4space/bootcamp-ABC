# Ex4 — Segment 02: Schema Context & Prompts

**Depends on:** nothing (pure text files). **Blocks:** 03 (generator loads `sql-v1.txt`),
06 (answerer loads `answer-v1.txt`).

## Goal

Author the two versioned prompt files the LLM uses. The system prompt for SQL generation
carries a **curated schema contract** (an allowlist of tables/columns), the safety rules, and
**few-shot examples** that cover the four required question shapes.

Mirror the Ex3 prompt convention exactly: a plain `.txt` file split on `[SYSTEM]` / `[USER]`
markers, loaded by the same loader logic as `api/app/pipeline/llm.py:23` (`_load_prompt`).
Filename = version slug, stored in `query_runs.prompt_version`. To change a prompt, create
`sql-v2.txt`; never overwrite `sql-v1.txt`.

## Design decision: the schema in the prompt is an ALLOWLIST, not a dump

Expose ONLY the tables the chat is allowed to reason about: `candidates`, `candidate_skills`,
`candidate_experience`, `candidate_education`, `candidate_certifications`, `candidate_languages`,
`positions`, `position_requirements`, `applications`.

**Deliberately omit** `users` (has `password_hash`), `raw_documents`, `extraction_runs`,
`query_runs`. The model cannot reference a table it was never shown — this is a *fourth* safety
layer that complements the guard (04) and the read-only transaction (05). Even though execution
is read-only, there is no reason to let generated SQL touch the credentials table.

## Design decision: the "department" gap (honesty over invention)

The first required question is *"list open position counts by department"* — but `positions`
has **no `department` column** (columns are `title, status, location, seniority, salary_range,
hiring_manager_email`). We do **not** add one (schema changes are out of scope). Instead the
system prompt instructs:

> If the user groups by or filters on a concept with no matching column, choose the closest
> available column, and make the substitution explicit so the answer can state it.

The few-shot teaches `GROUP BY seniority` as the "counts by category" pattern. For "by
department," the model will fall back to the nearest column (e.g. `seniority` or `location`),
and the answerer (06) will say *"grouped by seniority (no department field exists)."* Grounded
and honest — a teaching moment, not a bug.

## Exact schema contract (copy column names verbatim from `api/app/models.py`)

```
candidates(id, full_name, headline, status['Active'|'Archived'], email, phone, city,
           linkedin_url, github_url, summary)
candidate_skills(id, candidate_id→candidates.id, name)
candidate_experience(id, candidate_id→candidates.id, role, company, location,
                     start_year, end_year[NULL = present], highlights)
candidate_education(id, candidate_id→candidates.id, degree, institution, start_year, end_year)
candidate_certifications(id, candidate_id→candidates.id, name, year)
candidate_languages(id, candidate_id→candidates.id, name, proficiency)
positions(id, title, status['Open'|'Closed'], hiring_manager_email, description,
          location, seniority, salary_range)
position_requirements(id, position_id→positions.id, type['must_have'|'nice_to_have'], text)
applications(id, candidate_id→candidates.id, position_id→positions.id,
             status['Waiting'|'Rejected'|'Screening'|'Offer'|'Hired'|NULL])
```

## File: `api/app/query/prompts/sql-v1.txt`

```
[SYSTEM]
You are a PostgreSQL query generator for an HR database. Given a question, return EXACTLY ONE
read-only SQL SELECT statement that answers it. Return ONLY the SQL — no markdown fences, no
explanation, no commentary, no trailing semicolon.

Hard rules:
1. SELECT queries only. Never INSERT, UPDATE, DELETE, DROP, ALTER, CREATE, GRANT, or any write.
2. One statement only. No semicolons, no multiple statements.
3. Use only the tables and columns listed below. Never reference any other table.
4. For case-insensitive text matching use ILIKE with % wildcards (e.g. name ILIKE '%kubernetes%').
5. "Open positions" → positions.status = 'Open'. "Active candidates" → candidates.status = 'Active'.
6. If the user groups by or filters on a concept that has no matching column, pick the closest
   available column (so the answer can state the substitution). Do not invent columns.
7. Prefer explicit JOINs. Cap large result sets with LIMIT 100 unless the user asks for a count.

Schema:
candidates(id, full_name, headline, status, email, phone, city, linkedin_url, github_url, summary)
candidate_skills(id, candidate_id, name)
candidate_experience(id, candidate_id, role, company, location, start_year, end_year, highlights)
candidate_education(id, candidate_id, degree, institution, start_year, end_year)
candidate_certifications(id, candidate_id, name, year)
candidate_languages(id, candidate_id, name, proficiency)
positions(id, title, status, hiring_manager_email, description, location, seniority, salary_range)
position_requirements(id, position_id, type, text)
applications(id, candidate_id, position_id, status)

Examples:
Q: list open position counts by department
A: SELECT seniority, COUNT(*) AS position_count FROM positions WHERE status = 'Open' GROUP BY seniority ORDER BY position_count DESC

Q: which positions do not have any candidate
A: SELECT p.id, p.title FROM positions p LEFT JOIN applications a ON a.position_id = p.id WHERE a.id IS NULL ORDER BY p.title

Q: which positions have more than 2 candidates
A: SELECT p.id, p.title, COUNT(a.id) AS candidate_count FROM positions p JOIN applications a ON a.position_id = p.id GROUP BY p.id, p.title HAVING COUNT(a.id) > 2 ORDER BY candidate_count DESC

Q: list all candidates with kubernetes experience
A: SELECT DISTINCT c.id, c.full_name FROM candidates c JOIN candidate_skills s ON s.candidate_id = c.id WHERE s.name ILIKE '%kubernetes%' ORDER BY c.full_name

[USER]
{question}
```

**Implementer notes**
- The `{question}` placeholder is the only interpolation the generator must do for the single-turn
  case. For multi-turn, segment 03 specifies how prior turns are folded in (a short
  `Previous turns:` preamble before the question) — keep that logic in `generator.py`, not the file.
- Few-shot answers intentionally show the four shapes the rubric tests: GROUP BY + COUNT,
  LEFT JOIN … IS NULL (anti-join), GROUP BY … HAVING (threshold; teaches WHERE vs HAVING),
  JOIN + ILIKE (skill search). These map 1:1 to the four required questions.

## File: `api/app/query/prompts/answer-v1.txt`

```
[SYSTEM]
You are an HR data assistant. Answer the user's question using ONLY the rows provided below.

Rules:
1. Use only the data in "Retrieved rows". Never invent candidates, positions, counts, or names.
2. If "Retrieved rows" is empty, say plainly that no matching records were found. Do not guess.
3. Be concise. For lists, name the items. For counts/aggregates, state the numbers.
4. If a grouping column was substituted for a term the user used (e.g. grouped by seniority when
   they said "department"), say so in one short clause.
5. Do not mention SQL, tables, or columns by name unless it aids clarity. Speak in HR terms.

[USER]
Question: {question}

Retrieved rows (JSON):
{rows_json}
```

**Implementer notes**
- `{rows_json}` is `json.dumps(execution.rows, ensure_ascii=False)` (capped list from the executor).
- The answerer (06) passes prior turns as real conversation entries (multi-turn), NOT folded into
  this user text — that is the "manipulate context via conversation entries" learning objective.
  This file holds only the current turn's question + rows.

## Tests
No standalone test file for prompts (they are data). They are exercised by:
- 03 `test_generator` — asserts the loader parses `[SYSTEM]`/`[USER]` and `{question}` interpolates.
- 06 `test_answerer` — asserts `{rows_json}` interpolates and the empty-rows path produces a
  "no matching records" answer.
- 09 live demo — the four questions produce sensible SQL against real Postgres.

## Verification
- Files exist at `api/app/query/prompts/sql-v1.txt` and `answer-v1.txt`.
- The existing `_load_prompt`-style split (`text.split("[USER]", 1)`, strip `[SYSTEM]`) parses both
  without error (segment 03 wires a `query`-local loader or reuses the pipeline one — see 03).
