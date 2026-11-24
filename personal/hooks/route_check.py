"""Stop hook: ask once per session for a routing card when the work has grown medium/large without one.

Fires when the session has edited at least MIN_FILES distinct files (or made MIN_EDITS edit calls)
with Write/Edit/NotebookEdit, outside ~/.claude and the Brain vault, AND there is no sign of routing:
no `route` Skill call, no "/route" typed by the user, no "Routing card" in an assistant message, and no
"approved routing card" in a user message (the brief of a session started from an approved plan; the
route skill puts that phrase in every brief). Then it blocks the stop once with a reason, so Claude either writes the card for the remaining work
or says in one line why none is needed. Silent on re-entry (stop_hook_active) and after firing once
(flag file). Thresholds are tuned by later retros.
"""
import json
import sys
import tempfile
from pathlib import Path

MIN_FILES = 4
MIN_EDITS = 10
EDIT_TOOLS = {"Write", "Edit", "NotebookEdit"}
SKIP_PATH_PARTS = ("/.claude/", "/brain/")
SKILL = "route"
# A brief that says its phase follows an approved card (route skill, Step 5). The hook's own reason
# text says "no routing card", which does not match this phrase.
BRIEF_PHRASE = "approved routing card"


def user_routed(text: str) -> bool:
    return f"/{SKILL}" in text or BRIEF_PHRASE in text.lower()


def text_of(block):
    if block.get("type") == "text":
        return block.get("text", "")
    return ""


def scan(transcript: Path):
    files, edits, routed = set(), 0, False
    try:
        lines = transcript.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return files, edits, routed
    for line in lines:
        try:
            entry = json.loads(line)
        except ValueError:
            continue
        kind = entry.get("type")
        content = (entry.get("message") or {}).get("content")
        if isinstance(content, str):
            if kind == "user" and user_routed(content):
                routed = True
            elif kind == "assistant" and "routing card" in content.lower():
                routed = True
            continue
        if not isinstance(content, list):
            continue
        for b in content:
            if not isinstance(b, dict):
                continue
            if kind == "assistant" and b.get("type") == "tool_use":
                name, inp = b.get("name"), b.get("input") or {}
                if name == "Skill" and inp.get("skill") == SKILL:
                    routed = True
                elif name in EDIT_TOOLS:
                    path = str(inp.get("file_path") or inp.get("notebook_path") or "")
                    norm = path.replace("\\", "/").lower()
                    if path and not any(p in norm for p in SKIP_PATH_PARTS):
                        files.add(norm)
                        edits += 1
            elif kind == "assistant" and "routing card" in text_of(b).lower():
                routed = True
            elif kind == "user" and user_routed(text_of(b)):
                routed = True
    return files, edits, routed


def main():
    try:
        data = json.load(sys.stdin)
    except ValueError:
        return
    if data.get("stop_hook_active"):
        return
    flag = Path(tempfile.gettempdir()) / f"route-check-{data.get('session_id', 'unknown')}"
    if flag.exists():
        return
    files, edits, routed = scan(Path(data.get("transcript_path", "")))
    if routed or (len(files) < MIN_FILES and edits < MIN_EDITS):
        return
    flag.touch()
    reason = (f"Routing check: this session edited {len(files)} files ({edits} edits) and has no routing card. "
              f"If the task is medium or large (or grew into one), run the `{SKILL}` skill now for the remaining "
              f"or follow-up phases and show the card. If it is small or already finished, say in one line why "
              f"no card is needed. This check fires once per session.")
    print(json.dumps({"decision": "block", "reason": reason}))


if __name__ == "__main__":
    try:
        main()
    except Exception as e:  # a check must never break stopping
        print(f"route-check error: {e}", file=sys.stderr)
    sys.exit(0)
