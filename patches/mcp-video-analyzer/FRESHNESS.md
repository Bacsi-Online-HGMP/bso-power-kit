# Freshness: Gemini native-YouTube fallback (mcp-video-analyzer)

Last reviewed: 2026-09-25

A local addition to a vendored plugin. Edit the files in this directory, never the copies
under `plugins/`; then run `bash patches/add-gemini-youtube-fallback.sh` and
`bash revendor.sh --verify mcp-video-analyzer`.

| Fact | Where the skill relies on it | How to check |
|---|---|---|
| Every model in `FALLBACK_MODELS` exists, is not retired, and accepts a YouTube URL as video input | `gemini_youtube_fallback.py`, `FALLBACK_MODELS` | Gemini API models page and deprecations page (`ai.google.dev/gemini-api/docs/models`, `.../deprecations`). Blocked from the cloud environment; use a search. **Open item:** a search on 2026-09-25 reported `gemini-2.5-flash` scheduled for deprecation on 2026-10-16, not confirmed from Google's page. A retired model returns 404 and is skipped, so the cascade degrades, not breaks |
| The alias `gemini-flash-latest` still exists and points at a video-capable Flash model | `DEFAULT_MODEL` | The same models page |
| `gemini-2.5-flash-lite` still rejects video (`fileData`), which is why it is left out | Comment above `FALLBACK_MODELS` | The models page, input modalities. If it now accepts video, it is one more quota bucket |
| The request shape (`generateContent` with `fileData.fileUri` set to a YouTube URL) and host `generativelanguage.googleapis.com` are unchanged | `gemini_youtube_fallback.py`, request builder | The Gemini API video-understanding page, YouTube URL section |
| Free-tier limits are per model, and YouTube input takes public videos only, with a daily cap | `skill-section.md`, last paragraph; the cascade's reason to exist | The Gemini API rate-limits page and video-understanding page |
| API keys are created at `https://aistudio.google.com/apikey` | `readme-note.md` | Open the URL |
| Upstream mcp-video-analyzer still has no fallback of its own for blocked YouTube downloads | The reason this addition exists | Upstream `CHANGELOG.md` in `plugins/mcp-video-analyzer/` after each re-vendor. If upstream adds one, retire this patch |
| The README anchor row (`OPENAI_API_KEY` in the transcription table) still exists | `add-gemini-youtube-fallback.sh` | The patch fails loudly if it does not; the weekly re-vendor would show it |

## Behaviour that depends on the model

- The skill section tells the agent to use Gemini only as a last resort, and only for
  YouTube. Check that a new Claude model still tries the normal tools first.
