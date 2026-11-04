---
name: desktop-control
description: "Operate native desktop apps (Windows, macOS, Linux) through the OS accessibility tree with the agent-desktop CLI (Vercel Labs), instead of screenshots and pixel clicks. Use when a task needs a desktop app that has no API, CLI or file format and is not a web page: File Explorer, Windows Settings, classic Win32 dialogs, the system tray or notifications, a GUI-only lab tool, or testing and accessibility-auditing the user's own desktop app. Also on /desktop-control, 'use agent-desktop', 'click X in <app>', 'read the text from <app>'. Skip for web pages (use the browser tools), Office files (use their libraries), tools with a CLI, and custom-drawn canvases or games (use screenshot computer use)."
---

# Desktop control (agent-desktop)

agent-desktop reads an app's accessibility tree (the structured map of the UI that screen readers use) and returns JSON with a ref for each element. You act on refs, not on screen coordinates. It needs no screenshots and, by default, does not move the user's mouse.

## Step 1: Pick the right tool

Use the first rung that fits:

1. **API, CLI or file format** (git, `tshark`, Vivado Tcl, python-docx, Office COM). Exact and fast.
2. **Web page:** the browser tools (Claude in Chrome or the built-in browser). The DOM is richer than the tree.
3. **Native app with standard controls:** this skill.
4. **Custom-drawn UI** (canvas, game, Packet Tracer topology, some WinUI 3 flyouts): screenshot computer use.

If you pick rung 3, say why rungs 1 and 2 do not fit, in one line.

## Step 2: Set up

1. Check it is installed: `agent-desktop status`. If it is missing, tell the user the install command (`npm install -g agent-desktop`) and ask before installing.
2. Load the guides that match the installed version. They are built into the binary:
   - `agent-desktop skills get desktop` (the core loop, verification, retries)
   - `agent-desktop skills get windows` (or `macos`, `linux`)
3. Use `agent-desktop <command> --help` for flags. Do not guess flags.

## Step 3: The loop

Repeat for each step of the task:

1. **Observe:** `agent-desktop snapshot --app <name> -i --compact`. For a large app, use `--skeleton`, then `--root <ref>` to read one subtree.
2. **Act once:** one action on one ref from **this** snapshot.
3. **Verify:** `get <ref>`, `is <ref> --property <state>`, `wait --text '<text>'`, or `snapshot --app <name> --wait-for 'role:text'`. Read the action's own `disposition.delivery` (`delivered_verified` is best).
4. **Re-snapshot** before the next action.

Rules:
- **Never reuse a ref from an older snapshot.** Old refs can still resolve and repeat an action (measured: an old "Add New Tab" ref opened a second tab). Actions report `retry: unsafe`, so do not retry them blindly.
- **Quote every ref in PowerShell:** `agent-desktop click '@s8f3k2p9:e8'`. A bare `@token` is the splatting operator.
- **PowerShell 5.1 drops empty-string arguments.** Use `agent-desktop clear <ref>`, not `set-value <ref> ''`.
- Use `--session <name>` so refs from separate tasks do not mix.

## Step 4: Protect the user's work

- **Work in a fresh window or tab.** Apps often restore the user's files on launch (Notepad reopens old tabs). Do not act inside a file, tab or document the user already had open unless they asked.
- **`set-value` replaces all the text** in the field. Before you use it, check the field with `get <ref>`. If it has text and the user did not ask you to replace it, stop and ask.
- **Headless by default.** Use `--headed`, `hover`, `drag` or `mouse-*` (physical input that takes over the mouse) only after the user agrees.
- **Irreversible buttons need the user's yes:** send, submit, pay, buy, delete, remove, discard, uninstall, sign out, and dialog confirmations (OK, Yes, Don't save) that end such an action.
- **Snapshots, clipboard reads and screenshots can contain private data.** Do not paste them into commits, public pages or logs.

## Step 5: The safety hook (Windows setup)

On the user's Windows PC, the `agent_desktop_guard.py` hook checks each `agent-desktop` call in Bash and PowerShell before it runs. It asks the user first when a click targets a risky name, `set-value` or `clear` would overwrite text, or input is physical or in bulk.

The hook sees only the command line. It cannot see inside a script file. So:
- **Observation may run in a script** (snapshots, `find`, `get`, `wait` in a loop).
- **Every action that changes something runs as a direct `agent-desktop` call**, so the hook can check it.

## Known limits (agent-desktop 1.1.0, measured on Windows 11)

- **Speed:** about 0.5 to 1 s per CLI call, because each call starts a process. For a long observation loop, use a script. (`batch` also works, but the hook always asks before it, because it cannot check the steps.)
- **`type` needs `--headed` on Windows** (it is keystroke synthesis through `SendInput`). Headless, it returns `POLICY_DENIED`, and so do `right-click`, `double-click`, `triple-click` and `focus`. Use `set-value` when the field is empty or the user agreed.
- **Gaps in the tree:** WinUI 3 flyout menus (Notepad's File menu) and some hover-only buttons (Notepad's per-tab Close) were not in the tree. Do not loop on a missing element. After two failed snapshots, report it and propose the next rung.
- **Electron and Chromium apps** expose a tree only when accessibility is on. See `agent-desktop skills get windows` (`chromium-and-electron` reference) and `--force-electron-a11y`.
- **No MCP server mode** in 1.1.0 (`agent-desktop mcp` is not a command). Call the CLI from the shell.

## Accessibility audit (for the user's own apps)

If agent-desktop cannot see a control, a screen reader cannot see it either. To audit an app:
1. `launch <app> --activate`, then `snapshot --app <app> -i`.
2. Report interactive elements with an empty `name`, a generic role (`group`, `pane`) where a button is expected, or no `available_actions`.
3. Give each finding the element path and a fix (for example: add `aria-label`, `AutomationProperties.Name`, or an accessible name in the UI framework).
