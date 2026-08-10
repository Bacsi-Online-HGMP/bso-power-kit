---
name: vendored-plugin-audit
description: Diagnose and repair broken skills in a plugin marketplace or vendored-plugin repo, then keep them fixed. Use when a skill reports missing reference files, when `claude plugin validate` fails, when someone suspects files were lost while vendoring a third-party plugin, when auditing a marketplace repo before sharing it, or when asked to clean up unregistered/stale plugin directories. Covers diagnosis (upstream authoring bug vs. genuine file loss), class-level repair with idempotent scripts, a detector that avoids false positives, deletion of dead weight, and CI enforcement.
---

# Vendored plugin audit

Repair broken skills in a marketplace repo at the level of the *class*, not the
instance, and leave behind a detector so the class cannot come back.

## The finding that drives everything

When a skill says its reference files are missing, the overwhelmingly likely
cause is **not** that vendoring dropped them. It is that the upstream author
wrote a relative path that resolves from the plugin root, or from nowhere, while
the file sits somewhere else in the same repo.

Never accept "we lost files" as the premise. Confirm it. See
[references/diagnosis.md](references/diagnosis.md) for the four checks that
separate a real file loss from an upstream authoring bug, and for the reasoning
behind the two-tier detection rule.

## Workflow

1. **Verify the premise before touching anything.** Locate the plugin on disk,
   check whether it is a complete upstream checkout, and find where the cited
   documents actually live. Report what is really wrong even when that
   contradicts the person who asked.
2. **Detect at repo scale.** Run `scripts/check-skill-refs.sh` from the repo
   root. Count findings per plugin — one plugin means an instance, several mean
   a class.
3. **Repair with a script, never by hand.** Run
   `scripts/fix-skill-ref-paths.sh` and `scripts/fix-plugin-manifests.sh`. Hand
   edits die at the next re-vendor.
4. **Re-run the detector.** Then run both repair scripts a second time and
   confirm they report zero changes. A repair script that is not idempotent will
   corrupt the repo on its second run.
5. **Run the platform validator.** `claude plugin validate .` — do this early,
   not last. One malformed manifest reports as a failure for the entire
   marketplace, hiding everything else.
6. **Remove dead weight.** Directories registered in neither the manifest nor
   the build script are loaded by nothing. Verify first (below), then delete.
7. **Enforce it.** Install `assets/check-skill-refs.yml` and hook the repair
   scripts into the repo's re-vendor script. See
   [references/hardening.md](references/hardening.md).
8. **Verify, then push.** Fetch before pushing — long audits go stale. Confirm
   CI actually passed rather than assuming it did.

## Repair rules that must not be relaxed

When a cited document does not resolve, search for its basename inside that
plugin, then:

| Candidates | Action |
|---|---|
| exactly one | rewrite the path to it |
| several | prefer the longest shared directory prefix with the citing file |
| still tied | prefer the copy nearest the plugin root |
| still tied | **report and leave alone** |
| none (strict tier only) | demote the citation to plain text marked as not shipped upstream |

The refusal case is the important one. Replacing a visibly broken path with a
plausible wrong one is worse than leaving it broken, because nobody looks at it
again. Never invent a target to make a report go green.

## Before deleting any directory

Deletion is the only irreversible step. Confirm all four:

- absent from `marketplace.json` (`plugins[].source` **and** `plugins[].skills[]`)
- absent from the build script's plugin array
- not wired up in any `settings.json` — and note that a name appearing there
  often points at an *external* marketplace, not the vendored copy, so check
  which
- referenced elsewhere only in prose (a README "dropped, and why" table is fine
  to keep)

Keep removal tombstones (`renames` mapped to `null`) so machines that already
installed the plugin detach cleanly instead of erroring. Expect `git rm` to
refuse files a repair script just modified; inspect for untracked content, then
force.

## Environment traps

These cost real time in practice:

- **macOS ships bash 3.2.** No `mapfile`, no associative arrays. It also
  mis-parses a `case` pattern containing `)` inside `$( )` — collect findings in
  a temp file instead of a command substitution.
- **Repo paths contain spaces.** Never join roots into a space-delimited string;
  use `"$@"`.
- **Sandboxed shells have no git credentials and will wedge `.git/index.lock`.**
  Run every `git` command, including read-only ones, on the real machine.
- **`$?` after a pipe is the last command's status.** Test exit codes without
  piping through `sed`, or a broken check will look like it passed.

## Scripts

All three take an optional path argument and default to `./plugins` (the
detector defaults to `./plugins ./tools`). Run them from the repo root.

- `scripts/check-skill-refs.sh [path...] [--strict]` — report skills citing
  documents that do not exist. `--strict` exits 1 for CI; without it, always
  exits 0 so it never blocks a build by accident.
- `scripts/fix-skill-ref-paths.sh [path]` — repair broken citations by the rules
  above. Idempotent.
- `scripts/fix-plugin-manifests.sh [path]` — fix `plugin.json` shape errors that
  fail validation: `author` as a string, and `skills` entries pointing at a
  `SKILL.md` file rather than the directory containing it. Idempotent.

Read [references/hardening.md](references/hardening.md) before wiring the CI
workflow or documenting the divergence from upstream — vendored plugins that
differ from their source need a written reason, or the next person reads the
patches as corruption and reverts them.
