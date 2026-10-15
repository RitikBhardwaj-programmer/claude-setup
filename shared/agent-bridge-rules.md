## Agent bridge (Claude Code, Antigravity, Codex)
Work moves between coding agents through a brief file in the project's `.handoff/` folder. The user carries one pasted line between apps.
- At the start of a task, if `./.handoff/` has a file with `status: open` and `to:` your name (claude, antigravity or codex), tell the user and run the `agent-handoff` skill in mode `in` before anything else.
- To pass work on, run `agent-handoff` in mode `out`. To report back, run mode `return`. If you cannot see the skill, read `~/.claude/skills/agent-handoff/SKILL.md` and follow it.
- One writer per file set: write only the files in the brief's `may_write`, and only while you hold `.handoff/LOCK`. If another agent holds the lock, stop and tell the user.
- If something you need is missing (a file, a secret, access, a tool), say exactly what and stop. Never mock, substitute or guess. Report failures as they are.
- Never wrap another vendor's agent or reuse its login: do not run `agy`, `claude` or `codex` from inside a different agent, and do not copy tokens between apps. Their terms forbid it on consumer plans. The user switches apps by hand. (The one exception is Claude Code's own `codex exec` lane, set up in its `route` skill.)
