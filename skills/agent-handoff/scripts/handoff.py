"""Helpers for the agent-handoff skill. Standard library only; works on Windows and macOS.

  python handoff.py watcher-status            prints "on" if Antigravity's handoff watcher sidecar is alive, else "off"
  python handoff.py watch-add <project dir>   adds a project to the watcher's list (the user agrees first)
  python handoff.py copy <text>               puts <text> on the clipboard (fallback when the watcher is off)
  python handoff.py wait <return file> [--timeout SECONDS]
                                              blocks until the return file exists, then prints its path (exit 0);
                                              exit 2 on timeout. Run it as a background task so the agent wakes up.
"""
import argparse
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
    a = ap.parse_args()

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
