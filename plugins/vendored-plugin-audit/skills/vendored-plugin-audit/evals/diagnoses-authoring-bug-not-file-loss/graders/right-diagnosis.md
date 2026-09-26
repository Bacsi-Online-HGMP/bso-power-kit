---
type: llm
weight: 2
---

PASS if the reply says the file exists at plugins/seo-kit/references/eeat.md, and that the skill's citation resolves from the skill's own directory (plugins/seo-kit/skills/audit/) where there is no such file, so this is a path bug in the upstream plugin and nothing was dropped by vendoring.
FAIL if the reply concludes that files were lost, recommends re-downloading or re-vendoring as the fix, or does not say where the file actually is.
