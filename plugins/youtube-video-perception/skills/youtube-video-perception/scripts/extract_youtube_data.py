#!/usr/bin/env python3
"""
YouTube Video Perception Data Extractor
Extracts metadata, clean transcripts, and sampled visual keyframes from a YouTube video
so AI multimodal vision models can 'see' and analyze the video.
"""

import argparse
import json
import os
import re
import subprocess
import sys
from pathlib import Path

def run_command(cmd, check=True):
    """Executes a shell command and returns standard output."""
    result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    if check and result.returncode != 0:
        print(f"Error executing command: {' '.join(cmd)}", file=sys.stderr)
        print(f"Stderr: {result.stderr}", file=sys.stderr)
        result.check_returncode()
    return result.stdout

def clean_vtt(vtt_path):
    """Converts a WebVTT transcript file into clean, readable timestamped text."""
    if not os.path.exists(vtt_path):
        return ""
    
    with open(vtt_path, "r", encoding="utf-8") as f:
        lines = f.readlines()
    
    clean_lines = []
    seen_text = set()
    current_timestamp = ""
    
    for line in lines:
        line = line.strip()
        if not line or line.startswith("WEBVTT") or line.startswith("Kind:") or line.startswith("Language:"):
            continue
        
        # Match timestamp lines e.g., 00:00:01.500 --> 00:00:04.000
        ts_match = re.match(r"^(\d{2}:\d{2}:\d{2}\.\d{3}|\d{2}:\d{2}\.\d{3})\s+-->", line)
        if ts_match:
            current_timestamp = ts_match.group(1).rsplit('.', 1)[0]
            continue
        
        # Clean HTML tags and duplicates
        clean_text = re.sub(r"<[^>]+>", "", line).strip()
        if clean_text and clean_text not in seen_text:
            if current_timestamp:
                clean_lines.append(f"[{current_timestamp}] {clean_text}")
                current_timestamp = ""
            else:
                clean_lines.append(clean_text)
            seen_text.add(clean_text)
            
    return "\n".join(clean_lines)

def extract_youtube_data(url, output_dir, interval=10, max_frames=30, max_height=720):
    """Downloads metadata, transcript, and keyframes from a YouTube video."""
    out_path = Path(output_dir)
    out_path.mkdir(parents=True, exist_ok=True)
    frames_dir = out_path / "frames"
    frames_dir.mkdir(exist_ok=True)

    print(f"[*] Extracting metadata for: {url}")
    # 1. Extract JSON Metadata using yt-dlp
    meta_cmd = ["yt-dlp", "--dump-json", "--no-warnings", url]
    meta_stdout = run_command(meta_cmd)
    metadata = json.loads(meta_stdout)
    
    meta_file = out_path / "metadata.json"
    with open(meta_file, "w", encoding="utf-8") as f:
        json.dump({
            "id": metadata.get("id"),
            "title": metadata.get("title"),
            "uploader": metadata.get("uploader"),
            "duration": metadata.get("duration"),
            "view_count": metadata.get("view_count"),
            "description": metadata.get("description"),
            "chapters": metadata.get("chapters"),
            "webpage_url": metadata.get("webpage_url"),
            "thumbnail": metadata.get("thumbnail")
        }, f, indent=2)
    print(f"[+] Saved metadata to {meta_file}")

    # 2. Extract Subtitles / Transcript
    print("[*] Extracting transcript/subtitles...")
    sub_prefix = str(out_path / "sub")
    sub_cmd = [
        "yt-dlp",
        "--write-auto-subs",
        "--write-subs",
        "--sub-lang", "en,en-orig,vi,es,fr,de,ja",
        "--sub-format", "vtt",
        "--skip-download",
        "-o", sub_prefix,
        url
    ]
    run_command(sub_cmd, check=False)
    
    # Locate downloaded vtt
    vtt_files = list(out_path.glob("sub*.vtt"))
    clean_transcript = ""
    if vtt_files:
        clean_transcript = clean_vtt(vtt_files[0])
    
    transcript_file = out_path / "transcript.txt"
    with open(transcript_file, "w", encoding="utf-8") as f:
        f.write(clean_transcript if clean_transcript else "No subtitles found or available.")
    print(f"[+] Saved transcript to {transcript_file}")

    # 3. Extract Sampled Keyframes via yt-dlp + ffmpeg
    duration = metadata.get("duration", 0) or 0
    if duration > 0:
        calculated_interval = max(interval, int(duration / max_frames))
    else:
        calculated_interval = interval

    print(f"[*] Extracting video keyframes (1 frame every {calculated_interval} seconds)...")
    video_tmp = out_path / "temp_video.mp4"
    
    # Download lower resolution video for fast frame extraction
    dl_video_cmd = [
        "yt-dlp",
        "-f", f"bestvideo[height<={max_height}]+bestaudio/best[height<={max_height}]/best",
        "--merge-output-format", "mp4",
        "-o", str(video_tmp),
        url
    ]
    run_command(dl_video_cmd)

    # Use ffmpeg to sample keyframes
    ffmpeg_cmd = [
        "ffmpeg",
        "-y",
        "-i", str(video_tmp),
        "-vf", f"fps=1/{calculated_interval}",
        "-q:v", "2",
        str(frames_dir / "frame_%03d.jpg")
    ]
    run_command(ffmpeg_cmd)
    
    # Remove temp video file to conserve disk space
    if video_tmp.exists():
        os.remove(video_tmp)

    frame_count = len(list(frames_dir.glob("*.jpg")))
    print(f"[+] Extracted {frame_count} keyframe images in {frames_dir}")
    print(f"[✓] Pipeline complete! Output directory: {out_path.resolve()}")

def main():
    parser = argparse.ArgumentParser(description="Extract YouTube metadata, transcript, and keyframes for AI perception.")
    parser.add_argument("url", help="YouTube video URL")
    parser.add_argument("-o", "--output-dir", default="./yt_perception_data", help="Directory to save extracted files")
    parser.add_argument("-i", "--interval", type=int, default=10, help="Interval in seconds between extracted keyframes")
    parser.add_argument("-m", "--max-frames", type=int, default=30, help="Maximum number of frames to extract")
    parser.add_argument("--max-height", type=int, default=720, help="Maximum video resolution height for sampling (e.g. 720, 480)")
    
    args = parser.parse_args()
    extract_youtube_data(args.url, args.output_dir, args.interval, args.max_frames, args.max_height)

if __name__ == "__main__":
    main()
