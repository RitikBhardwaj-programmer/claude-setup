# My Claude Setup

This is my setup for **Claude Code** (the version of Claude that can work with files and code on your computer). It contains:

- **`CLAUDE.md`**: my rulebook. Claude reads it at the start of every conversation and follows it, a bit like a job contract for an assistant. It makes Claude plan first, avoid guessing, test its work and never delete your stuff without asking.
- **10 skills** (recipe cards Claude pulls out when a certain kind of job comes up):

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
| `personal/CLAUDE.personal.md` | My personal rules (explanation style, Windows shell, Brain vault, this workflow), appended to `CLAUDE.md` | Windows only |
| `personal/skills/` | Skills tied to my projects (lab-experiment-log) | Windows only |
| `personal/hooks/`, `personal/settings.hooks.json` | Hook scripts (PDF router, secret scan before publishing, retro nudge) and their registration | Windows only |
| `personal/setup.json` | Per-machine paths read by the portable skills (Python, retro notes, notes repo, this repo) | Windows only |
| `scripts/` | Windows installer logic and the drift check | — |

Skills that are links in `~/.claude/skills` (for example `brain-review`, which lives in my Brain vault's git) are managed there; the installer never overwrites a link.

**Change the setup:**
1. Edit files here (shared part if it is portable and has nothing personal, else `personal/`).
2. Install: `powershell -ExecutionPolicy Bypass -File install.ps1` (add `-DryRun` to preview). It backs up whatever it replaces to `~/.claude/backups/`, replaces only the `hooks` block of `settings.json`, and ends with a drift check.
3. Check: `py -3 scripts/check_drift.py` must say "In sync".
4. Commit and push.

**On another machine (no `personal/`):** the portable skills fall back to defaults when `~/.claude/setup.json` is missing (`python3`, retro notes in `~/.claude/retros/`, no notes repo).
