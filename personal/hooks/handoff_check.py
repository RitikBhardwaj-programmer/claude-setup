"""SessionStart hook: tell Claude when another agent left it an open brief in ./.handoff/.

Read-only and fast. Prints one context line if a file in .handoff/ has `status: open` and `to: claude`;
silent otherwise (no folder, no match, any error).
"""
import re
import sys
from pathlib import Path

FIELD = re.compile(r"^(\w+):[ \t]*(.*?)[ \t]*$")


def frontmatter(path: Path):
    """Top-level `key: value` pairs of the leading ---/--- block, or {} when there is none."""
    try:
        with path.open(encoding="utf-8", errors="replace") as f:
            if f.readline().strip() != "---":
                return {}
            out = {}
            for _ in range(60):
                line = f.readline()
                if not line or line.strip() == "---":
                    break
                m = FIELD.match(line.rstrip("\r\n"))
                if m:
                    out[m.group(1)] = m.group(2).split("#")[0].strip().lower()
            return out
    except OSError:
        return {}


def main():
    d = Path.cwd() / ".handoff"
    if not d.is_dir():
        return
    try:
        files = sorted(d.glob("*.md"), key=lambda p: p.stat().st_mtime, reverse=True)
    except OSError:
        return
    for p in files:
        fm = frontmatter(p)
        if fm.get("status") == "open" and fm.get("to") == "claude":
            sender = fm.get("from") or "another agent"
            print(f"Handoff waiting from {sender}: {p.name}. Run the agent-handoff skill in mode in.")
            return


if __name__ == "__main__":
    try:
        main()
    except Exception:
        pass
    sys.exit(0)
