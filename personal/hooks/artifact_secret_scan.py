"""PreToolUse hook for the Artifact tool: scan what is about to be published for secrets.

Checks the page (file_path) and text files in `files` for:
  1. known secret formats (private keys, cloud/API tokens, password=..., JWTs), and
  2. the actual secret VALUES found in .env files of the current project (catches real leaks
     such as a lab password typed into a report).
On a finding it returns permissionDecision "ask" so the user decides; the reason names the
pattern or the .env KEY, never the secret value. If images are published, it adds a reminder
to check them by eye (text inside images cannot be scanned here).
Never breaks the tool: any error -> exit 0 with no output.
"""
import json
import os
import re
import sys
from pathlib import Path

TEXT_EXT = {".html", ".htm", ".md", ".txt", ".js", ".css", ".json", ".csv", ".svg", ".xml"}
IMG_EXT = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp"}
MAX_BYTES = 8_000_000
PATTERNS = [
    ("private key block", re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH |DSA |ENCRYPTED )?PRIVATE KEY-----")),
    ("AWS access key", re.compile(r"\bAKIA[0-9A-Z]{16}\b")),
    ("GitHub token", re.compile(r"\bgh[pousr]_[A-Za-z0-9]{36,}\b")),
    ("Slack token", re.compile(r"\bxox[abprs]-[A-Za-z0-9-]{10,}\b")),
    ("OpenAI/Anthropic-style API key", re.compile(r"\bsk-(?:ant-)?[A-Za-z0-9_-]{20,}\b")),
    ("Google API key", re.compile(r"\bAIza[0-9A-Za-z_-]{35}\b")),
    ("JSON Web Token", re.compile(r"\beyJ[A-Za-z0-9_-]{10,}\.eyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\b")),
    ("password/secret assignment", re.compile(
        # name may carry prefixes/suffixes (RADIUS_SECRET, DB_PASSWORD_1); value: 8+ chars, not masked or a placeholder
        r"(?i)\b[A-Za-z0-9_]*(?:password|passwd|pwd|secret|api[_-]?key|token)[A-Za-z0-9_]*\s*[:=]\s*[\"']?"
        r"(?!\*{3,}|<|\$\{|%\{|x{4,})"
        r"(?![^\s\"'<>]*(?:changeme|example|placeholder|your[_-]|dummy|sample|redacted))[^\s\"'<>]{8,}")),
]
ENV_KEY_HINT = re.compile(r"(?i)(pass|secret|token|key|cred|auth)")
SKIP_DIRS = {"node_modules", ".git", ".venv", "venv", "__pycache__", "dist", "build"}


def env_secret_values(root: Path):
    """Return {value: 'file:KEY'} for secret-looking keys in .env files under root (depth <= 3)."""
    found = {}
    if not root.is_dir():
        return found
    for dirpath, dirnames, filenames in os.walk(root):
        rel_depth = len(Path(dirpath).relative_to(root).parts)
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS and rel_depth < 3]
        for fn in filenames:
            if fn != ".env" and not fn.startswith(".env.") or fn.endswith((".example", ".sample", ".template")):
                continue
            try:
                lines = Path(dirpath, fn).read_text(encoding="utf-8", errors="ignore").splitlines()
            except OSError:
                continue
            for line in lines:
                m = re.match(r"\s*(?:export\s+)?([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(.*)$", line)
                if not m or not ENV_KEY_HINT.search(m.group(1)):
                    continue
                val = m.group(2).strip().strip("\"'")
                if len(val) >= 8:
                    found[val] = f"{fn}:{m.group(1)}"
    return found


def gather(tool_input: dict):
    """Yield (label, path) of local files the publish would send."""
    fp = tool_input.get("file_path")
    if fp:
        yield "page", Path(fp)
    files = tool_input.get("files")
    root = Path(tool_input.get("root") or ".")
    if isinstance(files, dict):
        for pub, src in files.items():
            if isinstance(src, str):
                yield pub, root / src
            elif isinstance(src, dict) and src.get("from"):
                yield pub, root / src["from"]
    elif isinstance(files, list):
        for item in files:
            if isinstance(item, dict) and item.get("path"):
                yield item["path"], root / item["path"]
    for p in tool_input.get("file_paths") or []:
        yield p, Path(p)


def main():
    try:
        data = json.load(sys.stdin)
    except ValueError:
        return
    ti = data.get("tool_input") or {}
    if ti.get("action") not in (None, "publish"):
        return
    cwd = Path(data.get("cwd") or os.getcwd())
    secrets = env_secret_values(cwd)
    findings, images = [], []
    for label, path in gather(ti):
        if not path.is_absolute():
            path = cwd / path
        ext = path.suffix.lower()
        if ext in IMG_EXT:
            images.append(label)
            continue
        if ext not in TEXT_EXT or not path.is_file() or path.stat().st_size > MAX_BYTES:
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        for name, rx in PATTERNS:
            if rx.search(text):
                findings.append(f"{label}: {name}")
        for val, where in secrets.items():
            if val in text:
                findings.append(f"{label}: contains the value of {where}")
    out = {"hookEventName": "PreToolUse"}
    if findings:
        out["permissionDecision"] = "ask"
        out["permissionDecisionReason"] = (
            "Secret scan found possible secrets in what is about to be published: "
            + "; ".join(sorted(set(findings))[:10])
            + ". Check and redact before publishing, or approve if these are harmless examples.")
    elif images:
        out["additionalContext"] = (
            f"[secret-scan] Text files look clean. {len(images)} image(s) are being published "
            "(" + ", ".join(images[:5]) + "): text inside images cannot be scanned. Make sure you have "
            "looked at each one for passwords, keys or personal data.")
    else:
        return
    sys.stdout.write(json.dumps({"hookSpecificOutput": out}))


if __name__ == "__main__":
    try:
        main()
    except Exception as e:  # never break publishing because of the scanner
        print(f"artifact-secret-scan error: {e}", file=sys.stderr)
    sys.exit(0)
