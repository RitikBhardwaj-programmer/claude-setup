"""Report differences between this repo and the installed ~/.claude (exit 1 if anything drifted).

  py -3 scripts/check_drift.py [--shared-only]

Run it before changing the setup (to catch edits made directly in ~/.claude) and after install.
Fix drift by copying the live change INTO the repo (if it should be kept) and running the installer.

It also lists local branches with work that is not on main, and uncommitted files in the repo.
These are notes, not drift: the exit code does not change. Drift compares only the checked-out
working tree, so unmerged and uncommitted fixes are invisible to it.
"""
import argparse
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from setup_lib import PERSONAL, drift, stale_checkout_warning  # noqa: E402

REPO = Path(__file__).resolve().parent.parent


def git(repo, *args):
    return subprocess.run(["git", "-C", str(repo), *args], capture_output=True, text=True,
                          encoding="utf-8", errors="replace", check=True).stdout


def unmerged_branches(repo=REPO, base="main"):
    """Return (branch, count) for local branches with commits whose change is not on base.

    `git cherry` compares patches, so a commit cherry-picked to base does not count.
    """
    try:
        names = git(repo, "for-each-ref", "--format=%(refname:short)", "refs/heads").split()
        found = []
        for name in names:
            if name != base:
                count = sum(line.startswith("+") for line in git(repo, "cherry", base, name).splitlines())
                if count:
                    found.append((name, count))
        return found
    except (OSError, subprocess.CalledProcessError):
        return []  # no git, not a repo or no base branch: the drift check must still work


def uncommitted_files(repo=REPO):
    """Return `git status --porcelain` lines (modified, staged or untracked files) in the repo.

    An installed but uncommitted change looks "in sync", because drift compares the working tree.
    """
    try:
        return [line for line in git(repo, "status", "--porcelain").splitlines() if line.strip()]
    except (OSError, subprocess.CalledProcessError):
        return []


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--shared-only", action="store_true")
    a = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")
    found = drift(with_personal=PERSONAL.is_dir() and not a.shared_only)
    branches = unmerged_branches()
    if branches:
        print(f"Note: {len(branches)} local branch(es) have work not on main:")
        for name, count in branches:
            print(f"  - {name}: {count} commit(s)")
    dirty = uncommitted_files()
    if dirty:
        branch = git(REPO, "branch", "--show-current").strip() or "detached HEAD"
        print(f"Note: {len(dirty)} uncommitted file(s) on {branch} (installed but not in git):")
        for line in dirty[:10]:
            print(f"  {line}")
        if len(dirty) > 10:
            print(f"  ... and {len(dirty) - 10} more")
    warning = stale_checkout_warning()
    if warning:
        print(warning)
    if not found:
        print("In sync: ~/.claude matches the claude-setup repo.")
        return 0
    print(f"Drift ({len(found)}):")
    for f in found:
        print(f"  - {f}")
    return 1


if __name__ == "__main__":
    sys.exit(main())
