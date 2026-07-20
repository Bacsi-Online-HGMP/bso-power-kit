#!/usr/bin/env bash
# Bootstrap a Claude setup (new machine, or a second account) from this repo.
#
# Usage:
#   bash bootstrap.sh                    # set up default account (~/.claude)
#   bash bootstrap.sh ~/.claude-pro2     # set up a second account config dir
#
# What it does:
#   1. Copies dotfiles (CLAUDE.md, settings.json, agents/, commands/) into the config dir
#   2. Registers this repo as a plugin marketplace
#   3. Prints the install commands for the bundled plugins
#
# It NEVER touches credentials, session data, or the Desktop app config.
set -euo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
TARGET="${1:-$HOME/.claude}"

echo "==> Target config dir: $TARGET"
mkdir -p "$TARGET"

echo "==> Copying dotfiles"
cp -v "$HERE/dotfiles/claude-code/CLAUDE.md"      "$TARGET/" 2>/dev/null || true
cp -v "$HERE/dotfiles/claude-code/settings.json"  "$TARGET/" 2>/dev/null || true
for d in agents commands; do
  if [ -d "$HERE/dotfiles/claude-code/$d" ]; then
    mkdir -p "$TARGET/$d"
    cp -Rv "$HERE/dotfiles/claude-code/$d/." "$TARGET/$d/"
  fi
done

echo "==> Registering marketplace"
if [ "$TARGET" = "$HOME/.claude" ]; then
  claude plugin marketplace add "$HERE" || echo "  (add manually inside claude: /plugin marketplace add $HERE)"
else
  CLAUDE_CONFIG_DIR="$TARGET" claude plugin marketplace add "$HERE" \
    || echo "  (run: CLAUDE_CONFIG_DIR=$TARGET claude  then  /plugin marketplace add $HERE)"
fi

echo
echo "==> Done. Next steps:"
if [ "$TARGET" != "$HOME/.claude" ]; then
  echo "  CLAUDE_CONFIG_DIR=$TARGET claude     # launch, then /login with the other account"
fi
echo "  Inside claude: /plugin  ->  browse claude-power-kit  ->  install what you need"
echo
echo "Cowork: Settings > Capabilities > add this folder as a marketplace, enable plugins."
