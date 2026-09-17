---
name: digesting-books
description: Use when a book, textbook, guideline, thesis, long report or other long PDF, EPUB or DOCX has to be read and kept as reusable notes, when the user asks to digest, ingest, load or take notes on a book or reference material, or when later work needs a long source that was read in an earlier session.
---

# Digesting books

## Overview

Read a long source once. Write notes chapter by chapter. Later work reads the notes, not the book.
`scripts/extract_book.py` splits the book into chapter files. The reading and the notes are your job.

## When to use

- A textbook, guideline, thesis, long report or book as PDF, EPUB, DOCX, TXT or MD.
- A long source that later sessions will need again.

Do not use it for a short article that you read once. A scanned PDF needs OCR first.
A `.mobi` file needs conversion to `.epub` with Calibre first.

## Project rules come first

If the project's CLAUDE.md says where sources and notes go, or how an ingest runs, follow it and
use its paths instead of the paths below. Never write into a folder that the project marks
read-only, such as `sources/`.

## Steps

1. **Split the book.** The script is in `scripts/` in this skill's base directory (shown when the
   skill loads). A PDF needs `pypdf`: `python3 -m pip install pypdf`.
   ```bash
   python3 <skill-base-dir>/scripts/extract_book.py <book-or-folder> --out digests/text
   ```
   The output is `digests/text/<book>/00-contents.md` and one `NN-<chapter>.md` file per part.

2. **Check the split.** Read `00-contents.md`.
   - It has "Split warnings" or "Files not written by this run": tell the user which parts are
     affected and what they contain before you write notes. Do not merge, delete or rename parts.
   - It says "Split by every 3000 words": the parts are not chapters. Tell the user.
   - The total is more than 50,000 words: tell the user the part count and ask whether to digest
     every part or only selected parts.

3. **Read and write notes, one part at a time.** Read the whole part file. If the Read tool stops
   before the end, continue with an offset until the end. Write
   `digests/notes/<book>/NN-<chapter>.md` before you open the next part. A long book does not fit
   in one context, and notes on disk survive. Each notes file has these sections, in this order:
   - `Source`: the part file name and its title
   - `Main argument`: 2 to 5 sentences
   - `Numbers and study results`: each one quoted verbatim, with the study or table it comes from
   - `Terms`: as the author defines them
   - `Cases and examples`
   - `Claims the author rejects`
   - `Not covered here`

4. **Write the overview** in `digests/notes/<book>/00-overview.md`:
   - a table with the part file, the notes file and a one-line topic
   - the terms that several chapters share
   - the key numbers, each with its notes file
   - `What this source does not contain`

5. **Report** the parts you read, the warnings, and the notes folder.

## Later work

Read `00-overview.md`, then only the notes files that the task needs. Open a part file in
`digests/text/` only to check a quote. Do not read the whole book again.

## Common mistakes

| Mistake | Fix |
|---|---|
| A number is rounded or reworded | Copy it verbatim, with its source |
| General knowledge is added to the notes | Leave it out. The notes record only what the source says |
| Notes are written from the contents page or the first pages of a part | Read every part to the end |
| A split warning is ignored | A false split hides or duplicates a chapter. Check it first |
| Long passages are copied into the notes | Paraphrase. Quote only numbers, definitions and short key sentences |
