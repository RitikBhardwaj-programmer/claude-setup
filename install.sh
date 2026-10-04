#!/usr/bin/env bash
# Installs the shared Claude Code setup (CLAUDE.md + skills) into ~/.claude.
# Safe to re-run: anything it would replace is backed up first.
set -euo pipefail

SRC="$(cd "$(dirname "$0")" && pwd)"
DEST="$HOME/.claude"
SKILLS="context-handoff context-handoff-deep graphify llm-council"
BACKUP="$DEST/backups/pre-shared-setup-$(date +%Y%m%d-%H%M%S)"

mkdir -p "$DEST/skills"

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

# 2. Install
cp "$SRC/CLAUDE.md" "$DEST/CLAUDE.md"
for s in $SKILLS; do
  rm -rf "$DEST/skills/$s"
  cp -R "$SRC/skills/$s" "$DEST/skills/$s"
done

# 3. Report
echo ""
echo "Installed into $DEST:"
echo "  - CLAUDE.md"
for s in $SKILLS; do echo "  - skills/$s"; done
if [ "$backed_up" -eq 1 ]; then
  echo ""
  echo "Your previous files were backed up to:"
  echo "  $BACKUP"
fi
echo ""
echo "Note: /graphify needs Python 3. It installs its own package on first use,"
echo "or you can run:  pip3 install graphifyy"
echo ""
echo "Done. Start a NEW Claude Code session to load the setup."
