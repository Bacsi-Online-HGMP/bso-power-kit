# Freshness: vietnamese-anti-slop

Last reviewed: 2026-09-25

| Fact | Where the skill relies on it | How to check |
|---|---|---|
| `no-ai-slop` and `stop-slop` are installed, their word lists are English-only, and they disagree on scoring (`stop-slop` scores 1 to 10, `no-ai-slop` forbids scores) | *Why a separate skill is needed* | Read both skills as installed today. If either gains Vietnamese coverage, or they stop disagreeing, rewrite that section |
| The approved wording lives at `bso-marketing/docs/core/claims-matrix/`, and the compliance skill at `bso-marketing/tools/skills/supplement-compliance` | *The compliance boundary* | Both paths in the `bso-marketing` repository. If this session cannot reach it, mark the fact unverified |
| The words listed as both cliche and violation match the banned claim language in `supplement-compliance` | *The compliance boundary*, the word list | `bso-marketing/tools/skills/supplement-compliance/references/vn/`. A word banned there but missing here is the dangerous case. Report it; do not edit Vietnamese wording in the fix |
| The product names listed (Niasom, Hetik, Femakul, Hemky, HemkyD, Gueva, Binifa) are the current HGMP range | *The compliance boundary*, last paragraph | The `supplement-compliance` skill description, which lists the same range |

## Behaviour that depends on the model

- The cliche catalogue describes how models wrote Vietnamese in 2026. Newer models drop
  some tells and pick up new ones. Once a year, or on a new model: generate a few
  captions and scripts in Vietnamese with the current model, audit them with this skill,
  and note tells the catalogue misses. Propose additions in the pull request; Vietnamese
  examples are written by a person, not by the check.
