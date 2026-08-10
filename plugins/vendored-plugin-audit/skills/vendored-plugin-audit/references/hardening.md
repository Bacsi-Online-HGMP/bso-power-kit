# Hardening

Contents:
- [Why a repaired repo drifts back](#why-a-repaired-repo-drifts-back)
- [Three layers of enforcement](#three-layers-of-enforcement)
- [Documenting divergence from upstream](#documenting-divergence-from-upstream)
- [Working against a moving remote](#working-against-a-moving-remote)
- [Verification checklist](#verification-checklist)

## Why a repaired repo drifts back

Two independent paths reintroduce the bug:

- **Re-vendoring.** A build script that refreshes `plugins/` from upstream
  restores the upstream paths verbatim, undoing every repair.
- **Hand-added plugins.** Plugins are frequently committed directly, never
  passing through the build script at all. This is the more common route, and
  it is invisible without CI.

A fix that only survives one of these is not durable.

## Three layers of enforcement

**1. Re-vendor hook.** Make the build script run every repair script after
copying, then run the detector:

```bash
echo "Applying vendor patches"
for p in "$HERE"/patches/*.sh; do
  [ -f "$p" ] && bash "$p"
done
[ -f "$HERE/check-skill-refs.sh" ] && bash "$HERE/check-skill-refs.sh"
```

Loop over the directory. Naming one script explicitly means the second script
someone adds is silently unenforced.

**2. CI.** Install `assets/check-skill-refs.yml`. It runs three checks on push
and pull request:

- reference paths resolve (`--strict`, so it can fail)
- every plugin source named in the manifest exists on disk
- the repair scripts produce no diff, i.e. their output was actually committed

The third check is what catches a hand-added plugin. It is also why the repair
scripts must be idempotent.

**3. Destructive-rebuild guard.** If the build script begins with
`rm -rf plugins`, it will delete any plugin vendored straight into git. Either
refuse to run inside a git repo without an explicit `--force`, or move the tree
aside and restore whatever the copy loop did not recreate. Check whether the
repo already solves this before adding your own version.

## Documenting divergence from upstream

A vendored plugin that differs from its source needs a written reason, or the
next person diffs it, reads the patches as corruption, and reverts them. That is
the same misdiagnosis this whole skill exists to prevent.

Keep a `patches/README.md` covering, per script: what defect it fixes, the rules
it applies, which plugins were affected and how many citations, and what it
deliberately refuses to touch. State the upstream reporting status honestly —
until the bugs are reported, every fix stays local and re-applies forever rather
than eventually retiring.

Make in-file edits self-documenting. A citation demoted to plain text should
carry a pointer to the explanation, so a reader who hits it can find out why
without hunting.

Preserve upstream `LICENSE` files and attribution untouched. Flag plugins that
declare a licence in frontmatter but ship no licence text — AGPL and Apache both
require the text to accompany redistribution, and a marketplace exists to be
redistributed. Do not fix this by guessing: attaching the wrong licence is worse
than attaching none. Confirm each upstream first.

## Working against a moving remote

A repo-wide audit takes long enough for the remote to move. Before pushing:

```bash
git fetch origin
git log --oneline HEAD..origin/main
```

If the remote is ahead, check what it changed before rebasing. It may have
already vendored the plugin you just added (making yours a duplicate), already
fixed the problem you were solving, or dropped plugins you patched. Resetting
your own unpushed commits and re-applying only the parts that are still needed
is usually cleaner than resolving conflicts across a large diff — and is safe,
since the commits stay in the reflog.

Prefer the remote's solution when it is better than yours. Carrying a redundant
fix is its own maintenance burden.

## Verification checklist

Run all of it before declaring done. Each line failed at least once in practice.

- every script passes `bash -n`
- the detector reports clean, and `--strict` returns 1 on a deliberately broken
  tree and 0 on a clean one — test exit codes without piping, or you will read
  `sed`'s status
- every repair script reports zero changes on a second run
- `claude plugin validate .` passes
- every plugin source in the manifest exists on disk
- no unregistered directories remain in `plugins/` or `tools/`
- the build script's guard still refuses to run unsafely
- the CI workflow parses as YAML
- after pushing, confirm the CI run actually succeeded — do not assume
