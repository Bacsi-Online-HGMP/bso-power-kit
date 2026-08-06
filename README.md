# Claude Power Kit

Community skills, plugins and MCPs for Claude — Cowork and Code — kept down to the ones that survived scoring. Official Anthropic skills, plugins and connectors are deliberately absent: you already get those built in.

**For** clinicians, researchers, and hands-on builders who want a strong default toolset without wading through 1,800-skill mega-catalogs. Everything here is free and runs on almost any machine that can run Claude. Tools marked **`Code`** work only in Claude Code, not Cowork.

**31 plugins.** Every entry earned its place against a 9-axis rubric; the reasoning lives in `SCORING.md`, `RANKING-CLAUDE-CODE.md`, and `bootstrap-device/scoring-layer-2.md`. Rejections are recorded in `bootstrap-device/plugins-loai.tsv` so nobody re-litigates them from scratch.

## What's inside

`◆` = spine of its group · `Code` = Claude Code only · *catalogued* = shipped with `defaultEnabled: false`.

### A · Research
- **◆ academic-research-skills** — deep research and academic writing pipeline. Heavy: a full run costs roughly $4–6 by its own docs, so reach for a narrow mode (`/ars-outline`, `/ars-3w`) before `/ars-full`.
- **idea-validation-agents** — pressure-test a product idea before building it. No API key.

### C · Coding Discipline & Quality
- **◆ mattpocock-skills** — 19 engineering and productivity skills: grilling, diagnosing-bugs, writing-great-skills, code-review, tdd. Took over as spine when superpowers was dropped.
- **brooks-lint** — code review grounded in 12 engineering classics.
- **andrej-karpathy-skills** — house rules against common LLM-coding pitfalls.
- **verification-before-completion** — evidence before assertions. Split out of superpowers and kept when the rest of that plugin went (MIT, Jesse Vincent).
- **ponytail** — terse "one line, it works" style.
- **caveman** `Code` — ~65% fewer output tokens, same answers.

`ponytail` and `caveman` overlap only at the edges — one targets output length, the other code style — so both stay on.

### E · Writing
- **◆ anti-slop** — never asserts who wrote a draft; produces artifacts a human can check instead. Pairs with the Vietnamese `vietnamese-anti-slop` skill in the `bso` marketplace.

`no-ai-slop` and `stop-slop` are not vendored: both ship in the Anthropic bundle. `stop-slop` is also the wrong tool for regulated copy — it strips every adverb and hedge, and those hedges are a legal requirement for Vietnamese supplement claims.

### F · Frontend & Visual
- **◆ modern-web-guidance** — modern web best-practices and compatibility (Google Chrome team).
- **threads-carousel** — text into carousel PNG/PDF.
- **impeccable** · **ui-ux-pro-max** · **taste-skill** *(all catalogued)* — three of the four sources merged into the house `bso-design` skill. Kept for provenance, off by default: enable several competing aesthetic rulebooks at once and the agent picks one at random.

Two cautions from that merge. Use `nextlevelbuilder/ui-ux-pro-max-skill`, not the same-named `WAAMEngineer` fork. And do not adopt `taste-skill`'s blanket em-dash ban for supplement copy — formal style rules applied to legally load-bearing wording strip the hedges the regulation requires.

### G · Perception
- **◆ watch** — let Claude watch video from YouTube, Instagram, X, Vimeo, TikTok. On-device: no key, no cookie, no telemetry.
- **mcp-video-analyzer** — frame OCR and caching. Stronger than `watch`, at the cost of an npm dependency.

### V · Video
- **◆ video-editing** — FFmpeg editing, download, transcribe, motion graphics. AGPL-3.0 (OpenMontage).
- **claude-shorts** — longform to shortform: viral-segment scoring plus Remotion captions.
- **youtube-shorts-pipeline** — niche-driven shorts pipeline.

### H · Content & Trend Research
- **◆ claude-blog** — 32 skill directories behind a 5-Gate Delivery Contract that blocks delivery until the checks pass.
- **claude-youtube** — channel audits, video SEO, retention analysis.
- **youtuber** — source-cited Obsidian brain for YouTube creator growth.
- **claude-repurpose** — one source into many channel formats.
- **create-viral-content** — viral content patterns.
- **viral-hooks** — 100 hook formulas as a reference library.
- **last30days-skill** — last-30-days trends across Reddit / HN / X / YouTube / Polymarket.

This group is the most crowded in the kit, and the overlap is not free. Seven tools all generate titles, hooks and CTR-optimised scripts, and none of them knows Vietnamese supplement advertising law. Enable them for a content session, not permanently — every extra tool competing to answer the same prompt is another path for an overreaching claim to reach a draft before compliance review catches it.

### I · SEO & Ads
- **◆ claude-seo** — 25 sub-skills for SEO analysis.
- **claude-ads** — paid media for Google, Meta, YouTube. Read-only by default; a write needs six conditions (capability on · explicit ID · before/after diff · approval · idempotency + rollback · precondition verify). Worth reading as a safety template even if you never run an ad.

### S · Security
- **◆ cybersecurity-defense** — blue-team playbooks: incident response, host forensics, threat hunting, ISO 27001. Apache-2.0.

### U · Utilities
- **handoff** — write a session handoff doc instead of `/compact`.
- **worktrunk** `Code` — parallel git worktrees for running agents side-by-side.

## Dropped, and why

Recorded so the decisions are not made twice. Full reasoning in `bootstrap-device/plugins-loai.tsv`.

| Dropped | Reason |
|---|---|
| `superpowers` | mattpocock-skills covers grilling, diagnosing and writing-skills; `verification-before-completion` was pulled out and kept on its own. |
| `ecc` | `NG`=1 and no usable skill: its verification-loop wants a build and test suite that does not exist here, its security-review duplicates `security-guidance` in 494 lines. |
| `huggingface-skills` | Pulls 19 ML skills, all 19 hit the `PH` floor. Model training is not a job this setup has. |
| `ai-research-skills` | Same-sounding name, different domain — it trains models, it does not help write. Cut at the screening pass. |
| `socraticode` · `understand-anything` | Two tools for one job, and neither is being used. |
| `agentmemory` | Cowork already carries memory per account. |
| `chrome-devtools-mcp` | Claude in Chrome covers it, and it is still reachable from the Anthropic marketplace if needed. |
| `youtube-video-perception` | Superseded by `watch`; it also shipped two overlapping copies. |
| `apify-agent-skills` | The whole scraping group was dropped. |

Every one of these is in the `renames` block of `marketplace.json` mapped to `null`, so a machine that already installed it detaches cleanly instead of erroring.

## Registered separately, not vendored

Four repos are marketplaces or frameworks in their own right. Vendoring them would bolt ~490 MB of someone else's catalogue onto this one, so register them directly instead:

| Repo | What it is |
|---|---|
| `sickn33/agentic-awesome-skills` | A 2,000+ skill catalogue. Read it before running it. |
| `wshobson/agents` | A third-party marketplace. |
| `garrytan/gbrain` | Agent infrastructure (OpenClaw / Hermes). |
| `garrytan/gstack` | 23 opinionated role agents (CEO / Designer / QA…). |

## Installed by package manager, not vendored

`puppeteer` (npm) · `simple-icons` (npm) · `diffusionstudio/lottie` (npm) · `supertone-inc/supertonic-py` (pip). Libraries, not plugins — a pinned copy here would only go stale.

`GoogleCloudPlatform/knowledge-catalog` (OKF) already lives in `bso-marketing/assets/tools/okf/` and is not duplicated.

## Install

**1 — Make it standalone (once).** Copies each tool's repo into the bundle so the folder works on any machine:

```bash
bash build-standalone.sh
```

Populates `./plugins` (installable plugins) and `./tools` (CLIs and templates). Run it once, then zip and share.

**2 — Add the marketplace and install** (Claude Code; Cowork via its plugin manager):

```bash
/plugin marketplace add Bacsi-Online-HGMP/claude-power-kit
/plugin install <name>@claude-power-kit
```

The repo is private and org-owned, so `gh auth status` must show an account with access before Claude can pull the marketplace. Background auto-update drops the git credential helper on HTTPS, so either set `CLAUDE_CODE_PLUGIN_KEEP_MARKETPLACE_ON_FAILURE=1`, use an SSH remote with a loaded key, or just run `claude plugin marketplace update claude-power-kit` by hand.

**3 — `./tools` items install their own way:** `notebooklm-mcp-cli` (pip) · `Agent-Reach` (read its `docs/install.md` first — it auto-runs installers) · `ai-website-cloner` (fork → `/clone-website`) · `agentskills` (skill-authoring spec, read-only) · `agency-agents` (agent definitions, copy what you need) · `design.md` · `vercel-labs-skills` (see each README).

## Notes

- Breadth in the catalogue, restraint in what you switch on. Every enabled plugin is another set of skills the agent can pick from, and a wrong pick is more expensive than a missing tool.
- Vendored copies are hard snapshots taken at download time. Upstream changes do not flow in — re-download and commit over the top. That is the price paid for one stable source.
- Each tool is its original author's work, used as-is. Keep every `LICENSE` file and every source attribution inside `SKILL.md` intact. Shared privately for now — check each repo's licence before anything public or commercial.
- If you move this folder away from the other repos, update `SRC` at the top of `build-standalone.sh`.
