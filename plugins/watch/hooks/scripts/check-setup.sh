#!/usr/bin/env bash
# SessionStart hook for /watch — one-line status so users know what's wired up.
# Silent on a ready state to avoid spam. Points at the installer when something
# is missing. Everything runs locally: no API key, no config file, no secrets.
set -euo pipefail

HAS_FFMPEG=""
HAS_YTDLP=""
command -v ffmpeg >/dev/null 2>&1 && HAS_FFMPEG="yes"
command -v yt-dlp >/dev/null 2>&1 && HAS_YTDLP="yes"

# A local whisper engine is optional — captions cover most public videos.
HAS_WHISPER=""
if command -v python3 >/dev/null 2>&1; then
  if python3 - <<'PY' >/dev/null 2>&1
import importlib.util, sys
sys.exit(0 if (importlib.util.find_spec("mlx_whisper") or importlib.util.find_spec("whisper")) else 1)
PY
  then
    HAS_WHISPER="yes"
  fi
fi

# Binaries present → silent (whisper is optional, so its absence doesn't block).
if [[ -n "$HAS_FFMPEG" && -n "$HAS_YTDLP" ]]; then
  exit 0
fi

# First-run / partially-configured → one-line hint.
echo "/watch: needs ffmpeg + yt-dlp. Run \`python3 \$CLAUDE_PLUGIN_ROOT/scripts/setup.py\` once to install. Transcription runs fully on-device (no API key)."
