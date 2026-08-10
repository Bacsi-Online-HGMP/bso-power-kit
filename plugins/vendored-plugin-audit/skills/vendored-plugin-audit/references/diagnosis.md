# Diagnosis

Contents:
- [Is it really a file loss?](#is-it-really-a-file-loss)
- [Where the paths actually go wrong](#where-the-paths-actually-go-wrong)
- [The two-tier detection rule](#the-two-tier-detection-rule)
- [Placeholders that are not paths](#placeholders-that-are-not-paths)
- [Reading the scale of the problem](#reading-the-scale-of-the-problem)

## Is it really a file loss?

The report usually arrives as "the vendoring dropped files" or "this plugin is
missing its references". Run these four checks before accepting that.

1. **Is the plugin even vendored where they think?** A plugin installed from its
   own upstream marketplace has nothing to do with the repo being blamed. Check
   `.claude-plugin/marketplace.json` inside the installed plugin — it names the
   marketplace that actually shipped it.
2. **Is the checkout complete?** A lossy copy does not leave `LICENSE`,
   `pyproject.toml`, `.github/`, `install.sh` and the cover image behind while
   dropping only markdown. If the incidental files are all present, nothing was
   dropped.
3. **Do the documents exist somewhere in the plugin?** Search by basename. They
   are usually one directory away.
4. **Does the citing file resolve from a different root?** Paths written as
   `references/x.md` or `skills/y/references/x.md` frequently only work from the
   plugin root, not from the skill directory that cites them.

If 2 and 3 both hold, this is an upstream authoring bug. Say so plainly, even
though it contradicts the person who asked — the wrong diagnosis leads to a
re-download that changes nothing.

## Where the paths actually go wrong

Four shapes, all seen in the wild:

| Shape | Example | Fix |
|---|---|---|
| Hub/spoke | 20 sub-skills cite the hub's `references/` as if it were their own | `../hub/references/x.md` |
| Root-relative | `ads/references/x.md` cited from inside `skills/ads-google/` | relative path back up |
| Duplicated tree | plugin ships `.claude/skills/` *and* `cli/assets/skills/` | nearest subtree wins |
| Translated copy | `docs/ja-JP/skills/foo/` has no `references/`; the English original does | point at the original |

## The two-tier detection rule

This is the single most important design decision, and getting it wrong makes
the detector worthless.

A naive detector flags every backticked `*.md` path that does not resolve. That
catches **output** paths — files the skill is *told to write*, like
`linkedin/post.md` or `docs/report.md` — which are not supposed to exist. In
practice roughly nine findings in ten were noise. A checker people learn to
ignore is worse than no checker.

The fix is to split by directory name and confidence:

**Strict tier — `references/`**
Report even when the basename exists nowhere in the plugin. That case means the
skill promises a document it never shipped, which is worth surfacing. These are
the only citations eligible for demotion to plain text.

**Lenient tier — `agents/ docs/ templates/ rules/ logic/ assets/ examples/`**
Report only when a file of that name exists somewhere in the plugin, i.e. the
path is wrong but fixable. These directory names double as output destinations,
so a citation matching nothing is far more likely to be an intended output than
a missing document. Never demote these.

**Everything else** — bare paths like `linkedin/post.md` — is ignored entirely.

## Placeholders that are not paths

Skip any citation containing these; they are templates, not filenames:

```
<type>                              references/losses_<type>.md
{subcommand}                        references/{subcommand}.md
${VAR}                              ${CLAUDE_SKILL_DIR}/references/presets.md
*                                   docs/agents/*.md
@                                   @references/nightly-cleaner.md   (file-mention syntax)
http... / ... ~...                  URLs, absolute and home-relative paths
```

## Reading the scale of the problem

Group findings by plugin before deciding anything:

```bash
bash scripts/check-skill-refs.sh | grep BROKEN | sed 's|.*plugins/||; s|/.*||' | sort | uniq -c | sort -rn
```

One plugin with a handful of findings is an instance — patch it and move on.
Several plugins with the same shape is a class, and the response is a script
plus a detector plus CI, because hand-fixing a class guarantees it returns with
the next import.

Expect the count to jump when the repo gains plugins. A marketplace that was
clean can acquire dozens of broken citations from a single hand-added plugin,
which is exactly why the detector has to run automatically rather than on
request.
