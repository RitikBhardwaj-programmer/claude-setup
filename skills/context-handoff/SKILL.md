---
name: context-handoff
description: Generate a compact, high-value context handoff so a new Claude conversation or context window can continue the current work with minimal loss of context. It is a compressed snapshot of working state — objective, what's done/in-progress/blocked, decisions made and why, rejected approaches, open problems, and concrete next steps — never a chronological summary or transcript. Use this whenever the user wants to hand off, continue elsewhere, wrap up before a break, prepare for a new session, or mentions running low on context, compacting, starting fresh, or picking this up later — even if they don't say "context handoff" or "handoff" explicitly. Also trigger on requests like "summarize this so I can continue in a new chat," "write up where we are," or "get this ready to hand to another Claude." This is the default, lightweight handoff — for an explicit request for a "deep," "thorough," or graph-verified handoff, or one that should use the project's Graphify graph, use context-handoff-deep instead.
---

# Context Handoff

## Why this exists

A chronological summary tells the next Claude what happened. That's the wrong target. The next Claude needs to *act* — pick up the work correctly, not repeat finished steps, not re-litigate rejected approaches, not treat a guess as a fact. Optimize every sentence for "what does the next Claude need to know to continue correctly," not "what happened in this conversation." If a piece of information doesn't change what the next Claude does next, cut it.

## Step 1 — Read the conversation for state, not history

Work out: the project/task, the user's current objective, what's actually finished, what's mid-flight, what's untouched, what decisions got made, what got tried and rejected, what constraints the user stated explicitly, and what open questions or bugs remain. Skip greetings, repeated explanations, and anything that no longer bears on the current task.

Keep the immediate ask separate from the broader goal when they differ — "what the user wants done right now" and "what the project is ultimately working toward" aren't always the same sentence, and flattening them into one can point the next Claude at the wrong thing.

## Step 2 — Verify against the project, not just the conversation

The conversation is not the source of truth — the codebase is. When the task depends on code, config, or docs, inspect the files that actually matter for continuation before writing the handoff. Don't scan the whole repo; don't take the conversation's word for a file's contents when you can check it in a few seconds. Prefer what you just verified over what was merely discussed.

## Step 3 — Sort the work honestly

Split into four buckets and don't blur them:
- **Completed** — actually implemented/verified/finished.
- **In Progress** — actively being worked on right now.
- **Not Completed** — planned but untouched.
- **Blocked** — can't proceed without a dependency, a bug fix, or a decision.

Planned work is not completed work. If you're not sure which bucket something belongs in, that uncertainty is itself worth a line in the handoff rather than a guess.

## Step 4 — Record decisions and dead ends

For each decision that would change how the next Claude implements something, capture what was decided and, when it matters, why. Do the same for rejected approaches — that's what stops the next Claude from re-discovering a dead end the hard way.

```
- Decision: Use PostgreSQL instead of MongoDB.
  Reason: The existing relational model and JPA layer already depend on it.

- Rejected: Sequential processing for article ingestion.
  Reason: Doesn't scale to the expected number of sources.
```

Skip minor conversational preferences that don't affect implementation.

## Step 5 — Mark certainty, always

Never let an assumption read like a fact. Tag claims as:
- **VERIFIED** — confirmed via the current code, docs, command output, or an explicit user statement.
- **CONVERSATION DECISION** — agreed in conversation but not yet reflected in the code.
- **ASSUMPTION** — believed true, not checked.
- **UNVERIFIED** — mentioned or suspected; check before relying on it.

If the conversation and the project disagree, say so explicitly rather than picking one silently:

```
- UNVERIFIED: Conversation says Redis is enabled in production.
- Repository configuration currently shows no Redis production config.
- Verify before making architecture decisions that assume Redis is live.
```

## Step 6 — State the source-of-truth order

Include a short line establishing precedence, roughly: current source code → current config → current project docs → explicit user decisions → prior conversation → assumptions. Close with something like: "If this handoff conflicts with the actual codebase, trust the codebase. If docs conflict with the implementation, flag the discrepancy — don't silently pick one."

## Step 7 — Documents, only when they matter

List only the docs relevant to continuing the task, each with its path, what it contains, and why it matters right now. Leave out anything obsolete or unrelated. If a doc carries a requirement that isn't obvious from the code, preserve that requirement explicitly — don't make the next Claude re-read the whole doc to rediscover it.

## Step 8 — Technical details worth keeping exact

Preserve things that are expensive to rediscover: file paths, class/method names, API endpoints, DB tables/entities and key relationships, env var *names*, frameworks/libraries, service and topic names, Docker services, deployment config, important commands, branch names, relevant error messages, model names, pipeline stages. Point at where to look rather than reproducing the repository — don't paste large code blocks unless the exact code truly can't be reasonably rediscovered.

## Step 9 — Never include secrets

Never write out API keys, tokens, passwords, private keys, session tokens, OAuth secrets, `.env` values, or any other credential — including ones that appeared in the conversation or in a file you read. Environment variable *names* are fine and often useful:

```
- OPENAI_API_KEY is required.
- Actual value intentionally omitted.
```

This rule has no exceptions, regardless of how the secret showed up in context.

## Step 10 — Compress hard, but don't compress away what matters

Cut: greetings, filler, repeated explanations, duplicate decisions, basic-concept explanations, obsolete implementation details, dead ideas with no remaining relevance, anything trivially recoverable from an unrelated file, full code listings, and history that no longer affects the task.

Keep: the current objective, current implementation state, decisions and constraints, relevant architecture and files, existing bugs, approaches already tried and rejected, open questions, next steps, and anything easy to forget but costly to lose. Use the fewest words that preserve all of that — but never cut something load-bearing just to hit a target length.

## Step 11 — Let length follow complexity

Don't force a fixed size. Roughly: **~300–1000 words** for a simple task, **~1000–2000** for a medium one, **~2000–3500** for a complex or architectural one. These are guides, not caps — a genuinely critical detail is never cut to satisfy a word count, and a simple task shouldn't be padded to look thorough.

## Step 12 — Capture what the user actually required

Explicit technology choices, architecture constraints, performance targets, naming conventions, compatibility requirements, must/must-not features, and approaches the user explicitly ruled out. Skip anything personal or unrelated to the project.

## Step 13 — Preserve debugging history for open problems

For each unresolved problem: what it is, where it happens, what's already been tried and what happened, the current hypothesis if there is one, and what to check next. This is what stops the next Claude from re-running an experiment that already failed.

```
- Kafka consumer intermittently fails to connect.
  Location: event-processing-service
  Tried: changed bootstrap config and consumer group settings.
  Result: works locally, fails in Docker.
  Status: UNRESOLVED.
  Next: check Docker network hostname and advertised listeners.
```

## Step 14 — End with concrete next steps

Never "continue development." Give an ordered, actionable list — specific files to read, specific things to verify, and explicitly note anything that should be confirmed with the user before code changes.

---

## Required output format

Use exactly this structure. Omit a whole section only if it's genuinely empty (e.g. no open problems) — don't omit sections just to save space.

```
CONTEXT HANDOFF
(If an earlier handoff exists for this same task, this one supersedes it —
re-verify state against the project rather than trusting either blindly.)

PROJECT / TASK
Brief description of the project and the current task.

CURRENT OBJECTIVE
What we're trying to accomplish right now. If the immediate request and the
broader project goal differ, name both in a line each; if they're the same
thing, one line is enough.

CURRENT STATE
Completed
- ...
In Progress
- ...
Not Completed
- ...
Blocked
- ...

IMPORTANT DECISIONS
- Decision: ...
  Reason: ...
(include rejected approaches here when remembering them saves the next Claude from repeating the work)

TECHNICAL CONTEXT
- Architecture:
- Backend:
- Frontend:
- Database:
- Infrastructure:
- APIs:
- Important components:
- Other relevant technical details:
(only include the categories that are actually relevant)

SOURCE OF TRUTH
Most authoritative files/docs/sources for this task, and any conflicts between conversation, docs, and code, flagged explicitly.

RELEVANT FILES / DOCUMENTS
- path/to/file
  - Purpose:
  - Why relevant:
(only files that materially matter to continuation)

IMPLEMENTATION DETAILS
Concise bullets of implementation facts the next Claude needs.

PROBLEMS / OPEN QUESTIONS
- Problem/question:
  - Current status:
  - What's been tried:
  - Next investigation:

USER REQUIREMENTS / CONSTRAINTS
- ...

NEXT STEPS
1. ...
2. ...
3. ...

DO NOT FORGET
Critical, easy-to-lose facts only — e.g. "don't repeat the rejected sequential-processing approach," "this API contract must stay unchanged," "a migration must run before deploy," "this bug is config, not code."

CONTINUATION INSTRUCTION
A short, concrete instruction for how the next Claude should begin — e.g. "Continue from the state above. Inspect the files listed under Relevant Files and verify the current implementation before making changes. Don't redo completed work or revisit rejected approaches unless new evidence requires it."
```

## Before returning the handoff, check

- Is the current objective obvious in the first few lines?
- Is it clear what's already done vs. merely planned?
- Are the relevant files easy to find?
- Are decisions and rejected approaches preserved?
- Is every non-obvious claim tagged with a certainty level?
- Are unresolved problems and their debugging history clear?
- Are the user's explicit requirements preserved?
- Are next steps concrete, not vague?
- Is obsolete or redundant history gone?
- Are secrets absent — fully, including ones that appeared in the conversation?
- Is this substantially shorter than the conversation it's compressed from?
- Does it help the next Claude *continue*, not just *understand the past*?

If any answer is no, revise before returning it.
