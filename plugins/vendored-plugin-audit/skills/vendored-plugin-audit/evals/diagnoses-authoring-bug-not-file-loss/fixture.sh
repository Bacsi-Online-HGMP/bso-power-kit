#!/usr/bin/env bash
# A vendored plugin whose skill cites references/eeat.md from its own directory. The
# file exists, at the plugin root: an upstream path bug, not a lost file.
set -euo pipefail
mkdir -p .claude-plugin plugins/seo-kit/skills/audit plugins/seo-kit/references
cat > .claude-plugin/marketplace.json <<'FIXTURE'

{
  "name": "team-kit",
  "owner": {"name": "Team"},
  "plugins": [{"name": "seo-kit", "source": "./plugins/seo-kit"}]
}
FIXTURE
cat > plugins/seo-kit/skills/audit/SKILL.md <<'FIXTURE'

---
name: audit
description: Audit a web page for search quality signals.
---

# Audit

1. Fetch the page.
2. Score it against the checklist in `references/eeat.md`.
3. Report the three weakest signals.
FIXTURE
cat > plugins/seo-kit/references/eeat.md <<'FIXTURE'

# E-E-A-T checklist

- Named author with credentials
- First-hand experience shown
- Sources cited
FIXTURE
printf 'copied from upstream seo-kit v1.4.0 on 2026-09-01\n' > plugins/seo-kit/VENDORED.txt
