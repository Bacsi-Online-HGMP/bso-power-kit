#!/usr/bin/env bash
# Repair broken `references/...` citations in vendored SKILL.md files.
#
# THE BUG THIS FIXES
# Several upstream plugins keep shared reference documents in one directory and
# cite them from sibling skills using a path that only works from the plugin
# root -- or from nowhere at all. The files are present; the relative paths are
# wrong. An agent loading such a skill is told to read documents it cannot find,
# which looks like the vendoring dropped files when it did not.
#
# THE RULE
# For each unresolvable citation, search for the basename within that plugin.
# Rewrite ONLY when there is exactly one match. Zero matches means the file was
# never shipped; two or more means the correct target is ambiguous. In both
# cases leave the text alone and report it -- guessing would replace a visibly
# broken path with a plausible wrong one, which is worse.
#
# Idempotent: correct paths resolve and are skipped. Safe to re-run;
# build-standalone.sh runs it after every rebuild.
#
# Needs python3 for os.path.relpath. Skips with a notice if unavailable.
set -uo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
ROOT="${1:-./plugins}"

if ! command -v python3 >/dev/null 2>&1; then
  echo "fix-skill-ref-paths: python3 not found -- skipping."
  exit 0
fi

python3 - "$ROOT" <<'PY'
import os, re, sys

root = os.path.abspath(sys.argv[1])
if not os.path.isdir(root):
    print(f"fix-skill-ref-paths: no such directory {root} -- nothing to do.")
    raise SystemExit(0)

# Backticked path containing "references/" and ending in .md.
CITE = re.compile(r'`([^`\n]*/[^`\n]*\.md)`')
SKIP = ('http', '/', '~', '@')
# Placeholder syntaxes -- not literal paths, nothing to resolve:
#   <type>  {subcommand}  ${CLAUDE_SKILL_DIR}  docs/agents/*.md
PLACEHOLDER = ('<', '{', '$', '*')

# Companion-file directories, in two tiers. See check-skill-refs.sh for why.
#   strict  -- a citation with no match anywhere is a real defect (demoted).
#   lenient -- only a wrong-but-fixable path counts; these directory names also
#              appear as OUTPUT paths a skill is told to write.
STRICT = 'references'
LENIENT = ('agents', 'docs', 'templates', 'rules', 'logic', 'assets', 'examples')

def skip(ref):
    return ref.startswith(SKIP) or any(c in ref for c in PLACEHOLDER)

def tier(ref):
    parts = ref.split('/')[:-1]
    if STRICT in parts:
        return 'strict'
    if any(p in LENIENT for p in parts):
        return 'lenient'
    return None

fixed = ambiguous = missing = 0

for plugin in sorted(os.listdir(root)):
    pdir = os.path.join(root, plugin)
    if not os.path.isdir(pdir):
        continue

    # basename -> [absolute paths] for every markdown file under this plugin
    index = {}
    for dirpath, dirnames, filenames in os.walk(pdir):
        dirnames[:] = [d for d in dirnames if d not in ('node_modules', '.git')]
        for fn in filenames:
            if fn.endswith('.md'):
                index.setdefault(fn, []).append(os.path.join(dirpath, fn))

    for dirpath, dirnames, filenames in os.walk(pdir):
        dirnames[:] = [d for d in dirnames if d not in ('node_modules', '.git')]
        if 'SKILL.md' not in filenames:
            continue

        path = os.path.join(dirpath, 'SKILL.md')
        with open(path, encoding='utf-8') as fh:
            text = original = fh.read()

        for ref in sorted(set(CITE.findall(text))):
            if skip(ref) or os.path.isfile(os.path.join(dirpath, ref)):
                continue

            t = tier(ref)
            if t is None:
                continue

            hits = index.get(os.path.basename(ref), [])
            rel = os.path.relpath(dirpath, root)

            # A lenient-tier citation with no match anywhere is almost always an
            # output path the skill is told to write, not a missing document.
            # Never demote those -- only strict-tier promises get that treatment.
            if t == 'lenient' and not hits:
                continue

            # More than one candidate: prefer the one sharing the longest
            # directory prefix with the citing file. Plugins that ship the
            # same skill tree twice (.claude/skills and cli/assets/skills,
            # or extensions/<x>/skills) otherwise look ambiguous when the
            # intended target is plainly the copy in the same subtree.
            if len(hits) > 1:
                def shared(p):
                    a, b = dirpath.split(os.sep), os.path.dirname(p).split(os.sep)
                    n = 0
                    while n < min(len(a), len(b)) and a[n] == b[n]:
                        n += 1
                    return n
                top = max(shared(h) for h in hits)
                close = [h for h in hits if shared(h) == top]
                if len(close) == 1:
                    hits = close
                else:
                    # Still tied: prefer the copy nearest the plugin root. A
                    # root-level agents/ or docs/ is the canonical location;
                    # deeper duplicates are sub-tree copies, which the rule
                    # above already claims when they are the right answer.
                    depth = lambda h: len(os.path.relpath(h, pdir).split(os.sep))
                    shallow = min(depth(h) for h in close)
                    nearest = [h for h in close if depth(h) == shallow]
                    if len(nearest) == 1:
                        hits = nearest

            if len(hits) == 1:
                new = os.path.relpath(hits[0], dirpath)
                text = text.replace(f'`{ref}`', f'`{new}`')
                print(f"  fixed      {rel}/SKILL.md\n               {ref}\n            -> {new}")
                fixed += 1
            elif not hits:
                # The document does not exist anywhere in the plugin -- upstream
                # promised a file it never shipped. Repointing is impossible and
                # inventing one is not an option, so demote the citation to plain
                # text. The agent keeps the topic and stops being sent to a
                # phantom file. Idempotent: the result is no longer a citation.
                text = text.replace(
                    f'`{ref}`',
                    f'{ref} (not shipped upstream - see patches/README.md)')
                print(f"  MISSING    {rel}/SKILL.md -> {ref}")
                print( "             not shipped upstream; citation demoted to plain text")
                missing += 1
            else:
                print(f"  AMBIGUOUS  {rel}/SKILL.md -> {ref}")
                print(f"             {len(hits)} equally close candidates; left as-is")
                ambiguous += 1

        if text != original:
            with open(path, 'w', encoding='utf-8') as fh:
                fh.write(text)

print(f"fix-skill-ref-paths: {fixed} fixed, {missing} missing upstream, {ambiguous} ambiguous.")
PY
