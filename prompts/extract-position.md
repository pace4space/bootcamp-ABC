# Prompt: Job Email → Position JSON

> **THROWAWAY — Exercise 1 only.**
> Replaced by the real LLM extraction pipeline in Exercise 3.

---

## Your job

You are given:
1. A job email (plain text, `From/To/Subject` + body) from `CVsJobs/jobs/`.
2. A row from `jobs.xlsx` with the normalized title and hiring-manager email.

Output a **single valid JSON object** conforming exactly to the `Position` type below.
Output **only** the JSON — no explanation, no fences, nothing else.

---

## Output contract (copy of `src/lib/types.ts`)

```typescript
type PositionStatus = "Open" | "Closed"

type SourceEmail = {
  fileName: string   // e.g. "job_001_senior_devops.txt"
  path: string       // "/jobs/<fileName>"
}

type Position = {
  id: string              // GIVEN
  title: string           // GIVEN from jobs.xlsx — do NOT use the email Subject
  status: PositionStatus  // GIVEN
  hiringManagerEmail: string  // GIVEN from jobs.xlsx From: field
  description: string     // 2–4 sentence summary of the role from the email body
  requirements?: {
    mustHave: string[]    // extract concrete requirements (years, tools, certs)
    niceToHave: string[]  // extract "nice to have" / "bonus" items
  }
  location?: string       // city + work arrangement if stated
  seniority?: string      // "Junior" | "Mid" | "Senior" | "Lead" | "Staff"
  salaryRange?: string    // keep original currency + numbers if stated
  sourceDocument: SourceEmail  // GIVEN
}
```

---

## Rules

1. **`id`, `title`, `status`, `hiringManagerEmail`, and `sourceDocument` are GIVEN**
   — the caller supplies them. Preserve them verbatim.

2. **`description`** — write 2–4 sentences summarising the role and company context
   from the email body. Do not just copy the Subject line.

3. **`requirements`** — extract as bullet strings. Be concrete ("5+ years DevOps
   experience", "Kubernetes production experience", "AWS", "Terraform"). Omit vague
   soft-skills unless they're a hard requirement. If no requirements are listed,
   omit the field entirely.

4. **`location`** — include city + work mode if stated (e.g. "Tel Aviv (hybrid, 3
   days office)"). Omit if not mentioned.

5. **`seniority`** — infer from the title/body. Values: "Junior", "Mid", "Senior",
   "Lead", "Staff". Omit if unclear.

6. **`salaryRange`** — copy the exact wording from the email if present (e.g.
   "35,000–50,000 NIS/month"). Omit if not stated.

7. **Omit optional fields if absent** — do not include `null` values.

---

## Caller-supplied values

```
id:                 "job_NNN"
title:              <from jobs.xlsx normalized title column>
status:             "Open"   (or "Closed" if told)
hiringManagerEmail: <From: address in the email>
sourceDocument: {
  "fileName": "job_NNN_<slug>.txt",
  "path":     "/jobs/job_NNN_<slug>.txt"
}
```

---

## Worked example — job_001 (Senior DevOps Engineer)

**Input email:** `job_001_senior_devops.txt`
**Caller supplies:**
```
id: "job_001",  title: "Senior DevOps Engineer",  status: "Open"
hiringManagerEmail: "sarah.chen@company.com"
sourceDocument: { fileName: "job_001_senior_devops.txt", path: "/jobs/job_001_senior_devops.txt" }
```

**Expected output:**
```json
{
  "id": "job_001",
  "title": "Senior DevOps Engineer",
  "status": "Open",
  "hiringManagerEmail": "sarah.chen@company.com",
  "description": "A fintech startup (Series B) needs a Senior DevOps Engineer to lead infrastructure automation, architect an EKS migration, and mentor 2–3 junior engineers. The team is all-in on AWS and manages everything as code with Terraform. Hybrid work in Tel Aviv, strong urgency to hire within 4 weeks.",
  "requirements": {
    "mustHave": [
      "5+ years hands-on DevOps experience",
      "AWS (production)",
      "Kubernetes (production, not just theory)",
      "Terraform (IaC)",
      "GitLab CI/CD pipelines",
      "Python or Go for automation scripting"
    ],
    "niceToHave": [
      "Prometheus + Grafana monitoring stack",
      "AWS certifications (Solutions Architect or DevOps Engineer)",
      "Microservices architecture experience",
      "On-call/incident management experience"
    ]
  },
  "location": "Tel Aviv (hybrid, 3 days office)",
  "seniority": "Senior",
  "sourceDocument": {
    "fileName": "job_001_senior_devops.txt",
    "path": "/jobs/job_001_senior_devops.txt"
  }
}
```
