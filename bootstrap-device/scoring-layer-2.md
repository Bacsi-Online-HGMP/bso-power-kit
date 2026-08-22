# Scoring — Layer 2 (Claude Code plugins)

Scoring the 81 Layer-2 plugins against the 9-axis rubric in
`bso-marketing/docs/rubric-danh-gia-cong-cu.md`. Dated 2026-08-06. The results produce
`plugins-claude-code.tsv` (what gets installed) and `plugins-loai.tsv` (what was rejected, with the
reason kept).

> **Language note.** The axis codes (`PH`, `CP`, `AT`, `FR`, `ĐL`, `VH`, `NG`, `PB`, `TR`) and the pack
> names (`core`, `code`, `seo`, `vanphong`) are kept verbatim — the axes are the scoring-table headers
> shared across documents, and the pack names are literal values in the TSV files.

## Why this pass was necessary

The `pack` column assigned on 2026-08-05 was **a hand classification, not a score**. 62 entries were
marked `bo` (dropped) by feel, and not one of them went through the cut rule.

Worse: this repo's `SCORING.md` **deliberately excluded anything official from Anthropic** ("Harold's
rule" — built-in things need no scoring). So the 58 plugins from `anthropics/claude-plugins-official`
had never been scored by any rubric. This is **a first scoring, not a re-scoring**.

## A hole in the rubric that had to be patched before scoring was possible

The 58 first-party Anthropic plugins take a 5 almost automatically on `AT FR ĐL VH PB`. `csharp-lsp`
comes out at **40 points = tier S** even though BSO does not write a single line of C#. The old cut
rule only bit from tier B downward, so it never touched it.

Patched with **a hard floor: `PH` = 1 → rejected outright, independent of tier** (and `PB` = 1 →
rejected outright). The full reasoning is recorded in the rubric. In exchange, every `PH` = 1 below
**carries a one-line reason** — that was the condition the rubric set when it accepted the hard floor.

## Two different rejection rules — do not confuse them

| Rule | Where | What it examines |
|---|---|---|
| **The cut rule** | The rubric, section *Cut rule* | The quality of **one** entry: the `PH`/`PB` floors, tier, low-score flags |
| **The duplication rule** | `bso-marketing/assets/workspace-root/files/CLAUDE.md` — *heavy overlap, enable one* | The relationship between **two** entries |

The `TR` axis **is not used in the cut rule** — the rubric says so explicitly. So the 5 entries below
rejected for duplication were rejected under the *duplication rule*, not the cut rule. Their scores
remain high.

## Kept — 16 plugins, scored on all 9 axes

The score column runs `PH CP AT FR ĐL VH NG PB`, then `TR`.

| Plugin | Source | Pack | PH CP AT FR ĐL VH NG PB | TR | Total | Tier | Notes |
|---|---|---|---|:--:|:--:|:--:|---|
| `claude-md-management` | official | core | 5 5 5 5 5 5 5 5 | 5 | **45** | S | Four tiers of CLAUDE.md (root · marketing · core · assets) — exactly the job |
| `plugin-dev` | official | core | 5 5 5 5 5 5 5 5 | 5 | **45** | S | BSO runs two marketplaces of its own. Nothing replaces it |
| `skill-creator` | official | core | 5 5 5 5 5 5 5 5 | 4 | **44** | S | Slight overlap with the Cowork bundle copy — different layers, enable both |
| `commit-commands` | official | core | 4 5 5 5 5 5 5 5 | 4 | **43** | S | Daily commits across two repos |
| `pyright-lsp` | official | code | 4 5 5 5 5 5 4 5 | 5 | **43** | S | The video pipeline and `okf.py` are both Python |
| `security-guidance` | official | core | 3 5 5 5 5 5 5 5 | 4 | **42** | S | "Never commit a secret" is a house rule — a machine layer helping is welcome |
| `hookify` | official | core | 3 5 4 5 5 5 5 5 | 5 | **42** | S | A hook running `okf check` before a push |
| `desktop-commander` | official | core | 5 5 3 5 5 5 4 5 | 4 | **41** | S | **IN USE.** `AT`=3: it runs arbitrary shell on the real machine, a very wide permission |
| `code-review` | official | code | 3 5 5 5 5 5 5 5 | 3 | **41** | S | `TR`=3 against brooks-lint and mattpocock — light overlap, enable both |
| `caveman` | caveman | vanphong | 3 4 4 5 4 5 5 5 | 5 | **40** | S | 96k stars, pushed 04-08. Reduces output tokens; **never used for product-facing copy** |
| `ponytail` | ponytail | vanphong | 3 5 5 5 4 5 5 5 | 3 | **40** | S | 96.5k stars, pushed 15-07. Concise code style |
| `github` | official | code | 4 5 4 5 5 5 4 5 | 3 | **40** | S | `TR`=3: the `gh` CLI already does most of it |
| `andrej-karpathy-skills` | karpathy-skills | code | 4 5 2 5 5 5 5 4 | 4 | **39** | S | 🟠 **`AT`=2** — see the warning below |
| `chrome-devtools-mcp` | official | seo | 4 5 4 5 5 5 3 5 | 2 | **38** | S | Overlaps three ways — see *the duplication rule* |
| `superpowers` | official | code | 4 5 5 5 5 4 2 5 | 3 | **38** | S | `NG`=2: 14 self-triggering skills. The heaviest of the kept set |
| `ecc` | ecc | code | 2 4 3 5 4 4 1 5 | 3 | **31** | A | 238k stars. `NG`=1 — a full agent OS. Keep it in the store, **consider not enabling it** |

### 🟠 `andrej-karpathy-skills` — the repo changed hands

The source in the TSV reads `forrestchang/andrej-karpathy-skills`. The GitHub API returns
**`multica-ai/andrej-karpathy-skills`** — the repo has moved, and the old path still works through a
redirect. The repo **has no licence**, and was last pushed 2026-04-20.

Under the rubric, "an author who looks like an impersonating fork" is a low-`AT` signal; changing
hands plus losing the licence lands in that same box. The total is 39, so the cut rule cannot catch it
— **this is a human decision, not the rubric's.** Two routes: fix the source to `multica-ai/...` and
pin a commit, or drop it and keep the rules in an in-house skill. Undecided, and the source has not
been changed.

### `ecc` — keep it in the store, do not enable it yet

`NG`=1 is the heaviest score in the kept set: ECC is a full agent harness (agents + commands + hooks +
skills + MCP). Under the *generous store, tight enable list* rule it belongs in the TSV, but in the
`code` pack, installed only when there is a real need.

## Rejected under the duplication rule — 5 plugins, still scoring well

Nothing here is poor. They were rejected because **something else in the same domain fits BSO better**.

| Plugin | Score | Lost to | Why the other one wins |
|---|:--:|---|---|
| `frontend-design` | 39 (S) | `bso-design` | It carries the BSO identity; `bso-design` already merges four sources |
| `claude-code-setup` | 41 (S) | `bootstrap-device` | The in-house installer has the `pack` column and understands the three plugin layers |
| `playwright` | 38 (S) | `chrome-devtools-mcp` | Both drive a browser; DevTools can also read the console and the network |
| `remember` | 37 (A) | Cowork's memory | Memory already exists per account; a second layer is unnecessary |
| `huggingface-skills` *(the official copy)* | 35 (A) | — | It drags in 19 ML skills; all 19 are rejected by the `PH` floor below |

`chrome-devtools-mcp` overlaps **three** ways: the official copy (kept), the copy in the
`bso-power-kit` marketplace, and Claude-in-Chrome in Cowork. Enable **one** — the official copy,
because it travels with Claude Code and needs no build-standalone.

## Rejected by the hard `PH` = 1 floor — 44 plugins

Each row carries a reason, exactly as the rubric required when it accepted the hard floor.

| Plugin | Reason for `PH` = 1 |
|---|---|
| `csharp-lsp` · `jdtls-lsp` · `php-lsp` · `clangd-lsp` · `typescript-lsp` | BSO does not write C#, Java, PHP, C/C++ or TypeScript |
| `auth0` · `firebase` · `supabase` · `vercel` · `expo` | Web/mobile application infrastructure — BSO has no software product |
| `coderabbit` · `greptile` | Paid SaaS code review, duplicating the free `code-review` |
| `circleback` · `mintlify` · `datarobot-agent-skills` · `dataverse` · `fiftyone` | Out-of-domain SaaS: meetings, docs, AutoML, Microsoft CRM, vision datasets |
| `discord` · `telegram` · `imessage` · `fakechat` | Chat channels that are not BSO's (YouTube · Facebook · Zalo) |
| `data` · `data-engineering` | Data warehousing and ETL — BSO has neither |
| `agent-sdk-dev` · `atomic-agents` · `mcp-server-dev` · `mcp-tunnels` · `mcp-apps` | Building agents/MCP to sell or publish; BSO only consumes them |
| `microsoft-docs` | Looking up Microsoft documentation — touches no part of the work |
| `math-olympiad` | Competition mathematics — entirely the wrong domain |
| `playground` · `ralph-loop` | Agent-loop experiments, attached to no live work |
| `firecrawl` | Scraping requiring a paid key; the rubric also flags ToS risk in section 2 |
| The 19 `huggingface-skills` plugins | Training and deploying ML models: `hf-cli` · `hf-mem` · `huggingface-best` · `huggingface-community-evals` · `huggingface-datasets` · `huggingface-gradio` · `huggingface-llm-trainer` · `huggingface-local-models` · `huggingface-lora-space-builder` · `huggingface-paper-publisher` · `huggingface-papers` · `huggingface-spaces` · `huggingface-tool-builder` · `huggingface-trackio` · `huggingface-vision-trainer` · `huggingface-zerogpu` · `train-sentence-transformers` · `transformers-js` · `trl-training`. BSO uses models through an API and trains nothing |

## Rejected by the ordinary cut rule — 6 plugins

They do not hit the `PH` floor, but land in tier B with a flag, or at `PH` = 2 with no real work for
them.

| Plugin | PH | Why |
|---|:--:|---|
| `pr-review-toolkit` | 2 | BSO pushes straight to `main` and has no PR flow — `CLAUDE.md` says plainly "there is still no gate on `main`" |
| `code-modernization` | 2 | There is no legacy codebase to modernise; the two video pipelines run fine |
| `feature-dev` | 2 | BSO does not develop software features |
| `code-simplifier` | 2 | Duplicates `code-review`, and BSO's code is short scripts |
| `session-report` | 2 | The hand-written `HANDOFF-*.md` already does this job and fits the context better |
| `explanatory-output-style` · `learning-output-style` · `ai-plugins` | 2 | They change Claude's output register and touch no production work |

## Ideas to absorb — `harvest` from what was rejected

Exactly the third cell of the `harvest` table in the rubric: **do not install, read and take the idea**.

| Source | The idea to take |
|---|---|
| `session-report` | The structure of the sections it produces — compare against `HANDOFF-*.md` to see what is missing |
| `pr-review-toolkit` | Its pre-merge checklist — use it as a manual checklist for `core/claims-matrix/`, where pushing straight to `main` is a real risk |
| `firecrawl` | How it separates the main content from the page furniture — useful if a decree-reading step is ever written in-house |
| `caveman` | Already installed. Its "drop the connectives, keep the nouns" principle is worth re-examining in `vietnamese-anti-slop` |

## The 2026-08-06 pass, session two — four decisions revised

### `chrome-devtools-mcp` is kept, and moves from pack `web` → `seo`

It was nearly rejected on the assumption that Claude in Chrome covered it. **Checking
`~/.claude/plugins/installed_plugins.json` shows Claude Code does not have Claude in Chrome** — Claude
in Chrome is Layer 3, tied to the account, and lives only in Cowork/Desktop. Dropping this would leave
Claude Code entirely blind to the browser.

And it does not fully duplicate it even in Cowork. Claude in Chrome has `read_console_messages` and
`read_network_requests`, but **does not have** `lighthouse_audit`, `performance_start_trace`,
`take_heapsnapshot` or `emulate`. That is the entire Core Web Vitals measurement surface that
`searchfit-seo:technical-seo` needs — so its correct pack is `seo`, not `web`.

*The lesson: before rejecting something because "we already have that covered", check that the other
thing exists at the same layer.*

### `playwright` — the rejection stands

Claude in Chrome does everything on the interaction side. What Playwright adds beyond that is headless
running, test scripting, multi-browser and CI — and BSO does not write tests for a web app.

### The `andrej-karpathy-skills` source has been corrected

`forrestchang/andrej-karpathy-skills` → **`multica-ai/andrej-karpathy-skills`**. A GitHub search
confirms this is the original repo after an organisation rename (199,884 stars, 20,560 forks), not a
fork. It still **has no licence** — that fact has not changed; only the source now points at the right
place.

The `0xwilliamortiz/andrej-karpathy-skills` copy is MIT and pre-packaged as a Claude Code plugin, but
has 551 stars — it is a branch, not the canonical copy.

### `frontend-design` — everything worth taking has been taken; still rejected

Four ideas went into `bso-marketing/assets/skills/bso-design/SKILL.md`, with the source recorded:

| Idea | Why it was worth taking |
|---|---|
| The three default clusters of AI imagery, with the hex value `#F4F1EA` | Far more concrete than the old "signs of machine work" list — it can name the hex |
| Section 10, `Signature`, in `DESIGN.md` | The old nine sections describe what is *correct*; this one describes what is *memorable* |
| Structure must encode the truth (the `01/02/03` numbering test) | It blocks exactly the error that recurs in thumbnails and lower thirds |
| Interface copy: one action one name, an error does not apologise | A real gap — `bso-design` had no section on button copy |

This is exactly the third cell of the `harvest` table: **read it, take the idea, drop the repo.**

## `mattpocock/skills` — an additional scoring

97,679 stars · 8,638 forks · MIT · pushed 2026-05-20 · 36 skills. Enabled at **Layer 1 (Cowork)** and
never in the Layer 2 TSV.

| PH | CP | AT | FR | ĐL | VH | NG | PB | TR | Total | Tier |
|:--:|:--:|:--:|:--:|:--:|:--:|:--:|:--:|:--:|:--:|---|
| 3 | 5 | 4 | 5 | 3 | 4 | 2 | 5 | 2 | **33** | A |

- **`PH`=3** — a clear split. Hits: `handoff` (BSO already works this way), `writing-great-skills`,
  `grilling`, `diagnosing-bugs`, `code-review`, `teach`, `edit-article`. Misses: `to-issues`, `to-prd`,
  `triage`, `implement` and `setup-matt-pocock-skills` all assume an issue tracker BSO does not have;
  `migrate-to-shoehorn`, `setup-pre-commit` and `scaffold-exercises` are the TypeScript ecosystem;
  `obsidian-vault` is unused because BSO's knowledge base runs on OKF.
- **`AT`=4** — MIT, with an identifiable author. One point off because the default install path is
  `npx skills@latest add` (running a third party's network code), and several skills install Husky
  hooks and generate bash scripts.
- **`ĐL`=3** — the README funnels toward the `aihero.dev` newsletter and a `skills.sh` badge. Not paid
  SaaS, but it is a funnel and it depends on an installer.
- **`NG`=2** — 36 skills, of which **4 `deprecated` + 6 `in-progress` still ship**, plus `ask-matt`,
  a router running across all of them. A lot of description surface for roughly 8 genuinely useful
  skills.
- **`TR`=2** — overlaps three ways: `diagnosing-bugs` ↔ `systematic-debugging`, `tdd` ↔
  `test-driven-development`, `writing-great-skills` ↔ `writing-skills`, `handoff` ↔ the power-kit
  `handoff` plugin already in use, `code-review` ↔ the official `code-review` + `brooks-lint`.

**Not caught by the cut rule** (`PH`≠1, `PB`≠1, tier A). But two scores of 2 — had it landed in tier B
it would have been cut. This is the old hole in a milder form: the hard `PH` floor cannot catch
something *half-fitting but bulky*.

**Conclusion: do not install all 36.** The right treatment is what was already planned for
`superpowers` and `ecc` — extract the usable part into one merged set. `mattpocock` is the third source
for that set, not another plugin to enable.

## The 2026-08-06 pass, session three — one scoring error fixed, the merged set settled

### ⚠ Correcting the `mattpocock/skills` score: `NG` 2 → 3, total 33 → **34**

The previous scoring counted **36 skills** by running `find` for `SKILL.md` files on disk. That was
wrong. Reading `.claude-plugin/plugin.json` shows the plugin ships only **19 skills** — `deprecated/`
(4), `in-progress/` (6), `misc/` (4) and `personal/` (2) **are not in the manifest**; they are in the
repo but not packaged.

The usable ratio is **11/19**, not 8/36. `NG` = 3.

*The lesson, recorded so it does not recur: **count a plugin's skills from its manifest, not from
`find` on disk.** A repo contains more than it publishes.*

### The merged set: abandon the merge, install `mattpocock-skills` directly

Three of the four skills to be taken come from mattpocock. At 11/19 usable, extracting them means
**building a fork that has to be maintained** in exchange for very little — directly against the rule
*"extend what runs, do not build a second one"*. So install the whole set, in pack `code`.

Comparing each overlapping pair, and why mattpocock wins:

| Job | The winner | The loser | Why |
|---|---|---|---|
| Settling a plan | `grilling` (10 lines) | `brainstorming` (159) | One question at a time · each question proposes its own answer · looks it up in the code where it can. The superpowers version has a `<HARD-GATE>` forbidding any code before a design doc is committed to `docs/superpowers/specs/` — too heavy, and it writes into its own private path |
| Finding a bug | `diagnosing-bugs` (134) | `systematic-debugging` (296) | It teaches the genuinely hard part: build the pass/fail loop first, 10 concrete techniques, no guessing before the loop exists |
| Writing a skill | `writing-great-skills` (82) | `writing-skills` (689) | The same job at one-eighth the size |
| Writing tests | *(drop both)* | `tdd` · `test-driven-development` | BSO has no test suite |

### `verification-before-completion` is extracted as a standalone plugin

Mattpocock has no equivalent, and this is the thing that blocks an error BSO **actually made** — an
older handoff recorded the "uncommitted" list incorrectly, and the lesson in that file was *"read
`git status` before believing anything"*.

Keeping all of `superpowers` for one skill in fourteen is not worth it, so it was copied out into
`plugins/verification-before-completion/`: **verbatim, with only frontmatter added for attribution**
(`license: MIT` · `source` · `author: Jesse Vincent`) plus a `LICENSE`. The body carries a
do-not-edit line — to update it, copy again from the source rather than patching by hand.

`superpowers` and `ecc` now live in `plugins-loai.tsv`.

### Two colliding `handoff` skills — resolved through the description, not a fork

The mattpocock version writes the handoff into **the operating system's temporary directory**; the
power-kit version writes `HANDOFF-<date>.md` into the working directory. BSO's `CLAUDE.md` settles that
session-state files live at the project root, so the power-kit version is correct.

Rather than forking mattpocock to remove its skill, **make the power-kit version's description win
clearly**: add the sentence *"THIS is the handoff to use when the handoff file must live in the working
folder … prefer it over any handoff skill that writes to a temporary directory."*

While there, three ideas from the mattpocock version were taken into the power-kit one: a
`## Suggested skills` section at the end · never re-copying what is already in a commit/ADR/plan but
linking to it instead · masking sensitive information.

### An incidental fix: the power-kit marketplace was broken

`claude plugin validate .` reports **2 pre-existing errors**, not caused by this pass:
`ai-research-skills` declares `./02-tokenization/huggingface-tokenizers` and
`./02-tokenization/sentencepiece`, but the `02-tokenization/` directory **does not exist**.
`build-standalone.sh` only does a plain `cp -R` of the whole directory with no exclusions — so this is
an upstream bug, not a packaging bug.

The two dead entries were removed (98 → 96 skills). Validation now **passes**. This is an edit into a
third party's file, recorded here so it can be reconciled the next time upstream is updated.

## Three token-compression tools — scored 2026-08-06, all three rejected

Candidates supplied by the user. **They are not a replacement for `caveman`** — `caveman` trims what
Claude *writes*, while these three compress what *goes in*. Different stages, so `TR` is only 3, not a
duplication contest.

| Repo | Stars | Licence | PH CP AT FR ĐL VH NG PB | TR | Total | Tier | Rejected for |
|---|:--:|---|---|:--:|:--:|:--:|---|
| `alexgreensh/token-optimizer` | 1,811 | **PolyForm NC 1.0.0** | 3 5 2 **1** 3 4 4 4 | 3 | **29** | B | `FR`=1 |
| `headroomlabs-ai/headroom` | 65,018 | Apache-2.0 | **2** 4 **2** 5 3 4 **2** 5 | 3 | **30** | B | three scores of 2 |
| `ooples/token-optimizer-mcp` | 466 | MIT | 2 **1** 2 5 4 4 2 3 | 3 | **26** | B | `CP`=1 |

### `alexgreensh/token-optimizer` — a licence forbidding commercial use

GitHub displays `NOASSERTION`; reading the `LICENSE` file directly shows **PolyForm Noncommercial
License 1.0.0**.

BSO sells health supplements. Using a tool that forbids commercial use inside the pipeline that
produces sales content is **a licence breach**, not a matter of taste. `FR`=1 because it is free but
BSO cannot use it lawfully without buying a separate licence.

*This is the first time the cut rule has caught something on its licence. Recorded: `NOASSERTION` on
GitHub does not mean "no licence" — it means **GitHub could not identify it**, and the file has to be
opened and read.*

### `headroomlabs-ai/headroom` — a proxy standing between every request

65k stars, Apache-2.0, pushed 2026-08-05, with a `.claude-plugin/marketplace.json`. A strong repo.
Rejected anyway.

- **`AT`=2** — `headroom wrap` stands up a **local proxy**, **installs Serena itself**, then runs the
  agent through that proxy. Every request passes through an intermediary layer, including the contents
  of `core/claims-matrix/`. The repo says *local-first* and *reversible*, but it is still one more
  place compliance data flows through, and it installs a second tool without asking.
- **`PH`=2** — the advertised figures are *60–95% for JSON* and *15–20% for a coding agent*. BSO's
  heavy context is **Vietnamese markdown** — rules, claims, handoffs — not JSON. BSO lands squarely at
  the low end.
- **`NG`=2** — a library plus a proxy plus MCP, with a long list of extras, one of which needs a whole
  C++ toolchain.

The old `SCORING.md` met `headroom` once before and filed it *MESH → caveman* at 63 points. The new
rubric gives it 30 and rejects it outright. Two independent measurements reaching the same conclusion.

### `ooples/token-optimizer-mcp` — `CP`=1, a hard block

This is the only entry that touches the compliance axis, and it touches it hard. The README states the
mechanism plainly:

> *"It makes the expensive call impossible. Install the plugin and a built-in `Read` of a 200 KB file
> is **denied**, with the refusal naming the cached, [summarised] record."*

BSO's `CLAUDE.md` carries one rule that cannot be got wrong: **quote verbatim from
`core/claims-matrix/` only; rephrasing an approved claim also counts as creating a new claim.** A cache
layer that **refuses `Read` and returns a summary instead** is a core principle pushing straight toward
a breach — precisely the rubric's definition of `CP`=1.

On top of that, 466 stars is far too thin a confirmation for something that blocks an agent's built-in
tool.

### Ideas taken — `harvest`

| Source | The idea |
|---|---|
| `alexgreensh` | *"Find the ghost tokens"* — **measure what is eating the context before optimising anything.** Cowork already ships an `explain-usage` skill that does exactly this; nothing needs installing |
| `headroom` | Compression must be **reversible**. Any summarisation step in BSO's pipeline must keep a route back to the original |
| `ooples` | Read the cache statistics from **the client's own transcript** rather than self-reporting — a sound measurement principle |

**Conclusion: install nothing. `caveman` stays as it is.** All three solve the context problem by
inserting a layer between Claude and the data. For a repo where one wrong word in a claim is a
regulatory breach, that intervening layer is a risk, not a convenience.

## Still open

1. ~~**The merged skill set has not been built.**~~ **CLOSED (2026-08-06)** — the merge idea was
   abandoned; `mattpocock-skills` is installed directly and `verification-before-completion` extracted
   separately. See session three above.
   *The old text, kept for comparison:* three sources — `superpowers` (14 skills, MIT) · `ecc` (47
   skills under `.agents/skills/`, MIT) · `mattpocock` (36 skills, MIT) — all three MIT, so extraction
   was possible with only an attribution line. Each function **would have had to pick one version**, or
   the new set would reproduce exactly the contradiction `bso-marketing/assets/workspace-root/files/CLAUDE.md` forbids. Building it would
   have allowed removing `superpowers` (`NG`=2) and `ecc` (`NG`=1) from the install list.
2. ~~**`ecc` is in the store but enabling it is undecided**~~ **CLOSED** — rejected outright, moved to
   `plugins-loai.tsv`.
3. ~~**`mattpocock/skills` is not in the TSV**~~ **CLOSED** — added, in pack `code`.
4. **`andrej-karpathy-skills` still has no licence.** The source now points correctly, but no commit
   has been pinned.
5. **`ai-research-skills` has been edited by hand** (2 dead paths removed). The next upstream update
   must check whether `02-tokenization/` now exists, so the fix is not overwritten.

## The final install list — 16 plugins

| Pack | Count | Plugins |
|---|:--:|---|
| `core` | 8 | claude-md-management · plugin-dev · skill-creator · commit-commands · desktop-commander · hookify · security-guidance · **verification-before-completion** |
| `code` | 5 | pyright-lsp · code-review · github · andrej-karpathy-skills · **mattpocock-skills** |
| `seo` | 1 | chrome-devtools-mcp |
| `vanphong` | 2 | caveman · ponytail |

67 entries in `plugins-loai.tsv`. The total of 83 = the 81 scored + `mattpocock-skills` +
`verification-before-completion`.
