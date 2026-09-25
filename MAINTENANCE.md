# Keeping this repository current

Everything here goes stale in one of three ways: upstream releases a new version, someone
edits vendored code by hand, or the world a skill describes moves on (an app's UI, an API,
a model list, the Claude model itself). Each has its own loop.

| Loop | When | Runs | What it produces |
|---|---|---|---|
| Re-vendor | Mondays 06:17 UTC | `revendor` workflow | A pull request for every plugin or tool whose upstream moved |
| Guard local changes | Every PR touching vendored code | `verify-vendored` workflow | A red check if vendored code differs from upstream + `patches/` |
| Freshness check | 1st of each month | A Claude routine (below) | A pull request with the evidence for every fact checked |
| New Claude model | When one ships | You, with `run-evals.sh` | Skills adjusted to how the new model behaves |

The first two are described in `revendor.sh` and `patches/README.md`. This file covers
the other two.

---

## Freshness check

### What gets checked

Every first-party skill carries a `FRESHNESS.md` next to its `SKILL.md`. First-party means
`skills/*/`, the plugins that `sources.tsv` marks *authored here*, and each local addition
under `patches/*/` (the Gemini fallback, for one). `check-freshness.sh` fails CI when one
is missing.

A `FRESHNESS.md` lists the facts the skill depends on that can change without anyone
editing this repository: a UI label or flow, a CLI flag, an API endpoint or model name, a
library call, another skill or repo it defers to. Stable knowledge does not belong in it.

```markdown
# Freshness: <skill name>

Last reviewed: YYYY-MM-DD

| Fact | Where the skill relies on it | How to check |
|---|---|---|
| One checkable statement | File and section | The source of truth, and what to look for |

## Behaviour that depends on the model

- What the skill asks of the model that a newer model may do differently.
```

`Last reviewed` is the date of the last completed check. `check-freshness.sh` warns once it
is more than 45 days old: the monthly check has probably stopped running.

When you write or change a skill, add its facts at the same time. A fact nobody wrote
down is a fact nobody checks.

### The procedure

A Claude routine runs this on the 1st of every month. It can also be run by hand in any
Claude Code session: *"Run the monthly freshness check in MAINTENANCE.md."*

1. **Collect.** `bash check-freshness.sh` lists every first-party skill and its
   `FRESHNESS.md`. Read each one, then the `SKILL.md` it belongs to.
2. **Check each fact** against the source named in its row. Mark it:
   - **confirmed**: the source still says what the skill says;
   - **changed**: the source now says something else. Record the old and the new
     statement and the URL;
   - **unverified**: the source could not be reached or does not settle it. Say why.

   `WebSearch` works from the cloud environment. `curl` and `WebFetch` are blocked for
   some hosts by its network policy (`ai.google.dev`, `youtube.com` at the time of
   writing); try the official page, then a search, then mark the fact unverified.
   Never guess, and never mark a fact confirmed from memory.
3. **Fix what changed.** Edit the skill as little as the change requires, and update the
   fact's row. Rules that still apply:
   - `CLAUDE.md` first: English everywhere, and the Vietnamese carve-out stays
     byte-for-byte.
   - A local addition to a vendored plugin is edited in `patches/`, never in `plugins/`.
     Re-run its patch script, then `bash revendor.sh --verify <entry>`.
   - A change that alters what a skill does (not just a label, path or name) is proposed
     in the pull request, not made.
4. **Check the Claude models.** Compare the newest models on Anthropic's models overview
   page with the list under *New Claude model* below. If one is new, say so at the top of
   the pull request and recommend running the evals.
5. **Validate.** `bash check-skill-refs.sh --strict`, `bash check-freshness.sh`, and
   `claude plugin validate .`. Run `bash revendor.sh --verify` if anything under
   `patches/` changed.
6. **Report, always.** Set `Last reviewed` to today in every `FRESHNESS.md` that was
   checked, commit, and open a draft pull request titled
   `Monthly freshness check YYYY-MM`. Open it even when nothing changed: a check that runs
   silently cannot be told apart from one that stopped. The body is one table:

   | Skill | Fact | Status | Evidence | Change |
   |---|---|---|---|---|

   Put changed and unverified facts first.

---

## New Claude model

Each first-party skill has an eval suite in `evals/` next to its `SKILL.md`: a few
realistic requests, each with graders on the result and on the steps taken (was the
skill used, was a file written, was a secret left out). `run-evals.sh` runs them with
`claude plugin eval`. Each case runs three times with the skill and three times without
it; `Δ` is what the skill adds.

When a new model ships:

1. Run the suites on the model you use now and on the new one:
   `bash run-evals.sh -- --model <current id>`, then `bash run-evals.sh -- --model <new id>`.
2. Read the reports (`<skill>/evals/results/<timestamp>/report.html`):
   - **Passes on the old model, fails on the new**: find the instruction the new model
     reads differently and make it clearer. Not louder: capitals and "MUST" tend to make
     newer models over-apply a rule.
   - **`Δ` near zero on the new model**: it now does this unaided. Trim that part of the
     skill and keep what still moves the score.
   - **`skill-fired` fails**: the description no longer triggers on natural phrasing.
     Rewrite the description.
3. Update the model list below and the *Behaviour that depends on the model* section of
   each skill you changed.

While editing a skill, a cheap pass is `bash run-evals.sh <skill> -- --runs 1 --ablation none`.
Every run is a model call on your plan: a full pass of all four suites is 72 agent runs,
and each suite stops at $10 of list-price cost.

A new first-party skill gets an `evals/` folder too: at least one request that should
use it, one that should not, and one that tests the rule it most needs to keep. The
format is at `https://code.claude.com/docs/en/plugin-evals`.

Newest Claude models at the last review (2026-09-25): Fable 5.1 (`claude-fable-5-1`),
Opus 5.5 (`claude-opus-5-5`), Sonnet 5 (`claude-sonnet-5`), Haiku 4.5
(`claude-haiku-4-5-20251001`).

When the freshness check reports a new model, update this list in the same pull request.
