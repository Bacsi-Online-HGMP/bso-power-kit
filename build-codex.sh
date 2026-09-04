#!/usr/bin/env bash
# Export this kit to Codex CLI, which has no plugin or skill system of its own.
#
# Codex reads AGENTS.md natively and takes reusable prompts as plain markdown in
# ~/.codex/prompts/. It has no skill loader -- nothing scans a folder and pulls a
# SKILL.md in when the task matches. So the skills are not copied anywhere; they
# stay where they are and Codex is handed a map to them.
#
# Three artefacts, under integrations/codex/:
#   AGENTS.md         small, always in context: house rules + the 33-plugin map
#   SKILLS-INDEX.md   every skill, one line each, read on demand via the map
#   prompts/*.md      the plugin slash commands, as Codex prompts
#
# Splitting the index out of AGENTS.md is the whole point. All 378 descriptions
# are ~197 KB; inlining them into an always-on file spends a third of the context
# window before the user types. The map costs ~1 KB and says where to look.
#
#   bash build-codex.sh              # generate into integrations/codex/
#   bash build-codex.sh --install    # generate, then copy to ~/.codex/
#
# Not folded into build-standalone.sh (re-vendors plugins) or check-skill-refs.sh
# (lints companion paths) -- neither reads frontmatter or emits anything.
set -euo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
OUT="$HERE/integrations/codex"
INSTALL=0
[ "${1:-}" = "--install" ] && INSTALL=1

rm -rf "$OUT"
mkdir -p "$OUT/prompts"

# --- skill enumeration --------------------------------------------------------
# Several plugins ship the same skill duplicated into per-harness folders
# (.claude/, .codex/, .openclaw/, .cursor/ ...). 64 of the 378 SKILL.md files are
# those mirrors. Listing them would offer the same skill three times under three
# paths, so only the plain copy is indexed. No plugin is mirror-only, so nothing
# is lost by the filter.
real_skills() { find plugins skills -name SKILL.md | grep -vE '/\.[a-zA-Z]+/' | sort; }

# --- frontmatter reader -------------------------------------------------------
# Pulls one key out of the leading --- block, following folded/continued lines,
# and flattens the result to a single line.
fm() {
  awk -v key="$2" '
    NR==1 && $0 ~ /^---[[:space:]]*$/ { infm=1; next }
    infm && $0 ~ /^---[[:space:]]*$/  { exit }
    infm {
      if ($0 ~ "^" key ":") {
        sub("^" key ":[[:space:]]*", ""); sub(/^[>|][-+]?[[:space:]]*$/, "")
        val = $0; grabbing = 1; next
      }
      if (grabbing) {
        if ($0 ~ /^[a-zA-Z_-]+:/) { grabbing = 0 }
        else { line = $0; sub(/^[[:space:]]+/, "", line); val = val " " line }
      }
    }
    END { gsub(/^[[:space:]]+|[[:space:]]+$/, "", val); gsub(/"/, "'"'"'", val); print val }
  ' "$1"
}

# --- SKILLS-INDEX.md ----------------------------------------------------------
{
  echo "# Skill index — bso-power-kit"
  echo
  echo "Every skill in the kit. Read the \`SKILL.md\` at the path given; it is the"
  echo "full instruction, this line is only the label. Paths are relative to"
  echo "\`$HERE\`."
  echo
} > "$OUT/SKILLS-INDEX.md"

cd "$HERE"
last_plugin=""
real_skills | while read -r f; do
  plugin=$(echo "$f" | cut -d/ -f2)
  [ "$plugin" != "$last_plugin" ] && { printf '\n## %s\n\n' "$plugin" >> "$OUT/SKILLS-INDEX.md"; last_plugin="$plugin"; }
  name=$(fm "$f" name); [ -z "$name" ] && name=$(basename "$(dirname "$f")")
  desc=$(fm "$f" description)
  [ ${#desc} -gt 220 ] && desc="${desc:0:217}..."
  printf -- '- **%s** — %s\n  `%s`\n' "$name" "$desc" "$f" >> "$OUT/SKILLS-INDEX.md"
done

# --- AGENTS.md ----------------------------------------------------------------
{
  cat <<HDR
# bso-power-kit — agent instructions

A library of $(real_skills | wc -l | tr -d ' ') skills lives at:

    $HERE

Codex has no skill loader, so nothing here loads on its own. When a task looks
like one the library covers — writing, reviewing, research, SEO, video, ads,
compliance — do this before improvising:

1. Grep the index: \`grep -i '<topic>' "$HERE/integrations/codex/SKILLS-INDEX.md"\`
2. Read the \`SKILL.md\` it points at, in full.
3. Follow it. If it cites companion files (\`references/\`, \`scripts/\`), read those too.

Do not read SKILLS-INDEX.md end to end — it is ~200 KB. Grep it.

## What is in the library

HDR
  for d in plugins/*/; do
    p=$(basename "$d")
    n=$(find "$d" -name SKILL.md | grep -vE "/\.[a-zA-Z]+/" | wc -l | tr -d ' ')
    desc=$(python3 - "$HERE/.claude-plugin/marketplace.json" "$p" <<'PY' 2>/dev/null || true
import json,sys
try:
    m=json.load(open(sys.argv[1]))
    want=sys.argv[2]
    hit=next((x.get("description","") for x in m.get("plugins",[])
              if x.get("source","").rstrip("/").endswith(want) or x.get("name","")==want
              or want.startswith(x.get("name",""))), "")
    print(hit)
except Exception:
    print("")
PY
)
    [ -z "$desc" ] && desc="$n skills"
    printf -- '- **%s** (%s) — %s\n' "$p" "$n" "$desc"
  done
  echo
  echo "## Plugins that ship their own Codex instructions"
  echo
  echo "These were written for Codex upstream. When using one of these plugins,"
  echo "read its own AGENTS.md first — it outranks the generic guidance above."
  echo
  find plugins -maxdepth 2 -name 'AGENTS.md' | sort | while read -r a; do
    printf -- '- `%s`\n' "$HERE/$a"
  done
  cat <<'FTR'

## Caveats carried over from Claude Code

Some skills were written for a harness Codex does not have:

- Skills that say "dispatch a subagent" / "use the Task tool" — do the work inline instead.
- Skills that name `allowed-tools` — ignore that line, it is not a Codex concept.
- Hooks do not exist here. Anything a skill expects to fire automatically must be run by hand.
FTR
} > "$OUT/AGENTS.md"

# --- prompts ------------------------------------------------------------------
# Skip opencode mirrors (duplicates of caveman-main/commands) and CLAUDE.md files,
# which are instructions to Claude, not commands.
find plugins -path '*/commands/*.md' \
  ! -path '*/opencode/*' ! -name 'CLAUDE.md' | sort | while read -r f; do
  slug=$(basename "$f" .md)
  proot="plugins/$(echo "$f" | cut -d/ -f2)"
  desc=$(fm "$f" description)
  {
    [ -n "$desc" ] && printf -- '<!-- %s -->\n\n' "$desc"
    # Drop the frontmatter (model:, allowed-tools: etc. mean nothing to Codex),
    # then resolve $CLAUDE_PLUGIN_ROOT, which Codex does not set, to a real path.
    awk 'NR==1 && /^---[[:space:]]*$/ {fm=1; next} fm && /^---[[:space:]]*$/ {fm=0; next} !fm' "$f" \
      | sed -e "s|\${CLAUDE_PLUGIN_ROOT}|$HERE/$proot|g" -e "s|\$CLAUDE_PLUGIN_ROOT|$HERE/$proot|g"
  } > "$OUT/prompts/$slug.md"
done

echo "generated:"
echo "  $OUT/AGENTS.md              ($(wc -c < "$OUT/AGENTS.md" | tr -d ' ') bytes)"
echo "  $OUT/SKILLS-INDEX.md        ($(wc -c < "$OUT/SKILLS-INDEX.md" | tr -d ' ') bytes)"
echo "  $OUT/prompts/               ($(ls "$OUT/prompts" | wc -l | tr -d ' ') prompts)"

if [ "$INSTALL" -eq 1 ]; then
  mkdir -p "$HOME/.codex/prompts"
  cp "$OUT/AGENTS.md" "$HOME/.codex/AGENTS.md"
  cp "$OUT/prompts/"*.md "$HOME/.codex/prompts/"
  echo
  echo "installed to ~/.codex/ — AGENTS.md and $(ls "$OUT/prompts" | wc -l | tr -d ' ') prompts"
  echo "SKILLS-INDEX.md stays in the repo; AGENTS.md points at it by absolute path."
fi
