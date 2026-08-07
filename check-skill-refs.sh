#!/usr/bin/env bash
# Report SKILL.md files that cite a reference document which does not exist.
#
# This is the class of bug that makes a plugin look like it lost files during
# vendoring, when in fact the relative paths were wrong upstream. Run it after
# adding or updating any vendored plugin.
#
#   bash check-skill-refs.sh              # scan plugins/ and tools/
#   bash check-skill-refs.sh plugins/foo  # scan one plugin
#
# Scope: only backticked paths containing `references/`. That is the shared
# convention for "companion file this skill must READ". Deliberately excludes
# output paths a skill is told to WRITE (`linkedin/post.md`), which are not
# expected to exist on disk and would otherwise drown the signal.
#
# Reports and exits 0 -- informational, never blocks a build.
#
# bash 3.2 compatible (macOS system bash). Two gotchas this avoids:
#   - findings go to a temp file, not $( ), because bash 3.2 mis-parses a
#     case pattern containing ')' when nested inside a command substitution;
#   - roots come from "$@", never a space-joined string, because the repo
#     path itself can contain spaces.
set -uo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
if [ "$#" -eq 0 ]; then
  set -- "$HERE/plugins" "$HERE/tools"
fi

FOUND="$(mktemp "${TMPDIR:-/tmp}/cpk-refs.XXXXXX")"
trap 'rm -f "$FOUND"' EXIT

for root in "$@"; do
  [ -d "$root" ] || continue
  find "$root" -name SKILL.md -not -path '*/node_modules/*' -print 2>/dev/null | while read -r f; do
    d="$(dirname "$f")"
    grep -o '`[^`]*references/[^`]*\.md`' "$f" 2>/dev/null | tr -d '`' | sort -u | while read -r ref; do
      # Skip what we cannot or should not resolve:
      #   http*  external links
      #   /*, ~* absolute and home-relative paths
      #   @*     Claude Code file-mention syntax, not a filesystem path
      # Placeholder syntaxes -- not literal paths, nothing to resolve:
      #   references/losses_<type>.md   references/{subcommand}.md
      #   ${CLAUDE_SKILL_DIR}/references/presets.md
      case "$ref" in
        http*)  continue ;;
        /*)     continue ;;
        '~'*)   continue ;;
        '@'*)   continue ;;
        *'<'*)  continue ;;
        *'{'*)  continue ;;
        *'$'*)  continue ;;
      esac
      if [ ! -f "$d/$ref" ]; then
        printf '  BROKEN  %s\n          -> %s\n' "${f#$HERE/}" "$ref" >> "$FOUND"
      fi
    done
  done
done

if [ -s "$FOUND" ]; then
  cat "$FOUND"
  echo "check-skill-refs: broken reference paths found (see above)."
else
  echo "check-skill-refs: all reference paths resolve."
fi
exit 0
