# Changelog

All notable changes to `/watch` are documented here.

## [1.0.0] — 2026-05-29

Fork of [bradautomates/claude-video](https://github.com/bradautomates/claude-video) 0.1.3, reworked for fully-local, key-free operation.

### Changed
- **Transcription is now 100% local.** Replaced the Groq/OpenAI Whisper API fallback with on-device transcription via `mlx-whisper` (Apple Silicon, `whisper-large-v3-turbo`) or `openai-whisper` (CPU, `base`). No API key, no `.env`, no config file — and the audio never leaves the machine.
- `setup.py` preflight now checks for a local whisper engine instead of an API key. Removed all `.env` scaffolding, key storage, and the `SETUP_COMPLETE` marker.
- SessionStart hook rewritten: reports only missing binaries, never anything about keys or secrets.
- Whisper language is auto-detected (works for any-language video) instead of being fixed.

### Added
- **Browser-cookie support** for login-gated sources: `--cookies-from-browser <chrome|firefox|safari|edge|brave|…>` and `--cookies <file>`. Makes Instagram, X/Twitter, and private/age-restricted videos downloadable. Cookies are read live at runtime and never stored or transmitted by the skill.

### Removed
- Groq / OpenAI Whisper API clients, multipart upload, retry/backoff for HTTP, and all API-key handling.

---

## Upstream history (bradautomates/claude-video)

### [0.1.3] — 2026-05-09
- Windows UTF-8 fixes for `video.info.json`; hardened subprocess argv against option injection (`--` before the URL, stricter `is_url`, absolute path resolution).

### [0.1.0–0.1.2] — 2026-04
- Initial release: `/watch` slash command, yt-dlp download + native captions, ffmpeg auto-scaled frame extraction, `--start`/`--end` focused mode, Whisper API fallback, `setup.py` preflight, SessionStart hook, `.skill` bundle packaging.
