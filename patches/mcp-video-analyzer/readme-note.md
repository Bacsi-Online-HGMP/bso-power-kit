> **`GEMINI_API_KEY` / `GEMINI_MODEL` / `GEMINI_MODELS` (BSO downstream addition, not upstream).**
> Read by `scripts/gemini_youtube_fallback.py`, the last-resort Gemini native-YouTube lane wired into
> the `/video` skill — used when the normal tools return no transcript for a public YouTube URL, or
> to read a video whose download is blocked. Key resolves from `GEMINI_API_KEY` in the environment,
> else `GEMINI_API_KEY=...` in `~/.config/video-analyzer/.env` (`chmod 600`). Because free-tier
> RPM/RPD limits are **per model**, the request **cascades across a chain of distinct video-capable
> Flash models** (best → lite); a per-model 429 (quota) or 5xx (congestion) falls straight to the
> next, multiplying throughput across many clips. `GEMINI_MODEL` sets the cascade's primary (default
> floating `gemini-flash-latest`); `GEMINI_MODELS` (comma-separated) replaces the whole cascade. It
> is a separate CLI, **not** consumed by the MCP server — so this key does **not** belong in the
> server's `.mcp.json` env. Get a key at <https://aistudio.google.com/apikey>.
