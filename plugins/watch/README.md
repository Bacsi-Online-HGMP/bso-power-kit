# /watch — give Claude eyes for video

**Let Claude watch a video from almost anywhere — and transcribe it 100% on your machine, no API key.**

Paste a URL (YouTube, Instagram, X/Twitter, Vimeo, TikTok, Loom, and ~1800 more) or a local file, ask a question, and Claude downloads the video, extracts frames, pulls a timestamped transcript, and *reads every frame as an image*. By the time it answers, it has **seen** the video and **heard** the audio.

```
/watch https://youtu.be/dQw4w9WgXcQ what happens at the 30 second mark?
```

> This is a fork of [bradautomates/claude-video](https://github.com/bradautomates/claude-video). The big change: **transcription runs locally** via [mlx-whisper](https://github.com/ml-explore/mlx-examples/tree/main/whisper) (Apple Silicon) or [openai-whisper](https://github.com/openai/whisper) (CPU) instead of a paid Whisper API. No keys, no config file, no audio ever leaves your machine. Also adds browser-cookie support so login-gated sources (Instagram, X) work.

---

## Install

**Claude Code (plugin):**
```
/plugin marketplace add mathiaschu/claude-video
/plugin install watch@claude-video
```

**Generic skill folder (Codex, etc.):**
```bash
git clone https://github.com/mathiaschu/claude-video.git ~/.claude/skills/watch
```

Then run once to install dependencies (or let the first `/watch` do it):
```bash
python3 ~/.claude/skills/watch/scripts/setup.py
```

> **Windows:** use `python` instead of `python3` (the `python3` alias is a Microsoft Store stub). `ffmpeg` + `yt-dlp` install via the `winget` commands the setup script prints; for transcription use `pip install openai-whisper` (mlx-whisper is Apple Silicon only).

## Requirements

- **Python 3.9+**
- **ffmpeg** + **yt-dlp** — auto-installed via Homebrew on macOS; on Linux/Windows the installer prints the exact command.
- **A local Whisper engine** (only needed for videos *without* captions):
  - **mlx-whisper** — `pip3 install mlx-whisper` — preferred on Apple Silicon, runs on the GPU/Neural Engine.
  - **openai-whisper** — `pip3 install openai-whisper` — CPU fallback, cross-platform.

There is **no API key**. Captions cover most public videos for free; when a video has no captions, the audio is transcribed locally.

## How it works

1. **You paste a video and a question.** A URL (anything yt-dlp supports) or a local path (`.mp4`, `.mov`, `.mkv`, `.webm`, …).
2. **`yt-dlp` downloads it** into a temp working directory. Local files are probed in place, no download.
3. **`ffmpeg` extracts frames at an auto-scaled rate.** Duration-aware budget — ≤30s gets ~30 frames, 1-3min ~60, 3-10min ~80, longer 100 sparsely. Hard ceilings: 2 fps, 100 frames. JPEGs at 512px wide (bump with `--resolution 1024` to read on-screen text).
4. **The transcript comes from one of two places.** First: yt-dlp pulls native captions (free, instant). Fallback: a mono 16 kHz audio clip is transcribed **locally** with mlx-whisper / openai-whisper.
5. **Frames + transcript are handed to Claude.** It `Read`s each frame as an image and aligns them to the timestamped transcript.
6. **Claude answers grounded in what's on screen and in the audio** — not the title, not a guess.
7. **Cleanup.** The script prints its working directory; Claude removes it when you're done.

## Login-gated sources (Instagram, X, private videos)

Public videos download with no auth. For sources that require a login — Instagram, X/Twitter, age-restricted or private/unlisted YouTube — `/watch` needs **your own** browser cookies so yt-dlp can authenticate as you. You don't have to set anything up in advance: just run `/watch <url>` normally, and if it fails with a login/private error, do this.

### The easy way — borrow cookies from your browser

1. Make sure you're **logged into the site** (e.g. Instagram) in a normal browser.
2. Tell Claude which browser it is, or run it directly:

```
/watch https://www.instagram.com/reel/XXXX/ --cookies-from-browser chrome
```

Supported: `chrome`, `firefox`, `safari`, `edge`, `brave`, `chromium`, `opera`, `vivaldi`.

**macOS gotchas (the usual culprits):**
- **Chrome must be fully quit** (Cmd-Q, not just the window) — it locks its cookie database while running.
- A **Keychain prompt** may appear ("… wants to use confidential information stored in Chrome Safe Storage"). Click **Always Allow** — that's macOS letting the tool decrypt Chrome's cookies on your own machine.
- **Safari** requires giving your terminal / Claude Code **Full Disk Access** (System Settings → Privacy & Security → Full Disk Access).
- When in doubt, **Firefox** tends to "just work" without closing it.

### The reliable way — export a cookies.txt

If browser extraction keeps fighting you, export the cookies manually (works everywhere):

1. Install a cookies exporter: **"Get cookies.txt LOCALLY"** (Chrome/Edge) or **"cookies.txt"** (Firefox) — both open-source.
2. Open and log into the site (e.g. `instagram.com`).
3. Click the extension → **Export** → save it, e.g. `~/Downloads/cookies.txt`.
4. Run:

```
/watch https://www.instagram.com/reel/XXXX/ --cookies ~/Downloads/cookies.txt
```

### Privacy

**Your cookies are read live from your own machine and piped straight into yt-dlp.** The skill never copies, stores, logs, or transmits them. If you exported a `cookies.txt`, it stays on your disk — delete it whenever you want.

## Useful flags

| Flag | What it does |
|------|--------------|
| `--start T` / `--end T` | Focus on a section (`SS`, `MM:SS`, or `HH:MM:SS`); denser frame rate |
| `--max-frames N` | Lower the frame cap for a tighter token budget |
| `--resolution W` | Frame width in px (default 512; 1024 to read on-screen text) |
| `--fps F` | Override auto-fps (clamped to 2 fps) |
| `--cookies-from-browser B` | Read cookies from a local browser for login-gated sources |
| `--cookies FILE` | Use a Netscape-format `cookies.txt` instead |
| `--whisper mlx\|openai-whisper` | Force a specific local engine |
| `--no-whisper` | Skip transcription entirely (frames only) |

## Privacy

- **No API key, no account, no telemetry.** There is no `.env`, no config file, no secret of any kind.
- **Audio never leaves your machine** — transcription is fully on-device.
- The only outbound network traffic is yt-dlp fetching the video/captions from the source URL, and a one-time ~1.5 GB Whisper model download from Hugging Face (cached afterwards).

## Credits

Original skill: [bradautomates/claude-video](https://github.com/bradautomates/claude-video) (MIT). This fork swaps the Whisper API for local transcription and adds browser-cookie support. Licensed MIT — see [LICENSE](LICENSE).
