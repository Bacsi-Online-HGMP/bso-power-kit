# Ultimate Sharable Bundle — Repo Scoring (one-by-one)

Working scorecard. The polished manual (the bundle's README) comes at the end, once we decide the mesh/keep set.

**Scope:** the 56 repos in `Turn these to skill bundles/`. Excludes official Anthropic (Harold's rule).
**Weighting:** balanced — your fit and general usefulness count equally.

## Rubric (each dimension 0–5)

| Dim | Meaning | Weight |
|---|---|---|
| **Fit** | Serves a real thread of yours: clinical/research · fertility education+content · app-learning · local-LM · marketing/comms | ×2 |
| **Gen** | Useful to any Cowork/Code user (general audience) | ×2 |
| **Cow** | Works in Cowork now (5) / Code-only skill (2–3) / not an installable skill at all (0) | ×2 |
| **Uniq** | Unique idea → keep as-is (5) vs overlaps a better tool → mesh/drop (0–3) | ×2 |
| **Free** | Free + runs on CPU-only Intel Mac (paid or GPU-only caps it) | ×2 |
| **Qual** | Real, maintained, effective (not a toy/demo/bare library) | ×1 |
| **Shr** | License permits sharing + broadly giftable | ×1 |

Total = 2(Fit+Gen+Cow+Uniq+Free) + Qual + Shr, max 60, normalized to /100.
Buckets: **CORE** (keep as-is) · **CODE-ONLY** (keep, label — no-op/limited in Cowork) · **MESH** (fold into a bigger sibling) · **REFERENCE** (on-disk study only) · **WATCH** (pending your call) · **CUT** · **EXCLUDED** (official Anthropic).

---

## Ranked scorecard

| # | Repo | Fit | Gen | Cow | Uniq | Free | Qual | Shr | **Total** | Bucket |
|---|---|:--:|:--:|:--:|:--:|:--:|:--:|:--:|:--:|---|
| 1 | Understand-Anything | 4 | 5 | 5 | 4 | 5 | 4 | 5 | **92** | CORE |
| 2 | chrome-devtools-mcp | 3 | 5 | 5 | 4 | 5 | 5 | 5 | **90** | CORE |
| 3 | AI-Research-SKILLs | 5 | 4 | 4 | 4 | 5 | 4 | 5 | **88** | CORE |
| 4 | academic-research-skills | 5 | 4 | 4 | 4 | 5 | 5 | 3 | **87** | CORE |
| 5 | agent-skills (Addy Osmani) | 3 | 5 | 4 | 4 | 5 | 5 | 5 | **87** | CORE |
| 6 | modern-web-guidance | 3 | 5 | 4 | 4 | 5 | 5 | 5 | **87** | CORE |
| 7 | superpowers | 3 | 5 | 4 | 4 | 5 | 5 | 4 | **85** | CORE |
| 8 | agentmemory | 3 | 5 | 5 | 3 | 5 | 4 | 4 | **83** | CORE* |
| 9 | brooks-lint | 3 | 5 | 4 | 4 | 5 | 4 | 4 | **83** | CORE |
| 10 | tasteskill | 3 | 5 | 4 | 4 | 5 | 4 | 4 | **83** | CORE* |
| 11 | impeccable | 3 | 5 | 3 | 4 | 5 | 5 | 4 | **82** | CORE* |
| 12 | ECC | 3 | 5 | 3 | 4 | 5 | 4 | 4 | **80** | CORE (mesh-hub) |
| 13 | notebooklm-mcp-cli | 5 | 4 | 2 | 5 | 4 | 4 | 4 | **80** | CODE-ONLY |
| 14 | SocratiCode | 3 | 4 | 5 | 3 | 5 | 4 | 3 | **78** | CORE* (AGPL) |
| 15 | ponytail | 3 | 4 | 4 | 3 | 5 | 4 | 4 | **77** | CORE* |
| 16 | last30days-skill | 3 | 4 | 4 | 4 | 4 | 4 | 4 | **77** | CORE* |
| 17 | agents (wshobson) | 3 | 5 | 3 | 3 | 5 | 4 | 4 | **77** | CORE (mesh-hub) |
| 18 | design.md | 3 | 4 | 3 | 4 | 5 | 4 | 4 | **77** | CORE* |
| 19 | andrej-karpathy-skills | 3 | 4 | 4 | 3 | 5 | 3 | 4 | **75** | CORE* |
| 20 | huggingface-skills | 3 | 4 | 4 | 3 | 4 | 4 | 4 | **73** | CORE |
| 21 | mattpocock-skills | 2 | 4 | 4 | 3 | 5 | 4 | 4 | **73** | CORE* |
| 22 | gsd-core-next | 2 | 5 | 3 | 3 | 5 | 4 | 4 | **73** | MESH (frameworks) |
| 23 | ai-website-cloner-template | 3 | 4 | 2 | 4 | 4 | 4 | 4 | **70** | CODE-ONLY |
| 24 | harness | 2 | 4 | 3 | 3 | 5 | 4 | 4 | **70** | MESH (orchestration) |
| 25 | codebase-memory-mcp | 2 | 4 | 3 | 3 | 5 | 4 | 4 | **70** | MESH→likely CUT (redundant) |
| 26 | ai-devkit | 2 | 4 | 2 | 3 | 5 | 4 | 4 | **67** | CODE-ONLY (mesh) |
| 27 | vercel-labs-skills | 2 | 4 | 2 | 3 | 5 | 4 | 4 | **67** | CODE-ONLY (skill installer) |
| 28 | caveman | 2 | 4 | 1 | 4 | 5 | 4 | 4 | **67** | CODE-ONLY |
| 29 | antigravity-awesome-skills | 2 | 5 | 3 | 2 | 5 | 3 | 3 | **67** | REFERENCE (browse, 1894 skills) |
| 30 | Agent-Reach | 3 | 4 | 1 | 4 | 3 | 4 | 4 | **63** | CODE-ONLY |
| 31 | headroom | 2 | 4 | 2 | 3 | 4 | 4 | 4 | **63** | CODE-ONLY (mesh w/ caveman) |
| 32 | agent-skills (Apify) | 2 | 4 | 3 | 3 | 3 | 4 | 4 | **63** | CODE-ONLY (scraping) |
| 33 | worktrunk | 2 | 4 | 2 | 3 | 4 | 4 | 4 | **63** | CODE-ONLY |
| 34 | claude-code-best-practice | 2 | 4 | 2 | 2 | 5 | 3 | 4 | **62** | REFERENCE (docs) |
| 35 | cognee | 2 | 4 | 2 | 3 | 3 | 4 | 4 | **60** | CUT (heavy, redundant) |
| 36 | lottie (text-to-lottie) | 2 | 3 | 3 | 3 | 4 | 3 | 3 | **60** | CUT (niche) |
| 37 | ai-engineering-from-scratch | 2 | 4 | 1 | 3 | 3 | 4 | 4 | **57** | REFERENCE (503-lesson course) |
| 38 | cc-skills-golang | 0 | 3 | 3 | 2 | 5 | 4 | 4 | **57** | CUT (Go-only, no fit) |
| 39 | Anthropic-Cybersecurity-Skills | 1 | 3 | 3 | 2 | 5 | 3 | 2 | **55** | CUT (dual-use; defense subset already extracted) |
| 40 | simple-icons | 1 | 3 | 1 | 2 | 5 | 5 | 4 | **55** | CUT (asset library) |
| 41 | last30days-skill-cn | 2 | 3 | 2 | 3 | 3 | 3 | 3 | **53** | CODE-ONLY (China-only, scraping) |
| 42 | UZI-Skill | 0 | 2 | 3 | 3 | 4 | 4 | 4 | **53** | WATCH (stocks) |
| 43 | sia | 2 | 3 | 1 | 4 | 2 | 4 | 4 | **53** | REFERENCE (GPU research code) |
| 44 | agency-agents | 0 | 3 | 2 | 2 | 5 | 3 | 4 | **52** | CUT (no clinical fit — full-repo checked) |
| 45 | puppeteer | 1 | 3 | 1 | 1 | 5 | 5 | 4 | **52** | CUT (library → chrome-devtools wins) |
| 46 | agents-cli (Google) | 1 | 3 | 2 | 2 | 3 | 4 | 4 | **50** | CUT (Gemini-platform-locked) |
| 47 | healthcare (adrianhajdin app) | 2 | 2 | 1 | 2 | 5 | 3 | 3 | **50** | CUT (Next.js tutorial app, not a skill) |
| 48 | daily_stock_analysis | 0 | 2 | 2 | 3 | 3 | 4 | 4 | **47** | WATCH (stocks) |
| 49 | iOS-OCR-Server | 1 | 2 | 0 | 3 | 2 | 4 | 2 | **37** | CUT (native iPhone app) |
| 50 | lottie-react-native | 0 | 1 | 0 | 0 | 5 | 4 | 2 | **30** | CUT (JS library) |
| 51 | lottie-web | 0 | 0 | 0 | 0 | 5 | 4 | 1 | **27** | CUT (JS library) |
| — | claude-supermemory | 3 | 4 | 4 | 3 | **0** | 4 | 3 | gated | CUT (requires paid Supermemory Pro) |
| — | anthropic-skills | — | — | — | — | — | — | — | — | EXCLUDED (official Anthropic) |
| — | claude-code | — | — | — | — | — | — | — | — | EXCLUDED (official Anthropic) |
| — | healthcare (anthropics/healthcare) | — | — | — | — | — | — | — | — | EXCLUDED (official Anthropic — but core to *your own* use) |
| — | OpenMontage | 5 | 4 | 3 | 4 | 4 | 4 | 4 | (80) | REFERENCE — you already distilled your own `video-editing` skill from it; keep source, don't re-bundle |

\* CORE items already installed/active in your environment.

**Tally:** 56 total = CORE 21 · CODE-ONLY 10 · MESH 3 · REFERENCE 5 · WATCH 2 · CUT 12 · EXCLUDED 3.

---

## Big-overlap clusters (principle 2 — mesh smaller into bigger)

1. **Agent frameworks / mega-collections** — ECC · agents (wshobson) · gsd-core · harness · ai-devkit. ECC is the largest → mesh target; others fold in or stay as alternatives.
2. **Coding-discipline skills** — agent-skills (Addy) · superpowers · andrej-karpathy-skills · ponytail · brooks-lint · caveman. Pick a spine (agent-skills or superpowers), mesh the small rule-packs in.
3. **Codebase comprehension** — Understand-Anything · SocratiCode · codebase-memory-mcp. UA + SocratiCode both strong; codebase-memory is redundant.
4. **Memory** — agentmemory · cognee · supermemory · codebase-memory · (Pensyve already active). Keep one free local one (agentmemory) — the rest CUT/redundant.
5. **Visual / frontend polish** — impeccable · tasteskill · design.md · modern-web-guidance. Your old "make-it-look-good" module — mesh into one.
6. **Content / trend research** — last30days · last30days-cn · Agent-Reach. Overlap; last30days works partly in Cowork, the other two are Code-only.
7. **Browser automation** — chrome-devtools-mcp beats puppeteer for agents.
8. **Token compression** — caveman (light) vs headroom (heavy). Both Code-only.
9. **Research writing** — AI-Research-SKILLs vs academic-research-skills. Overlap (idea→paper); ARS is CC BY-NC (non-commercial) — matters for a sharable bundle.

## Flags for your call

- **healthcare (anthropics/healthcare)** — excluded by your "no official Anthropic" rule, yet it's the spine of your clinical work. It stays in *your* setup; just not part of a *community* sharable bundle.
- **Stocks (UZI-Skill, daily_stock_analysis)** — parked on WATCH. No evidence stocks are a real thread for you. Say the word and they move to CUT or get their own evaluation.
- **License caveats for sharing** — academic-research-skills = CC BY-NC (non-commercial), SocratiCode = AGPL-3.0 (copyleft). Fine to share, but flag before packaging.
