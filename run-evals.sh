#!/usr/bin/env bash
# Run the eval suites of the first-party skills with `claude plugin eval`.
#
#   bash run-evals.sh                                   # every suite
#   bash run-evals.sh handoff digesting-books           # only these skills
#   bash run-evals.sh -- --runs 1 --ablation none       # cheap pass: one run, no baseline
#   bash run-evals.sh -- --model claude-opus-5-5        # the same suites on another model
#
# Arguments before `--` pick skills by directory name; everything after it goes to
# `claude plugin eval` unchanged.
#
# Each suite lives in evals/ next to the skill's SKILL.md. `claude plugin eval` needs a
# plugin directory, and two of these skills exist only as entries in marketplace.json,
# so this assembles one throwaway plugin per skill: the skill without its evals/ (a run
# must never be able to read its own graders), a minimal plugin.json, and the suite
# beside it. Results and the HTML report land in <skill>/evals/results/ (git-ignored).
#
# Every run is a real model call on your account. By default each case runs three
# times with the skill and three times without it, and each suite stops at $10 of
# list-price cost. The suites are ours, so their fixture scripts (--scaffold), the
# Write tool and trust are granted; nothing else is.
#
# Exits 1 if any suite scored below its threshold or failed to run.
set -euo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
cd "$HERE"

want=""
while [ "$#" -gt 0 ] && [ "$1" != "--" ]; do
  want="$want $1"
  shift
done
[ "${1:-}" = "--" ] && shift

command -v claude >/dev/null 2>&1 || { echo "ERROR: the claude CLI is not installed."; exit 1; }

TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT
STAMP="$(date -u '+%Y-%m-%dT%H-%M-%SZ')"
ran=0
failed=""

for skill in $(bash check-freshness.sh --list); do
  name="$(basename "$skill")"
  [ -d "$skill/evals" ] || continue
  [ -n "$want" ] && case " $want " in *" $name "*) ;; *) continue ;; esac

  plug="$TMP/$name"
  mkdir -p "$plug/.claude-plugin" "$plug/skills"
  rsync -a --exclude /evals "$skill/" "$plug/skills/$name/"
  rsync -a --exclude /results "$skill/evals/" "$plug/evals/"
  printf '{\n  "name": "%s",\n  "version": "0.0.0-eval"\n}\n' "$name" > "$plug/.claude-plugin/plugin.json"

  echo
  echo "=== $name"
  if claude plugin eval "$plug" \
       --trust-plugin --scaffold \
       --output-dir "$HERE/$skill/evals/results/$STAMP" \
       --max-cost-usd 10 \
       --allow-tools Write \
       "$@"; then
    :
  else
    failed="$failed $name"
  fi
  ran=$((ran + 1))
done

echo
if [ "$ran" -eq 0 ]; then
  echo "No eval suite matched${want:+ '$want'}. Suites live in <skill>/evals/ next to SKILL.md."
  exit 1
fi
echo "Ran $ran suite(s). Results: <skill>/evals/results/$STAMP/"
if [ -n "$failed" ]; then
  echo "Below threshold or failed:$failed"
  exit 1
fi
