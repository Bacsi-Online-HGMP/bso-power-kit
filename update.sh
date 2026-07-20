#!/usr/bin/env bash
# One-command update for every account on this machine:
#   pull repo -> refresh dotfiles into each config dir -> update marketplace.
# Run manually, or let the LaunchAgent (install-autosync.sh) run it daily.
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
cd "$HERE"

echo "==> git pull"
git pull --rebase --autostash

# Config dirs to keep in sync. Add more as you create accounts.
TARGETS=( "$HOME/.claude" "$HOME/.claude-pro2" )

for T in "${TARGETS[@]}"; do
  [ -d "$T" ] || continue
  cp "$HERE/dotfiles/claude-code/CLAUDE.md"     "$T/" 2>/dev/null || true
  cp "$HERE/dotfiles/claude-code/settings.json" "$T/" 2>/dev/null || true
  for d in agents commands; do
    if [ -d "$HERE/dotfiles/claude-code/$d" ]; then
      mkdir -p "$T/$d"
      cp -R "$HERE/dotfiles/claude-code/$d/." "$T/$d/"
    fi
  done
  echo "==> dotfiles refreshed: $T"
done

# Marketplace update per account (non-fatal if CLI absent or logged out)
command -v claude >/dev/null 2>&1 && {
  claude plugin marketplace update claude-power-kit 2>/dev/null \
    && echo "==> marketplace updated: default account" || true
  [ -d "$HOME/.claude-pro2" ] && CLAUDE_CONFIG_DIR="$HOME/.claude-pro2" \
    claude plugin marketplace update claude-power-kit 2>/dev/null \
    && echo "==> marketplace updated: pro2 account" || true
}

echo "==> update complete $(date '+%Y-%m-%d %H:%M')"
