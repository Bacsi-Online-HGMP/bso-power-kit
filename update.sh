#!/usr/bin/env bash
# One-command update for every account on this machine:
#   pull repo -> refresh dotfiles into each config dir -> update marketplace.
# Run manually, or let the LaunchAgent (install-autosync.sh) run it daily.
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
cd "$HERE"

echo "==> git pull"
git pull --rebase --autostash

# Config dirs to keep in sync. Add more as you create accounts/profiles.
# (bacsi-online + science are claude-multiprofile / launcher profiles)
TARGETS=(
  "$HOME/.claude"
  "$HOME/.claude-bacsi-online"
  "$HOME/.claude-science"
  "$HOME/.claude-pro2"
)

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
  # Per-profile overlay — applied AFTER shared, so it wins.
  # dotfiles/profiles/<name>/ maps to ~/.claude-<name> (~/.claude = "default")
  P="$(basename "$T" | sed 's/^\.claude-\{0,1\}//')"; [ -z "$P" ] && P=default
  if [ -d "$HERE/dotfiles/profiles/$P" ]; then
    cp -R "$HERE/dotfiles/profiles/$P/." "$T/"
    echo "==> profile overlay applied: $P"
  fi
  echo "==> dotfiles refreshed: $T"
done

# Marketplace update per config dir (non-fatal if CLI absent or logged out)
if command -v claude >/dev/null 2>&1; then
  for T in "${TARGETS[@]}"; do
    [ -d "$T" ] || continue
    if [ "$T" = "$HOME/.claude" ]; then
      claude plugin marketplace update claude-power-kit 2>/dev/null \
        && echo "==> marketplace updated: default" || true
    else
      CLAUDE_CONFIG_DIR="$T" claude plugin marketplace update claude-power-kit 2>/dev/null \
        && echo "==> marketplace updated: $(basename "$T")" || true
    fi
  done
fi

echo "==> update complete $(date '+%Y-%m-%d %H:%M')"
