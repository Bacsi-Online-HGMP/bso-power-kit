# Claude Power Kit

A maintained best-of community skills, plugins & MCPs for Claude — Cowork and Code. Curated with a balanced "useful to me *and* to anyone" rubric; official Anthropic skills, plugins and connectors are intentionally excluded (you already get those built in).

**For** clinicians, researchers, and hands-on builders who want a strong default toolset without wading through 1,800-skill mega-catalogs. Everything here is **free** and runs on almost any computer that can run Claude. Tools marked **`Code`** work only in Claude Code, not Cowork.

**38 plugins** in `.claude-plugin/marketplace.json`. The catalogue is deliberately wider than what you should switch on: entries marked *catalogued* ship with `defaultEnabled: false` because they duplicate another entry or were folded into a house skill. Breadth in the catalogue, restraint in the enabled list.

## What's inside

`◆` = spine of its group · `Code` = Claude Code only · *catalogued* = in the marketplace, off by default.

### A · Research & Academic
- **◆ academic-research-skills** — deep research + writing pipeline (the daily driver).
- **ai-research-skills** — idea → paper suite. Same-sounding name, different domain: this one trains ML models.
- **huggingface-skills** — dataset / model / eval tasks for AI work.
- **idea-validation-agents** — validate a product idea before building it. No API key required.

### B · Codebase Comprehension & Memory
- **◆ socraticode** *(catalogued)* — semantic code search + dependency graph + context.
- **understand-anything** *(catalogued)* — codebase or docs into an explorable knowledge graph. Same job as socraticode; enable one.
- **agentmemory** *(catalogued)* — persistent cross-session memory. Cowork has this built in.

### C · Coding Discipline & Quality
- **◆ superpowers** — dev methodology that auto-fires the right skill.
- **brooks-lint** — code review grounded in 12 engineering classics.
- **andrej-karpathy-skills** — house rules against common LLM-coding pitfalls.
- **verification-before-completion** — evidence before assertions (MIT, Jesse Vincent; rescued from superpowers).
- **ponytail** — terse "one line, it works" style.
- **caveman** `Code` — ~65% fewer output tokens, same answers.
- **mattpocock-skills** *(catalogued)* — 19 TypeScript engineering skills. Its `handoff` skill is packaged standalone below; don't enable the whole set just to get it.

### D · Agent Framework
- **◆ ECC** — the big agent-harness "OS" (agents, commands, hooks, skills, MCP; Vietnamese docs included).

### E · Writing
- **◆ anti-slop** — never asserts authorship; produces artifacts a human can check. Pairs with the Vietnamese `vietnamese-anti-slop` skill in the `bso` marketplace.

`no-ai-slop` and `stop-slop` are **not** vendored here — both ship in the Anthropic skill bundle, and this kit excludes what you already get built in.

### F · Frontend & Visual Polish
- **◆ modern-web-guidance** — modern web best-practices + compatibility (Google Chrome team).
- **threads-carousel** — text into carousel PNG/PDF.
- **impeccable** · **ui-ux-pro-max** · **taste-skill** *(all catalogued)* — three of the four sources merged into the house `bso-design` skill. Kept for provenance, off by default: enabling several competing aesthetic rulebooks at once means the agent picks one at random.

Two cautions carried over from the merge. Use `nextlevelbuilder/ui-ux-pro-max-skill`, not the same-named `WAAMEngineer` fork. And `taste-skill`'s blanket em-dash ban must not be adopted wholesale for regulated supplement copy — formal rules applied to legally load-bearing wording strip the hedges the regulation requires.

### G · Perception
- **◆ watch** — let Claude watch video from YouTube, Instagram, X, Vimeo, TikTok. On-device: no key, no cookie, no telemetry.
- **mcp-video-analyzer** — frame OCR and caching. Stronger than `watch`, but adds an npm dependency.

### Video
- **◆ video-editing** — FFmpeg editing, download, transcribe, motion graphics. AGPL-3.0 (OpenMontage).
- **claude-shorts** — longform to shortform: viral-segment scoring plus Remotion captions.
- **youtube-shorts-pipeline** — niche-driven shorts pipeline.

### H · Content & Trend Research
- **◆ claude-blog** — 32 skill directories behind a 5-Gate Delivery Contract that blocks delivery until checks pass.
- **claude-youtube** — channel audits, video SEO, retention analysis.
- **youtuber** — source-cited Obsidian brain for YouTube creator growth.
- **claude-repurpose** — one source into many channel formats.
- **create-viral-content** — viral content patterns.
- **viral-hooks** — 100 hook formulas as a reference library.
- **last30days-skill** — last-30-days trends across Reddit / HN / X / YouTube / Polymarket.

### I · SEO & Ads
- **◆ claude-seo** — 25 sub-skills for SEO analysis.
- **claude-ads** — paid media for Google, Meta, YouTube. Read-only by default; writes require six conditions (capability on · explicit ID · before/after diff · approval · idempotency + rollback · precondition verify). Worth reading as a safety template even if you never run ads.

### S · Security
- **◆ cybersecurity-defense** — blue-team playbooks: incident response, host forensics, threat hunting, ISO 27001. Apache-2.0.

### U · Utilities
- **handoff** — write a session handoff doc instead of `/compact`.
- **worktrunk** `Code` — parallel git worktrees for running agents side-by-side.

## Registered separately, not vendored

Four repos are marketplaces or frameworks in their own right, and vendoring them would add ~490 MB of someone else's catalogue to this one. Register them directly instead:

| Repo | What it is |
|---|---|
| `sickn33/agentic-awesome-skills` | A 2,000+ skill catalogue. Read it before running it. |
| `wshobson/agents` | A third-party marketplace. |
| `garrytan/gbrain` | Agent infrastructure (OpenClaw / Hermes). |
| `garrytan/gstack` | 23 opinionated role agents (CEO / Designer / QA…). |

## Not vendored, installed by package manager

`puppeteer` (npm) · `simple-icons` (npm) · `diffusionstudio/lottie` (npm) · `supertone-inc/supertonic-py` (pip). These are libraries, not plugins — pinning a copy here would only go stale.

`GoogleCloudPlatform/knowledge-catalog` (OKF) already lives in `bso-marketing/assets/tools/okf/`; it is not duplicated here.

## Install

**1 — Make it standalone (once).** This copies each tool's repo into the bundle so it works on any machine:

```bash
bash build-standalone.sh
```

Populates `./plugins` (installable plugins) and `./tools` (CLIs & templates). Roughly 300 MB. Run it once, then the whole folder is self-contained — zip it and share.

**2 — Add & install the plugins** (Claude Code; Cowork via its plugin manager):

```bash
/plugin marketplace add Bacsi-Online-HGMP/claude-power-kit
/plugin install <name>@claude-power-kit
```

The repo is private and org-owned, so `gh auth status` must show an account with access before Claude can pull the marketplace.

**3 — The `./tools` items install their own way:** `notebooklm-mcp-cli` (pip) · `Agent-Reach` (read its `docs/install.md` first — it auto-runs installers) · `ai-website-cloner` (fork → `/clone-website`) · `agentskills` (skill-authoring spec, read-only) · `agency-agents` (agent definitions, copy what you need) · `design.md` · `vercel-labs-skills` (see each README).

## Notes

- Overlapping tools were curated to one spine each, redundant ones dropped — full reasoning in `SCORING.md` (and `RANKING-CLAUDE-CODE.md` for the Code-only view). Not included: official Anthropic (built-in), stocks (parked), and libraries/apps/paid/no-fit tools.
- **Removed in 0.2.0:** `chrome-devtools-mcp` (Claude in Chrome covers it) · `youtube-video-perception` (superseded by `watch`; also shipped two overlapping copies) · `apify-agent-skills` (the whole scraping group was dropped). The `renames` block in `marketplace.json` maps all three to `null` so machines that already installed them detach cleanly instead of erroring.
- Vendored copies are hard snapshots taken at download time. Upstream updates do not flow in — re-download and commit over the top. That is the accepted price for one stable source.
- Each tool is its original author's work, used as-is. Keep each `LICENSE` and every source attribution inside `SKILL.md` intact. Sharing privately with colleagues for now — check each repo's LICENSE before anything public or commercial.
- If you move this folder away from the other repos, update `SRC` at the top of `build-standalone.sh`.
