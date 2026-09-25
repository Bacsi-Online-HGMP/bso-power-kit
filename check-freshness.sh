#!/usr/bin/env bash
# Check that every first-party skill says what can go stale in it.
#
#   bash check-freshness.sh
#   bash check-freshness.sh --list   # print the first-party skill directories, one per line
#
# First-party means skills/*/, the plugins sources.tsv marks "authored here", and each
# local addition under patches/*/. Each needs a FRESHNESS.md with a "Last reviewed:"
# date and at least one fact row -- the format is in MAINTENANCE.md, and the monthly
# freshness check works from these files.
#
# A missing or malformed file fails. A review older than 45 days only warns: it means
# the monthly check has probably stopped running, which is worth seeing on every PR
# but is not the PR's fault.
set -euo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
cd "$HERE"

dirs=""
for d in skills/*/; do
  [ -f "$d/SKILL.md" ] && dirs="$dirs ${d%/}"
done
for p in $(awk -F'\t' '!/^#/ && $5 ~ /^authored here/ {print $1}' sources.tsv); do
  for d in plugins/"$p"/skills/*/; do
    [ -f "$d/SKILL.md" ] && dirs="$dirs ${d%/}"
  done
done
# Tracked directories only: running a patch leaves an untracked __pycache__ behind.
for d in $(git ls-files patches | awk -F/ 'NF > 2 {print $1 "/" $2}' | sort -u); do
  dirs="$dirs $d"
done

if [ "${1:-}" = "--list" ]; then
  for d in $dirs; do [ -f "$d/SKILL.md" ] && echo "$d"; done
  exit 0
fi

# shellcheck disable=SC2086 # word splitting is the point: one argument per directory
python3 - 45 $dirs <<'PY'
import datetime, os, re, sys

max_age = int(sys.argv[1])
today = datetime.date.today()
in_ci = os.environ.get('GITHUB_ACTIONS') == 'true'
failed = stale = 0

for d in sys.argv[2:]:
    path = os.path.join(d, 'FRESHNESS.md')
    if not os.path.isfile(path):
        print(f'  MISSING  {path}')
        failed += 1
        continue
    text = open(path, encoding='utf-8').read()
    date = re.search(r'^Last reviewed: (\d{4}-\d{2}-\d{2})\s*$', text, re.M)
    rows = [l for l in text.splitlines()
            if l.startswith('|') and not re.match(r'^\|[\s|:-]+\|$', l)]
    if not date or len(rows) < 2:  # the header row plus at least one fact
        print(f'  MALFORMED {path} -- needs "Last reviewed: YYYY-MM-DD" and a fact table')
        failed += 1
        continue
    age = (today - datetime.date.fromisoformat(date.group(1))).days
    if age > max_age:
        msg = f'{path} last reviewed {age} days ago -- is the monthly freshness check running?'
        print(f'::warning file={path}::{msg}' if in_ci else f'  STALE    {msg}')
        stale += 1
    else:
        print(f'  ok       {path} ({len(rows) - 1} facts, reviewed {date.group(1)})')

print(f'check-freshness: {len(sys.argv) - 2} first-party skills, {failed} missing or malformed, '
      f'{stale} not reviewed in {max_age} days.')
if failed:
    print('Add a FRESHNESS.md next to the SKILL.md -- format in MAINTENANCE.md.')
sys.exit(1 if failed else 0)
PY
