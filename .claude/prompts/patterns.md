# Prompt Patterns — Personal Library

Harvested from Ex1 sessions. Each pattern: what you typed (or should have), why it worked, when to use it.

---

## Pattern 1: Orient Before You Implement

**What you wrote:**
> "I wish to trace back to defining commits purposes, say 9 specifically. Trying to understand where X meets Y. I am not oriented in the functions themselves or in the order of contexts and components. Is there a way a drawio diagram would depict this?"

**Why it worked:**
- Named the confusion explicitly ("not oriented") rather than asking for code
- Suggested a representational format (diagram) rather than more explanation text
- Asked for the *structure* first, not the implementation

**When to use:**
Before any commit where you don't have a clear mental model of where the new code lives and what it connects to.

**Template:**
```
I'm not yet oriented in [area]. Before we code:
- What does [ComponentA] know about [ComponentB]?
- Where does [action] currently live?
- Can you produce a [diagram/map/table] showing the relationships before we touch the code?
```

---

## Pattern 2: Verify Claims Against Reality

**What you wrote:**
> "I dont see them here in UI (nor in CC TUI CLI in new session), no files related in cwd — Where or what is 'phase 2'?"

**Why it worked:**
- Went and checked the actual state before accepting the declaration
- Named the specific artifact that should exist but didn't (files in cwd, items in UI)
- Forced a correction that uncovered the hallucinated completion

**When to use:**
Any time Claude declares something "done", "set up", or "ready." Check the filesystem, run the tests, look at the UI — before moving on.

**Template:**
```
You said [X] is done. I don't see [specific artifact] in [location].
Can you verify it actually exists before we proceed?
```

---

## Pattern 3: Retrospective Completeness Check

**What you wrote:**
> "We enhanced first phase inspired by Hermes, did we also refine any MD thanks to roeyw's repo?"

**Why it worked:**
- Created a gap between what was *done* and what was *planned*
- Named the specific source (roeyw's repo) so Claude could cross-reference
- Surfaced work that had been planned but silently skipped

**When to use:**
After any multi-source research phase. Before closing a session where several inputs informed decisions. At the end of each exercise.

**Template:**
```
We did [X] based on [source A]. Did we also incorporate the relevant parts of [source B]?
What was planned from [source B] that we haven't done yet?
```

---

## Pattern 4: External Checklist Audit

**What you wrote:**
> [Pasted the Tips and Pointers list] "Anything we neglected out of these?"

**Why it worked:**
- Third-party checklist neutralizes blind spots from both you and Claude
- Specific framing ("neglected") invites criticism, not validation
- Produced a structured gap analysis rather than a summary

**When to use:**
End of each exercise. When you feel like something is missing but can't name it. When a mentor/course provides a rubric.

**Template:**
```
Here is [checklist/rubric/criteria]. 
Go through each item and tell me:
1. Where we aligned — with specific evidence
2. Where we neglected or only partially addressed it
3. What would need to change to fully satisfy it
```

---

## Pattern 5: Explain the Pattern Before the Code

**What CLAUDE.md says:** "explain the Context pattern before coding"

**Why it works:**
- If you can't explain the pattern in plain language, the code will be wrong in subtle ways
- Forces Claude to surface assumptions before they're baked into 80 lines of code
- One-sentence summary of a pattern (e.g. "Context is an in-memory working copy, not a cache") is auditable; code is not

**When to use:**
Any new architectural pattern being introduced for the first time: Context, custom hooks, HOCs, middleware, dependency injection.

**Template:**
```
Before writing any code: explain [PatternName] in plain language.
Specifically:
- What problem does it solve here?
- What does it own vs what does it delegate?
- What would break if we did this differently?
Only then write the implementation.
```

---

## Pattern 6: Structured End-of-Exercise Validation

**Source:** The Validation & Self-Check format from the course.

**Why it works:**
- Specific yes/no questions force concrete answers over vague "it works"
- Edge cases (sparse data, missing fields) are named explicitly
- "Design signal vs implementation bug" framing prevents over-engineering

**When to use:**
After completing every exercise before moving to the next. Before declaring an exercise done.

**Template:**
```
Run the following validation against the current state:
1. [Feature X] — does it behave correctly when [edge case]?
2. If I [add/remove/change Y], does the rest of the system degrade gracefully or break?
3. Could [non-technical persona] use this without explanation?
For any "no" or "unclear": treat it as a design signal, not an implementation bug.
Report: what passes, what fails, what is a signal for future work.
```

---

## Pattern 7: Force the Tradeoff Into the Open

**Source:** From the course tips: "Solve worthwhile things more than one way."

**Why it works:**
- Claude defaults to one answer. Asking for the tradeoff reveals the assumption.
- "What would the alternative look like" produces better designs than "implement X"
- Tradeoffs written down = interview-ready reasoning

**When to use:**
Any architectural decision point: data modeling, state management placement, API design, testing strategy.

**Template:**
```
Before implementing: give me two approaches to [decision].
For each:
- What it enables
- What it makes harder
- Which exercises (Ex2–Ex8) would feel this choice most
Then recommend one and say why.
```

---

## Anti-Patterns (What Produced Revision Cycles)

**"Set it up" without a verification step** → produced the Phase 1 hallucination. Always follow setup tasks with an explicit "verify X exists" check.

**Asking for implementation without orientation** → led to the ApplicationsContext confusion. Orient first (Pattern 1), then implement.

**Accepting a "complete" declaration at face value** → costs a full revision cycle when the artifact doesn't exist. Apply Pattern 2 every time.

---

## Maintenance

Add a new pattern when: a prompt produced notably better output than expected, or when a revision cycle could have been avoided with a different framing.

Mark patterns `[STALE]` when they stop working (model updates change behavior).
