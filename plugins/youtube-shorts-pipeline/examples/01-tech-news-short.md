# Example 01 — Tech news Short, full pipeline

Goal: turn a one-line headline into an uploaded YouTube Short using the default providers (Claude for script, Gemini for b-roll, Edge TTS for voice).

## Keys needed

- `ANTHROPIC_API_KEY` (script) — or swap `--provider` for `gemini`, `openai`, or `ollama`
- `GEMINI_API_KEY` (b-roll + thumbnail) — without it the pipeline uses solid-color fallback frames
- YouTube OAuth for the upload stage (`python scripts/setup_youtube_oauth.py`)

## Step 1 — Draft

```bash
python -m verticals draft --topic "Alpine Linux 3.24 released with major package updates" --niche tech
```

Expected output shape (script text will differ run to run):

```
  Drafting: Alpine Linux 3.24 released with major package updates [niche: tech, platform: shorts]

  Loaded niche profile: tech
  Researching topic via DuckDuckGo...
  Calling LLM via claude...

  Draft saved: ~/.verticals/drafts/1781048758.json

  Script:
  Alpine Linux 3.24 drops. Everyone's ignoring it. Here's the thing: ...

  Title: Alpine Linux 3.24 Breaks Everything You Didn't See Coming

  B-roll prompts:
  1. Close-up of terminal output showing Alpine Linux version ...
  2. Abstract data visualization with glowing nodes ...
  3. Minimalist shot of a circuit board macro ...
```

The draft JSON contains the script, platform metadata, b-roll prompts, and per-stage completion state, so every later stage is resumable.

## Step 2 — Produce

```bash
python -m verticals produce --draft ~/.verticals/drafts/1781048758.json --lang en
```

Expected output shape:

```
  Producing EN video for job 1781048758 [niche: tech]
  Generating b-roll frame 1/3 via Gemini Imagen...
  Generating b-roll frame 2/3 via Gemini Imagen...
  Generating b-roll frame 3/3 via Gemini Imagen...
  Generating en voiceover via Edge TTS (voice: en-US-GuyNeural)...
  Edge TTS voiceover saved: voiceover_en.mp3
  Transcribing with Whisper (word timestamps)...
  SRT captions saved: captions_en.srt
  ASS captions saved: captions_en.ass
  Assembling video...
  Video assembled: ~/.verticals/media/verticals_1781048758_en.mp4
```

Result: a 1080x1920 h264/aac MP4, roughly 45–90 seconds depending on the script. Verify with:

```bash
ffprobe -v quiet -show_entries stream=codec_name,width,height -of csv ~/.verticals/media/verticals_1781048758_en.mp4
# stream,h264,1080,1920
# stream,aac
```

Note: if your ffmpeg build lacks libass, the pipeline logs a warning and skips caption burn-in instead of failing; the SRT is still attached at upload.

## Step 3 — Upload

```bash
python -m verticals upload --draft ~/.verticals/drafts/1781048758.json --lang en
```

Uploads private by default with title, description, tags, SRT captions, and a generated thumbnail, then prints the video URL. Flip visibility in YouTube Studio when you are happy with it.

## One-command version

```bash
python -m verticals run --topic "Alpine Linux 3.24 released with major package updates" --niche tech
```

Runs all three stages back to back.
