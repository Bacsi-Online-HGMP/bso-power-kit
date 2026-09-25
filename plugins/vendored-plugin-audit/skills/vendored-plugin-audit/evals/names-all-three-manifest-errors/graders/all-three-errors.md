---
type: llm
weight: 2
---

PASS if the reply identifies all three problems in plugin.json and gives the corrected form of each: (1) "author" must be an object such as {"name": "Pod Team"}, not a string; (2) the "skills" entry "./SKILL.md" must name the directory that contains SKILL.md, which here is the plugin root "."; (3) "agents/runner.md" must start with "./", as "./agents/runner.md".
FAIL if any of the three is missing or wrong, or if the reply names a different change as the cause.
