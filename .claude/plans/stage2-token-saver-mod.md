# Stage 2: token-saver mod (plan, 2026-10-23)

## Goal
Automate the token habits measured in stage 1, so the user does not have to remember them:
warn at 200k context, show which sessions still have a warm prompt cache before a break,
shrink screenshots unless a visual-design task is running, nudge big exploration into an
Explore subagent, defer the Browser-pane tools, and make graphify run by itself in the big repos.

Evidence (measured from 546 local logs, 2026-10-23): 69% of weighted cost comes from responses
with context over 200k; 124 mid-session cache rewrites = ~20% of cost; 492 Browser-pane
image results; graphify query ran in only 8 of 29 sessions in repos that have a graph, and
X-News, Networking Project, IBM-DATATHON and Hackathons have no graph at all.

## Files
| File | Change |
|---|---|
| `mods/token-saver/.claude-plugin/plugin.json` | new: manifest (shared, portable: no PC paths) |
| `mods/token-saver/hooks/hooks.json` | new: `{ "modules": ["./register.tsx"] }` |
| `mods/token-saver/hooks/register.tsx` | new: the hooks module (features A–E below) |
| `mods/token-saver/types/index.d.ts` | new: `$.state` contract |
| `mods/token-saver/hooks/*.test.ts` | new: `claude plugin test` cases |
| `.claude-plugin/marketplace.json` | new: this repo as a local marketplace that lists `token-saver` |
| `scripts/setup_lib.py`, `install.sh` | add `token-saver@claude-setup` to `PLUGINS`; add the local marketplace |
| `README.md` | one table row + one usage line |

## Features and acceptance criteria
**A. Handoff warning** (`session.measure`)
- At context >= 200k (configurable through `userConfig`), once per threshold (200k, 300k, 400k...):
  a toast and an above-prompt band "Context 2xxk: hand off at the next breakpoint", with a button that
  fills `/context-handoff` into the prompt (`$.prompt.fill`). It never submits by itself.
- Main session only; subagents do not warn.

**B. Warm-sessions pane** (`$.ui.open` + `$.clock.every`)
- Each session that loads the mod writes `~/.claude/token-saver/sessions/<id>.json`
  (`cwd`, title, last response time, context tokens) on every `session.measure`.
- Slash command `/warm` opens a pane: one row per session with last response < 60 min ago:
  project, context size, minutes until the 1-hour cache expires, and the cost of letting it go cold
  (context x 2 cache-write units). Sorted by that cost. Refreshes every 60 s. Old files (> 1 day) are ignored.
- Labelled as an estimate: the server's cache state cannot be read, only inferred from the TTL.

**C. Screenshot auto-scale** (`tool.call` on `mcp__Claude_Browser__computer` and `browser_batch`)
- A `screenshot` / `zoom` with no `scale` gets `scale: 0.5`. An explicit `scale` is never changed.
- Visual mode turns it off for the session when `skill.prompt` fires for `ui-design`,
  `frontend-design:frontend-design`, `artifact-design` or `dataviz`, or `agent.spawn` starts `design-review`.
  `/token-saver visual on|off` sets it by hand.

**D. Explore nudge** (`tool.call` on `Read`, `Grep`, `Glob`, main agent only)
- After 8 such calls in one user turn, one note per turn suggests an Explore subagent.
  Delivery: appended to the tool result if the API allows it (to verify), else a status-line entry.
  It never blocks a call.

**E. Browser-tool deferral** (`tool.describe`)
- `mcp__Claude_Browser__*` gets `isDeferred: true`; ToolSearch loads them when needed.
  A `userConfig` switch turns it off. Answer fixed at session start (no mid-session cache bust).

**F. graphify (no mod code)**: in each repo the user picks: `graphify update .` (AST only, no LLM),
`graphify hook install` (post-commit update), `graphify claude install` (PreToolUse nudge hook).

## Risks
- A mod bug could block tool calls: every hook passes through with `next(e)` on any error (`.catch`).
- `browser_batch` items and the `scale` field name must match the live tool schema (check `claude-code-mcp` types).
- Unverified API points, checked first in the build: tool-result append (D), absolute `$.fs.write` outside
  the project (B), local-directory marketplace install (Files), desktop-app pane placement (B).
- Deferring Browser tools adds one ToolSearch response in sessions that use them (~49 of 554).
- Turning the mod on changes the tool list: it takes effect in new sessions only.

## Verification
- `claude plugin validate mods/token-saver` and `tsc -p mods/token-saver`.
- `claude plugin test mods/token-saver`: A thresholds (199k no warn, 201k warn, once only), C scale added /
  explicit scale kept / visual mode skips, D 8th call nudges once, E deferral flag.
- Manual: new session -> `/context` shows the Browser tools deferred; `/warm` lists this session;
  a screenshot result is smaller; `check_drift.py` in sync after `install.ps1`.

## Routing card
| Phase | Agent | Model | Effort | Why |
|---|---|---|---|---|
| Verify the 4 open API points | Explore subagent in the build session | haiku | low | grep in the 14k-line types file; easy to check |
| Build A–E + tests + installer | new session from this plan | sonnet | medium | clear plan; failures are loud (validate, tsc, tests) |
| Review the diff | subagent | opus | high | tool.call rewrites can fail quietly |
| F: graphify per repo | build session, after the user picks repos | sonnet | low | three CLI commands per repo |
Codex handoffs: none (the mod needs the Claude Code engine to test).
Antigravity handoffs: none.
Switch needed: build in a new session at sonnet/medium. This session is Opus with a large context.
