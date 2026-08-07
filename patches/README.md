# Vendor patches

Fixes applied to vendored third-party plugins. Upstream `LICENSE` files and
attribution are never touched — only the specific defect named below is changed.

`build-standalone.sh --force` runs every `patches/*.sh` after re-vendoring, then
runs `check-skill-refs.sh`. Pulling an upstream update therefore cannot silently
reintroduce these bugs. Every script here is idempotent and safe to run by hand.

If you diff a vendored plugin against its upstream repo and find differences,
check here first. They are deliberate.

---

## `fix-skill-ref-paths.sh`

**Fixes:** broken `references/…` citations in `SKILL.md` files
**Applies to:** every plugin under `plugins/`, automatically

Many upstream plugins keep shared reference documents in one directory and cite
them from sibling skills using a path that only resolves from the plugin root —
or from nowhere at all. The documents are present in the repo; the relative
paths are wrong.

The symptom is easy to misread. An agent loading such a skill is told to read
files it cannot find, which looks exactly like the vendoring step dropped them.
It did not. This is an upstream authoring bug in each affected plugin, and it is
why this script exists rather than a re-download.

### The rules

For each citation that does not resolve, search for the basename within that
plugin, then:

- **exactly one match** → rewrite the path to point at it.
- **several matches** → prefer the one sharing the longest directory prefix with
  the citing file. Plugins that ship the same skill tree twice (`.claude/skills`
  and `cli/assets/skills`, or `extensions/<x>/skills`) otherwise look ambiguous
  when the intended target is plainly the copy in the same subtree. A genuine
  tie is reported and left alone.
- **no match anywhere** → the document was never shipped. Repointing is
  impossible and inventing one is not an option, so the citation is demoted to
  plain text marked `(not shipped upstream)`. The agent keeps the topic and
  stops being sent to a phantom file.

Placeholders are skipped, not resolved: `references/losses_<type>.md`,
`references/{subcommand}.md`, `${CLAUDE_SKILL_DIR}/references/presets.md`.

### What it repaired

162 citations across 60 files in 9 plugins:

| Plugin | Files | Nature of the bug |
|---|---:|---|
| `claude-repurpose` | 19 | sub-skills cite the hub's `references/` as if it were their own |
| `claude-blog` | 14 | same shape — shared references cited from sibling skills |
| `claude-ads` | 14 | `ads/references/…` only resolves from the plugin root |
| `academic-research-skills-main` | 4 | plugin-root-relative paths cited one level down |
| `claude-seo` | 3 | duplicate skill trees; resolved by nearest-subtree rule |
| `ui-ux-pro-max-skill` | 2 | 8 citations to 4 token docs that exist nowhere |
| `AI-Research-SKILLs-main` | 2 | `citation-workflow.md` lives under a different skill |
| `ECC-main` | 1 | ja-JP translated skill has no `references/`; English original does |
| `agent-skills-main` | 1 | sibling skill cited via `skills/…` from inside `skills/` |

Nine citations were demoted rather than repointed, because the documents do not
exist upstream: `draft_model.md` in `speculative-decoding`, and the four
`*-tokens.md` / `token-architecture.md` files in `design-system` (which ships in
two copies).

**Why not symlinks:** this repo is distributed as a zip and used on Windows.
Symlinked `references/` directories survive neither.

**Upstream status:** not reported to any of the nine projects. Each fix can be
dropped once upstream corrects its own paths — the script will find nothing to
do.

---

## `check-skill-refs.sh` (repo root, not a patch)

Reports `SKILL.md` files citing reference documents that do not exist. Run it
after adding or updating any vendored plugin:

```bash
bash check-skill-refs.sh              # whole repo
bash check-skill-refs.sh plugins/foo  # one plugin
```

It reports and exits 0 — informational, never blocks a build. It is the
detector for this whole class of bug, not just the instances fixed above.
