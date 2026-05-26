# Extract Candidate → JSON

> **THROWAWAY — Exercise 1 only.** Replaced by the real pipeline in Exercise 3.

Stub. Full prompt body is written in commit 4 (needs the `Candidate` type from
commit 1 as its output contract).

Planned strategy: paste the exact `Candidate` type as the contract; one worked
example; rules (don't invent fields, unknown optionals → null, preserve original-
language strings incl. Hebrew, deterministic sub-ids, JSON only); bilingual CVs go
to a multimodal model on the **original PDF** (text extraction scrambles Hebrew RTL).
