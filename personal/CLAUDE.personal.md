<!-- Personal part of ~/.claude/CLAUDE.md on this Windows PC. install.ps1 appends it to the shared
     CLAUDE.md. It is never installed on Mac. -->

## Explanation style (all projects, all topics)
I am an IT student and want to learn the real technical vocabulary. Don't dumb explanations down.
- Use technical terms freely. Put a short plain-language explanation in brackets right after each term, e.g. "quantile regression (predicting a range like best/likely/worst case instead of one number)".
- Always include concrete examples and analogies for the ideas you explain.
- Start from the "why": before a formula, rule or answer, state in 1–2 lines the puzzle or need that makes the idea necessary. A name or a restatement is not a reason. For a deeper build-up, offer `/intuition`.
- Raise the technical depth gradually over time (more advanced concepts and maths).
- ALWAYS bracket-explain every technical term each time it appears in a response, even if an earlier response already explained it. Never assume a term is known. A higher level means deeper content, not dropped definitions.

## New ideas
When I bring an idea or ask to build, automate or add something new ("I want to...", "what if we..."), run the augment-lens skill first, then ask build questions in the same reply. Skip it when I say "just build it" or the task is a fix, lookup or explanation.

## Windows environment
- Shells are Git Bash and PowerShell 5.1. Set `PYTHONIOENCODING=utf-8` when Python prints non-ASCII; the console is cp1252.
- Write scripts longer than ~15 lines, or with Windows backslash paths, to a scratchpad file with the Write tool. Don't use heredocs or `python -c` for them.
- If a file shows `â†’`/`â€“`, it is UTF-8 saved as cp1252: repair it with `line.encode("cp1252").decode("utf-8")`, after a backup.

## Knowledge base (Brain vault)
My long-term notes are in `C:\Users\DELL\Brain` (a junction to `C:\Users\DELL\OneDrive\Brain`), available through the `basic-memory` MCP server (project `brain`) and as plain files.
- At the start of a non-trivial task, search the vault for the project or topic; read `Index.md` only if search finds nothing useful.
- When you learn a lasting decision, gotcha or pattern, save it to the matching note following `Vault Rules.md`.
- Never delete vault notes; the vault is in git.

## Claude setup repo
My Claude Code setup (CLAUDE.md, skills, hooks, hook settings) is managed in the git repo `C:\Users\DELL\claude-setup`; it is the source of truth.
- Change files in the repo, never directly in `~/.claude`. Shared, portable parts go at the top level (they also install on my friend's Mac); anything with this PC's paths or my personal data goes under `personal/`.
- Then run `powershell -ExecutionPolicy Bypass -File C:\Users\DELL\claude-setup\install.ps1`, check `py -3 C:\Users\DELL\claude-setup\scripts\check_drift.py` reports no drift, commit and push.
- Per-machine paths live in `~/.claude/setup.json` (from `personal/setup.json`); portable skills read it.
