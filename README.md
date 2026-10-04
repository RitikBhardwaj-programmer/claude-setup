# My Claude Setup

This is my setup for **Claude Code** (the version of Claude that can work with files and code on your computer). It contains:

- **`CLAUDE.md`**: my rulebook. Claude reads it at the start of every conversation and follows it, a bit like a job contract for an assistant. It makes Claude plan first, avoid guessing, test its work and never delete your stuff without asking.
- **4 skills** (recipe cards Claude pulls out when a certain kind of job comes up):

| Skill | What it does | How to use it |
|---|---|---|
| **context-handoff** | When a chat gets too long, writes a short "where we are" note so a new chat can carry on without losing anything | say "hand this off" |
| **context-handoff-deep** | A more thorough version that also double-checks the code and its history | say "deep handoff" |
| **graphify** | Draws a mind-map of a project showing how all the files connect, so Claude can understand it quickly | type `/graphify` |
| **llm-council** | Five helper Claudes look at a decision from different angles, judge each other's answers, and a "chairman" gives one final answer | say "council this" or ask "should I X or Y?" |

Nothing private is in here: no passwords, no login keys, no project notes.

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
