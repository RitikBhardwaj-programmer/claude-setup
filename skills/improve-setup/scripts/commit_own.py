"""Commit only this run's changes to a notes repo, even when other sessions left uncommitted work there.

Usage (stdlib only):
  python3 commit_own.py --file "Retros/2026-10-07 X.md" --file "Projects/A/Gotchas.md" \
      --log-match "unique text of my log line" --message "Subject line" [--body "..."] [--dry-run] \
      [--repo PATH] [--log-file log.md]

--repo / --log-file default to "notes_repo" / "notes_log" in ~/.claude/setup.json.
- Stages the given files by name (paths relative to the repo). Refuses paths outside the repo.
- Stages the log file as: the committed version + only the NEW lines that contain a --log-match text,
  so other sessions' log lines stay unstaged for them.
- Shows the staged diff stat; with --dry-run it then unstages everything again and commits nothing.
- Adds a Claude co-author trailer. Never pushes.
"""
import argparse
import json
import subprocess
import sys
from pathlib import Path

TRAILER = "Co-Authored-By: Claude <noreply@anthropic.com>"
CONFIG = Path.home() / ".claude" / "setup.json"


def config():
    try:
        return json.loads(CONFIG.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def main():
    cfg = config()
    ap = argparse.ArgumentParser()
    ap.add_argument("--file", action="append", default=[])
    ap.add_argument("--log-match", action="append", default=[])
    ap.add_argument("--message", required=True)
    ap.add_argument("--body", default="")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--repo", default=cfg.get("notes_repo"))
    ap.add_argument("--log-file", default=cfg.get("notes_log", "log.md"))
    ap.add_argument("--trailer", default=cfg.get("commit_trailer", TRAILER))
    a = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")
    if not a.repo:
        sys.exit("No notes repo: pass --repo or set notes_repo in ~/.claude/setup.json.")
    repo = Path(a.repo).resolve()
    log = a.log_file

    def git(*args, inp=None, check=True):
        r = subprocess.run(["git", "-C", str(repo), *args], input=inp, capture_output=True, text=True, encoding="utf-8")
        if check and r.returncode:
            sys.exit(f"git {' '.join(args)} failed: {r.stderr.strip()}")
        return r.stdout

    if git("diff", "--cached", "--name-only").strip():
        sys.exit("Something is already staged in the repo. Commit or unstage it first, so this commit stays clean.")
    staged_paths = []
    for f in a.file:
        p = (repo / f).resolve()
        if not p.is_relative_to(repo):
            sys.exit(f"Refusing a path outside the repo: {f}")
        if not p.exists():
            sys.exit(f"No such file in the repo: {f}")
        rel = p.relative_to(repo).as_posix()
        git("add", "--", rel)
        staged_paths.append(rel)

    if a.log_match:
        head = git("show", f"HEAD:{log}").replace("\r\n", "\n")
        work = (repo / log).read_text(encoding="utf-8").replace("\r\n", "\n")
        head_lines = set(head.splitlines())
        mine = [ln for ln in work.splitlines()
                if ln.startswith("- ") and ln not in head_lines and any(m in ln for m in a.log_match)]
        if not mine:
            git("reset", "-q", "--", *staged_paths, check=False)
            sys.exit(f"No new {log} line matches --log-match; add your log line first.")
        staged = head.rstrip("\n") + "\n" + "\n".join(mine) + "\n"
        sha = git("hash-object", "-w", "--stdin", f"--path={log}", inp=staged).strip()
        git("update-index", "--cacheinfo", f"100644,{sha},{log}")
        staged_paths.append(log)
        print(f"{log}: staged {len(mine)} own line(s); other new lines stay unstaged")

    print(git("diff", "--cached", "--stat").rstrip())
    if a.dry_run:
        git("reset", "-q", "--", *staged_paths, check=False)
        print("dry run: unstaged again, nothing committed")
        return 0
    msg = a.message + ("\n\n" + a.body.strip() if a.body.strip() else "") + "\n\n" + a.trailer + "\n"
    git("commit", "-q", "-F", "-", inp=msg)
    print(git("log", "--oneline", "-1").strip())
    return 0


if __name__ == "__main__":
    sys.exit(main())
