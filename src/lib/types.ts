// Pure data model — no UI imports, no framework deps.
// Three top-level entities mirror three future Postgres tables (Exercise 2):
//   candidates.json → Candidate[]
//   positions.json  → Position[]
//   applications.json → Application[]
//
// All reads go through src/lib/db.ts; never import these files directly in components.

// ---------------------------------------------------------------------------
// Sub-types shared by Candidate
// ---------------------------------------------------------------------------

export type Skill = {
  id: string    // stable slug, e.g. "skill-1"; diff uses set ops on `name`
  name: string
}

export type ExperienceItem = {
  id: string
  role: string
  company: string
  location?: string
  startYear: number
  endYear: number | null  // null means "Present"; kept numeric so db layer sorts
  highlights: string[]    // original CV bullets, may include Hebrew strings
}

export type EducationItem = {
  id: string
  degree: string
  institution: string
  startYear: number
  endYear: number
}

export type Certification = {
  id: string
  name: string
  year: number
}

export type Language = {
  id: string
  name: string
  proficiency: string  // free string: data shows "Native"/"Professional"/"Fluent"/etc.
}

export type SourceDocument = {
  fileName: string   // e.g. "cv_001.pdf"
  format: 'pdf' | 'docx'
  path: string       // public-served URL path, e.g. "/cvs/cv_001.pdf"
}

// ---------------------------------------------------------------------------
// Candidate
// ---------------------------------------------------------------------------

// Assigned manually in Ex1 JSON.
// Derived/managed by the FastAPI backend starting in Exercise 2.
export type CandidateStatus = 'Active' | 'Archived'

export type Candidate = {
  id: string           // "cv_001" — stable, derived from source filename
  fullName: string     // must match the name in jobs.xlsx to resolve applications
  headline: string     // e.g. "Senior Platform Engineer" | "Aspiring DevOps Engineer"
  status: CandidateStatus
  contact: {
    email: string      // required — future Ex2 unique key
    phone?: string
    city?: string
    linkedinUrl?: string
    githubUrl?: string
  }
  summary: string
  skills: Skill[]           // sort alphabetically; diff = set intersection/difference on name
  experience: ExperienceItem[]  // sort by startYear desc in db layer
  education: EducationItem[]
  certifications: Certification[]
  languages: Language[]
  sourceCv: SourceDocument  // link to original, immutable CV file
}

// ---------------------------------------------------------------------------
// Position
// ---------------------------------------------------------------------------

// Assigned manually in Ex1 JSON.
// Derived/managed by the FastAPI backend starting in Exercise 2.
export type PositionStatus = 'Open' | 'Closed'

export type SourceEmail = {
  fileName: string   // e.g. "job_001_senior_devops.txt"
  path: string       // "/jobs/job_001_senior_devops.txt"
}

export type Position = {
  id: string              // "job_001" — stable, derived from source filename
  title: string           // from jobs.xlsx normalized column, NOT the email subject line
  status: PositionStatus
  hiringManagerEmail: string  // from jobs.xlsx; this is who the Ex6 agent contacts via Gmail
  description: string     // normalized from the email body prose
  requirements?: {
    mustHave: string[]
    niceToHave: string[]
  }
  location?: string
  seniority?: string
  salaryRange?: string
  sourceDocument: SourceEmail  // link to original, immutable job email file
}

// ---------------------------------------------------------------------------
// Application  (the M:N join between Candidate and Position)
// ---------------------------------------------------------------------------
//
// Why a join entity, not a field on Candidate or Position:
//   1. The relationship is genuinely M:N (Abel McKinney → jobs 1, 3, 4).
//   2. `status` is a property of the *pair* — a candidate can be Rejected for one
//      position and Waiting for another. It does not belong on either parent entity.
//   3. Both screens read it from opposite directions (positions → their candidates;
//      candidates → their positions); one entity serves both without denormalization.
//   4. Exercise 2 models this as a Postgres join table; Exercise 6 agent acts on
//      applications. The mental model carries through unchanged.
//
// `status: ApplicationStatus | null` — null models a listed-but-unactioned row
// (blank Status cells in jobs.xlsx). Ex6 will extend the ApplicationStatus union.

export type ApplicationStatus = 'Waiting' | 'Rejected' | 'Screening' | 'Offer' | 'Hired'

export type Application = {
  id: string
  candidateId: string  // → Candidate.id
  positionId: string   // → Position.id
  status: ApplicationStatus | null
}

// ---------------------------------------------------------------------------
// Diff helpers (used by the Compare screen in commit 8)
// ---------------------------------------------------------------------------

export type CandidateDiff = {
  sharedSkills: Skill[]
  onlyInA: Skill[]
  onlyInB: Skill[]
}

// ---------------------------------------------------------------------------
// Chat (Ex4 — SQL-RAG)
// ---------------------------------------------------------------------------

// ---------------------------------------------------------------------------
// Ex5 semantic search types
// ---------------------------------------------------------------------------

export type CandidateMatch = {
  candidateId: string
  fullName: string
  headline: string
  score: number   // cosine similarity 0..1
}

export type PositionMatch = {
  positionId: string
  title: string
  score: number
  explanation: string
}

export type ChatRole = 'user' | 'assistant'
export type ChatTurn = { role: ChatRole; content: string }

export type ChatTrace = {
  rowCount: number
  columns: string[]
  rows: Record<string, unknown>[]
  promptVersion?: string
}

export type ChatResponse = {
  answer: string
  sql: string
  status: 'success' | 'unsafe' | 'sql_error' | 'llm_error'
  model: string
  runId: number
  trace: ChatTrace
  error?: string | null
  suggestion?: string | null
}
