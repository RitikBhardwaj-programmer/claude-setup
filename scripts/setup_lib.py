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
# Agent bridge: other apps that read the shared skills and rules. Each target is only touched when its app folder exists.
HOME = Path.home()
CODEX_AGENTS = HOME / ".codex" / "AGENTS.md"
GEMINI_CONFIG = HOME / ".gemini" / "config"
GEMINI_SKILLS_JSON = GEMINI_CONFIG / "skills.json"
GEMINI_MCP_JSON = GEMINI_CONFIG / "mcp_config.json"
# Antigravity runs this sidecar itself (the user enables it in its Automations dashboard; the installer never does).
GEMINI_SIDECAR_JSON = GEMINI_CONFIG / "sidecars" / "handoff-watcher" / "sidecar.json"
# Skills with no Claude-only tool calls (checked by grep), so Antigravity can load them from ~/.claude/skills.
PORTABLE_SKILLS = ["agent-handoff", "context-handoff", "explain", "intuition", "youtube-transcript"]
RULES_BLOCK_FILE = REPO / "shared" / "agent-bridge-rules.md"
BLOCK_START, BLOCK_END = "<!-- agent-bridge:start -->", "<!-- agent-bridge:end -->"


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


def personal_plugin_config():
    """(marketplaces {name: owner/repo}, plugin ids) from personal/setup.json's "plugins" key."""
    cfg = setup_key("plugins") or {}
    return dict(cfg.get("marketplaces") or {}), list(cfg.get("install") or [])


def wanted_plugins(with_personal: bool):
    """Plugin ids the setup expects: the shared PLUGINS, plus the personal ones on this PC."""
    return PLUGINS + (personal_plugin_config()[1] if with_personal else [])


def known_marketplaces():
    """Names of the plugin marketplaces Claude Code already knows (empty set if the file is missing)."""
    data = read_json_file(DEST / "plugins" / "known_marketplaces.json")
    return set(data) if isinstance(data, dict) else set()


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
        for p in wanted_plugins(with_personal):
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
        found += bridge_drift()
        found += claude_mcp_drift()
        found += desktop_mcp_drift()
        found += writer_task_drift()
    return found


# ---- Agent bridge (Codex rules, Antigravity skills.json and MCP) ----

def rules_block() -> str:
    body = RULES_BLOCK_FILE.read_text(encoding="utf-8").replace("\r\n", "\n").strip("\n")
    return f"{BLOCK_START}\n{body}\n{BLOCK_END}"


def merge_block(text: str) -> str:
    """text (LF newlines) with the agent-bridge block added or replaced; nothing outside the markers changes."""
    block = rules_block()
    i, j = text.find(BLOCK_START), text.find(BLOCK_END)
    if i != -1 and j > i:
        return text[:i] + block + text[j + len(BLOCK_END):]
    return (text.rstrip("\n") + "\n\n" if text.strip() else "") + block + "\n"


def read_json_file(path: Path):
    """Parsed JSON object of a file; {} when missing or empty. Raises ValueError on invalid JSON."""
    if not path.is_file() or not path.read_text(encoding="utf-8").strip():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def want_skills_json(have: dict) -> dict:
    """skills.json with our ~/.claude/skills entry set, keeping every other key and entry."""
    out = dict(have)
    entries = [e for e in out.get("entries", []) if e.get("path") != "~/.claude/skills"]
    entries.append({"path": "~/.claude/skills", "include_only": list(PORTABLE_SKILLS)})
    out["entries"] = entries
    return out


def setup_key(key: str):
    """One top-level value of personal/setup.json, or None."""
    sj = PERSONAL / "setup.json"
    return json.loads(sj.read_text(encoding="utf-8")).get(key) if sj.is_file() else None


def basic_memory_server():
    """The basic-memory stdio server entry (command, args, env) from personal/setup.json, or None."""
    cfg = setup_key("basic_memory_mcp")
    if not cfg:
        return None
    return {"command": cfg["command"], "args": cfg.get("args", []), "env": cfg.get("env", {})}


def want_mcp_json(have: dict):
    """mcp_config.json with the basic-memory server set (from personal/setup.json), or None when not configured."""
    server = basic_memory_server()
    if not server:
        return None
    out = dict(have)
    out["mcpServers"] = {**out.get("mcpServers", {}), "basic-memory": server}
    return out


# ---- basic-memory for Claude Code (user scope) and the single writer task ----
# Every session starts its own basic-memory process. They are readers (no file watcher); one hidden
# Task Scheduler process is the only watcher, so edits are not embedded by several processes at once.

CLAUDE_JSON = HOME / ".claude.json"


def claude_mcp_drift():
    """Drift finding for the user-scope basic-memory server in ~/.claude.json (read only; `claude mcp` writes it)."""
    server = basic_memory_server()
    if not server:
        return []
    try:
        live = read_json_file(CLAUDE_JSON).get("mcpServers", {}).get("basic-memory")
    except ValueError:
        return ["~/.claude.json: invalid JSON"]
    want = {"type": "stdio", **server}
    if not live or {k: live.get(k) for k in want} != want:
        return ["~/.claude.json: user-scope basic-memory MCP server missing or changed"]
    return []


# Claude Desktop chat starts its own basic-memory process from this file, so it gets the same reader env.
def claude_desktop_json() -> Path:
    """The config file Claude Desktop reads. The Store (MSIX) build moves its user data from %APPDATA%\\Claude to
    %LOCALAPPDATA%\\Claude-Data\\claude_<publisher id> and leaves only a `.user-data-left.*` marker behind."""
    local = sorted(Path(os.environ.get("LOCALAPPDATA", HOME / "AppData" / "Local")).glob("Claude-Data/claude_*"),
                   key=lambda p: p.stat().st_mtime, reverse=True)
    base = local[0] if local else Path(os.environ.get("APPDATA", HOME / "AppData" / "Roaming")) / "Claude"
    return base / "claude_desktop_config.json"


CLAUDE_DESKTOP_JSON = claude_desktop_json()


def desktop_mcp_drift():
    """Drift finding for the basic-memory server in claude_desktop_config.json (only when Claude Desktop is installed)."""
    if not CLAUDE_DESKTOP_JSON.parent.is_dir():
        return []
    try:
        have = read_json_file(CLAUDE_DESKTOP_JSON)
    except ValueError:
        return ["claude_desktop_config.json: invalid JSON"]
    want = want_mcp_json(have)
    if want is not None and want != have:
        return ["claude_desktop_config.json: basic-memory MCP server missing or changed"]
    return []


def writer_task_action():
    """(task name, executable, arguments) of the writer task, or None when not configured. conhost --headless
    keeps it windowless; cmd sets the env vars because Task Scheduler actions cannot. No space before && : cmd
    keeps it in the value ("true " fails pydantic's bool parsing and the writer exits)."""
    cfg, server = setup_key("basic_memory_writer"), basic_memory_server()
    if not cfg or not server:
        return None
    sets = "".join(f"set {k}={v}&& " for k, v in cfg.get("env", {}).items())
    inner = sets + f'"{server["command"]}" ' + " ".join(cfg["args"])
    return cfg["task_name"], "conhost.exe", f'--headless cmd.exe /d /s /c "{inner}"'


def live_task_action(name: str):
    """(executable, arguments) of a scheduled task's first action, or None when the task does not exist."""
    ps = (f"$t = Get-ScheduledTask -TaskName '{name}' -ErrorAction SilentlyContinue; "
          "if ($t) { $t.Actions[0] | Select-Object Execute, Arguments | ConvertTo-Json -Compress }")
    r = subprocess.run(["powershell", "-NoProfile", "-Command", ps], capture_output=True, text=True, encoding="utf-8")
    if not r.stdout.strip():
        return None
    a = json.loads(r.stdout)
    return a["Execute"], a["Arguments"]


def writer_task_drift():
    want = writer_task_action()
    if not want:
        return []
    name, exe, args = want
    if live_task_action(name) != (exe, args):
        return [f"Task Scheduler: {name} (basic-memory writer) missing or changed"]
    return []


def want_sidecar_json(have: dict) -> dict:
    """Handoff-watcher sidecar.json with our launch keys set. Other keys (agent_permissions that Antigravity or the
    user adds after a test run) are kept."""
    script = DEST / "skills" / "agent-handoff" / "scripts" / "antigravity_watcher.py"
    out = dict(have)
    out.update({
        "command": (shutil.which("py") or "py").replace("\\", "/"),
        "args": ["-3", str(script).replace("\\", "/")],
        "restart_policy": "always",
        "display_name": "Agent handoff watcher",
        "description": "Starts an Antigravity conversation when a project on the watch list gets an open "
                       ".handoff/ brief addressed to Antigravity (agent-handoff skill).",
    })
    return out


# Files outside ~/.claude that the bridge manages: (path, function giving the wanted JSON from the current JSON).
BRIDGE_JSON = ((GEMINI_SKILLS_JSON, want_skills_json), (GEMINI_MCP_JSON, want_mcp_json),
               (GEMINI_SIDECAR_JSON, want_sidecar_json))


def bridge_drift():
    """Drift findings for the agent-bridge files outside ~/.claude."""
    found = []
    if CODEX_AGENTS.parent.is_dir():
        have = CODEX_AGENTS.read_text(encoding="utf-8").replace("\r\n", "\n") if CODEX_AGENTS.is_file() else ""
        if merge_block(have) != have:
            found.append("~/.codex/AGENTS.md: agent-bridge block missing or changed")
    if GEMINI_CONFIG.is_dir():
        for path, want_fn in BRIDGE_JSON:
            name = path.relative_to(GEMINI_CONFIG).as_posix()
            try:
                have = read_json_file(path)
            except ValueError:
                found.append(f"~/.gemini/config/{name}: invalid JSON")
                continue
            want = want_fn(have)
            if want is not None and want != have:
                found.append(f"~/.gemini/config/{name}: our entry is missing or changed")
    return found
