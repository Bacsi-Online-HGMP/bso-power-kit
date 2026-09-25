#!/usr/bin/env bash
# Re-vendor plugins and tools from their upstream repositories.
#
#   bash revendor.sh                    # check only: report upstream drift, write nothing
#   bash revendor.sh --apply            # re-vendor every row that has a confirmed source
#   bash revendor.sh --apply ui-ux-pro-max-skill tools/design.md    # ...or just these
#   bash revendor.sh --verify           # rebuild from the lock + patches/, fail on any other change
#
# --verify is the guard for local changes. It rebuilds every vendored directory from
# upstream at the exact commit in sources.lock.tsv, runs patches/ over it, and compares
# the result with what git tracks. Any difference is a hand edit that the next
# re-vendor would delete without a word -- how the Gemini fallback in
# mcp-video-analyzer was lost on 2026-09-21. CI runs it on every change to vendored code.
#
# Reads sources.tsv (the upstream map) and writes sources.lock.tsv (what was actually
# pulled: <dir> <repo> <ref> <date pulled> <commit>, tab separated; check mode writes
# nothing). Never commits: it leaves the diff for you to review, same
# as build-standalone.sh. The one thing it stages is an upstream file that .gitignore
# would otherwise drop -- see force_add_ignored.
#
# Exits 1 when any row cannot be resolved or pulled. The weekly workflow depends on
# that: a plugin that quietly fails to update is how vendored code goes stale unseen.
#
# Why this is not build-standalone.sh: that script copies from a local sibling folder and
# opens with `rm -rf plugins tools`. This one fetches from GitHub, replaces one vendored
# directory at a time, and refuses to touch a dirty working tree.
#
# bash 3.2 (macOS default) — no mapfile, no associative arrays.
set -euo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
MAP="$HERE/sources.tsv"
LOCK="$HERE/sources.lock.tsv"
TODAY="$(date '+%Y-%m-%d')"

APPLY=0
VERIFY=0
case "${1:-}" in
  --apply)  APPLY=1;  shift ;;
  --verify) VERIFY=1; shift ;;
esac
ONLY="$*"

[ -f "$MAP" ] || { echo "ERROR: $MAP missing."; exit 1; }

if [ "$APPLY" -eq 1 ] && [ -d "$HERE/.git" ] && [ -n "$(git -C "$HERE" status --porcelain)" ]; then
  echo "REFUSING TO RUN — working tree is dirty."
  echo "Re-vendoring overwrites vendored directories. Commit or stash first, so the diff is readable."
  exit 1
fi

# Only the GitHub API knows which tag is the latest *release*, so gh is used when it
# works. It is not required: without it -- not installed, not logged in, or the API
# unreachable -- `latest` resolves to the newest version tag over plain git, and the
# report marks each such row `[via tag]`.
USE_GH=0
if [ "$VERIFY" -eq 1 ]; then
  :  # verify reads the lock; it never resolves a ref
elif command -v gh >/dev/null 2>&1 && gh api rate_limit >/dev/null 2>&1; then
  USE_GH=1
else
  echo "NOTE: gh is unavailable, so \`latest\` resolves to the newest version tag, not the latest release."
  echo
fi

url() { printf 'https://github.com/%s.git' "$1"; }

_gh_value() {
  out="$(gh api "$1" --jq "$2" 2>/dev/null || true)"
  case "$out" in ''|'{'*|'['*|*'Not Found'*) out="" ;; esac
  printf '%s' "$out"
}

# A plain version tag, optionally behind a letter prefix: v2.7.0, skill-v4.3.1, 0.4.0.
# Anything after the numbers (v2.0.0-rc1) makes it a pre-release, and it never matches.
VERSION_RE='[0-9]+(\.[0-9]+)*'
is_version() { printf '%s\n' "$1" | grep -Eq "^([A-Za-z][A-Za-z_-]*)?$VERSION_RE\$"; }

# The prefix a version tag shares with its siblings: skill-v4.3.1 -> skill-v, 0.4.0 -> "".
tag_family() { printf '%s\n' "$1" | sed -E "s/$VERSION_RE\$//"; }

# True when version tag $1 sorts strictly before $2.
older_than() { [ "$1" != "$2" ] && [ "$(printf '%s\n%s\n' "$1" "$2" | sort -V | head -1)" = "$1" ]; }

# Every tag name, one per line. Fails -- rather than printing nothing -- when the
# repository cannot be reached, so "no tags" and "no network" stay distinguishable.
list_tags() {
  out="$(git ls-remote --tags --refs "$(url "$1")" 2>/dev/null)" || return 1
  printf '%s\n' "$out" | sed 's#.*refs/tags/##'
}

# Newest version tag on stdin whose prefix matches the family regex.
pick_newest() { grep -E "^$1$VERSION_RE\$" | sort -V | tail -1 || true; }

default_branch() {
  git ls-remote --symref "$(url "$1")" HEAD 2>/dev/null \
    | awk '$1 == "ref:" { sub("refs/heads/", "", $2); print $2; exit }' || true
}

# Resolve `latest` to something reproducible, in order: newest release, newest version
# tag, default branch. The second field says which, because a silent downgrade is the
# bug this function already caused once.
#
# Three lessons are baked in. First, gh prints its 404 body to stdout as well as failing,
# so every gh call is captured and screened. Second, a branch is NOT an acceptable
# stand-in for a release: nextlevelbuilder/ui-ux-pro-max-skill ships v2.15.0 while its
# main branch still reads 2.13.0, so falling through to `main` because the network
# blinked pulls OLDER code than the release it was asked for. Releases are tried twice,
# and when the tag list cannot be fetched at all this gives up rather than fall through.
# Third, tags are compared as versions within one family: impeccable tags `cli-v*`,
# `engine-v*`, `ext-v*` and `skill-v*` side by side, and caveman once shipped `bin-v*`
# next to its `v*` releases. The family comes from the ref locked last time.
#
# Prints "<ref><TAB><how it was resolved>", empty on total failure. It returns the source
# rather than setting a global because resolve_ref runs inside $( ), and a global
# assigned in a subshell never reaches the caller -- which is how the first version
# reported every resolution as "pinned".
resolve_ref() {  # <owner/repo> <ref locked last time, may be empty>
  if [ "$USE_GH" -eq 1 ]; then
    for attempt in 1 2; do
      got="$(_gh_value "repos/$1/releases/latest" .tag_name)"
      [ -n "$got" ] && { printf '%s\trelease\n' "$got"; return; }
    done
  fi
  reached=0
  for attempt in 1 2; do
    if tags="$(list_tags "$1")"; then reached=1; break; fi
  done
  [ "$reached" -eq 1 ] || { echo ""; return; }

  family='v?'
  if is_version "$2"; then family="$(tag_family "$2")"; fi
  got="$(printf '%s\n' "$tags" | pick_newest "$family")"
  if [ -z "$got" ] && [ "$family" != 'v?' ]; then
    got="$(printf '%s\n' "$tags" | pick_newest 'v?')"
  fi
  [ -n "$got" ] && { printf '%s\ttag\n' "$got"; return; }

  got="$(default_branch "$1")"
  [ -n "$got" ] && { printf '%s\tbranch - no release or tag found\n' "$got"; return; }
  echo ""
}

# The commit a tag or branch points at, peeled through annotated tags. A branch lock is
# unverifiable without it: `main` last month and `main` today are the same string.
ref_commit() {  # <owner/repo> <ref>
  out="$(git ls-remote "$(url "$1")" "refs/tags/$2" "refs/tags/$2^{}" "refs/heads/$2" 2>/dev/null)" || return 1
  printf '%s\n' "$out" | awk -v t="refs/tags/$2" -v h="refs/heads/$2" '
    { c[$2] = $1 }
    END { if ((t "^{}") in c) print c[t "^{}"]; else if (t in c) print c[t]; else if (h in c) print c[h] }'
}

# One field of this entry's lock row: 3 = ref, 5 = commit. Rows written before commits
# were recorded have no field 5.
locked() {  # <dir> <field>
  [ -f "$LOCK" ] || return 0
  awk -F'\t' -v d="$1" -v f="$2" '$1 == d { print $f; exit }' "$LOCK"
}

# A bare name is a plugin; anything with a slash is a path from the repo root (tools/x).
dest_of() {
  case "$1" in
    */*) printf '%s/%s' "$HERE" "$1" ;;
    *)   printf '%s/plugins/%s' "$HERE" "$1" ;;
  esac
}

# Stage upstream files that .gitignore would drop. A vendored repo's own .gitignore can
# ignore files it nevertheless ships (youtuber ignores `.obsidian/` and still tracks two
# vaults' worth of it), and this repo's secret globs once hid 36 source files
# (f386b3f0). Either way `git add -A` leaves them out without a word and the vendored
# copy is quietly incomplete. Upstream publishes these files, so staging them exposes
# nothing that is not already public.
force_add_ignored() {  # <file listing the copied paths, repo-relative, one per line>
  [ -d "$HERE/.git" ] || return 0
  hidden="$(git -C "$HERE" check-ignore --stdin < "$1" || true)"
  [ -n "$hidden" ] || return 0
  printf '        %s upstream file(s) hidden by .gitignore -- staged with add -f\n' \
    "$(printf '%s\n' "$hidden" | wc -l | tr -d ' ')"
  printf '%s\n' "$hidden" | git -C "$HERE" --literal-pathspecs add -f --pathspec-from-file=-
}

# Exactly one commit, by hash. verify rebuilds what the lock recorded, not whatever the
# branch or tag points at today.
fetch_commit() {  # <owner/repo> <commit> <dir>
  git init -q "$3" 2>/dev/null \
    && git -C "$3" fetch -q --depth 1 "$(url "$1")" "$2" 2>/dev/null \
    && git -C "$3" checkout -q FETCH_HEAD 2>/dev/null
}

# Mirror the upstream checkout in $1 into $2. A whole-repo row takes the entire tree. A
# directory row takes only $3, at the same relative path, plus the licence files, and
# leaves everything else in $2 alone. Writes the copied paths, relative to $2, to $4.
# Returns 1 when the directory is not in the checkout.
copy_upstream() {  # <checkout> <dest> <path> <list out>
  if [ "$3" = "." ]; then
    git -C "$1" -c core.quotePath=false ls-files > "$4"
    rm -rf "$1/.git"
    rsync -a --delete "$1/" "$2/"
    return 0
  fi
  [ -d "$1/$3" ] || return 1
  git -C "$1" -c core.quotePath=false ls-files -- "$3" > "$4"
  mkdir -p "$2/$3"
  rsync -a --delete "$1/$3/" "$2/$3/"
  # The licence travels with any piece of the work.
  for f in "$1"/LICEN[CS]E* "$1"/COPYING* "$1"/NOTICE*; do
    [ -f "$f" ] || continue
    cp "$f" "$2/"
    basename "$f" >> "$4"
  done
  return 0
}

# Compare a rebuilt directory with the files git tracks for it. Prints one line per
# difference and exits 1 if there is any. For a directory row only that directory and
# the licence files are compared; the rest of the vendored directory is ours.
compare_tree() {  # <rebuilt dir> <repo-relative dir> <path>
  python3 - "$1" "$HERE" "$2" "$3" <<'PY'
import os, re, subprocess, sys

built, root, rel, path = sys.argv[1:5]
licence = re.compile(r'(LICEN[CS]E|COPYING|NOTICE)[^/]*$')

def in_scope(f):
    return (path == '.' or f == path or f.startswith(path + '/')
            or ('/' not in f and bool(licence.match(f))))

def rebuilt_files():
    out = set()
    for dp, dirs, files in os.walk(built):
        for name in files + [d for d in dirs if os.path.islink(os.path.join(dp, d))]:
            out.add(os.path.relpath(os.path.join(dp, name), built))
    return out

def content(p):
    if os.path.islink(p):
        return ('link', os.readlink(p))
    if os.path.isfile(p):
        with open(p, 'rb') as fh:
            return ('file', fh.read())
    return None

raw = subprocess.run(['git', '--literal-pathspecs', '-C', root, 'ls-files', '-z', '--', rel],
                     capture_output=True, check=True).stdout
prefix = rel.rstrip('/') + '/'
tracked = {p.decode('utf-8', 'surrogateescape')[len(prefix):] for p in raw.split(b'\0') if p}

expected = {f for f in rebuilt_files() if in_scope(f)}
actual = {f for f in tracked if in_scope(f)}
rows = [('missing', f) for f in sorted(expected - actual)]
rows += [('extra', f) for f in sorted(actual - expected)]
rows += [('changed', f) for f in sorted(expected & actual)
         if content(os.path.join(built, f)) != content(os.path.join(root, rel, f))]
for kind, f in rows[:15]:
    print(f'          {kind:8} {f}')
if len(rows) > 15:
    print(f'          ... and {len(rows) - 15} more')
sys.exit(1 if rows else 0)
PY
}

TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT
touched=0
skipped=0
failed=0
edited=0
verified=0
: > "$TMP/lock.new"
: > "$TMP/verify.list"
SCRATCH="$TMP/tree"
mkdir -p "$SCRATCH"

fail() { printf '  FAIL  %-40s %s\n' "$1" "$2"; failed=$((failed + 1)); }

while IFS=$'\t' read -r dir repo ref path note || [ -n "$dir" ]; do
  case "$dir" in ''|'#'*) continue ;; esac
  [ -n "$ONLY" ] && case " $ONLY " in *" $dir "*) ;; *) continue ;; esac

  if [ "$repo" = "-" ] || [ -z "$repo" ]; then
    printf '  SKIP  %-40s %s\n' "$dir" "${note:-no upstream recorded}"
    skipped=$((skipped + 1))
    continue
  fi
  case "$path" in ''|'-') path="." ;; esac

  if [ "$VERIFY" -eq 1 ]; then
    # Rebuild into the scratch tree; the comparison runs once patches/ has been applied.
    commit="$(locked "$dir" 5)"
    dest="$(dest_of "$dir")"
    rel="${dest#"$HERE"/}"
    if [ -z "$commit" ]; then
      fail "$dir" "no commit in sources.lock.tsv -- re-vendor it with --apply first"
      continue
    fi
    if [ ! -d "$dest" ]; then
      fail "$dir" "$rel does not exist"
      continue
    fi
    src="$TMP/src"
    rm -rf "$src"
    if ! fetch_commit "$repo" "$commit" "$src"; then
      fail "$dir" "cannot fetch $repo at $commit"
      continue
    fi
    mkdir -p "$(dirname "$SCRATCH/$rel")"
    cp -R "$dest" "$SCRATCH/$rel"
    if ! copy_upstream "$src" "$SCRATCH/$rel" "$path" "$TMP/files"; then
      fail "$dir" "no $path in $repo at $commit"
      continue
    fi
    printf '%s\t%s\t%s\n' "$dir" "$rel" "$path" >> "$TMP/verify.list"
    continue
  fi

  have="$(locked "$dir" 3)"
  have_commit="$(locked "$dir" 5)"

  want="$ref"
  via=""
  if [ "$ref" = "latest" ]; then
    resolved="$(resolve_ref "$repo" "$have")"
    want="$(printf '%s' "$resolved" | cut -f1)"
    how="$(printf '%s' "$resolved" | cut -f2)"
    # Anything but a release is worth saying out loud: a tag may never have been
    # released, and a branch is a moving target that can be older than the newest release.
    [ "$how" = "release" ] || via=" [via ${how:-unknown}]"
  fi
  if [ -z "$want" ]; then
    fail "$dir" "cannot reach $repo"
    continue
  fi

  # Never step backwards. Without gh, `latest` is the newest tag, which can run ahead of
  # the latest release; the next run with gh would otherwise "update" the plugin back
  # down to that release. Keep what is vendored and say so.
  if [ -n "$have" ] && is_version "$have" && is_version "$want" \
     && [ "$(tag_family "$have")" = "$(tag_family "$want")" ] && older_than "$want" "$have"; then
    printf '  ahead %-40s vendored=%s upstream=%s%s -- kept\n' "$dir" "$have" "$want" "$via"
    continue
  fi

  if [ "$APPLY" -eq 0 ]; then
    if [ "$have" != "$want" ]; then
      printf '  DRIFT %-40s vendored=%s upstream=%s%s\n' "$dir" "${have:-unrecorded}" "$want" "$via"
      continue
    fi
    # Same ref name. A tag that has not moved is current; a branch can only be judged by
    # its commit, and a lock row written before commits were recorded cannot be judged.
    if ! now="$(ref_commit "$repo" "$want")" || [ -z "$now" ]; then
      fail "$dir" "cannot resolve $want in $repo"
      continue
    fi
    if [ -n "$have_commit" ] && [ "$have_commit" != "$now" ]; then
      printf '  DRIFT %-40s %s moved: vendored=%.10s upstream=%.10s%s\n' "$dir" "$want" "$have_commit" "$now" "$via"
    elif [ -z "$have_commit" ] && ! is_version "$want"; then
      printf '  DRIFT %-40s %s, vendored commit not recorded%s\n' "$dir" "$want" "$via"
    else
      printf '  ok    %-40s %s%s\n' "$dir" "$want" "$via"
    fi
    continue
  fi

  dest="$(dest_of "$dir")"
  rel="${dest#"$HERE"/}"
  if [ ! -d "$dest" ]; then
    fail "$dir" "$rel does not exist"
    continue
  fi

  printf '  pull  %-40s %s@%s%s\n' "$dir" "$repo" "$want" "$via"
  src="$TMP/src"
  rm -rf "$src"
  if ! git clone --quiet --depth 1 --branch "$want" "$(url "$repo")" "$src" 2>/dev/null; then
    fail "$dir" "clone failed (ref $want)"
    continue
  fi
  commit="$(git -C "$src" rev-parse HEAD)"

  if ! copy_upstream "$src" "$dest" "$path" "$TMP/files"; then
    fail "$dir" "no $path in $repo@$want"
    continue
  fi
  sed "s#^#$rel/#" "$TMP/files" > "$TMP/files.rel"
  force_add_ignored "$TMP/files.rel"

  printf '%s\t%s\t%s\t%s\t%s\n' "$dir" "$repo" "$want" "$TODAY" "$commit" >> "$TMP/lock.new"
  touched=$((touched + 1))
done < "$MAP"

if [ "$APPLY" -eq 1 ] && [ "$touched" -gt 0 ]; then
  # Written before the patches run, so the lock matches the tree even if a patch fails.
  # Rows for entries this run did not pull keep their old line.
  if [ -f "$LOCK" ]; then
    awk -F'\t' 'NR==FNR {seen[$1]=1; next} !($1 in seen)' "$TMP/lock.new" "$LOCK" >> "$TMP/lock.new"
  fi
  LC_ALL=C sort -o "$LOCK" "$TMP/lock.new"

  # Re-vendoring restores upstream's broken reference paths and drops our local
  # additions -- same reason build-standalone.sh runs these. All are idempotent.
  echo; echo "Applying vendor patches"
  for p in "$HERE"/patches/*.sh; do [ -f "$p" ] && bash "$p"; done
  echo "Checking skill reference paths"
  [ -f "$HERE/check-skill-refs.sh" ] && bash "$HERE/check-skill-refs.sh"
fi

if [ "$VERIFY" -eq 1 ] && [ -s "$TMP/verify.list" ]; then
  # The same patches, run over the rebuilt tree. Each one finds plugins relative to its
  # own directory, so a copy of patches/ inside the scratch tree patches the scratch tree.
  cp -R "$HERE/patches" "$SCRATCH/patches"
  for p in "$SCRATCH"/patches/*.sh; do
    [ -f "$p" ] || continue
    if ! bash "$p" > "$TMP/patch.log" 2>&1; then
      fail "patches/$(basename "$p")" "failed on the rebuilt tree:"
      tail -5 "$TMP/patch.log" | sed 's/^/          /'
    fi
  done
  while IFS=$'\t' read -r dir rel path; do
    if report="$(compare_tree "$SCRATCH/$rel" "$rel" "$path")"; then
      printf '  ok    %s\n' "$dir"
      verified=$((verified + 1))
    else
      printf '  EDIT  %-40s differs from upstream at its locked commit + patches/\n' "$dir"
      printf '%s\n' "$report"
      edited=$((edited + 1))
    fi
  done < "$TMP/verify.list"
fi

echo
if [ "$VERIFY" -eq 1 ]; then
  echo "Verified $verified, differing $edited, skipped $skipped, failed $failed."
  if [ "$edited" -gt 0 ]; then
    echo
    echo "  changed  the file differs from what upstream + patches/ produce"
    echo "  extra    committed here, but neither upstream nor patches/ makes it"
    echo "  missing  upstream ships it, but it is not committed here"
    echo
    echo "The next re-vendor would silently undo each of these. Keep a local change by"
    echo "turning it into a script in patches/ (see patches/README.md); otherwise revert it."
    exit 1
  fi
elif [ "$APPLY" -eq 1 ]; then
  echo "Re-vendored $touched, skipped $skipped, failed $failed. Lock file: sources.lock.tsv"
  echo "Review before committing:  git -C \"$HERE\" status --short | head -40"
else
  echo "Checked. $skipped without a confirmed upstream — fix those rows in sources.tsv."
  echo "To pull:  bash revendor.sh --apply"
fi
if [ "$failed" -gt 0 ]; then
  echo "$failed row(s) failed -- see FAIL above. Nothing that failed was changed."
  exit 1
fi
