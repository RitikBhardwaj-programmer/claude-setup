---
name: route
description: "Write a routing card (which model, effort and agent does each phase of the task) as part of the plan for any medium or large task, before implementation starts, so paid tokens go where they add value; also on /route or when the user asks 'which model/effort should we use', 'save tokens', 'is Opus needed for this', or 'should Codex do this part'. After the user approves the card, carry it out: start the build session or subagents at the chosen model and effort, and offer Codex handoffs. Skip for small tasks (typo, rename, one-file fix, a quick question)."
---

# Route

Paid tokens are limited. The bill is roughly **context size × number of turns × price per token ÷ chance of first-try success**. So the two biggest levers are a small context and few retries. Model price comes after those. This skill picks a model and effort **per phase** and keeps big contexts out of expensive sessions.

Model scores and prices: `references/models.md`. Read it each time you write a card.

## Step 1: Split the task into phases

Typical phases: **explore** (find files, read docs), **plan / design**, **build** (implement an approved plan), **mechanical** (renames, formatting, boilerplate), **review**, **research** (web or long documents). Skip the phases the task does not have.

## Step 2: Pick a model, an effort and an agent for each phase

Defaults (adjust them with `references/models.md`):

| Phase | Agent | Model | Effort |
|---|---|---|---|
| Explore | Explore subagent: a big read stays out of the main context | haiku | low |
| Plan / design, hard debugging, security | main session | opus | high (xhigh for a cross-cutting design) |
| Build an approved, clear plan | new session started from the plan, or the main session | sonnet | medium |
| Mechanical edits | subagent | haiku | low |
| Review of a medium/large diff | subagent (independent eyes) | sonnet (opus for security or tricky logic) | high |
| Long research or a separate module | Codex handoff (Step 3), else a subagent | n/a or sonnet | medium |

Rules:
- **Raise the model when failure is quiet.** If a wrong answer would look right (design, concurrency, auth, maths), use the stronger model. If a failure is loud (a test fails at once), use the cheaper one.
- **Effort is a separate dial.** High effort on a rename wastes thinking tokens. Low effort on a plan makes a shallow plan, and every later phase pays for it.
- **Switch at phase borders only.** Prompt caching (the provider stores the repeated context so re-reading it costs less) is per model. After a model switch, the next turn re-reads the whole context uncached. A fresh session for the build phase avoids this, and it also starts with a small context.
- **Do not use a model that is dominated** (another model scores higher and costs less per task). See `references/models.md`.

## Step 3: Codex handoff candidates

Only if the Codex CLI is installed: `codex --version` works in Bash, or on Windows `Get-Command codex` finds it in PowerShell (npm puts it in `%APPDATA%\npm`, which Git Bash may not have on PATH). The Codex desktop app alone is not enough: `codex exec` needs the CLI. If it is missing, write "none (Codex CLI not installed: `npm i -g @openai/codex`)" in the card. Codex runs on the user's ChatGPT plan quota, not on Claude tokens. Offer a phase to Codex only when **all** of these are true:
1. It is self-contained: the brief can describe it without the repo's whole context.
2. Its result is cheap to check: a test passes, a file exists, or a short skim is enough.
3. The work is large compared with the brief: a research pass, a separate module, a second-opinion review.
4. No other agent writes the same files while it runs.

The handoff command (non-interactive): `codex exec -s <read-only|workspace-write> "<brief: goal, files, what done looks like, where to write the result>"`. Use `read-only` for reviews and questions, `workspace-write` only when it must create files. Run long jobs in the background. Check the result before you report it as done.

Windows: if every Codex shell call fails with `helper_unknown_error: setup refresh had errors`, the config has `[windows] sandbox = "elevated"` (set up by the Codex desktop app; the CLI cannot refresh it). Add `-c 'windows.sandbox="unelevated"'` to the command. Do not edit the user's `config.toml`. Expect ~15k ChatGPT-quota tokens of overhead per call, so one larger handoff beats many small ones.

Do not route anything through free third-party gateways (for example OmniRoute). The user parked that option on 2026-10-08 (security and data concerns).

## Step 4: Write the card into the plan

```
**Routing card**
| Phase | Agent | Model | Effort | Why |
|---|---|---|---|---|
| ... | ... | ... | ... | one short reason |
Codex handoffs: <phase, or "none">
Switch needed: <"none" | "build in a new session at sonnet/medium" | "user: pick opus in the model menu">
```

Keep the card to 3–6 rows. The user approves it together with the plan.

## Step 5: Carry it out after approval

The approval of the card is the user's instruction to act on it. Do not ask again.
- **Subagents:** pass `model` and `effort` on each Agent call, as the card says.
- **Build in a new session:** use `start_session` with `initiation: "user_asked"`, `context: "fresh"`, the card's `model` and `effort`, and the approved plan as the brief (goal, files, steps, verification). That session can only use a model and effort the same as or cheaper than this one.
- **This session's own model:** the session tools refuse to change it (a session must not re-price its own turns). If a phase needs a **stronger** model than the current one, tell the user in one line to pick it in the model menu (CLI: `/model`, `/effort`) before that phase.
- **Codex:** after the user approves the handoff in the card, run `codex exec`.
- **Every brief** (session, subagent or Codex) says how the worker checks its own work before it reports done, and contains: "If something you need is missing (a file, a secret, access, a tool), say exactly what and stop. Never mock, substitute or guess." A wrong brief otherwise fails quietly.
- **Canary first:** when one brief feeds several sessions, subagents or Codex jobs, start one, check its result, fix the brief if needed, then start the rest.
- **Verify after start:** after `start_session`, check the session's model and effort (`get_session`). If they differ from the card, fix it or tell the user before the work goes on.

## Step 6: Learn from the result

When a task ends, note in one line in the summary whether the card was right: "card held", "under-routed: sonnet build needed 2 retries", or "over-routed". If the user keeps a notes vault, save repeated patterns there, so later cards improve.
