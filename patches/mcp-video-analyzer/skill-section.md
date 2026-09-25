## Gemini native-YouTube fallback (downstream addition, not upstream)

Route A and Route B reach YouTube through `yt-dlp`. When that path fails — a
region lock, login wall, age gate, or throttling in `warnings`, **or** a long
video that comes back with an empty `transcript` and a "no Whisper backend"
warning — Gemini can read the **public YouTube URL natively**, without any
download. Use it only as a last resort, and only for YouTube.

Trigger it when **all** of these hold:

- the source is a public YouTube URL (`youtube.com/watch`, `youtu.be/…`, `/shorts/`, `/live/`); and
- the normal tool returned `transcript: []` (or the `warnings` name a yt-dlp download/caption failure); and
- a Gemini key is available — `GEMINI_API_KEY` in the environment, or `GEMINI_API_KEY=...` in `~/.config/video-analyzer/.env` (chmod 600). The script resolves both; if neither is present it exits with that hint and you skip the fallback.

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/gemini_youtube_fallback.py" "<youtube-url>"
# or, when frames are also unavailable (download fully blocked), ask directly:
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/gemini_youtube_fallback.py" "<youtube-url>" --ask "<the user's question>"
```

Without `--ask` it prints a timestamped transcript (`M:SS\ttext`); with `--ask` it
prints Gemini's answer. Exit non-zero with a reason on stderr means Gemini could
not help (no key, not a YouTube URL, blocked, or API error) — relay that and fall
back to whatever the normal tools did return.

**What this is not:** the text comes from *Gemini's* reading of the video, not
from frames you can re-inspect. Prefer the MCP/CLI frames+transcript whenever
they succeed; reach for this only to fill the gap they leave. Free-tier Gemini
caps daily YouTube minutes and rejects private/unlisted videos.
