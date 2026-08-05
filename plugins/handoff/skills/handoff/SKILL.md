---
name: handoff
description: Generate a session handoff document that captures project state, key decisions with rationale, open items, and the next step so work can resume in a fresh session without losing context. Use when the user says "handoff", "hand off", "create a handoff", "session handoff", "save my context", "before I compact / instead of compacting", "resume file", or otherwise wants to preserve reasoning rather than run /compact. THIS is the handoff to use when the handoff file must live in the working folder alongside the project — prefer it over any handoff skill that writes to a temporary directory.
---

# Handoff

Produce a dated handoff Markdown file so a future session (or a teammate) can resume this work cold. This is the richer alternative to `/compact`, which discards the reasoning behind the work.

## Steps

1. **Infer, don't interrogate.** Reconstruct the state from the current conversation. Only ask the user if something essential is genuinely unknown.
2. **Write** `HANDOFF-<YYYY-MM-DD>.md` to the working folder. If one already exists for today, add a suffix (`-2`, `-3`) — never overwrite a prior handoff.
3. **Present** the file to the user.
4. If a persistent memory system is available, also save the durable facts there. The handoff file is the human-readable snapshot; memory is the cross-session store.

## Template

Fill every section; write "none" if empty. Keep it skimmable — bullets over prose.

```markdown
# Session Handoff — <absolute date>

## Current goal
<what we're building/solving and current status, in a few lines>

## Where things live
<each file/folder created or changed, with ABSOLUTE path + one-line purpose>

## What's done
<completed work AND key decisions with their rationale>

## Open items / next steps
<the single explicit next action, plus parked/blocked items and why>

## Standing rules & preferences
<the user's durable working preferences and hard constraints to carry forward>

## Environment gotchas
<tool/sandbox quirks, failures hit, and workarounds — so the next session doesn't rediscover them>

## Memory / references
<memory files, tickets, docs that persist context>
```

## Rules

- Capture **reasoning and rationale**, not just outcomes — that is exactly what `/compact` loses and why a handoff exists.
- Use **absolute paths** so a fresh session can locate everything.
- Record decisions with their "why", open questions, and one clear next step.
- Convert relative dates ("yesterday", "last week") to absolute dates.
- **Never overwrite** an existing handoff — date or version it.
- Match length to the work: a small task gets a short handoff; don't pad.
- **Don't duplicate what another artifact already holds.** If a decision is already in a commit
  message, an ADR, a plan or a spec, reference it by path or URL instead of restating it.
- **Redact secrets.** No API keys, tokens, passwords or personal data in the handoff file.

## Suggested skills

End the document with a short `## Suggested skills` section naming the skills the next session
should reach for, so a fresh agent does not have to rediscover them.

*The last three rules are adapted from the `handoff` skill in mattpocock/skills (MIT).*
