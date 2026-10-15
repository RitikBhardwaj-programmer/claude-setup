---
name: agent-handoff
description: Pass work between coding agents (Claude Code, Antigravity, Codex) through a brief file in the project's `.handoff/` folder, so the user can switch apps by pasting one line. Three modes - out (write a brief for another agent and print the line to paste), in (read the brief addressed to me, check it against git, take the writer lock, continue), return (write the result back, mark the brief done, release the lock). Use when the user says "hand this to Antigravity/Codex/Claude", "continue what Claude/Antigravity started", "pick up the handoff", "write the return", or pastes a line that names this skill. Never starts or wraps another vendor's agent; the user carries the line between apps.
---

# agent-handoff

## Why this exists

Each app (Claude Code, Antigravity, Codex) has its own quota, and each is better at some jobs. Moving work between them loses context. A brief file in the repo carries the state, and the user carries one pasted line. The user switches apps by hand on purpose: Google and Anthropic forbid wrapping their agent inside another tool on a consumer plan (see the rules below).

For the content of a brief (state, decisions, rejected approaches, certainty tags, no secrets), follow the structure of the `context-handoff` skill (`~/.claude/skills/context-handoff/SKILL.md`). Do not copy it here. This skill adds the file format, the lock and the three modes.

Every step below is plain "read a file, run git, write a file". Use whatever file and shell tools your app has.

## Rules (all modes)

- **One writer per file set.** Only the agent that holds `.handoff/LOCK` writes to the files named in `may_write`.
- **Missing means stop.** If something you need is missing (a file, a secret, access, a tool, a brief), say exactly what and stop. Never mock, substitute or guess.
- **Honesty.** Report failures, skipped steps and unverified claims as they are. Never show only the passing results. Mark each claim VERIFIED, ASSUMPTION or UNVERIFIED.
- **No secrets** in a brief or a return. Env var names only.
- **Never wrap another vendor's agent or reuse its login.** Do not run `agy`, `claude` or `codex` from inside a different agent to do the other one's work, and do not copy tokens between apps. The one exception is the user's own existing Codex lane: `codex exec` run from Claude Code through the `route` skill. Everything else goes through the user.

## Files

```
.handoff/
  2026-10-15-add-login-page.md          the brief (written by `out`)
  2026-10-15-add-login-page-return.md   the result (written by `return`)
  LOCK                                  exists only while an agent is writing
```

Brief frontmatter:

```yaml
---
from: claude            # claude | antigravity | codex
to: antigravity
status: open            # open -> done
created: 2026-10-15T14:30:00+05:30
may_write:              # globs the target may change; nothing outside them
  - src/login/**
  - tests/login/**
---
```

Body: use the `context-handoff` sections that matter (objective, done / in progress / blocked, decisions and why, rejected approaches, technical context, next steps), plus these three, always:

- `## Verify` : the exact commands or checks the target runs before it reports done.
- `## If something is missing` : "Say exactly what and stop. Never mock, substitute or guess."
- `## Honesty` : "Report failures and unverified parts as they are."

`LOCK` is two lines: `agent: <name>` and `brief: <brief file name>`, plus `since: <timestamp>` as a third line.

## First use in a project

1. Create `.handoff/` if it is missing.
2. Add `.handoff/` to the project's `.gitignore` (create the file if needed). Default is to keep briefs out of git. Ask the user once: "Commit the briefs instead?" If yes, do not ignore the folder, but still ignore `.handoff/LOCK`.

## Mode `out` (write a brief for another agent)

1. Name yourself (`from`) and the target (`to`). If the user did not say which agent, ask once.
2. Run `git status --short` and `git log --oneline -5`. Note the branch and any uncommitted work. Uncommitted work the target will touch is a risk: say so in the brief.
3. Refuse if `.handoff/LOCK` exists and names another agent: someone is mid-write. Tell the user and stop.
4. Write `.handoff/<YYYY-MM-DD>-<slug>.md` with the frontmatter and body above. Keep `may_write` as narrow as the task allows. Check it against the `context-handoff` checklist (state not history, certainty tags, no secrets, concrete next steps).
5. Print the paste line for the user, and nothing that starts the other agent:

```
Run the agent-handoff skill in mode in. Brief: .handoff/<file>.md
```

For Antigravity, tell the user to open the project in Antigravity and paste that line. For Codex, paste it in a Codex session (or the `route` skill's `codex exec` lane may run it). If the target app cannot see this skill, paste the brief path and say "read it and follow it, then write the return as the brief says".

## Mode `in` (continue work handed to me)

1. Find the newest file in `.handoff/` (a brief, or a `-return` file) with `status: open` and `to:` equal to my agent name. A return file is only read and checked, with no lock and no `may_write`; see the end of mode `return`. If the user gave a path, use it. If none exist, say so and stop.
2. **Lock.** If `.handoff/LOCK` exists and names a different agent, refuse: print who holds it, since when, and for which brief. Stop. Only the user may clear it. If it names me, continue. Otherwise write `LOCK` with my name, the brief name and the time.
3. **Git check.** Run `git status --short`, `git branch --show-current` and `git log --oneline -10`. Compare with the brief: branch, files it calls done or in progress, commits it mentions. If they disagree, trust the repo, list the differences to the user and continue only with the part that still holds. If the repo is not a git repo, say that the check was skipped.
4. Read the files the brief names. Work only inside `may_write`. If the task needs a file outside it, stop and ask the user.
5. Do the work. Run the `## Verify` checks. Keep the brief's decisions and rejected approaches unless you find evidence against them, and then say so.
6. When done or blocked, run mode `return`.

## Mode `return` (write the result back)

1. Write `.handoff/<same-name>-return.md` with frontmatter `from`, `to` (the original sender), `status: open`, `result: done` or `result: blocked`, `created`. Body:
   - What changed (files, one line each; check with `git status` and `git diff --stat`).
   - Verify results: each command, its real result, pass or fail.
   - Open issues, assumptions and anything unverified.
   - What the sender should do next.
2. Set `status: done` (or `blocked`) in the brief's frontmatter.
3. Delete `.handoff/LOCK` if it names me.
4. Do not commit unless the brief or the user says to. Print the paste line for the user to give the sender:

```
Run the agent-handoff skill in mode in. Return: .handoff/<file>-return.md
```

The sender, on `in`, reads a return file addressed to it the same way as a brief: check it against git before trusting it, then set the return file's `status: done` so the SessionStart reminder stops. (A return file is `open` until its receiver has read it. It does not take the lock.)

## Before finishing, check

- Is the lock state right (held by me during work, gone after `return`)?
- Does every claim in the return match `git` and the real command output?
- Are secrets absent?
- Did I stay inside `may_write`?
