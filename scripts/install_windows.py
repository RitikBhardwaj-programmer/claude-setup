"""Install this repo into ~/.claude on Windows: shared + personal parts, subagents, marketplace plugins, hooks,
setup.json, the hooks block of settings.json and the agent bridge (Codex rules block, Antigravity skills.json and
basic-memory MCP entry). Everything it replaces is backed up first. Called by install.ps1.

  py -3 scripts/install_windows.py [--dry-run] [--shared-only]

Leaves alone: other settings keys (theme, permissions...), ~/.claude/skills/synced, tools/, projects/, any
skill that is not in this repo (reported, not deleted).
"""
import argparse
import json
import os
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from setup_lib import (BRIDGE_JSON, CODEX_AGENTS, DEST, GEMINI_CONFIG, HOME, IGNORE, PERSONAL,  # noqa: E402
                       PLUGINS, agent_sources, compose_claude_md, drift, hook_sources, hooks_block, installed_plugins,
                       is_link, merge_block, read_json_file, skill_sources)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--shared-only", action="store_true", help="install only the shared part (like install.sh)")
    a = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")
    personal = not a.shared_only
    backup = DEST / "backups" / f"pre-setup-{datetime.now():%Y%m%d-%H%M%S}"
    actions, backed = [], []

    def save(path: Path):
        if path.exists():
            # Files under ~/.claude keep their relative path; others (Codex, Antigravity) go under home/.
            inside = path.is_relative_to(DEST)
            target = backup / (path.relative_to(DEST) if inside else Path("home") / path.relative_to(HOME))
            if not a.dry_run:
                target.parent.mkdir(parents=True, exist_ok=True)
                (shutil.copytree if path.is_dir() else shutil.copy2)(path, target)
            backed.append(str(path.relative_to(DEST)) if inside else str(path))

    # 1. CLAUDE.md
    md = compose_claude_md(personal)
    live = DEST / "CLAUDE.md"
    if not live.is_file() or live.read_text(encoding="utf-8").replace("\r\n", "\n") != md:
        save(live)
        actions.append("CLAUDE.md")
        if not a.dry_run:
            live.write_text(md, encoding="utf-8", newline="\n")

    # 2. Skills
    for name, src in skill_sources(personal).items():
        dst = DEST / "skills" / name
        if is_link(dst):
            # Never delete or overwrite through a link/junction: its real folder belongs to another repo.
            print(f"SKIPPED skills/{name}: it is a link to {os.path.realpath(dst)} (managed there)")
            continue
        save(dst)
        actions.append(f"skills/{name}")
        if not a.dry_run:
            if dst.exists():
                shutil.rmtree(dst)
            shutil.copytree(src, dst, ignore=shutil.ignore_patterns(*IGNORE))

    # 2b. Subagents
    for ag in agent_sources():
        dst = DEST / "agents" / ag.name
        if dst.is_file() and dst.read_bytes().replace(b"\r\n", b"\n") == ag.read_bytes().replace(b"\r\n", b"\n"):
            continue
        save(dst)
        actions.append(f"agents/{ag.name}")
        if not a.dry_run:
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(ag, dst)

    # 2c. Marketplace plugins (needs the `claude` CLI)
    have = installed_plugins()
    if have is None:
        print("NOTE: `claude` CLI not found; install these plugins by hand: " +
              ", ".join(f"claude plugin install {p}" for p in PLUGINS))
    for p in PLUGINS:
        if have is None or p in have:
            continue
        actions.append(f"plugin {p}")
        if not a.dry_run:
            r = subprocess.run([shutil.which("claude"), "plugin", "install", p], capture_output=True, text=True,
                               encoding="utf-8")
            if r.returncode != 0:
                print(f"WARNING: plugin install failed for {p}: {(r.stderr or r.stdout).strip()}")

    if personal:
        # 3. Hooks
        for h in hook_sources():
            dst = DEST / "hooks" / h.name
            save(dst)
            actions.append(f"hooks/{h.name}")
            if not a.dry_run:
                dst.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(h, dst)
        # 4. setup.json
        sj = PERSONAL / "setup.json"
        if sj.is_file():
            save(DEST / "setup.json")
            actions.append("setup.json")
            if not a.dry_run:
                shutil.copy2(sj, DEST / "setup.json")
        # 5. settings.json: replace only the hooks block
        settings_path = DEST / "settings.json"
        settings = json.loads(settings_path.read_text(encoding="utf-8")) if settings_path.is_file() else {}
        if settings.get("hooks") != hooks_block():
            save(settings_path)
            settings["hooks"] = hooks_block()
            actions.append("settings.json (hooks block)")
            if not a.dry_run:
                settings_path.write_text(json.dumps(settings, indent=2) + "\n", encoding="utf-8")
        # warn about hook commands that point at missing files
        for event, groups in hooks_block().items():
            for g in groups:
                for hk in g.get("hooks", []):
                    for p in [x for x in hk.get("command", "").split('"') if x.lower().endswith(".py")]:
                        if not Path(p).is_file():
                            print(f"WARNING: {event} hook script not found: {p}")

        # 6. Agent bridge: rules block for Codex; shared skills and basic-memory MCP for Antigravity.
        # Antigravity documents no global rules file, so it gets the rules per project (AGENTS.md); see README.
        if CODEX_AGENTS.parent.is_dir():
            raw = CODEX_AGENTS.read_text(encoding="utf-8") if CODEX_AGENTS.is_file() else ""
            have = raw.replace("\r\n", "\n")
            new = merge_block(have)
            if new != have:
                save(CODEX_AGENTS)
                actions.append("~/.codex/AGENTS.md (agent-bridge block)")
                if not a.dry_run:
                    CODEX_AGENTS.write_text(new, encoding="utf-8", newline="\r\n" if "\r\n" in raw else "\n")
        else:
            print("NOTE: ~/.codex not found; skipped the Codex rules block.")
        if GEMINI_CONFIG.is_dir():
            for path, want_fn in BRIDGE_JSON:
                try:
                    have = read_json_file(path)
                except ValueError:
                    print(f"WARNING: {path} is not valid JSON; left alone. Fix it, then run the installer again.")
                    continue
                want = want_fn(have)
                if want is not None and want != have:
                    save(path)
                    actions.append(f"~/.gemini/config/{path.relative_to(GEMINI_CONFIG).as_posix()}")
                    if not a.dry_run:
                        path.parent.mkdir(parents=True, exist_ok=True)
                        path.write_text(json.dumps(want, indent=2) + "\n", encoding="utf-8")
        else:
            print("NOTE: ~/.gemini/config not found; skipped Antigravity skills.json, MCP config and watcher sidecar.")

    print(("DRY RUN - would install: " if a.dry_run else "Installed: ") + ", ".join(actions))
    if backed and not a.dry_run:
        print(f"Backup of replaced files: {backup}")
    if not a.dry_run:
        left = drift(personal)
        print("Drift check: in sync" if not left else "Drift check found:\n  - " + "\n  - ".join(left))
        print("Start a NEW Claude Code session to load changed CLAUDE.md, skills and hooks.")
        return 1 if left else 0
    return 0


if __name__ == "__main__":
    sys.exit(main())
