#!/usr/bin/env bash
# Re-vendor plugins from their upstream repositories.
#
#   bash revendor.sh                    # check only: report upstream drift, write nothing
#   bash revendor.sh --apply            # re-vendor every plugin that has a confirmed source
#   bash revendor.sh --apply ui-ux-pro-max-skill caveman-main    # ...or just these
#
# Reads sources.tsv (the upstream map) and writes sources.lock.tsv (what was actually
# pulled). Never commits: it leaves the diff for you to review, same as build-standalone.sh.
#
# Why this is not build-standalone.sh: that script copies from a local sibling folder and
# opens with `rm -rf plugins tools`. This one fetches from GitHub, replaces one plugin
# directory at a time, and refuses to touch a dirty working tree.
#
# bash 3.2 (macOS default) — no mapfile, no associative arrays.
set -euo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
MAP="$HERE/sources.tsv"
LOCK="$HERE/sources.lock.tsv"
TODAY="$(date '+%Y-%m-%d')"

APPLY=0
[ "${1:-}" = "--apply" ] && { APPLY=1; shift; }
ONLY="$*"

command -v gh >/dev/null 2>&1 || { echo "ERROR: gh not found — needed to resolve release tags."; exit 1; }
[ -f "$MAP" ] || { echo "ERROR: $MAP missing."; exit 1; }

if [ "$APPLY" -eq 1 ] && [ -d "$HERE/.git" ] && [ -n "$(git -C "$HERE" status --porcelain)" ]; then
  echo "REFUSING TO RUN — working tree is dirty."
  echo "Re-vendoring overwrites plugin directories. Commit or stash first, so the diff is readable."
  exit 1
fi

# Resolve `latest` to something reproducible, in order: newest release, newest tag,
# default branch. RESOLVED_VIA records which, because a silent downgrade is the bug
# this function already caused once.
#
# Two lessons are baked in here. First, gh prints its 404 body to stdout as well as
# failing, so an `||` chain concatenates error JSON onto the fallback -- every call is
# captured and screened. Second, a branch is NOT an acceptable stand-in for a release:
# nextlevelbuilder/ui-ux-pro-max-skill ships v2.15.0 while its main branch still reads
# 2.13.0, so falling through to `main` on a transient API blip pulls OLDER code than
# the release it was asked for. Releases and tags are each tried twice before a branch.
# Prints "<ref><TAB><how it was resolved>", empty on total failure. It returns the
# source rather than setting a global because resolve_ref runs inside $( ), and a
# global assigned in a subshell never reaches the caller -- which is how the first
# version reported every resolution as "pinned".
_gh_value() {
  out="$(gh api "$1" --jq "$2" 2>/dev/null || true)"
  case "$out" in ''|'{'*|'['*|*'Not Found'*) out="" ;; esac
  printf '%s' "$out"
}

resolve_ref() {
  for attempt in 1 2; do
    got="$(_gh_value "repos/$1/releases/latest" .tag_name)"
    [ -n "$got" ] && { printf '%s\trelease\n' "$got"; return; }
  done
  for attempt in 1 2; do
    got="$(_gh_value "repos/$1/tags?per_page=1" '.[0].name')"
    [ -n "$got" ] && { printf '%s\ttag\n' "$got"; return; }
  done
  got="$(_gh_value "repos/$1" .default_branch)"
  [ -n "$got" ] && { printf '%s\tbranch - no release or tag found\n' "$got"; return; }
  echo ""
}

# What the lock file recorded for this plugin last time, if anything.
locked_ref() {
  [ -f "$LOCK" ] || { echo ""; return; }
  awk -F'\t' -v d="$1" '$1==d {print $3; exit}' "$LOCK"
}

TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT
touched=0
skipped=0
: > "$TMP/lock.new"

while IFS=$'\t' read -r dir repo ref note || [ -n "$dir" ]; do
  case "$dir" in ''|'#'*) continue ;; esac
  [ -n "$ONLY" ] && case " $ONLY " in *" $dir "*) ;; *) continue ;; esac

  if [ "$repo" = "-" ] || [ -z "$repo" ]; then
    printf '  SKIP  %-34s %s\n' "$dir" "${note:-no upstream recorded}"
    skipped=$((skipped + 1))
    continue
  fi

  want="$ref"
  via=""
  if [ "$ref" = "latest" ]; then
    resolved="$(resolve_ref "$repo")"
    want="$(printf '%s' "$resolved" | cut -f1)"
    how="$(printf '%s' "$resolved" | cut -f2)"
    # Anything but a release is worth saying out loud: a tag may be a pre-release,
    # and a branch is a moving target that can be older than the newest release.
    [ "$how" = "release" ] || via=" [via ${how:-unknown}]"
  fi
  if [ -z "$want" ]; then
    printf '  FAIL  %-34s cannot reach %s\n' "$dir" "$repo"
    skipped=$((skipped + 1))
    continue
  fi

  have="$(locked_ref "$dir")"
  if [ "$APPLY" -eq 0 ]; then
    if [ "$have" = "$want" ]; then printf '  ok    %-34s %s%s\n' "$dir" "$want" "$via"
    else printf '  DRIFT %-34s vendored=%s upstream=%s%s\n' "$dir" "${have:-unrecorded}" "$want" "$via"; fi
    # Only --apply may write a row. Recording `$want` here would claim a version
    # nobody pulled, and the next check would then report a stale plugin as `ok`.
    [ -n "$have" ] && printf '%s\t%s\t%s\t%s\n' "$dir" "$repo" "$have" "$TODAY" >> "$TMP/lock.new"
    continue
  fi

  [ -d "$HERE/plugins/$dir" ] || { printf '  FAIL  %-34s not in plugins/\n' "$dir"; skipped=$((skipped + 1)); continue; }

  printf '  pull  %-34s %s@%s%s\n' "$dir" "$repo" "$want" "$via"
  rm -rf "$TMP/$dir"
  if ! git clone --quiet --depth 1 --branch "$want" "https://github.com/$repo.git" "$TMP/$dir" 2>/dev/null; then
    printf '  FAIL  %-34s clone failed (ref %s)\n' "$dir" "$want"
    skipped=$((skipped + 1))
    continue
  fi
  rm -rf "$TMP/$dir/.git"
  rsync -a --delete "$TMP/$dir/" "$HERE/plugins/$dir/"
  printf '%s\t%s\t%s\t%s\n' "$dir" "$repo" "$want" "$TODAY" >> "$TMP/lock.new"
  touched=$((touched + 1))
done < "$MAP"

if [ "$APPLY" -eq 1 ] && [ "$touched" -gt 0 ]; then
  # Re-vendoring restores upstream's broken reference paths — same reason
  # build-standalone.sh runs these. Both are idempotent.
  echo; echo "Applying vendor patches"
  for p in "$HERE"/patches/*.sh; do [ -f "$p" ] && bash "$p"; done
  echo "Checking skill reference paths"
  [ -f "$HERE/check-skill-refs.sh" ] && bash "$HERE/check-skill-refs.sh"
fi

# Merge: rows for plugins this run did not visit keep their old entry.
if [ -f "$LOCK" ]; then
  awk -F'\t' 'NR==FNR {seen[$1]=1; next} !($1 in seen)' "$TMP/lock.new" "$LOCK" >> "$TMP/lock.new"
fi
sort -o "$LOCK" "$TMP/lock.new"

echo
if [ "$APPLY" -eq 1 ]; then
  echo "Re-vendored $touched, skipped $skipped. Lock file: sources.lock.tsv"
  echo "Review before committing:  git -C \"$HERE\" status --short | head -40"
else
  echo "Checked. $skipped without a confirmed upstream — fix those rows in sources.tsv."
  echo "To pull:  bash revendor.sh --apply"
fi
