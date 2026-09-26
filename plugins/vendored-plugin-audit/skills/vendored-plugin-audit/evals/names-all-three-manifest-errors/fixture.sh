#!/usr/bin/env bash
# A plugin.json with the three shape errors claude plugin validate rejects.
set -euo pipefail
mkdir -p plugins/pod-tools/.claude-plugin plugins/pod-tools/agents
cat > plugins/pod-tools/.claude-plugin/plugin.json <<'FIXTURE'

{
  "name": "pod-tools",
  "version": "1.0.0",
  "author": "Pod Team",
  "skills": ["./SKILL.md"],
  "agents": ["agents/runner.md"]
}
FIXTURE
cat > plugins/pod-tools/SKILL.md <<'FIXTURE'

---
name: pod-tools
description: Helpers for podcast show notes.
---

Write show notes from a transcript.
FIXTURE
cat > plugins/pod-tools/agents/runner.md <<'FIXTURE'

---
name: runner
description: Runs the show-notes pipeline.
---

Run the pipeline.
FIXTURE
