"""Shared logic for install_windows.py and check_drift.py: what the installed ~/.claude should contain."""
import filecmp
import json
import os
import re
import shutil
import subprocess
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
DEST = Path.home() / ".claude"
PERSONAL = REPO / "personal"
IGNORE = {"__pycache__", ".DS_Store"}
# Marketplace plugins the setup expects (installed with the `claude` CLI). Keep in sync with PLUGINS in install.sh.
PLUGINS = ["frontend-design@claude-plugins-official", "claude-security@claude-plugins-official"]


def compose_claude_md(with_personal: bool) -> str:
    """The CLAUDE.md that should be installed: shared rules, plus the personal part on this PC."""
    shared = (REPO / "CLAUDE.md").read_text(encoding="utf-8").replace("\r\n", "\n").rstrip("\n") + "\n"
    if not with_personal:
        return shared
    personal = (PERSONAL / "CLAUDE.personal.md").read_text(encoding="utf-8").replace("\r\n", "\n")
    personal = re.sub(r"\A\s*<!--.*?-->\s*", "", personal, flags=re.S)  # repo-only note, not for Claude
    return shared + "\n" + personal.rstrip("\n") + "\n"


def skill_sources(with_personal: bool):
    """{skill name: source folder} for every skill the repo installs."""
    dirs = [REPO / "skills"] + ([PERSONAL / "skills"] if with_personal else [])
    out = {}
    for d in dirs:
        if d.is_dir():
            for s in sorted(p for p in d.iterdir() if p.is_dir() and p.name not in IGNORE):
                out[s.name] = s
    return out


def is_link(p: Path) -> bool:
    """True for symlinks and Windows junctions: such folders are managed elsewhere (e.g. the Brain vault)."""
    try:
        return p.is_symlink() or (p.exists() and os.path.realpath(p).lower() != os.path.abspath(p).lower())
    except OSError:
        return False


def agent_sources():
    """Subagent definitions (agents/*.md) the repo installs into ~/.claude/agents."""
    d = REPO / "agents"
    return sorted(d.glob("*.md")) if d.is_dir() else []


def installed_plugins():
    """Set of installed plugin ids (name@marketplace), or None when the `claude` CLI is not available."""
    exe = shutil.which("claude")
    if not exe:
        return None
    try:
        out = subprocess.run([exe, "plugin", "list", "--json"], capture_output=True, text=True,
                             encoding="utf-8", timeout=60).stdout
        entries = json.loads(out or "[]")
    except (OSError, ValueError, subprocess.SubprocessError):
        return None
    ids = set()
    for e in entries:
        if isinstance(e, str):
            ids.add(e)
        elif isinstance(e, dict):
            if e.get("id"):
                ids.add(e["id"])
            if e.get("name") and e.get("marketplace"):
                ids.add(f"{e['name']}@{e['marketplace']}")
    return ids


def hook_sources():
    d = PERSONAL / "hooks"
    return sorted(p for p in d.glob("*.py")) if d.is_dir() else []


def hooks_block():
    return json.loads((PERSONAL / "settings.hooks.json").read_text(encoding="utf-8"))["hooks"]


def tree_diff(src: Path, dst: Path):
    """List of relative paths that differ between two folders (missing, extra or changed files)."""
    if not dst.is_dir():
        return ["(missing folder)"]
    diffs = []

    def walk(c: filecmp.dircmp, rel=""):
        for n in c.left_only:
            if n not in IGNORE:
                diffs.append(f"{rel}{n} (only in repo)")
        for n in c.right_only:
            if n not in IGNORE:
                diffs.append(f"{rel}{n} (only in ~/.claude)")
        for n in c.common_files:
            a, b = Path(c.left) / n, Path(c.right) / n
            if a.read_bytes().replace(b"\r\n", b"\n") != b.read_bytes().replace(b"\r\n", b"\n"):
                diffs.append(f"{rel}{n} (changed)")
        for n, sub in c.subdirs.items():
            if n not in IGNORE:
                walk(sub, f"{rel}{n}/")

    walk(filecmp.dircmp(src, dst, ignore=list(IGNORE)))
    return diffs


def drift(with_personal: bool):
    """Return a list of human-readable drift findings (empty = in sync)."""
    found = []
    live_md = DEST / "CLAUDE.md"
    want = compose_claude_md(with_personal)
    have = live_md.read_text(encoding="utf-8").replace("\r\n", "\n") if live_md.is_file() else ""
    if want != have:
        found.append("CLAUDE.md differs from the composed repo version")
    srcs = skill_sources(with_personal)
    for name, src in srcs.items():
        if is_link(DEST / "skills" / name):
            found.append(f"skills/{name}: is a link in ~/.claude (managed elsewhere) but also in the repo; keep only one")
            continue
        for d in tree_diff(src, DEST / "skills" / name):
            found.append(f"skills/{name}: {d}")
    live_skills = ({p.name for p in (DEST / "skills").iterdir() if p.is_dir() and not is_link(p)}
                   if (DEST / "skills").is_dir() else set())
    for extra in sorted(live_skills - set(srcs) - {"synced"}):
        found.append(f"skills/{extra}: exists in ~/.claude but not in the repo")
    for a in agent_sources():
        live = DEST / "agents" / a.name
        if not live.is_file() or live.read_bytes().replace(b"\r\n", b"\n") != a.read_bytes().replace(b"\r\n", b"\n"):
            found.append(f"agents/{a.name}: missing or changed in ~/.claude")
    have = installed_plugins()
    if have is None:
        found.append("plugins: cannot check (the `claude` CLI is not on PATH)")
    else:
        for p in PLUGINS:
            if p not in have:
                found.append(f"plugins: {p} is not installed")
    if with_personal:
        for h in hook_sources():
            live = DEST / "hooks" / h.name
            if not live.is_file() or live.read_bytes().replace(b"\r\n", b"\n") != h.read_bytes().replace(b"\r\n", b"\n"):
                found.append(f"hooks/{h.name}: missing or changed in ~/.claude")
        settings = DEST / "settings.json"
        try:
            live_hooks = json.loads(settings.read_text(encoding="utf-8")).get("hooks")
        except (OSError, ValueError):
            live_hooks = None
        if live_hooks != hooks_block():
            found.append("settings.json: hooks block differs from personal/settings.hooks.json")
        sj = PERSONAL / "setup.json"
        live_sj = DEST / "setup.json"
        if sj.is_file() and (not live_sj.is_file() or
                             json.loads(sj.read_text(encoding="utf-8")) != json.loads(live_sj.read_text(encoding="utf-8"))):
            found.append("setup.json: missing or different in ~/.claude")
    return found
