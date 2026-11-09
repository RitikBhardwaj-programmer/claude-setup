---
name: improve-setup
description: Retrospective that improves Claude's own setup from real session evidence. It reviews the current session, past session transcripts since the last retro, and the user's notes for friction (failed commands, retries, user corrections, rejected plans, slow workarounds), finds root causes, proposes ranked changes to CLAUDE.md files, skills, hooks/settings and notes/memory, and builds only the approved ones with backups, tests and commits. Use when the user types /improve-setup, asks "what did you learn", "improve your setup/claude.md/skills/hooks from this session", or after an end-of-session retro nudge.
---

# /improve-setup

You turn real friction into lasting fixes. You **propose first** and build only what the user approves.

## 0. Read the machine config
`~/.claude/setup.json` is optional. Use each key if present, otherwise the default:

| Key | Meaning | Default |
|---|---|---|
| `python` | Python to run scripts | `python3` (`py -3` on Windows; there also set `PYTHONIOENCODING=utf-8`) |
| `retros_dir` | Where retro notes live | `~/.claude/retros/` |
| `notes_repo`, `notes_log` | Git repo of the user's notes and its change log | none: skip the notes commit and log line |
| `setup_repo`, `setup_install`, `setup_check` | Git repo that is the source of truth for the Claude setup, its installer and its drift check | none: edit `~/.claude` directly |

`SK` is this skill's folder, `~/.claude/skills/improve-setup`.

## 1. Find the window
- Read the newest note in `retros_dir`. Its frontmatter `covers_until:` is the start of the window. With no note, use the last 7 days.
- The window ends now. Note the time in ISO format with the zone.
- If `setup_check` is set, run it **now**. Drift means someone edited `~/.claude` directly; include it as a finding, because it must go back into the setup repo.

## 2. Gather evidence
1. **This conversation:** failed commands, retries, workarounds, your own wrong assumptions, the user's corrections and rejected plans, and anything the user had to ask for twice.
2. **Past sessions:**
   `PY SK/scripts/scan_sessions.py --since <covers_until>`
   It reports tool calls, error signatures (with "repeated in 2+ sessions" flags), rejections with the user's words, failed background tasks, retry loops, quiet stretches, skills used and most edited files. Snippets are redacted. Read the sessions further only when a signal is unclear.
3. **Notes:** earlier retro notes (open, deferred and rejected items) and, if a notes repo exists, its gotcha, decision and log files and project memory.
4. **Current setup:**
   - `~/.claude/CLAUDE.md` (line count; it must stay ≤ ~200);
   - project `CLAUDE.md` files;
   - `~/.claude/skills/*/SKILL.md`;
   - `~/.claude/hooks/*`;
   - the `hooks` block of `~/.claude/settings.json`.
   - If `setup_repo` is set, read these files **in the repo**; it is the source of truth.

## 3. Find root causes
Group symptoms by cause, not by tool. Example: three different shell failures may share one cause, "inline scripts with Windows paths". For each cause, count the evidence: sessions × occurrences. Keep only causes that cost real time or produced a wrong or unsafe result.

## 4. Pick the target with fixed rules
| The fix is… | Target |
|---|---|
| A behaviour rule true for every project | Global CLAUDE.md. If the file would go over ~200 lines, put the rule in a rules file and add a one-line pointer instead |
| A fact, command or gotcha of one project | That project's `CLAUDE.md` |
| A multi-step workflow done 2+ times, or likely to recur | A new or edited skill (`SKILL.md` + scripts) |
| Something a script can reliably detect or prevent | A hook: a script plus its registration in the settings `hooks` block |
| A lesson worth remembering, but not an instruction | A gotcha or decision note in the notes repo, or project memory |
| A missing tool | An install, after vetting the source and licence; it needs explicit approval |

**With a setup repo:** portable, shareable items go in its shared part. Anything with machine paths or personal data goes in its personal part. Follow the repo's README.

## 5. Remove duplicates
- Before proposing, grep CLAUDE.md files, skills, hooks and notes for existing coverage.
- If something covers it but fails, propose an **edit**, not a new item.
- Do not re-propose items marked rejected in an earlier retro unless there is new evidence; if so, say what is new.

## 6. Propose; build nothing yet
1. Show a ranked table: **#, finding, evidence (counts plus 1–2 examples), root cause, proposed change, target, effort (S/M/L), risk.** Put the cheapest high-value items first.
2. Ask which to build with AskUserQuestion (multi-select, up to 4 options per question; batch if more). Offer "none" too. If that tool is not available, ask in your reply and let the user answer with numbers.
3. Large items (a new skill or hook) get a short plan in chat before building, even if approved.

## 7. Build the approved items (quality gates)
For each item:
1. **Back up** every file you change and read it before editing. With a setup repo, edit **the repo**, not `~/.claude`.
2. Make the **smallest change** that fixes the root cause. Match the existing style.
3. **Test, based on the requirement and not the code:**
   - **Hooks:** scenario tests with fake inputs that cover allow, block or nudge, repeat and broken-input cases, plus one run on a real transcript or file. A hook must never break the tool it wraps: on any error it exits 0.
   - **Scripts and skills:** run them on real inputs, and compare the output with known facts.
   - **CLAUDE.md:** check it is valid UTF-8 with no mojibake (no `â€`, `â†`), and check the line count.
   - **Settings:** they must parse as JSON, and every hook they list must exist. Back them up first.
4. **Install:** with a setup repo, run `setup_install`, then `setup_check`; it must report "in sync".
5. **Secrets check:** no passwords, tokens or personal data in any new file or snippet, and nothing personal in the setup repo's shared part.
6. **Commit only this run's files:**
   - setup repo: stage files by name, review the diff, commit, and push only if the user agreed;
   - notes repo: `PY SK/scripts/commit_own.py --file <rel path> ... --log-match "<your log line>" --message "..."`. Other sessions' uncommitted work and log lines stay untouched.
7. Report each item as built + verified, or not built and why. With a setup repo, an item is "built" only when it is on the default branch and installed. Until then, report it as "built, not merged" and name the branch or PR.

## 8. Record
1. Copy `SK/retro-template.md` to `<retros_dir>/YYYY-MM-DD <topic>.md`. Fill it in, with `covers_since` and `covers_until` and every finding's decision: approved and built / built, not merged / approved, not built / rejected / deferred.
2. With a notes repo: add one line to `notes_log` and commit with `commit_own.py`.
3. Reply with a 3–6 line summary and the note path.

## Rules
- Evidence beats impressions. Each finding cites counts or a concrete example.
- Never change permissions, security settings or credentials. Never weaken a hook to make it pass.
- Follow the user's CLAUDE.md style in replies.
- If an end-of-session nudge hook is installed, tune its thresholds only when the evidence shows it fires too often or misses bumpy sessions.
