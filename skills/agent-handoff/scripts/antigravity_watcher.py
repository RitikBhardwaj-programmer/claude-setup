"""Antigravity sidecar: start an Antigravity conversation when a brief for Antigravity appears in a watched project.

Antigravity runs this itself (sidecar.json in ~/.gemini/config/sidecars/handoff-watcher/), so no other agent ever
starts or drives Antigravity: another agent only writes a file, and Antigravity's own `agentapi` picks it up.

Each tick it reads the watch list (watch-dirs.txt, edited by `handoff.py watch-add` with the user's consent), and for
every `.handoff/*.md` with `to: antigravity` and `status: open`:
  - skips it if git tracks it (a cloned repo must not be able to start an agent),
  - skips it while `.handoff/LOCK` names another agent,
  - sets `status: claimed` first (so a restart cannot start it twice), then runs
    `agentapi new-conversation -- <prompt>`. On failure it sets the status back to open and retries after RETRY_AFTER.

  python antigravity_watcher.py [--once]
"""
import argparse
import shutil
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from handoff import HEARTBEAT, STATE_DIR, frontmatter, set_status, watch_dirs  # noqa: E402

TICK = 3            # seconds between scans
RETRY_AFTER = 300   # seconds before retrying a brief whose launch failed
LOG = STATE_DIR / "watcher.log"
ME = "antigravity"
SKILL = Path.home() / ".claude" / "skills" / "agent-handoff" / "SKILL.md"


def log(msg: str):
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    with LOG.open("a", encoding="utf-8") as f:
        f.write(f"{datetime.now().isoformat(timespec='seconds')} {msg}\n")


def tracked_by_git(project: Path, rel: str) -> bool:
    """True if git tracks the file. If git cannot be run, answer True: never start a brief we could not check."""
    try:
        r = subprocess.run(["git", "-C", str(project), "ls-files", "--error-unmatch", rel],
                           capture_output=True, check=False, timeout=20)
    except (OSError, subprocess.TimeoutExpired):
        return True
    return r.returncode == 0


def lock_holder(project: Path):
    lock = project / ".handoff" / "LOCK"
    if not lock.is_file():
        return None
    for line in lock.read_text(encoding="utf-8", errors="replace").splitlines():
        if line.lower().startswith("agent:"):
            return line.split(":", 1)[1].strip().lower()
    return None  # empty LOCK = released (agents that cannot delete files empty it instead)


def prompt_for(project: Path, brief: Path) -> str:
    return (f"Run the agent-handoff skill in mode in. Brief: {brief}. Project folder: {project}. "
            f"Work only inside that folder. If you cannot see the skill, read {SKILL} and follow it exactly, "
            f"including mode return at the end.")


def scan(failed: dict, warned: set):
    agentapi = shutil.which("agentapi")
    for d in watch_dirs():
        project = Path(d)
        hd = project / ".handoff"
        if not hd.is_dir():
            continue
        for brief in sorted(hd.glob("*.md")):
            fm = frontmatter(brief)
            if fm.get("to") != ME or fm.get("status") != "open":
                continue
            key = str(brief)
            if time.time() - failed.get(key, 0) < RETRY_AFTER:
                continue
            if tracked_by_git(project, f".handoff/{brief.name}"):
                if key not in warned:
                    log(f"SKIP tracked by git (not started): {brief}")
                    warned.add(key)
                continue
            holder = lock_holder(project)
            if holder and holder != ME:
                continue
            if not agentapi:
                if "agentapi" not in warned:
                    log("ERROR agentapi not on PATH; is this running as an Antigravity sidecar?")
                    warned.add("agentapi")
                return
            if not set_status(brief, "claimed"):
                log(f"SKIP no status line: {brief}")
                failed[key] = time.time()
                continue
            r = subprocess.run([agentapi, "new-conversation", "--", prompt_for(project, brief)],
                               capture_output=True, text=True, check=False, timeout=120)
            if r.returncode == 0:
                log(f"STARTED {brief} :: {r.stdout.strip()[:200]}")
            else:
                set_status(brief, "open")
                failed[key] = time.time()
                log(f"FAILED rc={r.returncode} {brief} :: {(r.stderr or r.stdout).strip()[:300]}")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--once", action="store_true", help="scan once and exit (for tests)")
    a = ap.parse_args()
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    log("watcher start")
    failed, warned = {}, set()
    while True:
        HEARTBEAT.touch()
        try:
            scan(failed, warned)
        except Exception as e:  # keep the sidecar alive; Antigravity would restart it anyway
            log(f"ERROR {type(e).__name__}: {e}")
        if a.once:
            return 0
        time.sleep(TICK)


if __name__ == "__main__":
    sys.exit(main())
