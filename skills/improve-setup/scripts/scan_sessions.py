"""Mine Claude Code session transcripts for friction signals (read-only, stdlib only).

Usage:
  python3 scan_sessions.py --since 2026-10-04T00:00 [--project "My Project"] [--session ID] [--json]

Reads ~/.claude/projects/*/*.jsonl (top-level sessions; add --subagents for sidechains) and reports,
for entries at or after --since:
  - tool calls, errored tool results grouped by a normalised signature (hook denials included)
  - user rejections of tool calls (with the user's feedback text), plan rejections (ExitPlanMode)
  - timeouts, retry loops (same command 3+ times), "user hasn't heard from you" reminders (slow, quiet work)
  - skills invoked, most edited files
  - signals repeated in 2+ sessions
Snippets are short and redacted (secret patterns, e-mail addresses). Transcripts are never modified.
"""
import argparse
import json
import re
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

PROJECTS = Path.home() / ".claude" / "projects"
SNIP = 200
REJECT = "doesn't want to proceed"
REDACT = [
    re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----.*?-----END [A-Z ]*PRIVATE KEY-----", re.S),
    re.compile(r"\bAKIA[0-9A-Z]{16}\b"), re.compile(r"\bgh[pousr]_[A-Za-z0-9]{36,}\b"),
    re.compile(r"\bxox[abprs]-[A-Za-z0-9-]{10,}\b"), re.compile(r"\bsk-(?:ant-)?[A-Za-z0-9_-]{20,}\b"),
    re.compile(r"\beyJ[A-Za-z0-9_-]{10,}\.eyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\b"),
    re.compile(r"(?i)(\b[A-Za-z0-9_]*(?:password|passwd|secret|api[_-]?key|token)[A-Za-z0-9_]*\s*[:=]\s*)\S{6,}"),
    re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+"),
]


def redact(text, n=SNIP):
    text = " ".join(str(text).split())
    for rx in REDACT:
        text = rx.sub(lambda m: (m.group(1) if m.groups() else "") + "[REDACTED]", text)
    return text[:n] + ("…" if len(text) > n else "")


ERRORISH = re.compile(r"(?i)error|failed|fail\b|timed? ?out|not found|denied|invalid|exception|traceback|"
                      r"unexpected|cannot|can't|no such|refused|missing")


def signature(text):
    """Normalise an error message so the same problem groups together.

    Prefer the most error-like line (not 'Exit code 2' or a batch's first successful step)."""
    lines = [ln.strip() for ln in str(text).splitlines() if ln.strip()]
    useful = [ln for ln in lines if not re.fullmatch(r"(?i)exit code \d+", ln)]
    first = next((ln for ln in useful if ERRORISH.search(ln)), useful[0] if useful else "")[:300]
    s = re.sub(r"[A-Za-z]:[\\/][^\s'\"]*|/(?:c|tmp|usr|home)/[^\s'\"]*", "<path>", first)
    s = re.sub(r"\b[0-9a-f]{8,}\b", "<id>", s)
    s = re.sub(r"\d+(\.\d+)?", "<n>", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s[:140]


def result_text(block):
    c = block.get("content")
    if isinstance(c, str):
        return c
    if isinstance(c, list):
        return " ".join(x.get("text", "") for x in c if isinstance(x, dict))
    return ""


def parse_ts(s):
    try:
        return datetime.fromisoformat(s.replace("Z", "+00:00"))
    except (ValueError, AttributeError):
        return None


def project_name(folder):
    # folder names look like C--Users-NAME-My-Project (the cwd in the entries is preferred)
    parts = folder.split("--")
    return parts[-1].replace("-", " ") if parts else folder


def scan_file(path, since):
    s = {"session": path.stem, "project": project_name(path.parent.name), "title": "", "tools": 0,
         "errors": [], "rejections": [], "plan_rejections": 0, "timeouts": 0, "quiet_reminders": 0,
         "bg_failures": [],
         "skills": Counter(), "edits": Counter(), "commands": Counter(), "first": None, "last": None}
    tool_names = {}
    with path.open(encoding="utf-8", errors="replace") as fh:
        for line in fh:
            try:
                o = json.loads(line)
            except ValueError:
                continue
            t = o.get("type")
            if t == "custom-title" and o.get("customTitle"):
                s["title"] = o["customTitle"]
            if o.get("cwd") and s["project"] == project_name(path.parent.name):
                s["project"] = Path(o["cwd"]).name or s["project"]
            ts = parse_ts(o.get("timestamp", ""))
            if ts is None or ts < since:
                continue
            s["first"] = s["first"] or ts
            s["last"] = ts
            if t == "attachment":
                a = o.get("attachment") or {}
                if a.get("type") == "silent_turn_reminder":
                    s["quiet_reminders"] += 1
                elif a.get("type") == "queued_command" and "<status>failed</status>" in str(a.get("prompt", "")):
                    m = re.search(r"<summary>(.*?)</summary>", str(a.get("prompt", "")), re.S)
                    s["bg_failures"].append(redact(m.group(1) if m else "background task failed"))
                continue
            content = (o.get("message") or {}).get("content")
            if not isinstance(content, list):
                continue
            for b in content:
                if not isinstance(b, dict):
                    continue
                if t == "assistant" and b.get("type") == "tool_use":
                    name, inp = b.get("name", ""), b.get("input") or {}
                    tool_names[b.get("id")] = name
                    s["tools"] += 1
                    if name == "Skill":
                        s["skills"][inp.get("skill", "?")] += 1
                    elif name in ("Write", "Edit", "NotebookEdit"):
                        s["edits"][inp.get("file_path", "?")] += 1
                    elif name in ("Bash", "PowerShell"):
                        s["commands"][" ".join(str(inp.get("command", "")).split())[:300]] += 1
                elif t == "user" and b.get("type") == "tool_result":
                    text = result_text(b)
                    name = tool_names.get(b.get("tool_use_id"), "?")
                    if text.lstrip().startswith("The user " + REJECT) or text.lstrip().startswith("The user doesn"):
                        said = text.split("the user said:", 1)[-1] if "the user said:" in text else ""
                        s["rejections"].append((name, redact(said.strip())))
                        if name == "ExitPlanMode":
                            s["plan_rejections"] += 1
                    elif b.get("is_error"):
                        s["errors"].append((name, signature(text), redact(text)))
                        if re.search(r"(?i)timed? ?out", text):
                            s["timeouts"] += 1
    return s if s["first"] else None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--since", required=True, help="ISO time, e.g. 2026-10-04T00:00 (local time if no zone)")
    ap.add_argument("--project", help="substring of the project folder name, e.g. 'My Project'")
    ap.add_argument("--session", help="only this session id")
    ap.add_argument("--subagents", action="store_true")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")
    since = datetime.fromisoformat(a.since)
    if since.tzinfo is None:
        since = since.astimezone()
    since = since.astimezone(timezone.utc)

    files = sorted(PROJECTS.glob("*/**/*.jsonl" if a.subagents else "*/*.jsonl"))
    if a.project:
        key = a.project.lower().replace(" ", "-")
        files = [f for f in files if key in f.parent.name.lower() or key in str(f).lower()]
    if a.session:
        files = [f for f in files if f.stem == a.session]
    files = [f for f in files if datetime.fromtimestamp(f.stat().st_mtime, timezone.utc) >= since]
    sessions = [s for s in (scan_file(f, since) for f in files) if s]

    if a.json:
        out = [{**s, "first": str(s["first"]), "last": str(s["last"]), "skills": dict(s["skills"]),
                "edits": dict(s["edits"].most_common(10)), "commands": None} for s in sessions]
        print(json.dumps(out, indent=1, default=str))
        return 0

    sig_sessions, sig_count, sig_example = defaultdict(set), Counter(), {}
    for s in sessions:
        for name, sig, snip in s["errors"]:
            key = f"{name}: {sig}"
            sig_sessions[key].add(s["session"][:8])
            sig_count[key] += 1
            sig_example.setdefault(key, snip)

    print(f"# Session scan since {a.since}\n")
    print(f"{len(sessions)} session(s); {sum(s['tools'] for s in sessions)} tool calls; "
          f"{sum(len(s['errors']) for s in sessions)} errored results; "
          f"{sum(len(s['rejections']) for s in sessions)} rejections.\n")
    print("## Sessions\n")
    print("| Session | Project | Title | Tools | Errors | Rejections (plan) | Timeouts | Quiet reminders |")
    print("|---|---|---|---|---|---|---|---|")
    for s in sorted(sessions, key=lambda x: x["first"]):
        print(f"| {s['session'][:8]} | {s['project']} | {redact(s['title'], 50)} | {s['tools']} | {len(s['errors'])} | "
              f"{len(s['rejections'])} ({s['plan_rejections']}) | {s['timeouts']} | {s['quiet_reminders']} |")

    print("\n## Errors grouped by signature (most frequent first)\n")
    for key, n in sig_count.most_common(20):
        rep = " **[repeated in 2+ sessions]**" if len(sig_sessions[key]) > 1 else ""
        print(f"- **{n}×** in {len(sig_sessions[key])} session(s){rep}: `{key}`\n  - e.g. {sig_example[key]}")

    print("\n## Rejections and user feedback\n")
    any_rej = False
    for s in sessions:
        for name, said in s["rejections"]:
            any_rej = True
            print(f"- {s['session'][:8]} · {name}: {said or '(no text)'}")
    if not any_rej:
        print("- none")

    print("\n## Background tasks that failed\n")
    bg = [(s["session"][:8], f) for s in sessions for f in s["bg_failures"]]
    for sid, f in bg:
        print(f"- {sid}: {f}")
    if not bg:
        print("- none")

    print("\n## Retry loops (same command 3+ times in a session)\n")
    loops = [(s["session"][:8], c, n) for s in sessions for c, n in s["commands"].items() if n >= 3 and c]
    for sid, c, n in sorted(loops, key=lambda x: -x[2])[:10]:
        print(f"- {sid}: {n}× `{redact(c, 120)}`")
    if not loops:
        print("- none")

    skills = Counter()
    edits = Counter()
    for s in sessions:
        skills.update(s["skills"])
        edits.update(s["edits"])
    print("\n## Skills used\n")
    print(", ".join(f"{k} ({v})" for k, v in skills.most_common()) or "none")
    print("\n## Most edited files\n")
    for f, n in edits.most_common(10):
        print(f"- {n}× {f}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
