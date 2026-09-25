# Freshness: handoff

Last reviewed: 2026-09-25

| Fact | Where the skill relies on it | How to check |
|---|---|---|
| Claude Code has a `/compact` command, and it summarises the conversation, losing the reasoning behind decisions | Description; the opening paragraph; *Rules* | `https://code.claude.com/docs/en/slash-commands` (look for `/compact` and what it keeps) |
| Claude Code offers a persistent memory store the skill can also write to | *Steps*, step 4 | `https://code.claude.com/docs/en/memory` |
| The last three rules come from the `handoff` skill in mattpocock/skills | *Rules*, final note | Compare with the vendored copy at `plugins/mattpocock-skills-main/skills/productivity/handoff/SKILL.md` after each re-vendor. Adopt a new rule only if it fits a handoff file kept in the working folder |
| Another installed handoff skill writes to a temporary directory, so this one has to claim the working-folder case in its description | Description | The mattpocock `handoff` skill above: where does it write today? If it now writes to the working folder too, merge or drop one of the two |

## Behaviour that depends on the model

- *Infer, don't interrogate*: newer models may ask more questions before writing, or
  fewer. The evals check that a handoff is written without questions when the
  conversation holds the answers.
- The template's section order is what makes a handoff skimmable. Check that a new model
  still fills every section and writes `none` rather than dropping empty ones.
