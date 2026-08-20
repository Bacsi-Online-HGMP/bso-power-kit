> **Reference copy.** This is the original, fuller README — full "how it was chosen", per-tool licenses, and the complete mesh rationale. The active bundle README is `README.md` (trimmed). Kept for your reference. Note: the Install section below describes the earlier on-disk layout; the current **standalone** install (via `build-standalone.sh` + `./plugins`) lives in `README.md`.

---

# Claude Power Kit
### A curated, shareable bundle of community skills, plugins & MCPs for Claude Cowork and Claude Code

> Working title — rename freely. Built by curating 56 community repos down to a maintained best-of, using a balanced "useful to me *and* to anyone" rubric. Official Anthropic skills/plugins/connectors are intentionally excluded (you already get those built in).

**Who it's for:** clinicians, researchers, and hands-on builders who want a strong default toolset without wading through 1,800-skill mega-catalogs. Everything here is **free** and runs on a **CPU-only Mac**. Tools that only work in Claude Code (not Cowork) are labelled **`Code`**.

**How it was chosen:** every repo was scored 0–100 on Fit · General-use · Cowork-ready · Uniqueness · Free+CPU · Quality · Shareability. See `SCORING.md` (balanced) and `RANKING-CLAUDE-CODE.md` (Code-only). Overlapping tools were meshed by **curation, not code-fusion** — pick a spine, keep genuinely-distinct siblings alongside, drop the redundant. Nobody's repo was rewritten (respecting each creator's work).

---

## What's inside (the keep-set)

`◆` = **spine** of its group · `Code` = Claude Code only · licenses noted where confirmed, else "see repo".

### A · Research & Academic
- **◆ AI-Research-SKILLs** — idea → paper research skill suite. *MIT.*
- **academic-research-skills** — deep research + writing pipeline (the daily driver). *CC BY-NC 4.0 — non-commercial; fine to share, not to sell.*
- **huggingface-skills** — dataset / model / eval tasks for AI work. *see repo.*
- **notebooklm-mcp-cli** `Code` — bridge to Google NotebookLM for grounded RAG. *see repo.*

### B · Codebase Comprehension & Memory
- **◆ Understand-Anything** — turn any codebase/docs into an explorable knowledge graph. *see repo.*
- **SocratiCode** — semantic code search + dependency graph + context. *AGPL-3.0 — copyleft; keep the licence with it.*
- **agentmemory** — persistent cross-session memory. *see repo.* (Pensyve already covers this in your Cowork — pick one.)

### C · Coding Discipline & Quality
- **◆ superpowers** — full dev methodology that auto-fires the right skill. *see repo.*
- **brooks-lint** — code review grounded in 12 engineering classics. *see repo.*
- **andrej-karpathy-skills** — 4 house rules against common LLM-coding pitfalls. *see repo.*
- **ponytail** — "say nothing, write one line, it works" terseness. *see repo.*
- **mattpocock-skills** — TypeScript engineering skills. *see repo.*
- **caveman** `Code` — ~65% fewer output tokens, same answers. *see repo.*

### D · Agent Framework
- **◆ ECC** — the big agent-harness "OS" (agents, commands, hooks, skills, MCP; has Vietnamese docs). The mesh-hub the other frameworks fold into. *see repo.*

### E · Frontend & Visual Polish
- **◆ impeccable** — design guidance + 45 anti-slop detectors + live browser iteration. *see repo.*
- **tasteskill** — anti-slop premium frontend skills. *see repo.*
- **design.md** — a format spec for handing a visual identity to agents. *see repo.*
- **modern-web-guidance** — modern web best-practices + compatibility (Google Chrome team). *see repo.*

### F · Browser & Web
- **◆ chrome-devtools-mcp** — let the agent control & inspect a live Chrome. *Apache-2.0 (see repo).*

### G · Content & Trend Research
- **◆ last30days-skill** — last-30-days trends across Reddit / HN / X / YouTube / Polymarket. *see repo.*
- **Agent-Reach** `Code` — broad internet reach for agents (YouTube, RSS, GitHub, search free; social tiers need local login). *MIT.*
- **agent-skills (Apify)** `Code` *(optional)* — hosted web scraping via Apify Actors (needs your Apify token). *see repo.*

### H · App-Building & Dev Utilities
- **ai-website-cloner-template** `Code` — point at a URL, rebuild it as clean Next.js. *MIT.*
- **worktrunk** `Code` — parallel git worktrees for running agents side-by-side. *MIT OR Apache-2.0.*
- **vercel-labs-skills** `Code` — the `skills.sh` installer for the open skill ecosystem. *see repo.*

### Video
- Use **your own `video-editing` skill** (distilled from OpenMontage). It supersedes the OpenMontage original — kept on the reference shelf as source, not re-bundled.

**Keep-set total: ~25 tools** across 8 groups (1 optional).

---

## Install

Two ways, both free:

**1 — One bundle (Claude Code).** This folder ships a plugin marketplace pointing at the repos already on your disk under `../Turn these to skill bundles/`:
```
/plugin marketplace add ./Ultimate-Bundle
/plugin install <name>@bso-power-kit
```
(See `.claude-plugin/marketplace.json`. If a source path doesn't resolve, adjust the relative path to match where the repo folder sits.)

**2 — The Code-only CLIs / templates** (not plugins — install per their repos):
- `notebooklm-mcp-cli` → `pip install notebooklm-mcp-cli`
- `Agent-Reach` → read `Turn these to skill bundles/Agent-Reach-main/docs/install.md` first, then its `pipx`/venv install (it auto-runs installers — review before running).
- `ai-website-cloner-template` → fork the template, run `/clone-website` in Claude Code.
- `tasteskill` / `design.md` / `vercel-labs-skills` → see each repo's README.

**Cowork note:** the `Code`-tagged tools do nothing in Cowork (no persistent shell / browser profile). Everything untagged works in both.

---

## Why some overlaps were dropped (mesh decisions)

- **Frameworks:** ECC is the spine; `agents (wshobson)`, `gsd-core`, `harness`, `ai-devkit` are redundant mega-layers → reference shelf.
- **Discipline:** `superpowers` is the spine; `agent-skills (Addy Osmani)` is an excellent runner-up → reference. karpathy/ponytail/brooks stay (distinct angles).
- **Comprehension:** kept Understand-Anything + SocratiCode (graph vs search — complementary); dropped `codebase-memory-mcp` (redundant).
- **Memory:** one system only (agentmemory / Pensyve); `cognee`, `supermemory` (paid), `codebase-memory` dropped.
- **Browser:** chrome-devtools-mcp beats `puppeteer` (a library) for agents.
- **Compression:** caveman (light) over `headroom` (heavy).
- **Research writing:** AI-Research-SKILLs (MIT) is the shippable spine; academic-research-skills kept alongside but flagged CC BY-NC.

## Reference shelf (kept on disk, not shipped active)
`antigravity-awesome-skills` (browse 1,894), `ai-engineering-from-scratch` (503-lesson course), `claude-code-best-practice` (docs), `sia` (GPU research), `OpenMontage` (source of your video skill), and the framework/discipline runners-up above.

## Not included
- **Official Anthropic** (your rule): `anthropic-skills`, `claude-code`, `healthcare` — the last is still central to *your own* clinical work, just not part of a community bundle.
- **Parked — stocks:** `UZI-Skill`, `daily_stock_analysis` (no evidence this is a live thread for you).
- **Cut:** libraries not skills (`lottie` ×3, `simple-icons`, `puppeteer`), native apps (`iOS-OCR-Server`, the Next.js healthcare tutorial), paid (`claude-supermemory`), no-fit (`cc-skills-golang`, `agency-agents`, Google `agents-cli`), and dual-use (`Anthropic-Cybersecurity-Skills` — your hardened defense subset already lives separately).

## Credits & licences
Every tool is the work of its original author, used as-is. Before sharing publicly, keep each repo's LICENSE and attribution intact. Flagged licences to respect: **academic-research-skills** = CC BY-NC (non-commercial), **SocratiCode** = AGPL-3.0 (copyleft). Confirm the "see repo" licences against each repo's LICENSE file before redistribution.
