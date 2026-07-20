# Claude Power Kit

A maintained best-of community skills, plugins & MCPs for Claude — Cowork and Code. Curated with a balanced "useful to me *and* to anyone" rubric; official Anthropic skills, plugins and connectors are intentionally excluded (you already get those built in).

**For** clinicians, researchers, and hands-on builders who want a strong default toolset without wading through 1,800-skill mega-catalogs. Everything here is **free** and runs on almost any computer that can run Claude. Tools marked **`Code`** work only in Claude Code, not Cowork.

## What's inside
`◆` = spine of its group · `Code` = Claude Code only.

### A · Research & Academic
- **◆ AI-Research-SKILLs** — idea → paper research skill suite.
- **academic-research-skills** — deep research + writing pipeline (the daily driver).
- **huggingface-skills** — dataset / model / eval tasks for AI work.
- **notebooklm-mcp-cli** `Code` — bridge to Google NotebookLM for grounded RAG.

### B · Codebase Comprehension & Memory
- **◆ Understand-Anything** — turn any codebase or docs into an explorable knowledge graph.
- **SocratiCode** — semantic code search + dependency graph + context.
- **agentmemory** — persistent cross-session memory (Pensyve already covers this in Cowork — pick one).

### C · Coding Discipline & Quality
- **◆ superpowers** — dev methodology that auto-fires the right skill.
- **brooks-lint** — code review grounded in 12 engineering classics.
- **andrej-karpathy-skills** — house rules against common LLM-coding pitfalls.
- **ponytail** — terse "one line, it works" style.
- **mattpocock-skills** — TypeScript engineering skills.
- **caveman** `Code` — ~65% fewer output tokens, same answers.

### D · Agent Framework
- **◆ ECC** — the big agent-harness "OS" (agents, commands, hooks, skills, MCP; Vietnamese docs included).

### E · Frontend & Visual Polish
- **◆ impeccable** — design guidance + anti-slop detectors + live browser iteration.
- **tasteskill** — anti-slop premium frontend skills.
- **design.md** — a format for handing a visual identity to agents.
- **modern-web-guidance** — modern web best-practices + compatibility (Google Chrome team).

### F · Browser & Web
- **◆ chrome-devtools-mcp** — let the agent control & inspect a live Chrome.

### G · Content & Trend Research
- **◆ last30days-skill** — last-30-days trends across Reddit / HN / X / YouTube / Polymarket.
- **Agent-Reach** `Code` — broad internet reach for agents (YouTube, RSS, GitHub, search free; social tiers need local login).
- **agent-skills (Apify)** `Code` *(optional)* — hosted web scraping via Apify Actors (needs your Apify token).

### H · App-Building & Utilities
- **ai-website-cloner-template** `Code` — point at a URL, rebuild it as clean Next.js.
- **worktrunk** `Code` — parallel git worktrees for running agents side-by-side.
- **vercel-labs-skills** `Code` — the `skills.sh` installer for the open skill ecosystem.

### Video
- Use your own **`video-editing`** skill (distilled from OpenMontage).

## Install

**1 — Make it standalone (once).** This copies each tool's repo into the bundle so it works on any machine:
```
bash build-standalone.sh
```
Populates `./plugins` (installable plugins) and `./tools` (CLIs & templates). ~309 MB (impeccable is the heavy one). Run it once, then the whole folder is self-contained — zip it and share.

**2 — Add & install the plugins** (Claude Code; Cowork via its plugin manager):
```
/plugin marketplace add ./Ultimate-Bundle
/plugin install <name>@claude-power-kit
```

**3 — The `./tools` items install their own way:** `notebooklm-mcp-cli` (pip), `Agent-Reach` (read its `docs/install.md` first — it auto-runs installers), `ai-website-cloner` (fork → `/clone-website`), `tasteskill` · `design.md` · `vercel-labs-skills` (see each README).

## Notes
- Overlapping tools were curated to one spine each, redundant ones dropped — full reasoning in `SCORING.md` (and `RANKING-CLAUDE-CODE.md` for the Code-only view). Not included: official Anthropic (built-in), stocks (parked), and libraries/apps/paid/no-fit tools.
- Each tool is its original author's work, used as-is. Sharing privately with colleagues for now — check each repo's LICENSE before anything public or commercial.
- If you move this folder away from the other repos, update `SRC` at the top of `build-standalone.sh`.
