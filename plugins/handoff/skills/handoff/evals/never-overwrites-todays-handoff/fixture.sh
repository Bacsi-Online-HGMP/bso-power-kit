#!/usr/bin/env bash
# An earlier handoff from today is already in the working folder, next to the
# calendar draft the user says is finished.
set -euo pipefail
cat > "HANDOFF-$(date +%F).md" <<'FIXTURE'

# Session Handoff

## Current goal
Draft the October content calendar.

## Open items / next steps
Collect post ideas from the team.
FIXTURE
mkdir -p content
cat > content/october-calendar.md <<'FIXTURE'
# October content calendar (draft, complete)

| Week | Topic | Format |
|---|---|---|
| 1 | Sleep and screens | Reel |
| 2 | Morning light | Carousel |
| 3 | Naps at work | Article |
| 4 | Reader questions | Live |
FIXTURE
