"""PreToolUse hook for Bash: stop long heredocs before they run.

Long `cat > file <<'EOF'` and `python - <<'EOF'` blocks (120-310 lines in the 2026-10-23 retro)
failed again and again with "unexpected EOF while looking for matching `''". The CLAUDE.md rule
"write long scripts with the Write tool" did not stop it, so this hook does.
A heredoc whose body is longer than MAX_BODY_LINES (and whose end marker is found) is denied with
a reason that says to write the file with the Write tool and run it. Short heredocs (commit
messages, small configs), here-strings (<<<) and unterminated matches (e.g. `$((1<<3))`) pass.
Never breaks the tool: any error -> exit 0 with no output.
"""
import json
import re
import sys

MAX_BODY_LINES = 40
# <<EOF, <<'EOF', <<"EOF", <<-EOF; not <<< (here-string)
START = re.compile(r"(?<!<)<<(-?)[ \t]*(['\"]?)([A-Za-z_][A-Za-z0-9_]*)\2")


def longest_heredoc(command: str) -> int:
    lines = command.split("\n")
    longest = 0
    i = 0
    while i < len(lines):
        markers = START.findall(lines[i])
        i += 1
        for dash, _quote, word in markers:
            body = 0
            while i < len(lines):
                line = lines[i].lstrip("\t") if dash else lines[i]
                i += 1
                if line.rstrip("\r") == word:
                    longest = max(longest, body)
                    break
                body += 1
            else:
                return longest  # no end marker: not a heredoc we can judge
    return longest


def main():
    data = json.loads(sys.stdin.read() or "{}")
    if data.get("tool_name") != "Bash":
        return
    command = (data.get("tool_input") or {}).get("command") or ""
    if "<<" not in command:
        return
    body = longest_heredoc(command)
    if body <= MAX_BODY_LINES:
        return
    out = {
        "hookEventName": "PreToolUse",
        "permissionDecision": "deny",
        "permissionDecisionReason": (
            f"[heredoc-guard] This Bash command has a {body}-line heredoc (limit {MAX_BODY_LINES}). "
            "Long heredocs break on quotes and Windows paths. Next step, in 2 calls: (1) Write tool: put the "
            "body in the target file itself, or in a script in the scratchpad (e.g. <scratchpad>/step.sh or "
            "step.py); (2) Bash: run it with one short command (`bash <path>` or `py -3 <path>`). "
            "Do not retry with a shorter heredoc or split it into several heredocs."),
    }
    sys.stdout.write(json.dumps({"hookSpecificOutput": out}))


if __name__ == "__main__":
    try:
        main()
    except Exception as e:  # never break Bash because of the guard
        print(f"heredoc-guard error: {e}", file=sys.stderr)
    sys.exit(0)
