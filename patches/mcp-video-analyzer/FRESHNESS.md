# Freshness: Gemini native-YouTube fallback (mcp-video-analyzer)

Last reviewed: 2026-09-25

A local addition to a vendored plugin. Edit the files in this directory, never the copies
under `plugins/`; then run `bash patches/add-gemini-youtube-fallback.sh` and
`bash revendor.sh --verify mcp-video-analyzer`.

| Fact | Where the skill relies on it | How to check |
|---|---|---|
| Every model in `FALLBACK_MODELS` exists, is not retired, and accepts a YouTube URL as video input | `gemini_youtube_fallback.py`, `FALLBACK_MODELS` | Gemini API models page and deprecations page (`ai.google.dev/gemini-api/docs/models`, `.../deprecations`). Blocked from the cloud environment; use a search. Any failed model is skipped, so a retired one costs one request, not the cascade. **2026-09-26:** `gemini-2.5-flash` removed (closed to new users; its shutdown date moved between 2026-10-16, 2026-10-20 and "none announced", per searches, not Google's page). `gemini-3.1-flash-lite-preview` removed (shut down 2026-05-25). `gemini-3.7-flash` added (video input per its model card). `gemini-3-flash-preview` unverified: no shutdown date found, and developers were asking Google for one in September 2026 |
| The alias `gemini-flash-latest` still exists and points at a video-capable Flash model (`gemini-3.8-flash` since 2026-09-02), and `FALLBACK_MODELS` starts at the Flash model just below it | `DEFAULT_MODEL`; its comment; the first entry of `FALLBACK_MODELS` | The same models page, or the "What's new" page it links. When the alias moves, add the model it left to the top of `FALLBACK_MODELS` |
| `gemini-2.5-flash-lite` still rejects video (`fileData`), which is why it is left out | Comment above `FALLBACK_MODELS` | The models page, input modalities. If it now accepts video, it is one more quota bucket |
| The request shape (`generateContent` with `fileData.fileUri` set to a YouTube URL) and host `generativelanguage.googleapis.com` are unchanged | `gemini_youtube_fallback.py`, request builder | The Gemini API video-understanding page, YouTube URL section |
| Free-tier limits are per model, and YouTube input takes public videos only, with a daily cap | `skill-section.md`, last paragraph; the cascade's reason to exist | The Gemini API rate-limits page and video-understanding page |
| API keys are created at `https://aistudio.google.com/apikey` | `readme-note.md` | Open the URL |
| Upstream mcp-video-analyzer still has no fallback of its own for blocked YouTube downloads | The reason this addition exists | Upstream `CHANGELOG.md` in `plugins/mcp-video-analyzer/` after each re-vendor. If upstream adds one, retire this patch |
| The README anchor row (`OPENAI_API_KEY` in the transcription table) still exists | `add-gemini-youtube-fallback.sh` | The patch fails loudly if it does not; the weekly re-vendor would show it |

## Behaviour that depends on the model

- The skill section tells the agent to use Gemini only as a last resort, and only for
  YouTube. Check that a new Claude model still tries the normal tools first.
