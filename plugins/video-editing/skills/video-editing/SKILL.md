---
name: video-editing
description: End-to-end video editing and production toolkit. Use this skill whenever
  the user wants to edit, create, convert, trim, compress, download, transcribe,
  understand, or produce video — or generate images, design systems, diagrams, and
  motion graphics for video. Covers local FFmpeg editing, downloading from YouTube
  and 1000+ sites, local transcription/understanding, FLUX image generation, visual
  design systems, Mermaid/D3 visuals, motion graphics, and an autonomous video
  pipeline. Trigger it for any request involving video files, clips, footage,
  voiceover-less editing, format conversion, subtitles, or assembling a finished video.
license: AGPL-3.0
metadata:
  provenance: Lifted and consolidated from OpenMontage (github.com/calesthio/OpenMontage), AGPLv3. Each tool's original guide and files live under references/<tool>/.
---

# Video Editing

A consolidated toolkit of 14 video/visual tools. Each tool lives under
`references/<tool>/guide.md` with its own scripts/assets — read the guide for the
tool you need before acting, then use its bundled files.

## Prerequisites
- **Local video tools need `ffmpeg` and `yt-dlp` installed.** Confirm they're on PATH first.
- **API-key tools** (`bfl-api`, `flux-best-practices`, `video_toolkit`) call paid
  services — set the key as an environment variable; never hardcode or pass it on
  the command line.

## Pick the tool

**Local video — no API key:**
| Task | Read |
|---|---|
| Convert / resize / compress / extract audio | `references/ffmpeg/guide.md` |
| Trim, concat, speed, overlay, edit | `references/video-edit/guide.md` |
| Download video/audio from YouTube + 1000+ sites | `references/video-download/guide.md` |
| Transcribe / understand a video locally (Whisper) | `references/video-understand/guide.md` |

**Image generation — needs FLUX/BFL key:**
| Task | Read |
|---|---|
| Generate images via the BFL FLUX API | `references/bfl-api/guide.md` |
| FLUX prompting & best practices | `references/flux-best-practices/guide.md` |

**Design & visuals — mostly local:**
| Task | Read |
|---|---|
| Create/extract a portable visual design system | `references/visual-style/guide.md` |
| Render Mermaid diagrams to SVG/PNG | `references/beautiful-mermaid/guide.md` |
| Build interactive d3.js data visualizations | `references/d3-viz/guide.md` |
| Tailwind v4 design system / tokens | `references/tailwind-design-system/guide.md` |
| Review UI for accessibility / design quality | `references/web-design-guidelines/guide.md` |
| Motion with Framer Motion (12 animation principles) | `references/framer-motion/guide.md` |
| Lottie / Bodymovin animations | `references/lottie-bodymovin/guide.md` |

**Autonomous pipeline:**
| Task | Read |
|---|---|
| Build a full video end-to-end (orchestrator) | `references/video_toolkit/guide.md` |

## Typical flow
Acquire (download or import) → understand (transcribe) → edit (ffmpeg/video-edit) →
add visuals/images (flux, d3, mermaid, motion) → assemble/render. For a hands-off
build, start from `video_toolkit`.

## Safety & licensing
AGPLv3 — fine for personal use; redistributing or running it as a network service
triggers source-sharing obligations. Only download/process content you're permitted
to use; the `faceswap`-style misuse concerns don't apply here (not included).
