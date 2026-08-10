# Vendor patches

Fixes applied to vendored third-party plugins. Upstream `LICENSE` files and
attribution are never touched — only the specific defect named below is changed.

If you diff a vendored plugin against its upstream repo and find differences,
check here first. They are deliberate.

Three things keep this honest:

- `build-standalone.sh --force` runs every `patches/*.sh` after re-vendoring,
  then runs the checker — so pulling an upstream update cannot silently
  reintroduce the bug.
- `.github/workflows/check-skill-refs.yml` runs the checker on every push and
  pull request. Plugins get added to this repo by hand, not only through
  `build-standalone.sh`, and that is exactly how `claude-blog` and `claude-ads`
  arrived carrying broken paths.
- Every script here is idempotent, so running one by hand is always safe.

---

## `fix-skill-ref-paths.sh`

**Fixes:** broken companion-document citations in `SKILL.md` files
**Applies to:** every plugin under `plugins/`, automatically

Many upstream plugins keep shared documents in one directory and cite them from
sibling skills using a path that only resolves from the plugin root — or from
nowhere at all. The documents are present in the repo; the relative paths are
wrong.

The symptom is easy to misread. An agent loading such a skill is told to read
files it cannot find, which looks exactly like the vendoring step dropped them.
It did not. This is an upstream authoring bug in each affected plugin, and it is
why this script exists rather than a re-download.

### What counts as a citation

Backticked paths ending in `.md` under a known companion-file directory, in two
tiers, because the cost of a false positive differs:

| Tier | Directories | Rule |
|---|---|---|
| strict | `references/` | Flagged even when the document exists nowhere — a skill promising a file it never shipped is worth knowing about. |
| lenient | `agents/` `docs/` `templates/` `rules/` `logic/` `assets/` `examples/` | Flagged only when a file of that name exists somewhere in the plugin, i.e. the path is wrong but fixable. |

The lenient tier matters because those same directory names appear as **output**
paths a skill is told to write. An early version of the checker flagged
`linkedin/post.md` and `docs/report.md` as missing files; roughly nine in ten
findings were noise, which is worse than no checker at all.

Ignored entirely: URLs, absolute and home-relative paths, `@`-mentions, and
placeholders — `references/losses_<type>.md`, `references/{subcommand}.md`,
`${CLAUDE_SKILL_DIR}/references/presets.md`, `docs/agents/*.md`.

### How a broken path is resolved

Search for the basename within that plugin, then:

1. **One match** → rewrite the path to point at it.
2. **Several matches** → prefer the one sharing the longest directory prefix
   with the citing file. This is what disambiguates plugins shipping the same
   skill tree twice (`.claude/skills` and `cli/assets/skills`, or
   `extensions/<x>/skills`).
3. **Still tied** → prefer the copy nearest the plugin root. A root-level
   `agents/` is the canonical location; deeper duplicates belong to sub-trees,
   which rule 2 already claims when they are the right answer.
4. **Still tied** → report and leave alone.
5. **No match anywhere** (strict tier only) → the document was never shipped.
   Repointing is impossible and inventing one is not an option, so the citation
   is demoted to plain text marked
   `(not shipped upstream - see patches/README.md)`. The agent keeps the topic
   and stops being sent to a phantom file.

Rule 4 exists on purpose. Replacing a visibly broken path with a plausible wrong
one is worse than leaving it broken, because nobody goes looking for it again.

### What it repaired

279 citations across 59 files in 7 surviving plugins:

| Plugin | Files | Nature of the bug |
|---|---:|---|
| `claude-repurpose` | 19 | sub-skills cite the hub's `references/` as if it were their own |
| `claude-ads` | 15 | `ads/references/…` only resolves from the plugin root |
| `claude-blog` | 14 | shared references cited from sibling skills |
| `claude-seo` | 4 | duplicate skill trees; resolved by rules 2 and 3 |
| `academic-research-skills-main` | 4 | plugin-root-relative paths cited one level down |
| `ui-ux-pro-max-skill` | 2 | 8 citations to 4 token docs that exist nowhere |
| `mattpocock-skills-main` | 1 | `docs/agents/…` cited from inside a skill directory |

Four further plugins were repaired and then deleted in the same pass — they were
registered nowhere and are gone from `plugins/` entirely.

Ten citations were demoted rather than repointed, all in `ui-ux-pro-max-skill`:
the `design-system` skill promises `token-architecture.md` and three
`*-tokens.md` documents that exist nowhere upstream, and it ships in two copies.

**Why not symlinks:** this repo is distributed as a zip and used on Windows.
Symlinked directories survive neither.

**Upstream status:** not reported to any of the seven projects. Each fix can be
dropped once upstream corrects its own paths — the script will find nothing to
do.

---

## `fix-plugin-manifests.sh`

**Fixes:** `plugin.json` shape errors that fail `claude plugin validate`
**Applies to:** every plugin under `plugins/`, automatically

Two errors turn up in vendored manifests:

| Wrong | Right | Consequence |
|---|---|---|
| `"author": "Someone"` | `"author": {"name": "Someone"}` | manifest rejected |
| `"skills": ["./SKILL.md"]` | `"skills": ["."]` | the skill never loads — an entry must be a *directory* containing `SKILL.md`, not the file |

Repaired four manifests: `claude-youtube` and `claude-shorts` (author),
`youtuber` and `claude-blog/brain` (skills). Before this, `claude plugin
validate .` failed outright — and one bad manifest reports as a failure for the
whole repo, so genuine problems hide behind it.

Validation now passes. Eight advisory warnings remain — upstream plugins missing
`version`, `description` or `author`, plus a few fields Claude Code ignores at
load time. Those are upstream's to fill in; inventing values for someone else's
manifest would be worse than leaving them blank.

---

## `check-skill-refs.sh` (repo root, not a patch)

The detector for this whole class of bug.

```bash
bash check-skill-refs.sh              # whole repo
bash check-skill-refs.sh plugins/foo  # one plugin
bash check-skill-refs.sh --strict     # exit 1 on findings, for CI
```

Without `--strict` it reports and exits 0, so it never blocks a build by
accident. CI passes `--strict`.
