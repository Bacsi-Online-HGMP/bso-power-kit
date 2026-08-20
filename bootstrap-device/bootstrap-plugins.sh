#!/usr/bin/env bash
# Reinstall every Claude Code plugin on a NEW MACHINE, from plugins-claude-code.tsv.
#
# Covers LAYER 2 only (Claude Code plugins, installed per machine).
# Layer 1 (Cowork plugins) follows the Claude account and appears after signing in.
# Layer 3 (MCP connectors) must be authorised by hand. See bso-marketing/docs/thiet-bi-moi.md.
#
# The list passed the 9-axis rubric on 2026-08-06: 16 kept, 65 rejected.
# Per-item scores: scoring-layer-2.md - reasons for rejection: plugins-loai.tsv
#
# Dry run to see what it would do:  ./bootstrap-plugins.sh --dry-run
# Runs on bash 3.2 (the macOS default).
#
# PACK - column 4 of the TSV. Every marketplace is added; only plugins are filtered by pack.
# The house rule: a generous store, a tight enable list.
#
#   ./bootstrap-plugins.sh                    # the 'core' pack only
#   ./bootstrap-plugins.sh --pack core,code   # several packs, comma-separated
#   ./bootstrap-plugins.sh --all              # everything, including the unclassified '?' pack
#   ./bootstrap-plugins.sh --list-packs       # which packs exist, and how many plugins in each
set -uo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
LIST="$HERE/plugins-claude-code.tsv"
DRY=0
ALL=0
LISTPACKS=0
PACKS="core"

while [ $# -gt 0 ]; do
  case "$1" in
    --dry-run)    DRY=1 ;;
    --all)        ALL=1 ;;
    --list-packs) LISTPACKS=1 ;;
    --pack)       shift; PACKS="${1:-}"
                  [ -n "$PACKS" ] || { echo "--pack needs a pack name." >&2; exit 1; } ;;
    --pack=*)     PACKS="${1#--pack=}" ;;
    -h|--help)    sed -n '2,20p' "$0"; exit 0 ;;
    *)            echo "Unrecognised argument: $1" >&2; exit 1 ;;
  esac
  shift
done

[ -f "$LIST" ] || { echo "Cannot find $LIST" >&2; exit 1; }

if [ "$LISTPACKS" = 1 ]; then
  echo "Packs present in $(basename "$LIST"):"
  awk -F'\t' '$1=="plugin"{p=($4==""?"?":$4); c[p]++} END{for(k in c) printf "  %-10s %3d plugin\n", k, c[k]}' "$LIST" | sort
  echo
  echo "'?' = unclassified. Only installed with --all."
  exit 0
fi

command -v claude >/dev/null || { echo "No 'claude' command on the PATH." >&2; exit 1; }

# bash 3.2 has no associative arrays. A delimited string is used for lookups instead.
PACKSEL=",$(echo "$PACKS" | tr -d ' '),"
in_pack() {
  [ "$ALL" = 1 ] && return 0
  case "$PACKSEL" in *",$1,"*) return 0;; esac
  return 1
}

run() {
  if [ "$DRY" = 1 ]; then echo "  [dry] $*"; else "$@"; fi
}

if [ "$ALL" = 1 ]; then
  echo "Packs: ALL (--all)"
else
  echo "Packs: $PACKS   - add more with --pack a,b - list them with --list-packs"
fi
echo

# --- Step 1: marketplaces --------------------------------------------------
# This must finish first, or the install command has no idea where to get a plugin from.
echo "== Marketplaces (all added, never filtered by pack) =="
while IFS="$(printf '\t')" read -r kind name ref pack; do
  case "$kind" in \#*|'') continue;; esac
  [ "$kind" = "marketplace" ] || continue

  case "$ref" in
    /*)
      echo "  x $name - registered as a local directory ($ref). Skipped."
      echo "    The old machine must re-register it by git URL and run export-plugins.sh again."
      continue
      ;;
  esac

  echo "  + $name  <- $ref"
  run claude plugin marketplace add "$ref" || echo "    ! failed: $name (private repo? signed in to the wrong gh account?)"
done < "$LIST"

# --- Step 2: plugins -------------------------------------------------------
echo
echo "== Plugin =="
FAIL=""
SKIP=0
DONE=0
while IFS="$(printf '\t')" read -r kind name ref pack; do
  case "$kind" in \#*|'') continue;; esac
  [ "$kind" = "plugin" ] || continue

  [ -n "${pack:-}" ] || pack="?"
  if ! in_pack "$pack"; then
    SKIP=$((SKIP + 1))
    continue
  fi

  echo "  + $name@$ref  [$pack]"
  DONE=$((DONE + 1))
  if ! run claude plugin install "$name@$ref"; then
    FAIL="$FAIL $name@$ref"
  fi
done < "$LIST"

echo
echo "Installed $DONE plugins, skipped $SKIP (outside the selected packs)."
if [ -n "$FAIL" ]; then
  echo "! Failed to install:$FAIL"
  echo "  Usually because a marketplace in step 1 could not be added. Fix the source and re-run."
  exit 1
fi
echo "Done. Restart Claude Code or run /reload-plugins."
echo
echo "Reminder: this is LAYER 2 (Claude Code plugins). Cowork plugins are LAYER 1, tied to the Claude account,"
echo "and cannot be scripted - they must be enabled by hand in the UI. The list is in bso-marketing/docs/chon-cong-cu-2026-08-05.md."
