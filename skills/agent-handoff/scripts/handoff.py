"""Helpers for the agent-handoff skill. Standard library only; works on Windows and macOS.

  python handoff.py watcher-status            prints "on" if Antigravity's handoff watcher sidecar is alive, else "off"
  python handoff.py watch-add <project dir>   adds a project to the watcher's list (the user agrees first)
  python handoff.py copy <text>               puts <text> on the clipboard (fallback when the watcher is off)
  python handoff.py wait <return file> [--timeout SECONDS]
                                              blocks until the return file exists, then prints its path (exit 0);
                                              exit 2 on timeout. Run it as a background task so the agent wakes up.
  python handoff.py log-outcome --brief <brief file> --result pass|partial|redo --verify-ran yes|no
                    --handoff-turns N --self-turns N [--redo-turns N] [--note TEXT]
                                              appends one JSON line to <project>/.handoff/outcomes.jsonl (once per brief)
  python handoff.py outcomes [project dir ...]
                                              summary per worker agent: count, results, turns saved. Defaults to the
                                              watch list plus the current folder.
"""
import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path

# HANDOFF_STATE_DIR overrides the folder, for tests.
STATE_DIR = Path(os.environ.get("HANDOFF_STATE_DIR") or Path.home() / ".gemini" / "config" / "sidecars" / "handoff-watcher")
HEARTBEAT = STATE_DIR / "heartbeat"
WATCH_LIST = STATE_DIR / "watch-dirs.txt"
HEARTBEAT_MAX_AGE = 30  # seconds; the watcher touches the heartbeat every few seconds
FIELD = re.compile(r"^(\w+):[ \t]*(.*?)[ \t]*$")


def frontmatter(path: Path) -> dict:
    """Top-level `key: value` pairs of the leading ---/--- block (values lower-cased), or {}."""
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


def set_status(path: Path, status: str) -> bool:
    """Replace the `status:` line inside the frontmatter. Returns False if there is none."""
    raw = path.read_bytes().decode("utf-8")
    nl = "\r\n" if "\r\n" in raw else "\n"
    lines = raw.split(nl)
    if not lines or lines[0].strip() != "---":
        return False
    for i in range(1, min(len(lines), 61)):
        if lines[i].strip() == "---":
            return False
        if lines[i].startswith("status:"):
            lines[i] = f"status: {status}"
            path.write_bytes(nl.join(lines).encode("utf-8"))
            return True
    return False


def watch_dirs() -> list:
    if not WATCH_LIST.is_file():
        return []
    out = []
    for line in WATCH_LIST.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#"):
            out.append(line)
    return out


def watcher_on() -> bool:
    try:
        return time.time() - HEARTBEAT.stat().st_mtime < HEARTBEAT_MAX_AGE
    except OSError:
        return False


def copy(text: str) -> bool:
    if sys.platform == "win32":
        # clip.exe reads UTF-16 with a BOM correctly; plain bytes would break non-ASCII paths.
        return subprocess.run(["clip"], input=text.encode("utf-16"), check=False).returncode == 0
    for cmd in (["pbcopy"], ["wl-copy"], ["xclip", "-selection", "clipboard"]):
        if shutil.which(cmd[0]):
            return subprocess.run(cmd, input=text.encode("utf-8"), check=False).returncode == 0
    return False


def wait(path: Path, timeout: int) -> int:
    end = time.time() + timeout
    while time.time() < end:
        if path.is_file() and frontmatter(path):
            print(f"Return ready: {path}")
            return 0
        time.sleep(5)
    print(f"Timed out after {timeout}s waiting for {path}")
    return 2


def log_outcome(brief: Path, result: str, verify_ran: bool, handoff_turns: int, self_turns: int,
                redo_turns: int, note: str) -> int:
    """Append one outcome line for a finished brief. saved_turns = self - handoff - redo (negative = handoff cost more)."""
    fm = frontmatter(brief)
    if not fm:
        print(f"Not a brief (no frontmatter): {brief}")
        return 1
    log = brief.parent / "outcomes.jsonl"
    for row in read_outcomes(log):
        if row.get("brief") == brief.name:
            print(f"Already logged: {brief.name}")
            return 1
    row = {
        "date": time.strftime("%Y-%m-%d"),
        "brief": brief.name,
        "from": fm.get("from", ""),
        "to": fm.get("to", ""),
        "result": result,
        "verify_ran": verify_ran,
        "handoff_turns": handoff_turns,
        "self_turns": self_turns,
        "redo_turns": redo_turns,
        "saved_turns": self_turns - handoff_turns - redo_turns,
        "note": note,
    }
    with log.open("a", encoding="utf-8") as f:
        f.write(json.dumps(row, ensure_ascii=False) + "\n")
    print(f"Logged: {brief.name} -> {row['to']}, {result}, saved {row['saved_turns']} turns")
    return 0


def read_outcomes(log: Path) -> list:
    rows = []
    if log.is_file():
        for line in log.read_text(encoding="utf-8").splitlines():
            try:
                rows.append(json.loads(line))
            except ValueError:
                continue  # skip a damaged line rather than fail the whole summary
    return rows


def outcomes(dirs: list) -> int:
    seen, rows = set(), []
    for d in dirs:
        key = os.path.normcase(str(Path(d).resolve()))
        if key in seen:
            continue
        seen.add(key)
        rows += read_outcomes(Path(d) / ".handoff" / "outcomes.jsonl")
    if not rows:
        print("No outcomes logged yet.")
        return 0
    by = {}
    for r in rows:
        by.setdefault(r.get("to") or "?", []).append(r)
    print(f"{'worker':<12} {'n':>3} {'pass':>5} {'partial':>8} {'redo':>5} {'verify ran':>11} {'saved':>6} {'avg':>6}")
    for to, rs in sorted(by.items()) + [("ALL", rows)]:
        n = len(rs)
        count = {k: sum(1 for r in rs if r.get("result") == k) for k in ("pass", "partial", "redo")}
        ran = sum(1 for r in rs if r.get("verify_ran"))
        saved = sum(int(r.get("saved_turns", 0)) for r in rs)
        print(f"{to:<12} {n:>3} {count['pass']:>5} {count['partial']:>8} {count['redo']:>5} {ran:>5}/{n:<5} "
              f"{saved:>6} {saved / n:>6.1f}")
    print("saved = Claude turns it would have taken itself - handoff turns - redo turns (estimates; negative = a loss)")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("watcher-status")
    p = sub.add_parser("watch-add")
    p.add_argument("dir")
    p = sub.add_parser("copy")
    p.add_argument("text")
    p = sub.add_parser("wait")
    p.add_argument("file")
    p.add_argument("--timeout", type=int, default=3600)
    p = sub.add_parser("log-outcome")
    p.add_argument("--brief", required=True)
    p.add_argument("--result", required=True, choices=["pass", "partial", "redo"])
    p.add_argument("--verify-ran", required=True, choices=["yes", "no"])
    p.add_argument("--handoff-turns", required=True, type=int)
    p.add_argument("--self-turns", required=True, type=int)
    p.add_argument("--redo-turns", type=int, default=0)
    p.add_argument("--note", default="")
    p = sub.add_parser("outcomes")
    p.add_argument("dirs", nargs="*")
    a = ap.parse_args()

    if a.cmd == "log-outcome":
        if min(a.handoff_turns, a.self_turns, a.redo_turns) < 0:
            print("Turn counts must be 0 or more.")
            return 1
        return log_outcome(Path(a.brief), a.result, a.verify_ran == "yes", a.handoff_turns, a.self_turns,
                           a.redo_turns, a.note)
    if a.cmd == "outcomes":
        return outcomes(a.dirs or watch_dirs() + [os.getcwd()])

    if a.cmd == "watcher-status":
        print("on" if watcher_on() else "off")
        return 0
    if a.cmd == "watch-add":
        d = os.path.normcase(str(Path(a.dir).resolve()))
        have = [os.path.normcase(x) for x in watch_dirs()]
        if d in have:
            print(f"Already watched: {d}")
            return 0
        STATE_DIR.mkdir(parents=True, exist_ok=True)
        with WATCH_LIST.open("a", encoding="utf-8") as f:
            f.write(str(Path(a.dir).resolve()) + "\n")
        print(f"Added to the watch list: {Path(a.dir).resolve()}")
        return 0
    if a.cmd == "copy":
        ok = copy(a.text)
        print("Copied to clipboard." if ok else "Could not copy; paste the line by hand.")
        return 0 if ok else 1
    return wait(Path(a.file), a.timeout)


if __name__ == "__main__":
    sys.exit(main())
