# My Claude Setup

This is my setup for **Claude Code** (the version of Claude that can work with files and code on your computer). It contains:

- **`CLAUDE.md`**: my rulebook. Claude reads it at the start of every conversation and follows it, a bit like a job contract for an assistant. It makes Claude plan first, avoid guessing, test its work and never delete your stuff without asking.
- **13 skills** (recipe cards Claude pulls out when a certain kind of job comes up):

| Skill | What it does | How to use it |
|---|---|---|
| **context-handoff** | When a chat gets too long, writes a short "where we are" note so a new chat can carry on without losing anything | say "hand this off" |
| **context-handoff-deep** | A more thorough version that also double-checks the code and its history | say "deep handoff" |
| **graphify** | Draws a mind-map of a project showing how all the files connect, so Claude can understand it quickly | type `/graphify` |
| **llm-council** | Five helper Claudes look at a decision from different angles, judge each other's answers, and a "chairman" gives one final answer | say "council this" or ask "should I X or Y?" |
| **explain** | Explains a topic, file or error in the clearest form: short plain prose, a diagram, or an interactive page | type `/explain <thing>` |
| **report-publisher** | Turns a write-up into a professional web page and an A4 PDF, with diagrams and automatic layout checks | say "make a report/PDF of this" |
| **vendor-requirements-spec** | Writes a requirement spec for a purchase (numbered MUST/SHOULD items, tests, questions) plus an Excel sheet vendors fill in | say "write the requirements for the vendor" |
| **improve-setup** | Looks back at your recent Claude sessions, finds what went wrong or slowly, and proposes fixes to your rulebook and skills; builds only what you approve | type `/improve-setup` |
| **youtube-transcript** | Gets the text of a YouTube video from its link (clean paragraphs with time marks), so Claude can summarise it or answer questions about it | paste a YouTube link and ask |
| **intuition** | Teaches a topic or works through a problem the way physics teacher Mahesh Shenoy does: start from what is confusing, show why the obvious answer fails, find the real cause, and only then the formula. It can quiz you, explain, solve, or check your own explanation | type `/intuition <topic>` or say "build my intuition for X" |
| **agent-handoff** | Passes work between Claude Code, Antigravity and Codex through a short brief file in the project (`.handoff/`). You switch apps by hand and paste one line; the skill writes the brief, checks it against git, locks the files so only one agent writes at a time, and writes the result back | say "hand this to Antigravity" or paste the line it gives you |
| **route** | Before a bigger job starts, picks which Claude model and how much "thinking effort" each part of the job gets (strong model to plan, cheaper one to build, cheapest to search), so your usage limit lasts longer. It can also hand self-contained parts to Codex if you have it | it runs by itself in plans, or type `/route` |
| **ui-design** | When Claude builds or restyles a web page, dashboard or app screen, it follows clear design rules (no generic "AI look", real colours and fonts from your project, accessibility), then looks at its own result in a browser at desktop, tablet and phone size and fixes what it sees | it runs by itself on UI work, or type `/ui-design` |

- **1 helper agent** (a second Claude with its own fresh memory that does one job and reports back):
  - **design-review**: checks a finished screen like a senior designer would (flows, three screen sizes, polish, accessibility, error and empty states) and lists problems from "Blocker" to "Nit". It only reports; it never changes your code. Adapted from [OneRedOak/claude-code-workflows](https://github.com/OneRedOak/claude-code-workflows) (MIT licence).
- **3 plugins** (a ready-made add-on; two from Anthropic's official plugin store, one from this repo):
  - **frontend-design**: Anthropic's own design skill that pushes Claude towards bold, distinctive designs instead of the average look. The installer adds it for you with `claude plugin install`.
  - **claude-security**: Anthropic's multi-agent vulnerability scanner. Run `/claude-security` in a repo to scan it and get a report (and optional patch files you apply yourself).
  - **token-saver** (a mod in `mods/token-saver/`): saves tokens by itself. It warns at 200k context, shows sessions with a still-warm prompt cache (`/warm`), shrinks Browser-pane screenshots (not during visual design; `/token-saver visual on|off`), nudges toward an Explore subagent, and lists the Browser tools behind ToolSearch. Installed from this repo as the local marketplace `claude-setup`. Takes effect in new sessions.

Nothing private is in the parts the Mac installer uses: no passwords, no login keys, no project notes. The `personal/` folder is my own Windows PC's configuration; the Mac installer never touches it.

---

## Install (one time, about 5 minutes)

**Step 1: Get Claude.** Install the Claude desktop app (from claude.ai/download) and sign in with **your own** account. You'll use the **Code** tab.

**Step 2: Open Terminal.** Press `Cmd + Space`, type **Terminal** and press Enter. The Terminal is a window where you type commands to the Mac.

**Step 3: Download this setup.** First accept the GitHub invite email. **GitHub** is the website where this setup is stored. Then paste this into Terminal and press Enter:

```bash
git clone https://github.com/RitikBhardwaj-programmer/claude-setup.git ~/claude-setup
```

`git clone` means "download a copy". If the Mac asks to install "command line developer tools", click **Install**, wait for it to finish, then run the command again. If it asks you to log in, use your GitHub account.

**Step 4: Install it.**

```bash
bash ~/claude-setup/install.sh
```

This copies everything into the hidden `~/.claude` folder where Claude looks for it. If you already had your own `CLAUDE.md` or skills with the same names, they're **backed up first** (the script tells you where), so nothing is lost.

**Step 5: Check it worked.** Start a **new** session in the Claude Code tab and:
- ask *"What rules from my CLAUDE.md are you following?"*. It should describe the rulebook.
- type `/`. You should see the skills in the list.

---

## Getting updates

When I improve the setup, run these two commands in Terminal:

```bash
cd ~/claude-setup && git pull
```

```bash
bash ~/claude-setup/install.sh
```

`git pull` downloads the newest version and the second command installs it.

> ⚠️ If you've edited your own `~/.claude/CLAUDE.md`, the update will replace it. Your old version is saved in the backup folder the script prints, so you can copy your changes back.

---

## Good to know

- **graphify needs Python 3** (a programming language some tools are built with; most Macs already have it). The skill installs what it needs the first time you use it. If that fails, run `pip3 install graphifyy`.
- **Make it yours:** `~/.claude/CLAUDE.md` is just a text file. Open it with `open -e ~/.claude/CLAUDE.md` and change any rule you like.
- **Optional settings I use:** dark theme, and automatic updates to the newest Claude version. You can set these in the app's Settings.
- **Graphify rule in CLAUDE.md:** the rulebook tells Claude to use the project mind-map when one exists. If a project doesn't have one, Claude just works normally.

---

## For me: Windows PC and how this repo is managed

This repo is the **source of truth** for my Claude setup. I never edit `~/.claude` directly.

| Path | What it is | Installed on |
|---|---|---|
| `CLAUDE.md`, `skills/` | Shared rulebook and portable skills | Mac and Windows |
| `agents/` | Shared subagents (design-review), copied to `~/.claude/agents/` | Mac and Windows |
| `PLUGINS` in `scripts/setup_lib.py` and `install.sh` | Marketplace plugins the installers add with `claude plugin install` (frontend-design, claude-security, token-saver); keep both lists the same | Mac and Windows |
| `mods/token-saver/`, `.claude-plugin/marketplace.json` | The token-saver mod, and this repo as a local marketplace (`claude-setup`) that lists it | Mac and Windows |
| `personal/CLAUDE.personal.md` | My personal rules (explanation style, Windows shell, Brain vault, this workflow), appended to `CLAUDE.md` | Windows only |
| `personal/skills/` | Skills tied to my projects (lab-experiment-log) | Windows only |
| `personal/hooks/`, `personal/settings.hooks.json` | Hook scripts (PDF router, secret scan before publishing, retro nudge, handoff reminder) and their registration | Windows only |
| `personal/settings.skill-overrides.json` | The `skillOverrides` block of `settings.json`: skills listed to Claude by name only, to save tokens on every response | Windows only |
| `personal/setup.json` | Per-machine paths read by the portable skills (Python, retro notes, notes repo, this repo) | Windows only |
| `shared/agent-bridge-rules.md` | The short rules block (handoff protocol, one writer per file set, never wrap another vendor's agent) that the Windows installer merges into `~/.codex/AGENTS.md` | Windows only (for now) |
| `scripts/` | Windows installer logic and the drift check | — |

Skills that are links in `~/.claude/skills` (for example `brain-review`, which lives in my Brain vault's git) are managed there; the installer never overwrites a link.

**Change the setup:**
1. Edit files here (shared part if it is portable and has nothing personal, else `personal/`).
2. Install: `powershell -ExecutionPolicy Bypass -File install.ps1` (add `-DryRun` to preview). It backs up whatever it replaces to `~/.claude/backups/`, replaces only the `hooks` block of `settings.json`, and ends with a drift check.
3. Check: `py -3 scripts/check_drift.py` must say "In sync".
4. Commit and push.

**On another machine (no `personal/`):** the portable skills fall back to defaults when `~/.claude/setup.json` is missing (`python3`, retro notes in `~/.claude/retros/`, no notes repo).

### Agent bridge (Claude Code, Antigravity, Codex)

Goal: use the three apps side by side without breaking any vendor's terms. Google's FAQ says wrapping `agy` inside third-party agents is not supported on consumer plans (https://antigravity.google/docs/faq), and Anthropic keeps subscription logins for its own apps. So no agent starts another: the **`agent-handoff` skill** writes a brief in `.handoff/`, you paste one line into the other app, and the result comes back the same way.

What the installer sets up (Windows, `personal/` part; each target only if its app folder exists, each changed file is backed up to `~/.claude/backups/<run>/home/...`, `-DryRun` previews):
- **Codex:** merges the rules block into `~/.codex/AGENTS.md` between `<!-- agent-bridge:start -->` and `<!-- agent-bridge:end -->`. Text outside the markers is never touched.
- **Antigravity skills:** writes `~/.gemini/config/skills.json` with one entry, `~/.claude/skills`, and `include_only` = `agent-handoff`, `context-handoff`, `explain`, `intuition`, `youtube-transcript` (the skills with no Claude-only tool calls; list is `PORTABLE_SKILLS` in `scripts/setup_lib.py`). Other entries in the file are kept.
- **Antigravity MCP:** adds `basic-memory` to `~/.gemini/config/mcp_config.json`, from `basic_memory_mcp` in `personal/setup.json`.
- **basic-memory single writer:** the same `basic_memory_mcp` entry (with `env`) is set as Claude Code's user-scope server through `claude mcp add-json` (the CLI owns `~/.claude.json`), and merged into Claude Desktop's `claude_desktop_config.json` (the Store build keeps it in `%LOCALAPPDATA%\Claude-Data\claude_<id>\`, older builds in `%APPDATA%\Claude\`; backed up first; other keys are kept; quit Claude Desktop from the tray and reopen it afterwards, because it rewrites the file while it runs). Its env makes every session a *reader*: `BASIC_MEMORY_INDEX_CHANGES=false` (no file watcher) and `BASIC_MEMORY_AUTO_UPDATE=false` (the auto-update saves the whole config, which would write `index_changes: false` into the shared `config.json`). The only watcher is the Task Scheduler task `BasicMemoryWriter` from `basic_memory_writer`: `basic-memory mcp --transport streamable-http` on `127.0.0.1:8765`, started hidden at logon. Why: one watcher per session made 3-4 processes embed the same note at once (`UNIQUE constraint failed: search_vector_chunks`). Run `bm update` by hand now. Open sessions keep their old server until they restart.
- **Antigravity watcher sidecar:** writes `~/.gemini/config/sidecars/handoff-watcher/sidecar.json`, which runs `skills/agent-handoff/scripts/antigravity_watcher.py`. **You enable it yourself** in Antigravity's Automations dashboard ("Agent handoff watcher"); the installer never does. Once it is on, a brief for Antigravity in a project on its watch list (`watch-dirs.txt` in the same folder, added by `handoff.py watch-add` after you agree) starts an Antigravity conversation through Antigravity's own `agentapi`, so you paste nothing. Claude waits for the return file with `handoff.py wait` in the background. Safety: it never starts briefs that git tracks, waits while another agent holds `.handoff/LOCK`, and marks a brief `claimed` before it starts it. Log: `watcher.log` in the same folder.
- **Claude hook:** `personal/hooks/handoff_check.py` (SessionStart) prints "Handoff waiting from <agent>: <file>..." when `./.handoff/` holds an open brief for Claude.
- **`route` skill:** has an Antigravity lane (the watcher, or a paste line; never `agy`).

Not done, on purpose:
- **No Antigravity global rules file.** Its docs (`agy-customizations/docs/rules.md`) list only per-directory `GEMINI.md` / `AGENTS.md`, so the installer does not guess a path. Per project, put `AGENTS.md` in the repo (Antigravity and Codex read it) and add `@AGENTS.md` to the project's `CLAUDE.md`; copy `shared/agent-bridge-rules.md` into that `AGENTS.md`.
- **No Antigravity `PreInvocation` hook.** Its docs say a `PreInvocation` hook can inject a message, but that was not tested here, so it is not shipped. The rules block ("check `.handoff/` at the start") does the job.
- **`install.sh` (Mac) is not updated:** it does not share `scripts/setup_lib.py`, and the bridge needs this PC's paths. Follow-up: mirror the Codex block and `skills.json` there if the Mac needs it.

Round trip: Claude runs `agent-handoff` out to Antigravity and prints a line; paste it in Antigravity (it runs `in`, works inside `may_write`, runs `return`); paste the return line in Claude. A second `in` while `.handoff/LOCK` is held by another agent refuses.
