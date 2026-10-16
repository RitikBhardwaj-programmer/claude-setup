---
name: agent-handoff
description: Pass work between coding agents (Claude Code, Antigravity, Codex) through a brief file in the project's `.handoff/` folder, so work moves between apps with no paste when Antigravity's own watcher sidecar is on, or one pasted line otherwise. Three modes - out (write a brief for another agent and print the line to paste), in (read the brief addressed to me, check it against git, take the writer lock, continue), return (write the result back, mark the brief done, release the lock). Use when the user says "hand this to Antigravity/Codex/Claude", "continue what Claude/Antigravity started", "pick up the handoff", "write the return", or pastes a line that names this skill. Never starts or wraps another vendor's agent; the user carries the line between apps.
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
- **One command per call.** Run each shell command on its own; never chain them with `;`, `&&` or `|`. Chained commands get stricter permission review (Antigravity flags them), and one denial then hides which step failed.
- **Denied means skipped, not passed.** If the app denies a command (permission, sandbox, no approval in an unattended run), do not retry it another way or work around it. Mark that step UNVERIFIED in the return, say which command was denied, and let the sender run it.
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
status: open            # open -> claimed (by Antigravity's watcher) -> done | blocked
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

`LOCK` is two lines: `agent: <name>` and `brief: <brief file name>`, plus `since: <timestamp>` as a third line. An empty `LOCK` file means no lock.

## Helper script and the Antigravity watcher

`scripts/handoff.py` in this skill's folder (`~/.claude/skills/agent-handoff/scripts/handoff.py`; run it with `py -3` on Windows, `python3` on macOS):
- `watcher-status` prints `on` or `off`.
- `watch-add <project dir>` puts a project on the watcher's list.
- `copy "<text>"` puts text on the clipboard.
- `wait <return file> [--timeout 3600]` ends when the return file exists.

**The watcher** (`scripts/antigravity_watcher.py`) is an Antigravity sidecar: Antigravity itself runs it and restarts it, after the user enables "Agent handoff watcher" in Antigravity's Automations dashboard.
- When a watched project gets a brief with `to: antigravity` and `status: open`, the watcher sets `status: claimed` and starts an Antigravity conversation with Antigravity's own `agentapi`.
- No other agent starts Antigravity; they only write the file. This is why it stays inside Google's terms.
- It ignores briefs that git tracks, so a cloned repo cannot start an agent.
- It waits while another agent holds `LOCK`.
- Its runs are unattended, so Antigravity auto-denies commands that are not pre-approved (2026-10-16 test: `python test_calc.py` was denied, and the agent reported Verify as skipped). Approve the usual verify commands once in Antigravity's permission settings, or the sender runs `## Verify` itself on `in`.

## First use in a project

1. Create `.handoff/` if it is missing.
2. Add `.handoff/` to the project's `.gitignore` (create the file if needed). Default is to keep briefs out of git. Ask the user once: "Commit the briefs instead?" If yes, do not ignore the folder, but still ignore `.handoff/LOCK`. (The watcher never starts committed briefs, so committed briefs always need the paste line.)
3. Only before the first brief to Antigravity: ask the user once "Let Antigravity's watcher pick up briefs in this project automatically?" If yes, run `handoff.py watch-add <project dir>`.

## Mode `out` (write a brief for another agent)

1. Name yourself (`from`) and the target (`to`). If the user did not say which agent, ask once.
2. Run `git status --short` and `git log --oneline -5`. Note the branch and any uncommitted work. Uncommitted work the target will touch is a risk: say so in the brief.
3. Refuse if `.handoff/LOCK` exists and names another agent: someone is mid-write. Tell the user and stop.
4. Write `.handoff/<YYYY-MM-DD>-<slug>.md` with the frontmatter and body above. Keep `may_write` as narrow as the task allows. Check it against the `context-handoff` checklist (state not history, certainty tags, no secrets, concrete next steps).
5. Deliver it. Never start the other agent yourself (the one exception is the `route` skill's `codex exec` lane).
   - **To Antigravity, watcher on** (`handoff.py watcher-status` prints `on` and the project is in the watch list): tell the user "Antigravity's watcher will pick this up; nothing to paste." It starts within a few seconds.
   - **Otherwise:** build the paste line below, run `handoff.py copy "<line>"`, and tell the user it is on the clipboard: open the project in the target app and press Ctrl+V (Cmd+V). If copying fails, use your app's own clipboard tool if it has one (Claude desktop: computer-use `write_clipboard`, after the user grants clipboard access); otherwise print the line. (Gotcha, 2026-10-15: shell commands started by Claude Code desktop on Windows get "Access is denied" from the clipboard, inside and outside the sandbox.)

```
Run the agent-handoff skill in mode in. Brief: .handoff/<file>.md
```

   If the target app cannot see this skill, add: "If you cannot see the skill, read ~/.claude/skills/agent-handoff/SKILL.md and follow it."
6. **Wait for the return** if your app can run a command in the background and wake you when it ends (Claude Code: a background Bash task). Run `handoff.py wait .handoff/<file>-return.md --timeout 3600` in the background, end your turn, and when it finishes run mode `in` on the return. On timeout, tell the user and check the brief's status.

## Mode `in` (continue work handed to me)

1. Find the newest file in `.handoff/` (a brief, or a `-return` file) with `status: open` (or `claimed`, which means the watcher started me for it) and `to:` equal to my agent name. A return file is only read and checked, with no lock and no `may_write`; see the end of mode `return`. If the user gave a path, use it. If none exist, say so and stop.
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
3. Release `.handoff/LOCK` if it names me: delete it, or, if your tools cannot delete files, overwrite it with an empty file. An empty `LOCK` counts as no lock.
4. Do not commit unless the brief or the user says to. The sender may already be waiting for this file (mode `out` step 6), and then nothing else is needed. In case it is not, run `handoff.py copy "<line>"` and print the paste line for the user to give the sender:

```
Run the agent-handoff skill in mode in. Return: .handoff/<file>-return.md
```

The sender, on `in`, reads a return file addressed to it the same way as a brief: check it against git before trusting it, then set the return file's `status: done` so the SessionStart reminder stops. (A return file is `open` until its receiver has read it. It does not take the lock.)

## Before finishing, check

- Is the lock state right (held by me during work, gone after `return`)?
- Does every claim in the return match `git` and the real command output?
- Are secrets absent?
- Did I stay inside `may_write`?
