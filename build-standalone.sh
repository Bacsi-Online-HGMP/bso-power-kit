#!/usr/bin/env bash
# Vendors the keeper repos INTO this bundle so the folder is standalone/giftable.
# Run once from the Ultimate-Bundle folder:   bash build-standalone.sh
# Fast on your own Mac (a few seconds). Safe to re-run — it starts clean.
set -euo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
# Source repos. If you move this bundle, point SRC at wherever the repo folders live.
SRC="$HERE/../Turn these to skill bundles"

PLUGINS=(
  AI-Research-SKILLs-main academic-research-skills-main huggingface-skills-main
  idea-validation-agents
  Understand-Anything-main SocratiCode-main agentmemory-main
  superpowers-main brooks-lint-main andrej-karpathy-skills-main ponytail-main
  mattpocock-skills-main caveman-main verification-before-completion ECC-main
  anti-slop impeccable-main ui-ux-pro-max-skill taste-skill
  threads-carousel-claude-skill modern-web-guidance-main
  watch mcp-video-analyzer
  video-editing claude-shorts youtube-shorts-pipeline
  claude-blog claude-youtube youtuber claude-repurpose
  create-viral-content viral-hooks-skill last30days-skill-main
  claude-seo claude-ads
  cybersecurity-defense worktrunk-main handoff
)
TOOLS=(
  notebooklm-mcp-cli-main Agent-Reach-main agentskills agency-agents
  design.md ai-website-cloner-template-master vercel-labs-skills-main
)

# Dropped in 0.2.0 — do not re-add:
#   chrome-devtools-mcp-main   Claude in Chrome covers it
#   youtube-video-perception   superseded by `watch`
#   agent-skills-main (Apify)  whole scraping group dropped
#   tasteskill-main            stale snapshot; use plugins/taste-skill (has plugin.json)
#   design.md-main             stale snapshot; use tools/design.md
#
# Registered as separate marketplaces rather than vendored (~490 MB):
#   sickn33/agentic-awesome-skills  wshobson/agents  garrytan/gbrain  garrytan/gstack

if [ ! -d "$SRC" ]; then
  echo "ERROR: source folder not found: $SRC"
  echo "Edit SRC at the top of this script to point at your repo folder."
  exit 1
fi

echo "Cleaning old copies..."
rm -rf "$HERE/plugins" "$HERE/tools"
mkdir -p "$HERE/plugins" "$HERE/tools"

miss=0
echo "Copying plugins -> ./plugins"
for r in "${PLUGINS[@]}"; do
  if [ -d "$SRC/$r" ]; then cp -R "$SRC/$r" "$HERE/plugins/$r"; echo "  + $r"; else echo "  ! MISSING $r"; miss=1; fi
done
echo "Copying tools -> ./tools"
for r in "${TOOLS[@]}"; do
  if [ -d "$SRC/$r" ]; then cp -R "$SRC/$r" "$HERE/tools/$r"; echo "  + $r"; else echo "  ! MISSING $r"; miss=1; fi
done

echo
du -sh "$HERE/plugins" "$HERE/tools" 2>/dev/null || true
[ "$miss" -eq 0 ] && echo "Done — bundle is standalone." || echo "Done with warnings — some sources were missing (see ! lines)."
echo
echo "To share: zip it ->   (cd \"$HERE/..\" && zip -rq claude-power-kit.zip Ultimate-Bundle)"
echo "To use in Claude Code: /plugin marketplace add ./Ultimate-Bundle"
