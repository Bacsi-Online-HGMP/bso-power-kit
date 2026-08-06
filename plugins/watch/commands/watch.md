---
description: Watch a video (URL or local path). Downloads with yt-dlp, extracts frames with ffmpeg, transcribes from captions or local Whisper (no API key), and answers questions about what's in the video.
argument-hint: <video-url-or-path> [question]
allowed-tools: [Bash, Read]
---

Invoke the `watch` skill (defined in SKILL.md) with the user's arguments: $ARGUMENTS

Follow the skill's full pipeline: preflight setup check → download via yt-dlp (pass `--cookies-from-browser <browser>` for login-gated sources like Instagram or X) → extract frames at auto-scaled fps → pull captions or a local Whisper transcript → Read each frame → answer the user grounded in frames and transcript. If the user provided no arguments, ask them for a video URL or local path before proceeding.
