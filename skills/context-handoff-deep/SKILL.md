---
name: context-handoff-deep
description: Produce a deep, graph-verified context handoff for a completely new Claude context window to continue a substantial project with minimal re-investigation — reconciling the conversation, the project's Graphify knowledge graph (when one exists), current code, documentation, and git state into one compressed, accurate snapshot with explicit source labels and conflict-flagging. This is the heavier sibling of the context-handoff skill. Only use context-handoff-deep when the user explicitly asks for a deep, thorough, graph-verified, or "no stone unturned" handoff, explicitly asks to use Graphify/the project graph for the handoff, or names this skill directly. For an ordinary "hand this off" / "continue in a new chat" / "write up where we are" request with no such signal, use the lighter context-handoff skill instead — don't reach for this one by default.
---

# Deep Context Handoff

## Why this exists, and how it differs from `context-handoff`

The plain `context-handoff` skill compresses the conversation. This skill does more: it treats the conversation as only one of several sources of truth, uses the project's Graphify knowledge graph (when the project has one) to get project-wide structure cheaply instead of re-reading the repository, verifies the claims that actually matter with targeted file/git inspection, and explicitly reconciles what happens when those sources disagree. Reach for this only when the task is substantial enough to justify that extra verification pass — a quick status note doesn't need it.

Optimize for **continuation value × accuracy ÷ context cost**. Every fact earns its place by helping the next Claude act correctly; nothing goes in just because it was discussed or discovered along the way.

## Deep does not mean exhaustive

This is the easiest way for this skill to go wrong: treating "deep" as license to write more. It isn't.

```
Deep means:
- investigate more deeply,
- reconcile more sources,
- verify important claims more carefully,

while still producing the smallest handoff that preserves continuation.

Do not increase output length merely because this is the deep version.
```

A small task run through this skill should still produce a small handoff — the extra work is spent on verification (checking the graph, the code, git) before writing, not on describing more things once you sit down to write. If a full architectural walkthrough genuinely isn't needed to continue the task correctly, leave it out, exactly as `context-handoff` would. Use the same adaptive sizing it uses (~300–1000 words simple, ~1000–2000 medium, ~2000–3500 complex or architectural) as your default expectation — depth changes how much gets verified before writing, not how much gets written.

## Core workflow

```
Current conversation
        ↓
Identify current objective
        ↓
Graphify, if the project has it → project structure + relationships
        ↓
Identify the areas actually relevant to the task
        ↓
Targeted verification (code / docs / git) for claims that matter
        ↓
Reconcile every source
        ↓
Compress
        ↓
Deep Context Handoff
```

The governing rule: **use Graphify for breadth and relationships, targeted inspection for accuracy, and the conversation for intent and decisions.** Don't manually reconstruct project-wide understanding that Graphify already gives you cheaper — and don't trust Graphify (or anything else) on a claim that actually matters without checking it.

## Step 1 — Read the conversation for state, not history

Identify: the project, its current phase, the immediate task, the desired outcome, completed work, work in progress, unfinished work, decisions made, approaches rejected, explicit user requirements and constraints, bugs, open questions, important discoveries, and the immediate next action. Skip greetings, filler, repeated explanations, and history that no longer bears on the task. You're building a state snapshot, not a transcript.

Keep two things distinct while you do this: what the user is asking Claude to do *right now* (the current request) and what the broader project is ultimately working toward (the project objective). They're often the same thing, and when they are, one line is enough — but when they diverge (e.g. the immediate ask is "review this output" while the underlying project goal is "ship V3"), collapsing them into one sentence is exactly the kind of ambiguity that leads a new Claude to work on the wrong thing.

## Step 2 — Graphify first, when the project has it

Before doing broad manual exploration, check whether the project has a Graphify graph (typically `graphify-out/graph.json`, often paired with a project `CLAUDE.md` rule about using it). If it exists, use `graphify query` / `graphify path` / `graphify explain` to get project structure, component relationships, dependencies, database entities and relationships, documents, architecture, APIs, services, and event flows — this is cheaper and usually more complete than re-reading files by hand. If the project has no Graphify setup, skip this step entirely and go straight to targeted inspection; don't try to hand-build an equivalent map first.

Graphify is the map, not the destination — its output informs the handoff, but raw graph output never appears in the final document.

## Step 3 — Use Graphify to scope what matters — including cutting what doesn't

Once you have the graph, narrow to what's actually relevant to the current task, roughly in this priority: the components directly involved → their dependencies → their callers/dependents → relevant database entities → relevant documents → relevant configuration → relevant tests → relevant infrastructure. The question Graphify is answering here is "what parts of this project actually matter for this task?" — not "what does this whole project look like?" Leave unrelated parts of the repository unexplored.

This cuts both ways. Graphify will often surface a relationship that's real but not relevant — e.g. it might show three intermediate hops between the component you're touching and some distant service. If the continuation task doesn't need that chain, don't include it just because the graph revealed it. Use Graphify to filter what goes in the handoff, not only to collect more candidates for it — a relationship worth *knowing about* while you investigate isn't automatically a relationship worth *writing down*.

## Step 4 — Targeted verification

Graphify is the primary map, not automatically the final source of truth. Check an individual file, doc, or git state when: a claim is important to the task, the graph might be stale, the conversation and the graph disagree, documentation and the graph disagree, the task hinges on a specific implementation detail, a bug needs investigating, a consequential architecture decision is involved, or database/security/deployment behavior needs confirming. Don't re-read the whole repository after Graphify has already told you the shape of it — verify the specific things that matter, not everything.

## Step 5 — Know what each source is actually for

Resist the urge to rank these into one global hierarchy ("code > docs > Graphify > conversation") — that framing produces wrong answers the moment the question isn't "what's implemented." Different sources are authoritative for different *questions*, not for everything at once:

- **What is actually implemented?** → current code wins.
- **What did the user ask for or decide?** → the conversation wins.
- **What *should* be implemented?** → the current approved plan/documentation plus explicit user decisions, together.
- **How are components related?** → Graphify is the efficient source — use it, don't re-derive this by hand.
- **What changed recently, or what's uncommitted?** → git.

Match the source to the question you're actually answering, every time — don't default to one source's answer for a question it isn't positioned to answer.

## Step 6 — Reconcile the sources, and flag disagreement instead of resolving it silently

Compare what conversation, Graphify, code, docs, and git each say about anything important. Tag claims when the source matters:

`VERIFIED` (confirmed by code/docs/graph/command output) · `USER DECISION` (explicit) · `DOCUMENTED` (from project docs) · `GRAPH-DERIVED` (from Graphify, not independently re-checked because it wasn't necessary) · `CONVERSATION-DERIVED` (discussed but not confirmed against current state) · `ASSUMPTION` (believed, unverified) · `CONFLICT` (sources disagree).

Don't label every bullet — only where the source or certainty genuinely isn't obvious. When sources conflict on something that matters, resolve it using the question-specific mapping from Step 5 (what's implemented → code; what was requested → conversation; and so on) and say so explicitly rather than silently picking a source out of habit:

```
CONFLICT
Conversation: Feature X was described as implemented.
Graphify: Feature X appears connected to the expected components.
Current code: the required endpoint is missing.
Conclusion: treat Feature X as partially implemented, not done.
```

## Step 7 — Reconstruct current state honestly

Classify relevant work as: **Completed** (implemented and sufficiently verified) · **In Progress** (partially implemented or actively being worked) · **Planned / Not Started** (intended, untouched) · **Blocked** (can't proceed — unresolved dependency or problem) · **Broken** (was implemented, now failing). Never describe planned work as completed, and don't collapse "broken" into "in progress" — a regression is a different situation than unfinished work.

## Step 8 — Architecture and data/event flow, only when relevant

Use Graphify's relationships (not manual reconstruction) to describe only the architecture that bears on the current task — skip this section entirely for a task that doesn't need it (e.g. a styling fix). A compact block is enough:

```
Frontend → REST API → Application Service
                          ├── Database
                          ├── Cache
                          └── Event System → Worker → ML Service
```

For data-heavy or event-driven tasks, do the same for the relevant flow (ingestion → processing → dedup → storage, or producers → topics → consumers → processing stages). For database tasks, list only the relevant entities, relationships, fields, constraints, and migrations that matter — not the whole schema.

## Step 9 — Relevant documents

Use Graphify (or a directory check) to find documents relevant to the task; don't summarize every doc in the project. For each one worth including: path, purpose, and why it matters to continuation right now. Prioritize current plans, requirements, architecture docs, API specs, decision records, deployment docs, and technical notes; ignore obsolete documents unless one explains a constraint or a rejected approach that's still relevant.

## Step 10 — Decisions and rejected approaches

For each decision that shapes future implementation: what was decided, why (when it matters), and its current status (implemented / not yet). Record rejected approaches too, whenever remembering them stops the next Claude from repeating a mistake:

```
- Decision: Use PostgreSQL for persistence.
  Reason: existing relational model and JPA layer already depend on it.
  Status: Implemented.
```

## Step 11 — Debugging history, only where it has continuation value

For each issue worth preserving: the problem, the relevant component/file, what was tried and what happened, the current finding, current status, and what to investigate next — plus, when useful, an explicit "do not repeat" line for a fix that was already tried and didn't work:

```
Kafka connection issue — UNRESOLVED
Tried: changed bootstrap server; changed consumer group.
Finding: works locally, Docker networking remains problematic.
Next: verify service hostname and advertised listeners.
Do not repeat: changing the consumer group ID does not fix this.
```

## Step 12 — File map, by priority tier

Use Graphify to identify the files that actually matter, then tier them — don't list files just because they exist:

```
### Critical  — inspect before making changes
- src/.../NewsCollectionScheduler.java — current ingestion scheduling logic

### Important — helps understand/modify the task
- src/.../ArticleService.java — article processing logic

### Reference — background only, not urgent
- docs/old-architecture.md — historical architecture only
```

## Step 13 — Project-specific instructions

Note relevant instructions from `CLAUDE.md`, `AGENTS.md`, nested instruction files, or documented build/test/formatting/security/deployment rules the next Claude must follow — as pointers and key takeaways, not full copies of the files.

## Step 14 — Git state, only when it helps

Include current branch, important modified files, uncommitted work, and relevant recent commits — but only when git state actually matters to continuation, not as a routine section. Uncommitted changes deserve special care: never suggest discarding or overwriting them without understanding what they're for.

## Step 15 — Build/test/validation state, only what's actually verified

When relevant: build system, relevant commands, tests, last verified build/test status, known failures, environment requirements. Never say something passed unless it was actually run and confirmed — an assumption dressed up as a build status is worse than no status at all.

## Step 16 — Secrets: no exceptions

Never include API keys, passwords, access tokens, private keys, OAuth secrets, database or cloud credentials, session cookies, or any `.env` secret value — including ones that appeared in the conversation or in a file you read. Environment variable *names* are fine:

```
DATABASE_URL is required. Actual value omitted for security.
```

## Step 17 — Compress hard, using a real priority order

Cut: conversation filler, duplicate information, repeated explanations, generic programming knowledge, large code blocks, irrelevant files, obsolete architecture, historical detail with no current impact, anything trivially rediscoverable from the repo, and raw Graphify output. Keep: current objective, current implementation state, user decisions and constraints, important architecture relationships, relevant files, open problems, important failed approaches, validation state, next steps, and critical warnings.

If the handoff still needs to shrink further, sacrifice in this order (top survives longest):
1. Current objective
2. Current implementation state
3. User decisions and constraints
4. Open problems and blockers
5. Critical/relevant files
6. Immediate next steps
7. Important architecture relationships
8. Important debugging history
9. Historical context
10. Everything else

## Step 18 — Sections are conditional, not automatic

Include a section only when it carries continuation value for *this* task — not as a checklist to fill in regardless. No database section for a frontend styling task; no git section when git state is irrelevant; no architecture diagram for a trivial task; no debugging-history section when nothing was actually debugged. An adaptive, shorter handoff beats a complete-looking one padded with empty sections.

## Step 19 — This handoff supersedes earlier ones — say so, briefly

Someone will eventually generate a second handoff for the same project days or weeks after the first, having implemented some of what the first one described as "not started." Mark the handoff with a light freshness signal — the date if you have it, and one line naming what it covers — and make it explicit that it replaces any earlier handoff for the same task rather than sitting alongside it as an equally-valid alternative. This doesn't need timestamps or version numbers throughout the document; one small block at the top is enough. What matters more than the metadata itself is the instruction it carries: a future Claude reading this should re-verify current state against the live repository rather than trusting either this handoff or an older one it might also find — never inherit a previous handoff's implementation claims without checking them.

---

## Required output format

Use this structure as the default shape; omit any section (except Project Overview, Current Objective, Current State, and Next Steps, which are always present) when it wouldn't carry continuation value for this task.

```
DEEP CONTEXT HANDOFF

HANDOFF METADATA
- Generated: [date, if known from context — omit rather than guess]
- Scope: [the current task this handoff covers, in a few words]
This handoff supersedes any earlier handoff for the same task. Re-verify
current state against the live repository rather than trusting this
document's claims indefinitely — treat the repository as newer than any
handoff, including this one.

PROJECT OVERVIEW
- Project:
- Purpose:
- Current version/phase:
- Current development area:
(keep this brief)

CURRENT USER REQUEST
What the user is asking Claude to do right now.

PROJECT OBJECTIVE
What the broader project is ultimately working toward.
(omit this line and keep only Current User Request if the two are the same —
don't force a split that doesn't exist)

CURRENT STATE
Completed
- ...
In Progress
- ...
Planned / Not Started
- ...
Blocked
- ...
Broken
- ...

VERIFIED IMPLEMENTATION STATE
Summary of the actual current implementation, with file paths where useful.

ARCHITECTURE
(only if relevant)

DATA / EVENT FLOW
(only if relevant)

IMPORTANT DECISIONS
Decisions the next Claude must respect, with reason and status.

REJECTED / ABANDONED APPROACHES
Only approaches that shouldn't accidentally get repeated.

SOURCE RECONCILIATION
Important conflicts or uncertainty, labeled (VERIFIED / USER DECISION / DOCUMENTED / GRAPH-DERIVED / CONVERSATION-DERIVED / ASSUMPTION / CONFLICT) where the source isn't obvious — not on every line.

GRAPHIFY STATE
(only when Graphify was actually used this session — omit otherwise, don't
pad it in as a formality)
- Graph: path to the graphify-out/graph.json used
- Graph used for: which of architecture / DB / dependencies / documents it informed
- Verification performed: what was freshly queried/checked, vs. what's carried
  over from earlier in the conversation without re-checking
This tells the next Claude a project map already exists and was actually
consulted — not just summarized from memory.

RELEVANT FILE MAP
Critical
- ...
Important
- ...
Reference
- ...

RELEVANT DOCUMENTS
Only materially relevant ones, with purpose + relevance.

IMPORTANT IMPLEMENTATION DETAILS
Technical facts the next Claude needs and can't safely infer from the summary above.

BUGS / DEBUGGING HISTORY
(only if there's continuation value)

OPEN QUESTIONS / UNCERTAINTIES
Unresolved questions and assumptions, clearly marked as such.

USER REQUIREMENTS / CONSTRAINTS
Explicit requirements relevant to the current work.

GIT / WORKING TREE STATE
(only if relevant)

BUILD / TEST / VALIDATION STATE
(only verified information, only if relevant)

NEXT STEPS
Immediate
1. ...
After That
2. ...
3. ...
Later
4. ...
(the first step must be concretely actionable, not "continue development")

DO NOT FORGET
Critical, easy-to-lose facts only.

CONTINUATION INSTRUCTION
A short, concrete instruction for how to begin — e.g. "Continue from this handoff as the current project state. Use the Critical files as the starting context. Verify conflicts and important unverified assumptions before making changes. Don't redo completed work, discard existing changes, or reintroduce rejected approaches. Begin with the Immediate next step."
```

## Before returning the handoff, check

**Length discipline** — Is this the smallest handoff that preserves continuation, or did it grow just because this is the deep skill? Would a simpler version of this task have produced a noticeably shorter document? If yes, cut back to that size — the extra effort belongs in verification, not prose.

**Accuracy** — Does it reflect the current project? Were important claims actually verified? Are conflicts identified rather than silently resolved, using the right source for the question being asked rather than a blanket hierarchy? Are assumptions clearly distinguished from facts? Is outdated information excluded?

**Graphify usage** — Was it used for project-wide understanding when available? Used to scope relevance rather than to browse? Did you avoid unnecessary manual repository exploration because of it? Were important graph findings verified when it mattered? Is raw graph output absent from the final handoff?

**Continuation** — Is the objective obvious immediately? Is it clear what's done vs. in progress vs. not started vs. broken? Are the relevant files easy to find? Is it clear what's already been tried and what not to repeat? Is the very next action concrete?

**Compression** — Is unnecessary history gone? Are duplicate facts consolidated? Are irrelevant files excluded? Are large code blocks avoided? Are sections that don't apply here actually omitted, not left as empty placeholders?

**Security** — Are all secrets excluded, including any that appeared in the conversation or a file you read?

If any answer is no, revise before returning it. This handoff is a compressed, verified state snapshot — not a transcript, and not a Graphify dump. The goal is to make the next Claude remember everything that matters, and almost nothing that doesn't.
