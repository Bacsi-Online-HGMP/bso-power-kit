#!/usr/bin/env bash
# Repair plugin.json manifests that fail `claude plugin validate`.
#
# THE BUG THIS FIXES
# Two shape errors turn up in vendored plugins. Neither is our doing; both make
# the whole marketplace fail validation, which is worse than it sounds -- one bad
# manifest reports as a failure for the entire repo, so real problems hide behind
# it.
#
#   author as a string      "author": "Someone"
#                        -> "author": {"name": "Someone"}
#
#   skills pointing at a file   "skills": ["./SKILL.md"]
#                            -> "skills": ["."]
#     A skills entry must be a DIRECTORY containing SKILL.md. Pointing at the
#     file itself means the skill never loads.
#
# Idempotent: already-correct manifests are left byte-identical, and the script
# reports what it changed. Safe to re-run; build-standalone.sh runs it after
# every rebuild and CI fails if its output was not committed.
#
# Needs python3. Skips with a notice if unavailable.
set -uo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
ROOT="${1:-./plugins}"

if ! command -v python3 >/dev/null 2>&1; then
  echo "fix-plugin-manifests: python3 not found -- skipping."
  exit 0
fi

python3 - "$ROOT" <<'PY'
import json, os, sys

root = os.path.abspath(sys.argv[1])
if not os.path.isdir(root):
    print(f"fix-plugin-manifests: no such directory {root} -- nothing to do.")
    raise SystemExit(0)

fixed = 0

for dirpath, dirnames, filenames in os.walk(root):
    dirnames[:] = [d for d in dirnames if d not in ('node_modules', '.git')]
    if 'plugin.json' not in filenames:
        continue

    path = os.path.join(dirpath, 'plugin.json')
    try:
        with open(path, encoding='utf-8') as fh:
            original = fh.read()
        data = json.loads(original)
    except (ValueError, OSError):
        continue
    if not isinstance(data, dict):
        continue

    # The plugin root is the directory holding .claude-plugin/, or the manifest's
    # own directory when the manifest sits at the top level.
    base = os.path.dirname(dirpath) if os.path.basename(dirpath) == '.claude-plugin' else dirpath
    rel = os.path.relpath(path, root)
    changes = []

    author = data.get('author')
    if isinstance(author, str):
        data['author'] = {'name': author}
        changes.append(f"author: string -> object ({author!r})")

    skills = data.get('skills')
    if isinstance(skills, list):
        new, touched = [], False
        for s in skills:
            if isinstance(s, str) and os.path.basename(s) == 'SKILL.md':
                d = os.path.dirname(s).rstrip('/') or '.'
                # Normalise "./x" and a bare plugin root to "."
                if os.path.abspath(os.path.join(base, d)) == os.path.abspath(base):
                    d = '.'
                if d not in new:
                    new.append(d)
                touched = True
                changes.append(f"skills: {s!r} -> {d!r}")
            elif s not in new:
                new.append(s)
        if touched:
            data['skills'] = new

    if not changes:
        continue

    with open(path, 'w', encoding='utf-8') as fh:
        json.dump(data, fh, indent=2, ensure_ascii=False)
        fh.write('\n')

    print(f"  fixed  {rel}")
    for c in changes:
        print(f"           {c}")
    fixed += 1

print(f"fix-plugin-manifests: {fixed} manifest(s) repaired.")
PY
