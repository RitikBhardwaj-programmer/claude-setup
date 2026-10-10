#!/usr/bin/env bash
# Installs the shared Claude Code setup (CLAUDE.md, skills, subagents, plugins) into ~/.claude.
# Safe to re-run: anything it would replace is backed up first.
set -euo pipefail

SRC="$(cd "$(dirname "$0")" && pwd)"
DEST="$HOME/.claude"
SKILLS="context-handoff context-handoff-deep graphify llm-council explain report-publisher vendor-requirements-spec improve-setup intuition youtube-transcript route ui-design"
PLUGINS="frontend-design@claude-plugins-official"  # keep in sync with PLUGINS in scripts/setup_lib.py
BACKUP="$DEST/backups/pre-shared-setup-$(date +%Y%m%d-%H%M%S)"

mkdir -p "$DEST/skills" "$DEST/agents"

backed_up=0
backup() {
  mkdir -p "$BACKUP/skills"
  cp -R "$1" "$2"
  backed_up=1
}

# 1. Back up anything that is about to be replaced
if [ -f "$DEST/CLAUDE.md" ]; then
  backup "$DEST/CLAUDE.md" "$BACKUP/CLAUDE.md"
fi
for s in $SKILLS; do
  if [ -d "$DEST/skills/$s" ]; then
    backup "$DEST/skills/$s" "$BACKUP/skills/$s"
  fi
done
for f in "$SRC"/agents/*.md; do
  a="$(basename "$f")"
  if [ -f "$DEST/agents/$a" ]; then
    mkdir -p "$BACKUP/agents"
    backup "$DEST/agents/$a" "$BACKUP/agents/$a"
  fi
done

# 2. Install
cp "$SRC/CLAUDE.md" "$DEST/CLAUDE.md"
for s in $SKILLS; do
  rm -rf "$DEST/skills/$s"
  cp -R "$SRC/skills/$s" "$DEST/skills/$s"
done
cp "$SRC"/agents/*.md "$DEST/agents/"
plugin_note=""
if command -v claude >/dev/null 2>&1; then
  for p in $PLUGINS; do
    if ! claude plugin list --json 2>/dev/null | grep -q "$p"; then
      claude plugin install "$p" || plugin_note="$plugin_note $p"
    fi
  done
else
  plugin_note="$PLUGINS"
fi

# 3. Report
echo ""
echo "Installed into $DEST:"
echo "  - CLAUDE.md"
for s in $SKILLS; do echo "  - skills/$s"; done
for f in "$SRC"/agents/*.md; do echo "  - agents/$(basename "$f")"; done
if [ -n "$plugin_note" ]; then
  echo ""
  echo "These plugins were not installed. Run this for each one:  claude plugin install <name>"
  echo " $plugin_note"
else
  for p in $PLUGINS; do echo "  - plugin $p"; done
fi
if [ "$backed_up" -eq 1 ]; then
  echo ""
  echo "Your previous files were backed up to:"
  echo "  $BACKUP"
fi
echo ""
echo "Note: /graphify needs Python 3. It installs its own package on first use,"
echo "or you can run:  pip3 install graphifyy"
echo ""
echo "Note: report-publisher and vendor-requirements-spec need these Python packages"
echo "(and Google Chrome for PDFs):  pip3 install markdown-it-py pypdfium2 openpyxl"
echo ""
echo "Done. Start a NEW Claude Code session to load the setup."
