# Examples

Two worked end-to-end examples, with the exact commands and the output you should expect at each stage. Both were run against this repo as-is.

- [01 — Tech news Short, full pipeline](01-tech-news-short.md)
- [02 — Zero-cost draft with topic discovery](02-free-draft-discovery.md)

## Prerequisites

```bash
git clone https://github.com/rushindrasinha/youtube-shorts-pipeline.git
cd youtube-shorts-pipeline
pip install -r requirements.txt
```

`ffmpeg` must be on your PATH for the produce stage (`brew install ffmpeg` / `apt install ffmpeg`).

Keys: example 01 needs `ANTHROPIC_API_KEY` (or any LLM provider) and `GEMINI_API_KEY` for b-roll. Example 02 runs with no paid keys at all.
