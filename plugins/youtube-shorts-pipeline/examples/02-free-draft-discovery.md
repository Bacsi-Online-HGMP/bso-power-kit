# Example 02 — Zero-cost draft with topic discovery

Goal: discover a trending topic and draft a script with no paid API keys, using a local Ollama model. This exact flow was run to validate this document.

## Setup (all free)

```bash
# Install Ollama (https://ollama.com), then pull a model
ollama pull llama3.1:8b
```

No API keys required for this example.

## Step 1 — Discover trending topics

```bash
python -m verticals topics --niche tech --limit 5
```

Real output from a run on 2026-06-10:

```
  reddit: found 0 topics
  rss: found 5 topics

  Trending topics for [tech] (5 found):

   1. [rss/Hacker News: Front Page] If Claude Fable stops helping you, you'll never know [0.50]
   2. [rss/Hacker News: Front Page] Exif Smuggling [0.50]
   3. [rss/Hacker News: Front Page] Company Will Add Phone, AirPod, and Smartwatch Trackers to ALPRs [0.50]
   4. [rss/Hacker News: Front Page] Upcoming breaking changes for NPM v12 [0.50]
   5. [rss/Hacker News: Front Page] Alpine Linux 3.24.0 Released [0.50]
```

Sources are configured per niche profile (RSS feeds, subreddits, NewsAPI if a key is set).

## Step 2 — Draft with a local LLM

```bash
python -m verticals draft \
  --topic "Alpine Linux 3.24 released with major package updates" \
  --niche tech \
  --provider ollama
```

Real output (model: a local qwen3-coder:30b; yours depends on what you pulled):

```
  Drafting: Alpine Linux 3.24 released with major package updates [niche: tech, platform: shorts]

  Loaded niche profile: tech
  Researching topic via DuckDuckGo...
  Calling LLM via ollama...
  Using Ollama model: qwen3-coder:30b

  Draft saved: ~/.verticals/drafts/1781048758.json

  Script:
  Alpine Linux 3.24 drops. Everyone's ignoring it. Here's the thing: it ships with
  updated OpenSSL, glibc, and busybox. ... Follow for daily tech breakdowns.

  Title: Alpine Linux 3.24 Breaks Everything You Didn't See Coming

  B-roll prompts:
  1. Close-up of terminal output showing Alpine Linux version and package updates ...
  2. Abstract data visualization with glowing nodes ...
  3. Minimalist shot of a circuit board macro ...
```

## Step 3 (optional) — Produce for free

```bash
python -m verticals produce --draft ~/.verticals/drafts/<id>.json --lang en
```

With no `GEMINI_API_KEY`, b-roll uses solid-color fallback frames; Edge TTS and Whisper captions are free, so this still yields a complete 1080x1920 MP4. Add a Gemini key when you want real AI visuals.

## Interactive picker

```bash
python -m verticals run --discover --niche tech --dry-run
```

Lists trending topics, lets you pick a number (or type your own), and drafts it. Add `--auto-pick` to let the LLM choose.
