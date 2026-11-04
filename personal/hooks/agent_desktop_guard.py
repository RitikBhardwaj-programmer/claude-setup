"""PreToolUse hook for Bash and PowerShell: ask the user before risky agent-desktop actions.

agent-desktop (Vercel Labs) operates native apps through the accessibility tree. The 2026-11-04
Notepad test showed that a wrong action is easy: an old ref repeated a click, and `set-value`
replaces all the text in a field (Notepad had reopened the user's own files). This hook finds each
`agent-desktop <subcommand>` in the command and returns permissionDecision "ask" when:
- a ref action (click, toggle, select, ...) targets an element whose name looks irreversible
  (looked up read-only with `agent-desktop get <ref>`), or the name cannot be looked up;
- set-value / clear targets a field that already has text;
- input is physical (--headed, hover, drag, mouse-*), in bulk (batch, dismiss-all-notifications),
  forced (--force on any subcommand), a key that may confirm or close (return, enter, delete,
  alt+f4, ctrl+w), or `launch` passes --arg / --env (can run any program).
It never denies: the user decides. It sees only the command line, not inside script files
(the desktop-control skill says to run changing actions as direct calls).
`--help` calls and text that only mentions the tool inside quotes are ignored.
Never breaks the tool: any error -> exit 0 with no output.
"""
import json
import re
import shutil
import subprocess
import sys

TOOLS = {"Bash", "PowerShell"}
REF_ACTIONS = {"click", "double-click", "triple-click", "right-click", "toggle", "check",
               "uncheck", "select"}
OVERWRITE = {"set-value", "clear"}
PHYSICAL = {"hover", "drag", "mouse-move", "mouse-click", "mouse-wheel", "mouse-down", "mouse-up"}
BULK = {"batch", "dismiss-all-notifications"}
RISKY = re.compile(
    r"\b(delete|remove|send|submit|pay|purchase|buy|order|discard|don[’']?t save|erase|format|"
    r"uninstall|sign out|log ?out|reset|wipe|trash|overwrite|replace|confirm|ok|yes|"
    r"empty recycle bin)\b", re.IGNORECASE)
CONFIRM_KEYS = {"return", "enter", "delete", "del"}
REF = re.compile(r"^@s[a-z0-9]+:e\d+$", re.IGNORECASE)
# The npm shim, the native binary (agent-desktop-win32-x64.exe) and quoted full paths.
START = re.compile(r"(?<![\w-])agent-desktop(?:-win32-(?:x64|arm64))?(?:\.exe|\.cmd|\.ps1|\.js)?"
                   r"(?=[\s'\"])", re.IGNORECASE)
WITH_VALUE = {"--session", "--agent-id", "--app", "--window-id", "--timeout-ms", "--timeout",
              "--trace", "--screenshot", "--wait-for", "-w", "--wait-for-gone", "--wait-timeout",
              "--property", "--direction", "--amount", "--expected-app", "--expected-title",
              "--interval-ms", "--arg", "--env", "--cwd", "--surface", "--root", "--max-depth",
              "--element", "--window", "--text"}
GET_TIMEOUT = 5
MAX_LOOKUPS = 3  # 3 x 5 s stays inside the 20 s hook timeout in settings.hooks.json


def quote_state(command: str, end: int, esc: str):
    """The open quote character at position `end`, or None."""
    quote, i = None, 0
    while i < end:
        ch = command[i]
        if quote:
            if ch == quote:
                quote = None
        elif ch == esc:
            i += 1
        elif ch in "'\"":
            quote = ch
        i += 1
    return quote


def tokens_after(command: str, pos: int, esc: str) -> list:
    """Shell-like tokens from pos to the first unquoted ; | & ) } or newline.
    `esc` is the escape character: backslash in Bash, backtick in PowerShell."""
    out, cur, quote, i = [], "", None, pos
    while i < len(command):
        ch = command[i]
        if quote:
            if ch == quote:
                quote = None
            else:
                cur += ch
        elif ch == esc and i + 1 < len(command):
            i += 1
            if command[i] != "\n":  # escaped newline = line continuation
                cur += command[i]
        elif ch in "'\"":
            quote = ch
            if not cur and i + 1 < len(command) and command[i + 1] == ch:
                out.append("")  # keep an empty quoted argument ('') as a token
        elif ch in ";|&)}\n":
            break
        elif ch.isspace():
            if cur:
                out.append(cur)
            cur = ""
        else:
            cur += ch
        i += 1
    if cur:
        out.append(cur)
    return out


def invocations(command: str, esc: str) -> list:
    found = []
    for m in START.finditer(command):
        pos = m.end()
        open_quote = quote_state(command, m.start(), esc)
        if open_quote:
            # Inside quotes: a real call only if the quoted word ends here (& "agent-desktop" ...,
            # & 'C:\...\agent-desktop.cmd' ...). Otherwise it is text that mentions the tool.
            if command[pos:pos + 1] != open_quote:
                continue
            pos += 1
        found.append(tokens_after(command, pos, esc))
    return found


def split_args(toks: list):
    """Return subcommand, positional args, and options."""
    sub, pos, opts, i = None, [], {}, 0
    while i < len(toks):
        t = toks[i]
        if t.startswith("-") and len(t) > 1 and not REF.match(t):
            name, _, val = t.partition("=")
            if not val and name in WITH_VALUE and i + 1 < len(toks):
                val = toks[i + 1]
                i += 1
            opts[name] = val or True
        elif sub is None:
            sub = t.lower()
        else:
            pos.append(t)
        i += 1
    return sub, pos, opts


def lookup_text(ref: str, opts: dict, prop: str = "text"):
    """Read-only `agent-desktop get <ref> --property <prop>`. Returns (text, error).
    "text" gives the name for buttons; fields need "value" (text gives a document's name)."""
    exe = shutil.which("agent-desktop")
    if not exe:
        return None, "agent-desktop is not on PATH for the hook"
    cmd = [exe, "get", ref, "--property", prop]
    for name in ("--session", "--agent-id"):
        if isinstance(opts.get(name), str):
            cmd += [name, opts[name]]
    try:
        p = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8",
                           errors="replace", timeout=GET_TIMEOUT)
        data = json.loads(p.stdout.strip().splitlines()[-1])
    except Exception as e:
        return None, f"lookup failed ({type(e).__name__})"
    if not data.get("ok"):
        return None, (data.get("error") or {}).get("code") or "lookup failed"
    return str((data.get("data") or {}).get("value") or ""), None


def risky_combo(combo: str) -> bool:
    keys = {k.strip().lower() for k in combo.split("+")}
    last = combo.split("+")[-1].strip().lower()
    return last in CONFIRM_KEYS or {"alt", "f4"} <= keys or keys == {"ctrl", "w"}


def check(toks: list, budget: list) -> list:
    """Reasons to ask for one invocation. `budget` is a one-item list: lookups left."""
    sub, pos, opts = split_args(toks)
    if not sub or "--help" in opts or "-h" in opts or sub == "help":
        return []
    reasons = []
    if "--headed" in opts or sub in PHYSICAL:
        reasons.append(f"`{sub}` uses physical input (moves the mouse or takes focus)")
    if sub in BULK:
        reasons.append(f"`{sub}` acts in bulk and the hook cannot check each step")
    if "--force" in opts:
        reasons.append(f"`{sub} --force` overrides a safety check (kills the app, or sends a "
                       "blocked shortcut)")
    if sub == "launch" and ("--arg" in opts or "--env" in opts):
        reasons.append("`launch` with --arg/--env can run any program with any arguments")
    if sub == "press" and pos and risky_combo(pos[0]):
        reasons.append(f"`press {pos[0]}` may confirm a dialog or close a window")
    if sub == "notification-action" and len(pos) > 1 and RISKY.search(pos[1]):
        reasons.append(f"notification action '{pos[1]}' looks irreversible")
    if sub in REF_ACTIONS or sub in OVERWRITE:
        ref = pos[0] if pos else ""
        if not REF.match(ref):
            reasons.append(f"`{sub}` ref '{ref}' is not a literal ref (a variable?), so its name "
                           "cannot be checked")
            return reasons
        if budget[0] <= 0:
            reasons.append(f"`{sub} {ref}`: too many actions in one command to check them all")
            return reasons
        budget[0] -= 1
        text, err = lookup_text(ref, opts, "value" if sub in OVERWRITE else "text")
        if err:
            reasons.append(f"`{sub} {ref}`: could not read the element name ({err})")
        elif sub in OVERWRITE:
            if text.strip():
                reasons.append(f"`{sub} {ref}` replaces a field that already holds "
                               f"{len(text)} characters of text")
        else:
            hit = RISKY.search(text) or (sub == "select" and len(pos) > 1 and RISKY.search(pos[1]))
            if hit:
                reasons.append(f"`{sub} {ref}` targets '{text[:80]}', which looks irreversible")
    return reasons


def main():
    data = json.loads(sys.stdin.read().lstrip("﻿") or "{}")  # PowerShell pipes add a BOM
    tool = data.get("tool_name")
    if tool not in TOOLS:
        return
    command = (data.get("tool_input") or {}).get("command") or ""
    if "agent-desktop" not in command.lower():
        return
    esc = "`" if tool == "PowerShell" else "\\"
    reasons, budget = [], [MAX_LOOKUPS]
    for toks in invocations(command, esc):
        reasons += check(toks, budget)
    if not reasons:
        return
    out = {
        "hookEventName": "PreToolUse",
        "permissionDecision": "ask",
        "permissionDecisionReason": "[agent-desktop-guard] " + "; ".join(reasons) + ".",
    }
    sys.stdout.write(json.dumps({"hookSpecificOutput": out}))


if __name__ == "__main__":
    try:
        main()
    except Exception as e:  # never break the shell tools because of the guard
        print(f"agent-desktop-guard error: {e}", file=sys.stderr)
    sys.exit(0)
