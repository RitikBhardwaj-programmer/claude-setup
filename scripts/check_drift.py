"""Report differences between this repo and the installed ~/.claude (exit 1 if anything drifted).

  py -3 scripts/check_drift.py [--shared-only]

Run it before changing the setup (to catch edits made directly in ~/.claude) and after install.
Fix drift by copying the live change INTO the repo (if it should be kept) and running the installer.
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from setup_lib import PERSONAL, drift  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--shared-only", action="store_true")
    a = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")
    found = drift(with_personal=PERSONAL.is_dir() and not a.shared_only)
    if not found:
        print("In sync: ~/.claude matches the claude-setup repo.")
        return 0
    print(f"Drift ({len(found)}):")
    for f in found:
        print(f"  - {f}")
    return 1


if __name__ == "__main__":
    sys.exit(main())
