# Freshness: vendored-plugin-audit

Last reviewed: 2026-09-25

| Fact | Where the skill relies on it | How to check |
|---|---|---|
| `claude plugin validate .` is the platform validator, and rejects `author` as a string, a `skills` entry naming `SKILL.md`, and a relative entry without `./` (reported as `Invalid input`) | `SKILL.md` step 5 and *Scripts*; `scripts/fix-plugin-manifests.sh` | `https://code.claude.com/docs/en/plugins-reference`, then run `claude plugin validate` on a scratch plugin carrying each error |
| The bundled scripts match the repo's own copies, apart from the default path and the Apache-2.0 notice | `scripts/` | `diff` each against `check-skill-refs.sh` and `patches/fix-*.sh` at the repo root. Any other difference means a fix reached one copy only |
| The CI template uses the current major version of `actions/checkout`, the same as this repo's workflows | `assets/check-skill-refs.yml` | `git ls-remote --tags https://github.com/actions/checkout.git`; compare with `.github/workflows/*.yml` |
| Marketplace entries use `source` and `skills` paths starting with `./plugins/` | `assets/check-skill-refs.yml` manifest step | `https://code.claude.com/docs/en/plugin-marketplaces` |

## Behaviour that depends on the model

- The core instruction is to separate an upstream authoring bug from a real file loss
  before changing anything. The evals check that a model still diagnoses before it
  repairs.

*Found on 2026-09-25 while writing this file, and fixed in the same change: the bundled
`fix-plugin-manifests.sh` lacked the `./` rule the repo's copy gained on 2026-08-21, and
the CI template pinned `actions/checkout@v4` while the repo used `@v7`.*
