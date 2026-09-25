# Freshness: digesting-books

Last reviewed: 2026-09-25

| Fact | Where the skill relies on it | How to check |
|---|---|---|
| `pypdf` is the PDF reader, installed with `python3 -m pip install pypdf`, and exposes `PdfReader(...).pages[i].extract_text()` | `SKILL.md` step 1; `scripts/extract_book.py`, PDF branch | `https://pypi.org/pypi/pypdf/json` for the latest version, then its changelog for removals or renames of `PdfReader` or `extract_text`. Install the latest and run `python3 scripts/extract_book.py --self-check` |
| The script's self-check passes on current Python | `scripts/extract_book.py` | `python3 scripts/extract_book.py --self-check` prints `self-check OK` |
| Calibre converts `.mobi` to `.epub` (`ebook-convert book.mobi book.epub`) | `SKILL.md`, *When to use* | Calibre's `ebook-convert` manual; a search for Calibre MOBI support being dropped |
| Claude Code's Read tool stops at a line limit, and reading resumes with an offset | `SKILL.md` step 3 | The tools reference in the Claude Code docs (`https://code.claude.com/docs/en/`), Read tool section |

## Behaviour that depends on the model

- Notes must copy numbers verbatim and add no general knowledge. A model that summarises
  more freely drifts on both; the evals check it.
- The skill writes notes part by part to disk because a long book does not fit in one
  context. A model with a much larger context may try to read the whole book first.
  Keep the part-by-part rule unless the evals show it no longer helps.

Observed on 2026-09-25 (Claude Code 2.1.282, default model): the skill did not trigger for
a question answered from an existing digest ("From my sleep-science digest: ..."). The
model found the notes on its own and answered correctly, but skipped `00-overview.md`.
The eval `later-work-reads-notes` fails on this, on purpose. Proposed fix, not yet made:
add to the description "or when a question should be answered from a book already
digested under `digests/notes/`".
