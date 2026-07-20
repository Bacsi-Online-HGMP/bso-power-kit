# Claude Code-only Ranking

Same rubric and same six other dimensions as `SCORING.md` — only the **Cow** dimension is reinterpreted as **Code fit** (does it work well *in Claude Code*). Nearly every repo here is Claude-Code-native, so the Cowork penalty lifts and the **CODE-ONLY bucket collapses** — in a Code frame those tools are first-class.

Δ = change vs the balanced (Cowork-inclusive) total in `SCORING.md`.

| Repo | Code fit | **Total** | Δ | Bucket |
|---|:--:|:--:|:--:|---|
| AI-Research-SKILLs | 5 | **92** | +4 | CORE |
| Understand-Anything | 5 | **92** | 0 | CORE |
| chrome-devtools-mcp | 5 | **90** | 0 | CORE |
| academic-research-skills | 5 | **90** | +3 | CORE |
| agent-skills (Addy Osmani) | 5 | **90** | +3 | CORE |
| modern-web-guidance | 5 | **90** | +3 | CORE |
| notebooklm-mcp-cli | 5 | **90** | **+10** | CORE |
| superpowers | 5 | **88** | +3 | CORE |
| impeccable | 5 | **88** | +6 | CORE |
| brooks-lint | 5 | **87** | +4 | CORE |
| tasteskill | 5 | **87** | +4 | CORE |
| ECC | 5 | **87** | +7 | CORE (mesh-hub) |
| agentmemory | 5 | **83** | 0 | CORE |
| agents (wshobson) | 5 | **83** | +6 | CORE (mesh-hub) |
| design.md | 5 | **83** | +6 | CORE |
| caveman | 5 | **80** | **+13** | CORE |
| ponytail | 5 | **80** | +3 | CORE |
| last30days-skill | 5 | **80** | +3 | CORE |
| ai-website-cloner-template | 5 | **80** | +10 | CORE |
| gsd-core-next | 5 | **80** | +7 | MESH (frameworks) |
| SocratiCode | 5 | **78** | 0 | CORE |
| andrej-karpathy-skills | 5 | **78** | +3 | CORE |
| Agent-Reach | 5 | **77** | **+14** | CORE |
| huggingface-skills | 5 | **77** | +4 | CORE |
| mattpocock-skills | 5 | **77** | +4 | CORE |
| vercel-labs-skills | 5 | **77** | +10 | CORE (skill tooling) |
| harness | 5 | **77** | +7 | MESH (orchestration) |
| ai-devkit | 5 | **77** | +10 | MESH (frameworks) |
| codebase-memory-mcp | 5 | **77** | +7 | MESH → drop (redundant) |
| worktrunk | 5 | **73** | +10 | CORE (git util) |
| headroom | 5 | **73** | +10 | MESH (compression → caveman) |
| agent-skills (Apify) | 5 | **70** | +7 | CORE (scraping) |
| antigravity-awesome-skills | 4 | **70** | +3 | REFERENCE (browse, 1894 skills) |
| cognee | 4 | **67** | +7 | CUT (heavy, redundant) |
| claude-code-best-practice | 3 | **65** | +3 | REFERENCE (docs) |
| lottie (text-to-lottie) | 4 | **63** | +3 | OPTIONAL (niche) |
| cc-skills-golang | 5 | **63** | +6 | CUT (Go-only, no fit) |
| last30days-skill-cn | 5 | **63** | +10 | OPTIONAL (China only) |
| Anthropic-Cybersecurity-Skills | 5 | **62** | +7 | CUT (dual-use; defense subset extracted) |
| ai-engineering-from-scratch | 2 | **60** | +3 | REFERENCE (503-lesson course) |
| UZI-Skill | 5 | **60** | +7 | WATCH (stocks) |
| sia | 3 | **60** | +7 | REFERENCE (GPU research) |
| agency-agents | 4 | **58** | +6 | CUT (no fit) |
| agents-cli (Google) | 4 | **57** | +7 | CUT (Gemini-locked) |
| daily_stock_analysis | 5 | **57** | +10 | WATCH (stocks) |
| simple-icons | 1 | **55** | 0 | CUT (asset library) |
| puppeteer | 2 | **55** | +3 | CUT (library → chrome-devtools wins) |
| healthcare (adrianhajdin app) | 2 | **53** | +3 | CUT (tutorial app) |
| iOS-OCR-Server | 0 | **37** | 0 | CUT (iPhone app) |
| lottie-react-native | 1 | **33** | +3 | CUT (library) |
| lottie-web | 1 | **28** | +1 | CUT (library) |
| claude-supermemory | — | gated | — | CUT (requires paid Supermemory Pro) |
| anthropic-skills · claude-code · healthcare (anthropics) | — | — | — | EXCLUDED (official Anthropic) |
| OpenMontage | 5 | (87) | — | REFERENCE — you already built your own `video-editing` from it |

## What changed vs the balanced ranking

The big risers are exactly the tools Cowork penalized for being Code-native:
- **Agent-Reach +14** (63→77), **caveman +13** (67→80), **notebooklm-mcp-cli +10** (80→90), **ai-website-cloner +10**, **ai-devkit +10**, **worktrunk +10**, **headroom +10**, **last30days-cn +10**, **daily_stock +10**.
- In Code, **notebooklm-mcp-cli** joins the top tier (90) — your NotebookLM bridge was only held back by being Code-only.
- The CUT / WATCH / EXCLUDED verdicts don't move: libraries (lottie×3, puppeteer, simple-icons), native apps (iOS-OCR, healthcare tutorial app), paid (supermemory), no-fit (Go, Gemini, agency-agents), stocks, and official Anthropic stay where they were — environment doesn't change what those *are*.

The mesh clusters are identical to `SCORING.md`; only the scores shift.
