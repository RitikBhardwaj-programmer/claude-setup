"""Trigger eval for the augment-lens skill.

Runs each prompt in trigger_cases.json through `claude -p` in an empty temp folder
(no project context) and checks whether Claude calls the Skill tool for augment-lens.
Edit and shell tools are disabled and turns are capped, so the runs change nothing.

Usage: py -3 run_trigger_eval.py [--runs N] [--workers N]
Prints a pass/fail table, the trigger rates, and exits 1 when the target is missed
(>= 10/12 should-trigger and <= 1/10 false triggers, scaled to the case counts).
"""
import argparse
import json
import subprocess
import sys
import tempfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

SKILL = "augment-lens"
CASES = Path(__file__).with_name("trigger_cases.json")
BLOCKED_TOOLS = "Bash PowerShell Edit Write NotebookEdit Artifact Agent"
TIMEOUT_S = 300


def triggered(prompt: str, cwd: str) -> bool | None:
    """True/False if the skill was or was not called; None if the run failed."""
    cmd = ["claude", "-p", prompt, "--output-format", "stream-json", "--verbose",
           "--max-turns", "2", "--disallowedTools", BLOCKED_TOOLS]
    try:
        out = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True,
                             encoding="utf-8", errors="replace", timeout=TIMEOUT_S).stdout
    except (OSError, subprocess.TimeoutExpired):
        return None
    if not out.strip():
        return None
    for line in out.splitlines():
        try:
            entry = json.loads(line)
        except ValueError:
            continue
        if entry.get("type") != "assistant":
            continue
        for block in (entry.get("message") or {}).get("content") or []:
            if (isinstance(block, dict) and block.get("type") == "tool_use"
                    and block.get("name") == "Skill"
                    and str((block.get("input") or {}).get("skill", "")).split(":")[-1] == SKILL):
                return True
    return False


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--runs", type=int, default=1)
    ap.add_argument("--workers", type=int, default=4)
    args = ap.parse_args()

    cases = json.loads(CASES.read_text(encoding="utf-8"))
    jobs = [(p, True) for p in cases["should_trigger"]] + [(p, False) for p in cases["should_not_trigger"]]
    jobs = jobs * args.runs

    with tempfile.TemporaryDirectory(prefix="lens-eval-") as cwd:
        with ThreadPoolExecutor(args.workers) as pool:
            results = list(pool.map(lambda j: triggered(j[0], cwd), jobs))

    hits = misses = false_hits = failed = 0
    for (prompt, expected), got in zip(jobs, results):
        if got is None:
            failed += 1
            mark = "ERROR"
        elif got == expected:
            mark = "pass"
        else:
            mark = "FAIL"
        if got is not None:
            if expected:
                hits += got
                misses += not got
            else:
                false_hits += got
        print(f"{mark:5}  expect={'yes' if expected else 'no ':3}  got={got!s:5}  {prompt[:70]}")

    n_pos = len(cases["should_trigger"]) * args.runs
    n_neg = len(cases["should_not_trigger"]) * args.runs
    print(f"\nshould-trigger: {hits}/{n_pos}   false triggers: {false_hits}/{n_neg}   failed runs: {failed}")
    ok = hits >= round(n_pos * 10 / 12) and false_hits <= round(n_neg * 1 / 10) and failed == 0
    print("TARGET MET" if ok else "TARGET MISSED")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
