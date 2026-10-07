"""Stop hook: suggest /improve-setup once after a long, bumpy session. Never blocks.

Fires when the session has at least MIN_TOOL_CALLS tool calls AND friction:
at least MIN_ERRORS errored tool results, or at least MIN_REJECTIONS user rejections.
Silent when /improve-setup already ran in this session or the nudge already fired (flag file).
Output: {"systemMessage": "..."} shown to the user. Thresholds are tuned by later retros.
"""
import json
import sys
import tempfile
from pathlib import Path

MIN_TOOL_CALLS = 40
MIN_ERRORS = 5
MIN_REJECTIONS = 1
SKILL = "improve-setup"


def result_text(block):
    c = block.get("content")
    if isinstance(c, str):
        return c
    if isinstance(c, list):
        return " ".join(x.get("text", "") for x in c if isinstance(x, dict))
    return ""


def scan(transcript: Path):
    tools = errors = rejections = 0
    ran_retro = False
    try:
        lines = transcript.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return tools, errors, rejections, ran_retro
    for line in lines:
        try:
            entry = json.loads(line)
        except ValueError:
            continue
        content = (entry.get("message") or {}).get("content")
        if isinstance(content, str):
            if entry.get("type") == "user" and f"/{SKILL}" in content:
                ran_retro = True
            continue
        if not isinstance(content, list):
            continue
        for b in content:
            if not isinstance(b, dict):
                continue
            if entry.get("type") == "assistant" and b.get("type") == "tool_use":
                tools += 1
                if b.get("name") == "Skill" and (b.get("input") or {}).get("skill") == SKILL:
                    ran_retro = True
            elif b.get("type") == "tool_result":
                text = result_text(b).lstrip()
                if text.startswith("The user doesn't want to proceed"):
                    rejections += 1
                elif b.get("is_error"):
                    errors += 1
            elif entry.get("type") == "user" and b.get("type") == "text" and f"/{SKILL}" in b.get("text", ""):
                ran_retro = True
    return tools, errors, rejections, ran_retro


def main():
    try:
        data = json.load(sys.stdin)
    except ValueError:
        return
    flag = Path(tempfile.gettempdir()) / f"retro-nudge-{data.get('session_id', 'unknown')}"
    if flag.exists():
        return
    tools, errors, rejections, ran_retro = scan(Path(data.get("transcript_path", "")))
    if ran_retro or tools < MIN_TOOL_CALLS or (errors < MIN_ERRORS and rejections < MIN_REJECTIONS):
        return
    flag.touch()
    parts = []
    if errors:
        parts.append(f"{errors} failed tool calls")
    if rejections:
        parts.append(f"{rejections} rejected step{'s' if rejections != 1 else ''}")
    msg = (f"Bumpy session ({' and '.join(parts)} in {tools} tool calls). "
           f"Consider running /{SKILL} to turn them into fixes for CLAUDE.md, skills or hooks.")
    print(json.dumps({"systemMessage": msg}))


if __name__ == "__main__":
    try:
        main()
    except Exception as e:  # a nudge must never break stopping
        print(f"retro-nudge error: {e}", file=sys.stderr)
    sys.exit(0)
