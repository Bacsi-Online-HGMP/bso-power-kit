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
# beside it. Results and the HTML report land in <skill>/evals/results/ (git-ignored); the
# report is never published to claude.ai (memory no-auto-artifacts).
#
# Every run is a real model call on your account. By default each case runs three
# times with the skill and three times without it, and each suite stops at $10 of
# list-price cost. The suites are ours, so their fixture scripts (--scaffold), the
# Write tool and trust are granted; nothing else is.
#
# Exits 1 if any suite scored below its threshold or failed to run.
#
# Head-to-head: one suite against several skill sets, to settle which of two overlapping
# skills to enable.
#
#   bash run-evals.sh --suite DIR --arm NAME=PATH[,PATH...] --arm none= -- --ablation none
#
# Each arm becomes a throwaway plugin with the suite in evals/. A PATH holding
# .claude-plugin/plugin.json is copied as the whole plugin; otherwise each PATH is a skill
# directory, copied into skills/. An arm with no PATH is the no-skill baseline, so pass
# --ablation none to stop every arm running a baseline of its own. Results land in
# DIR/results/<timestamp>/<arm>/. The $10 ceiling applies to each arm.
set -euo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
CALLER="$(pwd)"
cd "$HERE"

want=""
suite=""
arms=""
while [ "$#" -gt 0 ] && [ "$1" != "--" ]; do
  case "$1" in
    --suite) suite="$2"; shift 2 ;;
    --arm)   arms="$arms$2"$'\n'; shift 2 ;;
    *)       want="$want $1"; shift ;;
  esac
done
[ "${1:-}" = "--" ] && shift

command -v claude >/dev/null 2>&1 || { echo "ERROR: the claude CLI is not installed."; exit 1; }
# --trust-plugin is newer than some CLIs (2.1.238 rejects it); pass it only where it exists.
TRUST=""
case "$(claude plugin eval --help 2>/dev/null || true)" in *--trust-plugin*) TRUST="--trust-plugin" ;; esac

TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT
STAMP="$(date -u '+%Y-%m-%dT%H-%M-%SZ')"
ran=0
failed=""

if [ -n "$suite" ]; then
  suite="$(cd "$CALLER" && cd "$suite" && pwd)"
  out="$suite/results/$STAMP"
  while IFS= read -r arm; do
    [ -n "$arm" ] || continue
    name="${arm%%=*}"
    paths="${arm#*=}"
    plug="$TMP/$name"
    first="${paths%%,*}"
    [ -z "$first" ] || first="$(cd "$CALLER" && cd "$first" && pwd)"
    if [ -n "$first" ] && [ -f "$first/.claude-plugin/plugin.json" ]; then
      rsync -a --exclude .git --exclude node_modules --exclude /evals "$first/" "$plug/"
    else
      mkdir -p "$plug/.claude-plugin" "$plug/skills"
      printf '{\n  "name": "%s",\n  "version": "0.0.0-eval"\n}\n' "$name" > "$plug/.claude-plugin/plugin.json"
      IFS=','
      for p in $paths; do
        p="$(cd "$CALLER" && cd "$p" && pwd)"
        rsync -a --exclude /evals "$p/" "$plug/skills/$(basename "$p")/"
      done
      unset IFS
    fi
    rsync -a --exclude /results "$suite/" "$plug/evals/"

    echo
    echo "=== $name"
    # </dev/null: claude must not read the remaining arms from this loop's input.
    if claude plugin eval "$plug" \
         $TRUST --scaffold --no-publish \
         --output-dir "$out/$name" \
         --report "$out/$name/report.html" \
         --max-cost-usd 10 \
         "$@" </dev/null; then
      :
    else
      failed="$failed $name"
    fi
    ran=$((ran + 1))
  done <<EOF
$arms
EOF
  echo
  echo "Ran $ran arm(s). Results: $out/"
  [ -z "$failed" ] || { echo "Below threshold or failed:$failed"; exit 1; }
  exit 0
fi

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
       $TRUST --scaffold --no-publish \
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
