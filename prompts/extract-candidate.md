# Prompt: CV → Candidate JSON

> **THROWAWAY — Exercise 1 only.**
> This prompt is the manual/agent extraction bridge used until the real LLM pipeline
> is built in Exercise 3. Do not carry it forward or depend on its output format
> staying stable.

---

## Your job

Extract one candidate profile from the attached CV file (PDF or DOCX) and output
a **single valid JSON object** that conforms exactly to the `Candidate` type below.
Output **only** the JSON object — no explanation, no markdown fences, nothing else.

---

## Output contract (copy of `src/lib/types.ts`)

```typescript
type Skill = { id: string; name: string }

type ExperienceItem = {
  id: string
  role: string
  company: string
  location?: string
  startYear: number
  endYear: number | null   // null = currently in this role
  highlights: string[]     // keep verbatim, including Hebrew strings
}

type EducationItem = {
  id: string
  degree: string
  institution: string
  startYear: number
  endYear: number
}

type Certification = { id: string; name: string; year: number }

type Language = { id: string; name: string; proficiency: string }

type SourceDocument = {
  fileName: string    // e.g. "cv_001.pdf"
  format: "pdf" | "docx"
  path: string        // "/cvs/<fileName>"
}

type CandidateStatus = "Active" | "Archived"

type Candidate = {
  id: string              // GIVEN — do not extract, use the value I provide
  fullName: string
  headline: string
  status: CandidateStatus // GIVEN — do not extract, use the value I provide
  contact: {
    email: string
    phone?: string
    city?: string
    linkedinUrl?: string
    githubUrl?: string
  }
  summary: string
  skills: Skill[]
  experience: ExperienceItem[]
  education: EducationItem[]
  certifications: Certification[]
  languages: Language[]
  sourceCv: SourceDocument  // GIVEN — do not extract, use the value I provide
}
```

---

## Rules

1. **`id`, `status`, and `sourceCv` are always GIVEN by the caller** — do not read
   them from the CV. The caller supplies these as part of the prompt.

2. **Stable, deterministic ids** — use sequential slugs: `skill-1`, `skill-2`, …
   `exp-1`, `exp-2`, … `edu-1`, `cert-1`, `lang-1`. Always start from 1.

3. **Ordering in the JSON**
   - `skills`: alphabetical by `name`.
   - `experience`: **as found in the CV** — do NOT sort; the db layer sorts by
     `startYear desc` at read time.
   - `education`, `certifications`, `languages`: as found.

4. **Do not invent fields.** If a field is optional and not present in the CV,
   omit it (do not include a `null` or empty-string value).

5. **Preserve original language** — Hebrew or mixed-language bullet points must
   be kept verbatim in `highlights[]`. Do not translate or omit them.

6. **Years only** — dates become `startYear`/`endYear` as integers. "Present" or
   "current" → `endYear: null`. If only a single year is given (e.g. "2023"),
   use it for both start and end.

7. **`company` is already anonymized** (values like "Company 328") — copy verbatim.

8. **`headline`** — use the candidate's stated title or top headline, not a
   synthesized summary. If absent, use their most recent `role`.

9. **Bilingual/RTL content**: feed this prompt with the **original PDF file** (not
   pdftotext output). pdftotext scrambles Hebrew RTL bullet ordering.

---

## Caller-supplied values (fill these in before submitting)

```
id:       "<cv_NNN>"
status:   "Active"          (or "Archived" if told otherwise)
sourceCv: {
  "fileName": "<cv_NNN.ext>",
  "format":   "pdf" | "docx",
  "path":     "/cvs/<cv_NNN.ext>"
}
```

---

## Worked example — cv_001 (Aarav Hayes)

**Input:** `cv_001.pdf`
**Caller supplies:** `id = "cv_001"`, `status = "Active"`,
`sourceCv = { fileName: "cv_001.pdf", format: "pdf", path: "/cvs/cv_001.pdf" }`

**Expected output:**

```json
{
  "id": "cv_001",
  "fullName": "Aarav Hayes",
  "headline": "Junior DevOps Engineer",
  "status": "Active",
  "contact": {
    "email": "aarav.hayes@email.com",
    "phone": "060-4281563",
    "city": "Be'er Sheva, Israel",
    "linkedinUrl": "https://linkedin.com/in/aarav-hayes",
    "githubUrl": "https://github.com/aaravhayes"
  },
  "summary": "Motivated Junior DevOps Engineer with 1.5 years of experience in cloud infrastructure and automation. Recently completed DevOps bootcamp and eager to apply CI/CD best practices in production environments.",
  "skills": [
    { "id": "skill-1", "name": "AWS (EC2, S3, RDS)" },
    { "id": "skill-2", "name": "Bash" },
    { "id": "skill-3", "name": "Docker" },
    { "id": "skill-4", "name": "ECS" },
    { "id": "skill-5", "name": "Git" },
    { "id": "skill-6", "name": "GitHub Actions" },
    { "id": "skill-7", "name": "Jenkins" },
    { "id": "skill-8", "name": "Kubernetes (basics)" },
    { "id": "skill-9", "name": "Python" }
  ],
  "experience": [
    {
      "id": "exp-1",
      "role": "Junior DevOps Engineer",
      "company": "Company 328",
      "location": "Tel Aviv",
      "startYear": 2023,
      "endYear": null,
      "highlights": [
        "Maintain and monitor AWS infrastructure for 3 client applications",
        "Write Bash and Python scripts to automate deployment tasks",
        "Assist in managing Docker containers and basic Kubernetes deployments",
        "Configure Jenkins pipelines for automated testing and deployment"
      ]
    }
  ],
  "education": [
    {
      "id": "edu-1",
      "degree": "DevOps Bootcamp Certificate",
      "institution": "Tech Institute",
      "startYear": 2022,
      "endYear": 2023
    }
  ],
  "certifications": [],
  "languages": [
    { "id": "lang-1", "name": "Hebrew", "proficiency": "Native" },
    { "id": "lang-2", "name": "English", "proficiency": "Native" }
  ],
  "sourceCv": {
    "fileName": "cv_001.pdf",
    "format": "pdf",
    "path": "/cvs/cv_001.pdf"
  }
}
```

---

## Solve-twice note (Exercise 1 learning objective)

For **cv_265** (Dallas Peterson — bilingual, career-changer), do the extraction **twice**:
1. **By hand** — read the PDF yourself, type the JSON against the schema.
2. **Agent-driven** — submit this prompt with `cv_265.pdf` to the agent.
Then `diff` the two outputs and journal every discrepancy. This is the exercise's
core lesson on owned vs. unowned agent output.
