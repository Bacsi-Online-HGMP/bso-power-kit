#!/usr/bin/env bash
# Repoint mattpocock's wait-what skill at a context file that exists here.
#
# THE BUG THIS FIXES
# Upstream `wait-what` ends by telling the agent to "use the ubiquitous language
# from CONTEXT.md". That file is Matt Pocock's own convention; no such file
# exists in bso-marketing or bso-strategy. Left alone, the skill instructs the
# agent to read a file it cannot find and then improvise the wording. For
# regulated supplement copy, improvised wording is the exact failure the claims
# matrix exists to prevent -- a synonym for an approved claim verb is a new claim.
#
# WHY NOT fix-skill-ref-paths.sh
# That patch rewrites a citation only when the basename resolves to exactly one
# file inside the plugin. CONTEXT.md was never shipped, so it correctly declines
# to guess. This patch supplies the target that only we can know.
#
# Idempotent: exits early once repointed, and if upstream drops the reference.
# revendor.sh runs every patches/*.sh after each vendor, so this survives
# upgrades that a hand-edit would lose.
set -uo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
SKILL="${1:-$HERE/../plugins/mattpocock-skills-main/skills/productivity/wait-what/SKILL.md}"

if [ ! -f "$SKILL" ]; then
  echo "fix-wait-what-context: skill not vendored -- nothing to do."
  exit 0
fi

if grep -q 'claims-matrix' "$SKILL"; then
  exit 0
fi

if ! command -v python3 >/dev/null 2>&1; then
  echo "fix-wait-what-context: python3 not found -- skipping."
  exit 0
fi

python3 - "$SKILL" <<'PY'
import pathlib, sys

path = pathlib.Path(sys.argv[1])
text = path.read_text(encoding="utf-8")
old = "`CONTEXT.md`"
new = ("`core/claims-matrix/` -- quote approved wording verbatim, "
       "never paraphrase it")

if old not in text:
    print("fix-wait-what-context: CONTEXT.md reference gone -- upstream changed, skipping.")
    sys.exit(0)

path.write_text(text.replace(old, new), encoding="utf-8")
print(f"fix-wait-what-context: repointed {path}")
PY
