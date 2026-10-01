---
type: Agent Instructions
title: bso-power-kit — the way in for every AI agent
description: The rules for this kit are in CLAUDE.md and bind every AI, not only Claude; this file sends Codex and the others there.
tags: [agent, rules]
authority: binding
status: draft
generated: { by: claude/opus-5.5, at: 2026-10-01T01:38:37Z }
---

# bso-power-kit — the way in for every AI agent

Codex reads this file itself. Gemini CLI and Qwen Code read `GEMINI.md` and `QWEN.md`, which
import it. Claude Code reads `CLAUDE.md`.

The rules for this kit are in `CLAUDE.md`, in this folder. Read it first. They bind every AI that
works here, not only Claude. The two that matter most before any edit:

- `plugins/` and `tools/` are vendored third-party code. Never edit them in place; a local change
  is a script in `patches/`.
- Everything committed is English.

To use this kit's skills in your own app, run `python3 bootstrap-device/install_ai_skills.py`. It
links the first-party skills, and the plugins that `bootstrap-device/plugins-other-apps.tsv` lists
for your app, into your app's skills folder. It skips what is current and deletes nothing.
