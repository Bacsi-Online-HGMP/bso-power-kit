---
name: youtube-video-perception
description: Extract YouTube video metadata, timestamped transcripts, and sampled visual keyframes using yt-dlp and ffmpeg for AI multimodal vision processing. Use when asked to watch, see, summarize, transcribe, or analyze a YouTube video URL.
---

# YouTube Video Perception Skill

This skill enables AI agents to "see" and analyze YouTube videos by extracting metadata, timestamped transcripts, and sampled keyframe images for multimodal vision models.

## Prerequisites

Ensure `yt-dlp` and `ffmpeg` are installed on the system:
- `yt-dlp`: `brew install yt-dlp` or `pip install yt-dlp`
- `ffmpeg`: `brew install ffmpeg`

## Workflow / How to execute

When the user provides a YouTube URL and asks to "see", "watch", "summarize", or "analyze" it:

1. **Run the extraction script:**
   ```bash
   python3 ./scripts/extract_youtube_data.py "<YOUTUBE_URL>" -o "./yt_data" --interval 10 --max-frames 30
   ```

2. **Inspect the output artifacts:**
   The output directory will contain:
   - `metadata.json`: Video title, author, duration, chapter timestamps, description.
   - `transcript.txt`: Timestamped transcript text extracted from closed captions / auto-subtitles.
   - `frames/`: Directory containing sampled keyframes (`frame_001.jpg`, `frame_002.jpg`, etc.).

3. **Multimodal Visual Analysis:**
   - Read `metadata.json` and `transcript.txt`.
   - Inspect the keyframe images in `frames/` to visually evaluate what is happening on screen (code snippets, diagrams, human actions, UI elements, slides).
   - Synthesize both visual and textual information to answer user questions or provide a comprehensive video breakdown.

## Customization Options

- `--interval <N>`: Set sampling rate in seconds (default: 10).
- `--max-frames <M>`: Cap maximum number of extracted images (default: 30).
- `--max-height <H>`: Resolution height cap to optimize speed and bandwidth (default: 720).
