# Extract Position → JSON

> **THROWAWAY — Exercise 1 only.** Replaced by the real pipeline in Exercise 3.

Stub. Full prompt body is written in commit 4 (needs the `Position` type from
commit 1 as its output contract).

Planned strategy: paste the exact `Position` type as the contract; normalize the
hiring-manager email body into `description` + `requirements{mustHave,niceToHave}`;
take `title`, `hiringManagerEmail`, and candidate links from `jobs.xlsx` (the join
table) rather than guessing from the email subject; JSON only.
