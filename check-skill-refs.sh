#!/usr/bin/env bash
# Report SKILL.md files citing companion documents that do not exist.
#
# This is the class of bug that makes a plugin look like it lost files during
# vendoring, when in fact the relative paths were wrong upstream. Run it after
# adding or updating any vendored plugin.
#
#   bash check-skill-refs.sh                  # scan plugins/ and tools/
#   bash check-skill-refs.sh plugins/foo      # scan one plugin
#   bash check-skill-refs.sh --strict         # exit 1 on findings (for CI)
#
# WHAT COUNTS AS A CITATION
# Only backticked paths ending in .md that sit under a known companion-file
# directory. Two tiers, because the cost of a false positive differs:
#
#   strict    references/
#             Reported even when the document exists nowhere in the plugin --
#             that is a skill promising a file it never shipped, which is worth
#             knowing about.
#
#   lenient   agents/ docs/ templates/ rules/ logic/ assets/ examples/
#             Reported only when a file of that name exists somewhere in the
#             plugin, i.e. the path is wrong but fixable. These directories also
#             appear as OUTPUT paths a skill is told to write (`docs/report.md`),
#             and flagging those would drown the signal.
#
# Everything else is ignored: bare paths like `linkedin/post.md`, URLs, absolute
# and home-relative paths, @-mentions, and placeholders such as
# references/losses_<type>.md, references/{subcommand}.md, ${VAR}/references/x.md
#
# bash 3.2 compatible (macOS system bash). Two gotchas this avoids:
#   - findings go to a temp file, not $( ), because bash 3.2 mis-parses a case
#     pattern containing ')' when nested inside a command substitution;
#   - roots come from "$@", never a space-joined string, because the repo path
#     itself can contain spaces.
set -uo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"

STRICT_EXIT=0
roots=()
for a in "$@"; do
  if [ "$a" = "--strict" ]; then STRICT_EXIT=1; else roots+=("$a"); fi
done
# ${roots[@]+...} guards the empty-array case, which trips `set -u` on bash 3.2.
set -- ${roots[@]+"${roots[@]}"}
[ "$#" -eq 0 ] && set -- "$HERE/plugins" "$HERE/tools"

FOUND="$(mktemp "${TMPDIR:-/tmp}/cpk-refs.XXXXXX")"
INDEX="$(mktemp "${TMPDIR:-/tmp}/cpk-index.XXXXXX")"
trap 'rm -f "$FOUND" "$INDEX"' EXIT

LENIENT='agents docs templates rules logic assets examples'

for root in "$@"; do
  [ -d "$root" ] || continue

  # Plugins are the immediate children of a root; each is its own search scope.
  for plugin in "$root"/*; do
    [ -d "$plugin" ] || continue
    find "$plugin" -name '*.md' -not -path '*/node_modules/*' -print 2>/dev/null > "$INDEX"

    find "$plugin" -name SKILL.md -not -path '*/node_modules/*' -print 2>/dev/null | while read -r f; do
      d="$(dirname "$f")"
      grep -o '`[^`]*/[^`]*\.md`' "$f" 2>/dev/null | tr -d '`' | sort -u | while read -r ref; do
        case "$ref" in
          http*)  continue ;;
          /*)     continue ;;
          '~'*)   continue ;;
          '@'*)   continue ;;
          *'<'*)  continue ;;
          *'{'*)  continue ;;
          *'$'*)  continue ;;
          *'*'*)  continue ;;
        esac

        # Which tier does this citation belong to?
        tier=""
        case "/$ref" in */references/*) tier="strict" ;; esac
        if [ -z "$tier" ]; then
          for c in $LENIENT; do
            case "/$ref" in */$c/*) tier="lenient"; break ;; esac
          done
        fi
        [ -z "$tier" ] && continue

        [ -f "$d/$ref" ] && continue

        if [ "$tier" = "lenient" ]; then
          # Only a wrong path is interesting here, not an invented one.
          grep -q "/$(basename "$ref")\$" "$INDEX" || continue
        fi

        printf '  BROKEN  %s\n          -> %s\n' "${f#$HERE/}" "$ref" >> "$FOUND"
      done
    done
  done
done

if [ -s "$FOUND" ]; then
  cat "$FOUND"
  n=$(grep -c BROKEN "$FOUND")
  echo "check-skill-refs: $n broken reference path(s) found."
  [ "$STRICT_EXIT" -eq 1 ] && exit 1
  exit 0
fi

echo "check-skill-refs: all reference paths resolve."
exit 0
