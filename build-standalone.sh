#!/usr/bin/env bash
# HISTORICAL — this is not how you set up a new machine any more. Use: git clone.
#
# It was the original one-time bootstrapper, back when the plugin repos lived in a sibling
# folder and this bundle was empty. Since then `plugins/` and `tools/` have been committed,
# so the repo already carries everything and a clone is all you need.
#
# Kept because re-vendoring is still the way to pull an upstream update: refresh the source
# folder, run this, commit the diff. Nothing else calls it.
#
# ⚠ It starts with `rm -rf plugins tools`. Run it with a stale source folder and you will
#   delete vendored plugins that exist only in git. The guard below refuses to run inside a
#   git repo unless you pass --force.
set -euo pipefail

FORCE=0
[ "${1:-}" = "--force" ] && FORCE=1

HERE="$(cd "$(dirname "$0")" && pwd)"
# Source repos. If you move this bundle, point SRC at wherever the repo folders live.
SRC="$HERE/../Turn these to skill bundles"

if [ -d "$HERE/.git" ] && [ "$FORCE" -eq 0 ]; then
  cat >&2 <<'MSG'
REFUSING TO RUN — this is a git repo, and plugins/ and tools/ are committed to it.

This script deletes both directories and rebuilds them from a local source folder. If that
folder is missing or out of date, you lose vendored plugins that exist nowhere else.

To set up a new machine, you do not need this script:
    git clone https://github.com/Bacsi-Online-HGMP/bso-power-kit.git
    claude plugin marketplace add Bacsi-Online-HGMP/bso-power-kit

To genuinely re-vendor from upstream, check `git status` is clean first, then:
    bash build-standalone.sh --force
and review the diff before committing.
MSG
  exit 1
fi

PLUGINS=(
  academic-research-skills-main idea-validation-agents
  mattpocock-skills-main brooks-lint-main andrej-karpathy-skills-main
  verification-before-completion ponytail-main caveman-main
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

# Dropped in 0.2.0 — do not re-add. Reasons: bootstrap-device/plugins-loai.tsv
#   superpowers-main           mattpocock-skills covers it; verification-before-completion split out
#   ECC-main                   NG=1, no usable skill
#   huggingface-skills-main    19 ML skills, all hit the PH floor
#   AI-Research-SKILLs-main    model training, not content work
#   SocratiCode-main           duplicate job, unused
#   Understand-Anything-main   duplicate job, unused
#   agentmemory-main           Cowork has memory per account
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

# Re-vendoring restores upstream's broken reference paths. Re-apply the fixes
# and re-check, so a refresh cannot silently reintroduce them. See patches/README.md.
echo
echo "Applying vendor patches"
for p in "$HERE"/patches/*.sh; do
  [ -f "$p" ] && bash "$p"
done
echo "Checking skill reference paths"
[ -f "$HERE/check-skill-refs.sh" ] && bash "$HERE/check-skill-refs.sh"

echo
du -sh "$HERE/plugins" "$HERE/tools" 2>/dev/null || true
[ "$miss" -eq 0 ] && echo "Done — bundle is standalone." || echo "Done with warnings — some sources were missing (see ! lines)."
echo
echo "To share: zip it ->   (cd \"$HERE/..\" && zip -rq bso-power-kit.zip Ultimate-Bundle)"
echo "To use in Claude Code: /plugin marketplace add ./Ultimate-Bundle"
