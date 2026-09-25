#!/usr/bin/env bash
# Re-apply the Gemini native-YouTube fallback to mcp-video-analyzer.
#
# THE GAP THIS FILLS
# mcp-video-analyzer reaches YouTube through yt-dlp. A blocked download (region, login,
# age gate, throttling) or a long captionless video with no Whisper backend comes back
# with an empty transcript. Gemini reads a public YouTube URL natively, with no
# download, so a small stdlib-only script covers exactly those two gaps. The design is
# recorded in bootstrap-device/scoring-layer-2.md, "mcp-video-analyzer -- Gemini
# native-YouTube fallback".
#
# WHY A PATCH
# This is a BSO-local addition, not an upstream contribution. It was first made by
# hand, and the weekly re-vendor of 2026-09-21 (v0.9.0 -> v0.10.1) deleted all of it
# without a word, because revendor.sh replaces the whole plugin directory. As a patch
# it is re-applied after every re-vendor, like everything else in this directory.
#
# WHAT IT DOES -- three changes, each skipped when already in place:
#   1. copies mcp-video-analyzer/gemini_youtube_fallback.py into the plugin's scripts/
#   2. appends mcp-video-analyzer/skill-section.md to skills/video/SKILL.md
#   3. inserts mcp-video-analyzer/readme-note.md into README.md, directly after the
#      transcription environment table (the row for OPENAI_API_KEY)
#
# Exits 1 when the README anchor is gone. Guessing a new spot would bury the note;
# failing stops the weekly job, so a person chooses where it goes.
#
# Idempotent. The plugin is MIT, so no MODIFICATIONS.md is written -- that obligation
# is Apache-2.0 only (see _apache_notice.py).
set -euo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
ASSETS="$HERE/mcp-video-analyzer"
PLUGIN="${1:-$HERE/../plugins/mcp-video-analyzer}"

if [ ! -d "$PLUGIN" ]; then
  echo "add-gemini-youtube-fallback: plugin not vendored -- nothing to do."
  exit 0
fi

if ! command -v python3 >/dev/null 2>&1; then
  echo "add-gemini-youtube-fallback: python3 not found -- cannot re-apply the fallback."
  exit 1
fi

python3 - "$PLUGIN" "$ASSETS" <<'PY'
import pathlib, sys

plugin, assets = (pathlib.Path(p) for p in sys.argv[1:3])
changed = []

script_src = assets / "gemini_youtube_fallback.py"
script_dst = plugin / "scripts" / "gemini_youtube_fallback.py"
if not script_dst.exists() or script_dst.read_bytes() != script_src.read_bytes():
    script_dst.parent.mkdir(parents=True, exist_ok=True)
    script_dst.write_bytes(script_src.read_bytes())
    script_dst.chmod(0o644)
    changed.append(str(script_dst))

section = (assets / "skill-section.md").read_text(encoding="utf-8")
skill = plugin / "skills" / "video" / "SKILL.md"
text = skill.read_text(encoding="utf-8")
if section.splitlines()[0] not in text:
    skill.write_text(text.rstrip("\n") + "\n\n" + section, encoding="utf-8")
    changed.append(str(skill))

note = (assets / "readme-note.md").read_text(encoding="utf-8")
readme = plugin / "README.md"
lines = readme.read_text(encoding="utf-8").splitlines(keepends=True)
if note.splitlines()[0] not in "".join(lines):
    anchor = next((i for i, l in enumerate(lines) if l.startswith("| `OPENAI_API_KEY` |")), None)
    if anchor is None:
        sys.exit("add-gemini-youtube-fallback: the OPENAI_API_KEY row is gone from README.md -- "
                 "upstream reshaped its transcription table. Choose a new spot for "
                 "patches/mcp-video-analyzer/readme-note.md and update this script.")
    at = anchor + 1
    if at < len(lines) and lines[at].strip() == "":
        at += 1
    lines[at:at] = [note.rstrip("\n") + "\n", "\n"]
    readme.write_text("".join(lines), encoding="utf-8")
    changed.append(str(readme))

for path in changed:
    print(f"add-gemini-youtube-fallback: restored {path}")
PY
