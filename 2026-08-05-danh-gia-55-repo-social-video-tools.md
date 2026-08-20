# Review and ranking of 55 repositories (Scraping / Management / Claude Skills / other)

*Compiled 2026-08-05 · GitHub figures pulled directly through the API the same day · For the Bacsi
Online / HGMP ecosystem*

> **Internal-use warning.** This is a technical review for choosing tools, NOT legal advice. Three
> categories of risk run through all of it:
> 1. **Installing a skill/plugin from GitHub means running a stranger's instructions and scripts on
>    your machine.** Always read `SKILL.md` and `install.sh`/`setup.sh` before running anything; never
>    `curl | bash` blind.
> 2. **Every scraping/auto-posting tool can breach a platform's ToS** (account ban) and some breach the
>    law outright (SSL bypass, paywall bypass).
> 3. **No repository knows Vietnamese health-supplement regulation.** Every title/script/caption they
>    produce has to pass through the `supplement-compliance` skill before publishing.

---

## 1. The scoring frame

Each repo is scored 1–5 on 6 axes (5 = best for the Bacsi Online context). The axis codes are kept
verbatim because they are the table headers used across several documents:

| Axis | Meaning | A 5 | A 1 |
|---|---|---|---|
| **PH** – Phù hợp (fit / applicability) | Solves the actual work of a medical channel + HGMP | Usable immediately, matches the need | Off-target, or duplicates an existing tool |
| **AT** – An toàn (safety / security) | ToS, credential handling, install scripts, write access | Read-only, no key, breaches nothing | Bypass/illicit scraping, writes to accounts, asks for cookies |
| **PB** – Phổ biến (popularity / liveness) | Stars, forks, still maintained | Many stars + a recent push | Few stars, or dead/archived |
| **FR** – Free | The repo's own cost | Entirely free | Payment required |
| **ĐL** – Độc lập (independence vs SaaS) | Whether it is a funnel selling SaaS | Independent, self-contained | A thin shell funnelling to paid SaaS |
| **VH** – Vận hành (running cost) | API/model/infrastructure cost per run | Runs at $0 | Needs several paid APIs |

**Overall tier:** S (use or study immediately) · A (good, with conditions) · B (usable for a narrow
job) · C (approach with caution) · D (avoid / reference only).

Warning symbols: 🔴 high legal/ToS risk · 🟠 needs a sensitive key/credential · 🟣 a SaaS funnel ·
⚰️ dead/archived/obsolete · ⭐ a philosophical bright spot.

---

## 2. Real figures (checked against the star counts you supplied)

Most of the star counts you listed match. A few notable discrepancies:

| Repo | Stars you noted | Actual stars | Important note |
|---|---|---|---|
| youtube/api-samples | 6.0k | 6,017 | ⚰️ **ARCHIVED**, official Google but frozen (last push 2024-06) |
| Schmavery/facebook-chat-api | 1.9k | 1,947 | ⚰️ **ARCHIVED** 2021, unofficial, breaches Facebook's ToS |
| drawrowfly/tiktok-scraper | 5.2k | 5,166 | ⚰️ last push **2023-05**; TikTok has changed its API since → most likely broken |
| pytube/pytube | 13.2k | 13,160 | ⚰️ last push 2024-08, famously breaks whenever YouTube changes |
| ytdl-org/youtube-dl | 140.9k | 140,872 | Barely alive; the actually-maintained fork is **yt-dlp** (a different repo) |
| Jamie-Landeg-Jones/youtube-dl | 37 | 38 | Merely a **fork** of youtube-dl, with no value of its own |
| ZeroPointRepo/youtube-skills | 485 | 487 | 🟣 a funnel to TranscriptAPI (paid credits) |
| AgriciDaniel/claude-ads | 7.8k | 7,828 | ⭐ the highest engineering discipline in the set |
| AgriciDaniel/claude-seo | 13.4k | 13,364 | ⭐ this author's largest repo |
| mvanhorn/last30days-skill | 57.3k | 57,278 | **Already installed** (`/last30days` is on the machine) |

*A very high star count does not mean it fits you. youtube-dl at 140k is a video downloader and has
nothing to do with producing content.*

---

## 3. THE SCRAPING GROUP (13 repos)

| Repo | PH | AT | PB | FR | ĐL | VH | Tier | Flags |
|---|:--:|:--:|:--:|:--:|:--:|:--:|:--:|---|
| **mathiaschu/watch** | 5 | 5 | 3 | 5 | 5 | 4 | **S** | ⭐ no key, on-device |
| **guimatheus92/mcp-video-analyzer** | 5 | 4 | 3 | 5 | 4 | 4 | **A** | MCP, npm, well maintained |
| davidteather/TikTok-Api | 3 | 3 | 5 | 5 | 4 | 3 | B | 🟠 uses cookies/Webshare |
| supadata-ai/mcp | 4 | 3 | 3 | 3 | 2 | 3 | B | 🟣🟠 the Supadata SaaS |
| ZeroPointRepo/youtube-skills | 4 | 3 | 4 | 2 | 2 | 3 | B | 🟣 a TranscriptAPI funnel |
| rugvedp/Trends-MCP | 3 | 3 | 2 | 4 | 4 | 3 | B | 🟠 RapidAPI, scrapes Later.com |
| apismith-labs/tiktok-transcript-api | 3 | 3 | 1 | 2 | 2 | 3 | C | 🟣 an Apify Actor funnel |
| ytdl-org/youtube-dl | 2 | 4 | 5 | 5 | 5 | 5 | C | ⚰️ use yt-dlp instead |
| Tyrrrz/YoutubeDownloader | 2 | 4 | 4 | 5 | 5 | 5 | C | A download GUI, barely relevant |
| pytube/pytube | 2 | 3 | 4 | 5 | 5 | 5 | C | ⚰️ breaks often |
| drawrowfly/tiktok-scraper | 2 | 2 | 4 | 5 | 5 | 4 | D | ⚰️🔴 dead + a scraper |
| **Zskkk/tiktok-ssl-bypass-skill** | 1 | 1 | 1 | 5 | 5 | 2 | **D** | 🔴 SSL pinning bypass, Frida |
| Jamie-Landeg-Jones/youtube-dl | 1 | 4 | 1 | 5 | 5 | 5 | D | a duplicate fork |

**Group conclusion:** what you actually need is **"let the agent watch/listen to video"**, not bulk
downloading.

- **mathiaschu/watch** is the first choice: yt-dlp + ffmpeg + Whisper running **on-device, with no API
  key, no telemetry and no stored cookies**. Exactly right for a medical channel that has to stay
  discreet. It is essentially a compact version of the `youtube-video-perception` skill you just used.
- **mcp-video-analyzer** is stronger (frame OCR, caching, several sources) if bulk processing is ever
  needed; the trade is an added npm dependency plus an optional paid TwelveLabs tier.
- 🔴 **tiktok-ssl-bypass-skill: avoid entirely.** Bypassing an app's SSL certificate is an attack
  technique with real legal risk, and has no place in a compliant marketing process.
- The download repos (youtube-dl/pytube/YoutubeDownloader) and the old TikTok scrapers: keep **yt-dlp**
  only, as foundational infrastructure, and skip the rest.

---

## 4. THE MANAGEMENT / PUBLISHING GROUP (9 repos)

| Repo | PH | AT | PB | FR | ĐL | VH | Tier | Flags |
|---|:--:|:--:|:--:|:--:|:--:|:--:|:--:|---|
| **pipeboard-co/meta-ads-mcp** | 4 | 3 | 4 | 3 | 2 | 3 | **A** | 🟣 Pipeboard, a Meta Business Partner |
| youtube/api-samples | 3 | 5 | 5 | 5 | 5 | 5 | B | ⚰️ archived, but it is the canonical sample code |
| iscale-llc/iscale-facebook-ad-builder | 3 | 3 | 2 | 4 | 4 | 2 | B | 🟠 full-stack, many keys |
| ndesv21/socialclaw | 3 | 3 | 2 | 3 | 2 | 3 | B | 🟣 the getsocialclaw service |
| makiisthenes/TiktokAutoUploader | 3 | 2 | 4 | 5 | 5 | 4 | C | 🔴 uploads illicitly through a session |
| wanglinsaputra/OmniPost-AI | 2 | 2 | 1 | 4 | 4 | 3 | C | 🔴 auto-posts by driving the browser DOM |
| brodyautomates/ig-setter | 2 | 2 | 1 | 4 | 4 | 3 | C | 🟠 auto-replies to Instagram DMs |
| warifp/FacebookToolkit | 1 | 1 | 4 | 5 | 5 | 4 | D | 🔴⚰️ a Facebook bot/scraper, old PHP |
| Schmavery/facebook-chat-api | 1 | 1 | 4 | 5 | 5 | 4 | D | 🔴⚰️ archived, unofficial |

**Group conclusion:** this is the **riskiest group**, because it *writes* to real accounts.

- Automated publishing through a reverse-engineered session (TiktokAutoUploader) or by driving the DOM
  (OmniPost, ig-setter) **gets accounts banned easily** and carries no safety controls. For a
  doctor-facing brand, one channel ban wipes out every bit of accumulated credibility.
- The correct route if automated publishing is ever needed: **the official OAuth API** (the sample in
  `youtube/api-samples` is still good reference code despite being archived), or an MCP with controlled
  writes along the lines of `pipeboard-co/meta-ads-mcp` (an approved Meta Business Partner — far safer
  than a scraper, at the cost of being a Pipeboard SaaS funnel).
- Licence note: `meta-ads-mcp` is marked **NOASSERTION** (no clear licence) → consider that before
  reusing its code.

---

## 5. THE CLAUDE SKILLS GROUP (31 repos)

Split by author/quality for readability.

### 5A. The AgriciDaniel family — "evidence discipline" ⭐ (the biggest bright spot in the whole list)

| Repo | PH | AT | PB | FR | ĐL | VH | Tier |
|---|:--:|:--:|:--:|:--:|:--:|:--:|:--:|
| **AgriciDaniel/claude-blog** | 5 | 5 | 4 | 5 | 5 | 3 | **S** |
| **AgriciDaniel/anti-slop** | 5 | 5 | 2 | 5 | 5 | 5 | **S** |
| **AgriciDaniel/claude-ads** | 4 | 5 | 5 | 5 | 5 | 3 | **A** |
| **AgriciDaniel/claude-seo** | 4 | 4 | 5 | 5 | 5 | 3 | **A** |
| AgriciDaniel/youtuber (YouTube Brain) | 4 | 5 | 2 | 5 | 5 | 4 | A |
| AgriciDaniel/claude-shorts | 4 | 4 | 3 | 5 | 4 | 3 | A |
| AgriciDaniel/claude-repurpose | 4 | 4 | 3 | 5 | 4 | 3 | A |

This set is worth **studying to copy the method**, even without installing any of it. See section 7
(philosophy).

- **claude-blog**: a 3-tier architecture (orchestrator → 31 sub-skills → agents + scripts), a **5-Gate
  Delivery Contract** blocking delivery until every check passes, 5-category quality scoring, and a
  sourced evidence "brain". A very good fit for building the HGMP blog machine.
- **anti-slop**: an "AI writing" detector designed to **never conclude who wrote something**; every
  signal must be routed into a procedure producing *an artifact a person can check*. The "evidence
  discipline" philosophy is extremely valuable in a medical setting that needs citations.
- **claude-ads**: an adapter that is **read-only by default**; writing requires 6 conditions
  (capability enabled, explicit ID, a before/after diff, approval, idempotency + rollback, precondition
  verification). This is **the safety template** to apply to everything that touches a real account.
- **youtuber (YouTube Brain)**: 5-level "maturity gates" where the score is **capped by maturity** —
  editing the markdown cannot self-declare "market-ready". It prevents internal overstatement.

### 5B. The sergebulaev family — a Publora funnel 🟣

| Repo | PH | AT | PB | FR | ĐL | VH | Tier |
|---|:--:|:--:|:--:|:--:|:--:|:--:|:--:|
| sergebulaev/linkedin-skills | 3 | 3 | 4 | 4 | 2 | 4 | B |
| sergebulaev/facebook-skills | 3 | 3 | 1 | 4 | 2 | 4 | B |
| sergebulaev/x-skills | 2 | 3 | 2 | 4 | 2 | 4 | B |
| sergebulaev/instagram-skills | 2 | 3 | 1 | 4 | 2 | 4 | C |
| sergebulaev/tiktok-skills | 2 | 3 | 1 | 4 | 2 | 4 | C |
| sergebulaev/threads-skills | 2 | 3 | 1 | 4 | 2 | 4 | C |

- The copywriting section and its **"voice rules"** (no em dashes, no AI words like
  "leverage/delve/unlock", concrete numbers instead of adjectives, a title is a promise not a summary)
  are very good — **worth extracting separately as a reference document**.
- Against it: the publishing route goes through **Publora** (a third-party SaaS, video uploaded to
  their S3, needs an API key, capped at 512MB). Not something to enable for medical content. The skills
  themselves are thin; the value is in the references.

### 5C. Notable large / independent skills

| Repo | PH | AT | PB | FR | ĐL | VH | Tier | Notes |
|---|:--:|:--:|:--:|:--:|:--:|:--:|:--:|---|
| **mvanhorn/last30days-skill** | 5 | 4 | 5 | 4 | 4 | 3 | **S** | Already installed. Multi-source research with community scoring |
| **rushindrasinha/youtube-shorts-pipeline** | 4 | 4 | 5 | 5 | 5 | 3 | **A** | ⭐ an anti-hallucination gate, niche profiles |
| **hassancs91/claude-youtube-editor** | 4 | 4 | 3 | 5 | 4 | 2 | **A** | A video build pipeline that is "honest about cost" |
| **MaxKmet/idea-validation-agents** | 4 | 5 | 4 | 5 | 5 | 4 | **A** | No key; suits validating HGMP products (see also section 6) |
| Affitor/affiliate-skills | 3 | 3 | 4 | 4 | 3 | 3 | B | ⭐ an 8-stage "flywheel", chain_metadata |
| nicojunk/claude-ig | 3 | 4 | 1 | 5 | 4 | 4 | B | ⭐ 7 quality gates, with G3 "affiliate status must be disclosed" |
| bradautomates/content-ideas | 3 | 3 | 3 | 3 | 3 | 3 | B | 🟠 the ScrapeCreators API; the HTML-feed rendering is the idea worth taking |
| aaaronmiller/create-viral-content | 3 | 4 | 2 | 5 | 5 | 4 | B | ⭐ 6 "adversarial refine" passes + an ethics frame |
| Hao0321/claude-skill-social-post | 3 | 2 | 4 | 5 | 4 | 4 | B | 🔴 auto-posts to Facebook via the DOM; but its 7 formulas for under-5K-follower accounts are good |
| zubair-trabzada/ai-ads-claude | 3 | 3 | 3 | 5 | 4 | 3 | B | 15 advertising skills, 5 agents in parallel |
| Hainrixz/claude-ads | 3 | 3 | 2 | 4 | 3 | 3 | B | ⭐ a transparent 3-tier cost model |
| itchernetski/threads-carousel-claude-skill | 3 | 4 | 2 | 5 | 4 | 4 | B | Text → a carousel of PNG/PDF, a 4-axis design system |
| iart-ai/tiktok-video-skills | 3 | 4 | 1 | 4 | 3 | 4 | B | 🟣 an iart.ai funnel; a hook→retention→loop grammar |
| Maartenlouis/remotion-ads | 3 | 4 | 2 | 5 | 4 | 2 | B | Remotion + ElevenLabs, word-level captions |
| moboutrig/instagram-claude-skill | 2 | 4 | 1 | 5 | 4 | 4 | C | 🟠 the official IG Graph API (safer than a scraper) |

### 5D. Small / single-author / personal-funnel skills (narrow value)

| Repo | Tier | Notes |
|---|:--:|---|
| rediumvex/viral-hooks-skill | C | 100 hook formulas — use it as a reference library |
| rediumvex/ai-video-generator-claude | C | 🟠 a prompt funnel for Higgsfield/Seedance (paid) |
| rediumvex/social-media-caption-generator-claude | C | Captions for 7 platforms, thin |
| dylanpakd-cyber/lazyreel | C | 🟣 a "doomscroll" MCP with 21B views, closed source |

---

## 6. STANDALONE REPOS

| Repo | Group | PH | AT | PB | FR | ĐL | VH | Tier | Notes |
|---|---|:--:|:--:|:--:|:--:|:--:|:--:|:--:|---|
| **DojoCodingLabs/remotion-superpowers** | Video edit | 4 | 4 | 2 | 5 | 5 | 3 | **A** | A free plugin turning Remotion into a studio; 5 MCP servers; needs several keys |
| **joeseesun/anything-to-notebooklm** | →NotebookLM | 4 | 2 | 5 | 5 | 4 | 3 | **B** | 🔴 includes a **paywall-bypass** feature (legal risk); 15+ sources → podcast/PPT/mindmap |
| **akitaonrails/tiktok_analysis** | Privacy | 3 | 5 | 1 | 5 | 5 | 5 | **B** | ⭐ Not a tool but a **reverse-engineering report** on TikTok — read it to understand the data risk |
| **MaxKmet/idea-validation-agents** | Idea | 4 | 5 | 4 | 5 | 5 | 4 | **A** | Already scored in 5C; validates ideas, no key needed |

- **remotion-superpowers**: if Dr. Hieu builds video from code (Remotion), this is a strong and free
  set, including a "see/hear/analyze" layer. Worth trying in the production branch.
- **anything-to-notebooklm**: the "any content → NotebookLM" idea fits turning medical material into
  study podcasts and mindmaps very well. **But** the paywall-bypass module is a legal line — if it is
  used at all, that part must be switched off and only content you have the rights to fed in.
- **tiktok_analysis**: keep as a data-security reference, not as a tool.

---

## 7. PHILOSOPHY / WORKFLOW / PIPELINE WORTH KEEPING

This is the most valuable section — distilled for reuse in the Bacsi Online/HGMP system, even if not a
single repo is installed.

### 7.1. Evidence discipline — *AgriciDaniel/anti-slop, youtuber, claude-ads*
- **Every figure must point back to a dated source in a "source ledger"** (URL + date retrieved +
  evidence tier + limitations). No source = the claim cannot be made. → Applies directly to
  health-supplement content: every benefit must anchor to permitted documentation.
- **Never conclude, only produce artifacts a person can check.** anti-slop never declares "this was
  written by AI"; it points at specific, verifiable defects.
- **Never let the model gatekeep its own edits** — the scanner re-runs after a fix (preventing
  self-congratulatory rubber-stamping).

### 7.2. A Delivery Contract with several "gates" — *claude-blog (5 gates), nicojunk/claude-ig (7 gates)*
- Content **cannot be delivered until it clears every gate**: all formats present → visual check
  (screenshots at 3 screen sizes) → review score ≥ 90 with 0 P0 defects → links/assets return 200.
- The orchestrator **retries up to 3 times itself** before escalating to a person. → The ideal model for
  the process: *draft → self-check compliance → self-check quality → only then submit for approval*.
- A "zero tolerance" quality gate: for example `/ig` has **G3 = never produce affiliate content without
  disclosure**. That is exactly where the health-supplement guardrail slots in.

### 7.3. Maturity gates — anti-overstatement — *AgriciDaniel/youtuber*
- 5 maturity levels: Scaffolded → Researched → Domain-adapted → Demo-verified → Market-ready. **The
  score is capped by the level; editing the markdown cannot promote it.** A very good fit for managing
  quality when several people work on the same thing.

### 7.4. An orchestrator plus specialised agents in parallel — *claude-ads, Hainrixz/claude-ads, ai-ads-claude, claude-blog*
- One "conductor" holds the scope and synthesises; **several specialist agents run in parallel**, each
  with its own checklist, loading references **on demand (RAG-style)**, and returning **both Markdown
  (for people) and JSON (for machines, validated against a schema)**.
- **If one agent fails, the whole run is marked "partial" and is never presented as complete.** Honest
  about evidence coverage (graded ≥80% / provisional 60–79% / insufficient <60%).

### 7.5. A safety frame for actions that write to accounts — *AgriciDaniel/claude-ads*
To let an AI *write* to a real account, all 6 layers are required: (1) the capability tested and
enabled, (2) an explicit account/object ID, (3) a before/after diff with the "blast radius", (4) owner
approval within a preset ceiling, (5) an idempotency key + audit + rollback + a verification window,
(6) verification that the remote state still matches the precondition. **Permanent deletion: not
supported.** → This should be your general policy for any automation touching a live channel.

### 7.6. A niche profile driving the whole pipeline — *rushindrasinha/youtube-shorts-pipeline*
- A single YAML "niche profile", loaded once, **shapes every stage**: script voice, visual style, music,
  thumbnail. Changing the profile changes the entire character without editing prompts one by one.
- **An anti-hallucination gate**: the Research stage injects facts (names/figures/claims) from real
  sources, and the LLM is forced to *use only the research data, never its training knowledge*. →
  Extremely well suited to medical content.
- It has a **"$0.00 mode"** (local Ollama + Edge TTS) — cost stays under control.

### 7.7. A closed-loop flywheel, skills chaining into skills — *Affitor/affiliate-skills*
- 8 stages: Research → Content → Blog/SEO → Offers → Distribution → Analytics → Automation → Meta, with
  **Analytics looping back into Research**. Each skill declares `chain_metadata.suggested_next` so **the
  agent chains them itself**, passing data through the conversation context rather than copy-pasting
  files.

### 7.8. Refining through several adversarial personas — *aaaronmiller/create-viral-content*
- 6 adversarial refinement passes: The Skeptic → The Expert → The Scroller → The Competitor → The Editor
  → (thumbnail). Together with **an explicit ethics frame** (allowed: sharpening your own point,
  translating expertise into accessible content; forbidden: astroturfing, misinformation,
  impersonation). → That ethics frame is close to mandatory for a doctor.

### 7.9. Voice rules against the AI register — *the sergebulaev family, anti-slop, viral-hooks*
- No em dashes; capitalise proper nouns; no AI clichés; **a concrete number beats an adjective**; **a
  title is a promise plus a specific payoff, not a summary**; **title and thumbnail are a pair and must
  not repeat each other**; **the first 30 seconds (3 seconds on a Short) is the real algorithm — drop
  the intro**.

### 7.10. Privacy-first perception — *mathiaschu/watch*
- Watching/listening to video with **no key, no telemetry, on-device transcription, and cookies read
  live and never stored**. The privacy standard a medical organisation should hold to.

### 7.11. A "self-learning feedback loop" from user actions — *bradautomates/content-ideas*
- Renders a self-contained HTML page where the user marks each idea ▲/▼; those reactions are stored as a
  **personalisation substrate** for next time. The "widget + gradual learning" model is worth copying.

---

## 8. RECOMMENDED ACTIONS FOR BACSI ONLINE

**Use or study now (Tier S–A, safe):**
- Video perception: **mathiaschu/watch** (or keep the existing `youtube-video-perception` skill).
- Research before producing content or holding a meeting: **last30days** (already installed).
- Learning the architecture for building our own content machine: **AgriciDaniel/claude-blog +
  anti-slop + claude-ads** (read them; installing is not necessary).
- Validating HGMP product or content ideas: **MaxKmet/idea-validation-agents** (no key).
- If a video pipeline is built: study **youtube-shorts-pipeline** (anti-hallucination + niche profiles)
  and **remotion-superpowers / claude-youtube-editor** for the assembly stage.

**Take the ideas only, do not install:**
- The voice rules and hook formulas (sergebulaev, viral-hooks, create-viral-content) → merge into one
  house-style document.
- The "gates / evidence ledger / maturity gates" → embed them in the existing `supplement-compliance`
  skill.

**Avoid:**
- 🔴 tiktok-ssl-bypass, TiktokAutoUploader, OmniPost-AI, ig-setter, FacebookToolkit, facebook-chat-api —
  anything writing to an account through reverse-engineering or the DOM.
- 🟣 Do not enable the Publora / TranscriptAPI / Supadata / Apify routes for medical content without a
  clear reason; prefer the official APIs.
- ⚰️ Skip dead/archived repos unless reading the code as a reference (`youtube/api-samples` is the
  exception worth reading).
- The paywall bypass in anything-to-notebooklm: switch it off and feed in only content you have the
  rights to.

**The golden rule over everything:** any title/script/caption produced by any skill →
**run it through `supplement-compliance` before publishing**. The "shock/curiosity-gap" hook formulas
are the most likely place for a non-compliant efficacy claim to appear.

---

*Data source: the GitHub REST API (`/repos/{owner}/{repo}` and the raw README), queried 2026-08-05. The
scores are a qualitative assessment against the Bacsi Online context, not an absolute objective metric.*
