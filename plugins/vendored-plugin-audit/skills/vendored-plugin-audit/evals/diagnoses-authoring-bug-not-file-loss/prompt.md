---
description: A missing reference is diagnosed as an upstream path bug before anything is changed.
tags: [smoke]
max_turns: 12
allowed_tools: [Read, Glob, Grep, Skill]
---

The audit skill in plugins/seo-kit keeps saying it can't find references/eeat.md. I think our vendoring step dropped files when we copied the plugin in. Can you check what happened? Don't change anything yet.
