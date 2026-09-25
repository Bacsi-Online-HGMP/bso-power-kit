#!/usr/bin/env bash
# Add attribution frontmatter to the verification-before-completion skill.
#
# THE GAP THIS FILLS
# verification-before-completion is one skill copied out of obra/superpowers when the
# rest of that plugin was dropped (bootstrap-device/scoring-layer-2.md). The copy is
# verbatim; the only addition is frontmatter saying where it came from, under which
# licence, and that the body must not be edited by hand.
#
# WHY A PATCH
# revendor.sh re-copies the skill from upstream, which replaces SKILL.md whole. The
# frontmatter was first added by hand and did not survive the first automatic
# re-vendor. As a patch it is re-applied after every one.
#
# Idempotent: skips a SKILL.md whose frontmatter already carries `source:`. The
# plugin is MIT, so no MODIFICATIONS.md is written (see _apache_notice.py).
set -euo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
SKILL="${1:-$HERE/../plugins/verification-before-completion/skills/verification-before-completion/SKILL.md}"

if [ ! -f "$SKILL" ]; then
  echo "add-verification-attribution: skill not vendored -- nothing to do."
  exit 0
fi

if ! command -v python3 >/dev/null 2>&1; then
  echo "add-verification-attribution: python3 not found -- cannot add the attribution."
  exit 1
fi

python3 - "$SKILL" <<'PY'
import pathlib, sys

path = pathlib.Path(sys.argv[1])
lines = path.read_text(encoding="utf-8").splitlines(keepends=True)

if not lines or lines[0].strip() != "---":
    sys.exit(f"add-verification-attribution: {path} has no frontmatter -- upstream changed its shape.")
end = next((i for i in range(1, len(lines)) if lines[i].strip() == "---"), None)
if end is None:
    sys.exit(f"add-verification-attribution: {path} frontmatter never closes.")
if any(l.startswith("source:") for l in lines[1:end]):
    sys.exit(0)

lines[end:end] = [
    "license: MIT\n",
    "source: https://github.com/obra/superpowers — skills/verification-before-completion\n",
    "author: Jesse Vincent\n",
    "note: Copied verbatim from the superpowers plugin by revendor.sh. Only this frontmatter was"
    " added (patches/add-verification-attribution.sh). Do not edit the body.\n",
]
path.write_text("".join(lines), encoding="utf-8")
print(f"add-verification-attribution: attributed {path}")
PY
