#!/usr/bin/env bash
# A book digested in an earlier session: the split parts and finished notes.
set -euo pipefail
mkdir -p digests/text/sleep-science
cat > digests/text/sleep-science/01-chapter-1-naps-and-memory.md <<'FIXTURE'
---
type: Source Material
title: "sleep-science - part 01"
description: "Part 01 of sleep-science.txt: Chapter 1: Naps and memory."
generated: { by: process:extract_book, at: "2026-09-25T16:33:32+00:00" }
---

# Chapter 1: Naps and memory

(Source: sleep-science.txt)

A short nap does more for memory than most readers expect. In the Lund cohort (n = 412), a 20-minute nap improved word-list recall by 23.7% compared with quiet rest (Table 3). The effect held for adults over 60, though it was smaller: 11.2% (Table 4).

The author defines a sleep spindle as a burst of 11 to 16 Hz activity lasting half a second to two seconds, seen mostly in stage 2 sleep. Spindle density, not nap length, predicted the recall gain.

The chapter walks through how the Lund team ran the study. Volunteers learned a list of word pairs in the early afternoon, then either napped in a quiet room or sat and rested with their eyes open for the same length of time. Everyone was tested again in the late afternoon, and the testers did not know who had slept. The author spends several pages on why the resting group matters: without it, any gain could simply come from a break away from the screen, not from sleep itself.

She also describes the recordings. Each napper wore a light headband that recorded brain activity, so the team could count spindles and see which stage of sleep each person reached. People who never left the lightest stage of sleep gained little. People who reached stage 2 and produced many spindles gained the most, whatever the exact length of the nap.

Case: a night-shift nurse who napped for 20 minutes before her 3 a.m. medication round made fewer transcription errors over six weeks. The author uses her story to show that the effect is not confined to the laboratory, while warning that one person's experience proves nothing on its own.

The author rejects the popular claim that any nap longer than an hour is harmful. What matters, she argues, is waking from light sleep, not the clock. Someone who wakes from deep sleep feels groggy for a while, and that grogginess, not the nap, gives long naps their bad name.

This chapter does not cover naps in children.
FIXTURE
cat > digests/text/sleep-science/02-chapter-2-light-at-night.md <<'FIXTURE'
---
type: Source Material
title: "sleep-science - part 02"
description: "Part 02 of sleep-science.txt: Chapter 2: Light at night."
generated: { by: process:extract_book, at: "2026-09-25T16:33:32+00:00" }
---

# Chapter 2: Light at night

(Source: sleep-science.txt)

Evening light delays the body clock. Blue-enriched light at 400 lux delayed melatonin onset by 1.9 hours (Study B, n = 58), while warm light at the same brightness delayed it by 0.6 hours.

The author defines circadian phase as the timing of the body clock relative to local time, measured here by dim-light melatonin onset.

Study B took place over two weeks in a university residence. Students spent their evenings under one of two lamps, with the brightness matched by a light meter each night. Saliva samples taken every half hour from late afternoon showed when melatonin began to rise. The author points out that the two groups went to bed at the same time on average, which is why the melatonin timing, not the bedtime, is the measure that counts.

She then turns to everyday settings. Kitchen lights, bathroom mirrors and phone screens all add to the evening dose, and the dose adds up over a whole evening rather than resetting with each lamp. A dim room with one bright screen can still push the clock later than a softly lit room with no screen at all.

Case: students who switched their desk lamps to warm light fell asleep 24 minutes earlier on average within two weeks. The author notes that the students chose to switch, so the group may have cared more about sleep than most.

The author rejects the idea that screen night modes solve the problem on their own; brightness matters as much as colour. A night mode at full brightness can still delay the clock more than a dim screen in its normal colours.

The chapter closes with advice the author is careful to label as her own reading of the evidence rather than a finding. Dim the whole home in the last two hours before bed, not only the screen in your hand. Prefer lamps placed low and to the side over bright ceiling lights. Keep mornings bright, because morning light pulls the clock earlier and partly cancels a late evening. She admits that none of this has been tested as a package, only piece by piece, and that people differ widely in how strongly their clocks respond.

This chapter does not cover shift-work lighting.
FIXTURE
cat > digests/text/sleep-science/00-contents.md <<'FIXTURE'
---
type: Source Material
title: "sleep-science - contents"
description: "Parts and word counts extracted from sleep-science.txt."
generated: { by: process:extract_book, at: "2026-09-25T16:33:32+00:00" }
---

# Contents: sleep-science.txt

2 parts, 721 words. Split by chapter headings in the text.

- `01-chapter-1-naps-and-memory.md` - Chapter 1: Naps and memory (339 words)
- `02-chapter-2-light-at-night.md` - Chapter 2: Light at night (372 words)
FIXTURE
mkdir -p digests/notes/sleep-science
cat > digests/notes/sleep-science/00-overview.md <<'FIXTURE'
# Overview: sleep-science

| Part | Notes | Topic |
|---|---|---|
| `digests/text/sleep-science/01-chapter-1-naps-and-memory.md` | `01-chapter-1-naps-and-memory.md` | Short naps and word-list recall |
| `digests/text/sleep-science/02-chapter-2-light-at-night.md` | `02-chapter-2-light-at-night.md` | Evening light and the body clock |

## Shared terms

- Sleep spindle (01), circadian phase (02)

## Key numbers

- Nap recall gain, Lund cohort: see `01-chapter-1-naps-and-memory.md`
- Melatonin delay under blue-enriched light: see `02-chapter-2-light-at-night.md`

## What this source does not contain

- Naps in children; shift-work lighting
FIXTURE
cat > digests/notes/sleep-science/01-chapter-1-naps-and-memory.md <<'FIXTURE'
# Notes: Chapter 1, Naps and memory

## Source
`01-chapter-1-naps-and-memory.md`, "Chapter 1: Naps and memory"

## Main argument
A short nap improves memory, and the gain depends on reaching stage 2 sleep with many spindles, not on how long the nap lasts.

## Numbers and study results
- "In the Lund cohort (n = 412), a 20-minute nap improved word-list recall by 23.7% compared with quiet rest (Table 3)."
- "The effect held for adults over 60, though it was smaller: 11.2% (Table 4)."

## Terms
- Sleep spindle: "a burst of 11 to 16 Hz activity lasting half a second to two seconds, seen mostly in stage 2 sleep"

## Cases and examples
- A night-shift nurse who napped for 20 minutes before a 3 a.m. round made fewer transcription errors over six weeks.

## Claims the author rejects
- That any nap longer than an hour is harmful.

## Not covered here
- Naps in children.
FIXTURE
cat > digests/notes/sleep-science/02-chapter-2-light-at-night.md <<'FIXTURE'
# Notes: Chapter 2, Light at night

## Source
`02-chapter-2-light-at-night.md`, "Chapter 2: Light at night"

## Main argument
Evening light delays the body clock, and brightness matters as much as colour.

## Numbers and study results
- "Blue-enriched light at 400 lux delayed melatonin onset by 1.9 hours (Study B, n = 58), while warm light at the same brightness delayed it by 0.6 hours."

## Terms
- Circadian phase: "the timing of the body clock relative to local time, measured here by dim-light melatonin onset"

## Cases and examples
- Students who switched to warm desk lamps fell asleep 24 minutes earlier on average within two weeks.

## Claims the author rejects
- That screen night modes solve the problem on their own.

## Not covered here
- Shift-work lighting.
FIXTURE
