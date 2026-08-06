# Claude Ads Codex Instructions

Read and follow `AGENTS.md`; it is the canonical portable repository contract.
Use `ads/SKILL.md` as the product entrypoint, load detailed skills and references
only after routing, and use `ads/agents/openai.yaml` for the Codex-facing skill
interface metadata.

Keep repository work read-only unless the user explicitly requests implementation.
Live advertising-account writes remain separately capability-gated and require the
full mutation contract even when repository mutation is authorized.
