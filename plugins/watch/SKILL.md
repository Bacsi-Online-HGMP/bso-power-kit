---
name: watch
description: Watch a video from YouTube, Instagram, X/Twitter, Vimeo, TikTok or any of ~1800 yt-dlp sites (or a local path). Downloads with yt-dlp, extracts auto-scaled frames with ffmpeg, pulls the transcript from captions (or local mlx-whisper fallback, no API key), and hands the result to Claude so it can answer questions about what's in the video.
argument-hint: "<video-url-or-path> [question]"
allowed-tools: Bash, Read
homepage: https://github.com/mathiaschu/claude-video
repository: https://github.com/mathiaschu/claude-video
author: Mathias Schusterman (fork of bradautomates/claude-video)
license: MIT
user-invocable: true
---

# /watch — Claude watches a video

You don't have a video input; this skill gives you one. A Python script downloads the video, extracts frames as JPEGs, gets a timestamped transcript (native captions first, then **local mlx-whisper** as fallback — runs on-device, no API and no key), and prints frame paths. You then `Read` each frame path to see the images and combine them with the transcript to answer the user.

## Step 0 — Setup preflight (runs every `/watch` invocation, silent on success)

**Python interpreter:** every `python3 ...` command in this skill is for macOS/Linux. On **Windows**, substitute `python` — the `python3` command on Windows is the Microsoft Store stub and will not run the script.

Before every `/watch` run, verify that dependencies are in place:

```bash
python3 "${CLAUDE_SKILL_DIR}/scripts/setup.py" --check
```

This is a <100ms lookup. On exit 0, the script emits **nothing** — proceed to Step 1 without comment. **Do NOT announce "setup is complete" to the user** — they don't need a status message on every turn. The only acceptable user-visible output from Step 0 is when remediation is required.

On non-zero exit, follow the table:

| Exit | Meaning | Action |
|------|---------|--------|
| `2` | Missing binaries (`ffmpeg` / `ffprobe` / `yt-dlp`) | Run installer |
| `3` | No local whisper engine (`mlx-whisper` / `openai-whisper`) | Run installer, then tell user the `pip3` command it prints |
| `4` | Both missing | Run installer |

The installer is idempotent — safe to re-run:

```bash
python3 "${CLAUDE_SKILL_DIR}/scripts/setup.py"
```

On macOS with Homebrew, it auto-installs `ffmpeg` and `yt-dlp`. On Linux/Windows, it prints the exact install commands for the user to run. For transcription it checks for a local whisper engine (`mlx-whisper` preferred on Apple Silicon, `openai-whisper` as a CPU fallback) and prints the `pip3 install` command if neither is present. **No API key, no config file, no `.env` — transcription runs entirely on-device.**

**If no whisper engine is installed:** run the installer and relay the exact `pip3 install …` command it prints (`mlx-whisper` on Apple Silicon, `openai-whisper` on Windows/Linux/Intel Macs — do not assume mlx, it only installs on Apple Silicon). If they don't want to install it, proceed with `--no-whisper` and tell them videos without native captions will come back frames-only.

**Structured mode (optional):** `python3 "${CLAUDE_SKILL_DIR}/scripts/setup.py" --json` emits `{status, missing_binaries, whisper_backend, has_whisper, platform}` where `status` is one of `ready | needs_install | needs_whisper | needs_install_and_whisper`.

Within a single session, you can skip Step 0 on follow-up `/watch` calls — once `--check` returned 0, nothing about the environment changes between turns.

## When to use

- User pastes a video URL (YouTube, Vimeo, X, TikTok, Twitch clip, most yt-dlp-supported sites) and asks about it.
- User points at a local video file (`.mp4`, `.mov`, `.mkv`, `.webm`, etc.) and asks about it.
- User types `/watch <url-or-path> [question]`.

## Recommended limits

- **Best accuracy: videos under 10 minutes.** Frame coverage scales inversely with duration.
- **Hard caps: 100 frames total and 2 fps.** Token cost grows with frame count, so the script targets a frame budget by duration (and never exceeds 2 fps even when the budget would imply more):
  - ≤30s → ~1-2 fps (up to 30 frames)
  - 30s-1min → ~40 frames
  - 1-3min → ~60 frames
  - 3-10min → ~80 frames
  - \>10min → 100 frames, sparsely spaced (warning printed)
- If the user hands you a long video, consider asking whether they want a specific section before burning tokens on a sparse scan.

## How to invoke

**Step 1 — parse the user input.** Separate the video source (URL or path) from any question the user asked. Example: `/watch https://youtu.be/abc what language is this in?` → source = `https://youtu.be/abc`, question = `what language is this in?`.

**Step 2 — run the watch script.** Pass the source verbatim. Do not shell-escape it yourself beyond normal quoting:

```bash
python3 "${CLAUDE_SKILL_DIR}/scripts/watch.py" "<source>"
```

Optional flags:
- `--start T` / `--end T` — focus on a section. Accepts `SS`, `MM:SS`, or `HH:MM:SS`. When either is set, fps auto-scales denser (see "Focusing on a section" below).
- `--max-frames N` — lower the cap for tighter token budget (e.g. `--max-frames 40`)
- `--resolution W` — change frame width in px (default 512; bump to 1024 only if the user needs to read on-screen text)
- `--fps F` — override auto-fps (clamped to 2 fps max)
- `--out-dir DIR` — keep working files somewhere specific (default: an auto-generated tmp dir)
- `--cookies-from-browser B` — read cookies from a local browser (`chrome`, `firefox`, `safari`, `edge`, `brave`, …) for login-gated sources
- `--cookies FILE` — path to a Netscape-format `cookies.txt` (alternative to `--cookies-from-browser`)
- `--whisper mlx|openai-whisper` — force a specific local Whisper engine (default: prefer mlx-whisper, fall back to openai-whisper)
- `--no-whisper` — disable the local Whisper fallback entirely (frames-only if no captions)

### Login-gated sources (Instagram, X, private/age-restricted videos)

Public videos (most of YouTube, Vimeo, TikTok, Loom, etc.) download with no auth. But some sources gate the download behind a login: **Instagram, X/Twitter, age-restricted or private/unlisted YouTube, members-only content**. Those need the *user's own* cookies.

**Do NOT pass cookies pre-emptively.** Always try the plain download first. Only reach for cookies when it fails with a login / private / 403 / "login required" / "rate-limit" error. The user never types the flag themselves — you add it and re-run. When that happens, walk the user through it (these are sub-steps of the main Step 2, not the main flow):

**(a) Ask which browser they're logged into.** "To grab this Instagram video I need to borrow the cookies from a browser where you're logged into Instagram. Which one are you logged in on — Chrome, Safari, Firefox, Edge, or Brave?" Supported values: `chrome`, `firefox`, `safari`, `edge`, `brave`, `chromium`, `opera`, `vivaldi`.

**(b) Re-run with that browser** (on Windows use `python`, not `python3` — see Step 0):
```bash
python3 "${CLAUDE_SKILL_DIR}/scripts/watch.py" "https://www.instagram.com/reel/XXXX/" --cookies-from-browser chrome
```

**(c) Handle the common per-browser snags** (tell the user the specific fix, don't just retry):
- **Chrome on macOS** locks its cookie DB while open *and* its cookies are encrypted. Two things may happen: (1) extraction fails with "could not copy/open the cookie database" → tell the user to **fully quit Chrome** (Cmd-Q, not just close the window) and retry; (2) a macOS **Keychain prompt** pops up ("… wants to use your confidential information stored in Chrome Safe Storage") → tell the user to click **Always Allow**. If Chrome keeps fighting it, suggest they switch to Safari or Firefox.
- **Chrome on Windows** also locks the DB while running → tell the user to fully close it (check the system tray) and retry.
- **Safari on macOS** needs the app running this (the terminal / Claude Code) to have **Full Disk Access** (System Settings → Privacy & Security → Full Disk Access). If Safari extraction fails, point them there, or fall back to another browser.
- **Firefox** usually works without closing it — good fallback on any OS when Chrome is stubborn.

**(d) Manual fallback if browser extraction just won't cooperate** (most reliable, works on macOS / Windows / Linux): guide the user to export a `cookies.txt` and pass it with `--cookies`:
1. Install a cookies-export extension — **"Get cookies.txt LOCALLY"** (open-source, exports Netscape format) for Chrome/Edge, or **"cookies.txt"** for Firefox.
2. Open and **log into the site** (e.g. `instagram.com`).
3. Click the extension → **Export** → save the file (e.g. `~/Downloads/cookies.txt`).
4. Re-run: `python3 "${CLAUDE_SKILL_DIR}/scripts/watch.py" "<url>" --cookies ~/Downloads/cookies.txt`

**Privacy note to reassure the user:** cookies are read live from their own machine and piped straight into the yt-dlp subprocess. The skill never copies, stores, logs, or transmits them anywhere. The `cookies.txt` file (if they used the manual fallback) stays on their disk — they can delete it after.

### Focusing on a section (higher frame rate)

When the user asks about a specific moment — "what happens at the 2 minute mark?", "zoom into 0:45 to 1:00", "the first 10 seconds" — pass `--start` and/or `--end`. The script switches to focused-mode budgets, which are denser than full-video budgets (still capped at 2 fps):

- ≤5s → 2 fps (up to 10 frames)
- 5-15s → 2 fps (up to 30 frames)
- 15-30s → ~2 fps (up to 60 frames)
- 30-60s → ~1.3 fps (up to 80 frames)
- 60-180s → ~0.6 fps (100 frames, capped)

Focused mode is the right call for:
- Any moment/range the user names explicitly ("around 2:30", "the intro", "the last 30 seconds").
- Any video longer than ~10 minutes where the user's question is about a specific part — running focused on the relevant section is far more useful than a sparse scan of the whole thing.
- Re-runs after a full scan didn't have enough detail in some region.

Transcript is auto-filtered to the same range. Frame timestamps are absolute (real video timeline, not offset-from-start).

Examples:
```bash
# Last 10 seconds of a 1 minute video
python3 "${CLAUDE_SKILL_DIR}/scripts/watch.py" video.mp4 --start 50 --end 60

# Zoom into 2:15 → 2:45 at 3 fps (90 frames)
python3 "${CLAUDE_SKILL_DIR}/scripts/watch.py" "$URL" --start 2:15 --end 2:45 --fps 3

# From 1h12m to the end of the video
python3 "${CLAUDE_SKILL_DIR}/scripts/watch.py" "$URL" --start 1:12:00
```

**Step 3 — Read every frame path the script lists.** The Read tool renders JPEGs directly as images for you. Read all frames in a single message (parallel tool calls) so you see them together. The frames are in chronological order with a `t=MM:SS` timestamp so you can align them to the transcript.

**Step 4 — answer the user.** You now have two streams of evidence:
- **Frames** — what's on screen at each timestamp
- **Transcript** — what's said at each timestamp. The report's header shows the source (`captions` = yt-dlp pulled native subs; `whisper (mlx)` or `whisper (openai-whisper)` = transcribed locally on-device).

If the user asked a specific question, answer it directly citing timestamps. If they didn't ask anything, summarize what happens in the video — structure, key moments, notable visuals, spoken content.

**Step 5 — clean up.** The script prints a working directory at the end. If the user isn't going to ask follow-ups about this video, delete it with `rm -rf <dir>`. If they might, leave it in place.

## Transcription

The script gets a timestamped transcript in one of two ways:

1. **Native captions (free, preferred).** yt-dlp pulls manual or auto-generated subtitles from the source platform if available.
2. **Local Whisper fallback (on-device, no API, no key).** If no captions came back (or the source is a local file), the script extracts audio (`ffmpeg -vn -ac 1 -ar 16000 -b:a 64k`, ~0.5 MB/min) and transcribes it locally:
   - **mlx-whisper** — `mlx-community/whisper-large-v3-turbo`. Preferred on Apple Silicon: fast, runs on the GPU/Neural Engine. Same engine ig-scraper uses. Install: `pip3 install mlx-whisper`.
   - **openai-whisper** — `base` model on CPU. Cross-platform fallback when mlx isn't available. Install: `pip3 install openai-whisper`.

The audio never leaves the machine. The script prefers mlx-whisper; override with `--whisper openai-whisper`. Language is auto-detected. Use `--no-whisper` to skip the fallback entirely.

## Failure modes and handling

- **Setup preflight failed** → run `python3 "${CLAUDE_SKILL_DIR}/scripts/setup.py"` (auto-installs ffmpeg/yt-dlp via brew on macOS; prints exact commands on Windows/Linux). If it reports no whisper engine, relay the exact `pip3 install …` command it printed (`mlx-whisper` only on Apple Silicon, `openai-whisper` elsewhere).
- **No transcript available** → captions missing AND (no local whisper engine OR `--no-whisper` set OR transcription failed). Script prints a hint pointing to setup. Proceed frames-only and tell the user.
- **Long video warning printed** → acknowledge it in your answer. Offer to re-run focused on a specific section via `--start`/`--end` rather than a sparse full-video scan.
- **Download fails (login/private/403)** → the source needs auth (common on Instagram, X, age-restricted or private videos). Re-run with `--cookies-from-browser <browser>` using a browser the user is logged into (see "Login-gated sources" above). If it's region-locked or genuinely unavailable, tell the user plainly; do not keep retrying.
- **Whisper fails** → the error is printed to stderr (likely: engine not installed, or a video with no audio track). The report will say "none available" for transcript. The first mlx run also downloads the model (~1.5 GB) once, then caches it.

## Token efficiency

This skill burns tokens primarily on frames. Order of magnitude:
- 80 frames at 512px wide is roughly 50-80k image tokens depending on aspect ratio.
- The transcript is cheap (a few thousand tokens at most for a 10-minute video).
- Bumping `--resolution` to 1024 roughly quadruples the image tokens per frame. Only do it when necessary.

If you already watched a video this session and the user asks a follow-up, do **not** re-run the script — you already have the frames and transcript in context. Just answer from what you have.

## Security & Permissions

**What this skill does:**
- Runs `yt-dlp` locally to download the video and pull native captions when the source supports them (public data; the request goes directly to whatever host the URL points at)
- Runs `ffmpeg` / `ffprobe` locally to extract frames as JPEGs and, when Whisper is needed, a mono 16 kHz audio clip
- Transcribes the audio clip **locally on-device** with mlx-whisper (or openai-whisper as a CPU fallback) — no network call, no API, no key
- Writes the downloaded video, frames, audio, and an intermediate transcript to a working directory under the system temp dir (or `--out-dir` if specified) so Claude can `Read` them
- On first mlx run, downloads the whisper model (~1.5 GB) from Hugging Face once and caches it under `~/.cache/huggingface`

**What this skill does NOT do:**
- Does not upload the video OR the audio to any API — transcription is fully local. The only outbound traffic is yt-dlp fetching the video/captions from the source URL (and the one-time model download)
- Does not log into or post to any account. It only reads browser cookies when the user explicitly passes `--cookies-from-browser` / `--cookies` for a login-gated source, and only to authenticate the yt-dlp download. Those cookies are read live and never copied, stored, logged, or transmitted by the skill
- Does not use, store, or require any API key — there is no `.env`, no config file, no secrets
- Does not persist anything outside the working directory and the Hugging Face model cache — clean up the working directory when you're done (Step 5)

**Bundled scripts:** `scripts/watch.py` (entry point), `scripts/download.py` (yt-dlp wrapper), `scripts/frames.py` (ffmpeg frame extraction), `scripts/transcribe.py` (caption parsing), `scripts/whisper.py` (local mlx/openai-whisper transcription), `scripts/setup.py` (preflight + installer)

Review scripts before first use to verify behavior.
