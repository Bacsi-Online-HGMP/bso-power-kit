---
type: Agent Instructions
title: bso-power-kit — house rules for AI
description: Rules for AI in the shared plugin and skill marketplace repo.
tags: [agent, rules]
authority: binding
status: stable
generated: { by: claude/opus-5, at: 2026-08-20T04:10:00Z }
---

<!-- lang-exception: documents the carve-out, which names Vietnamese paths. -->

# bso-power-kit — house rules for AI

The shared plugin and skill marketplace. **Nothing BSO-specific belongs here** — no claims, no
disclaimers, no brand identity, no production procedures. Anything carrying BSO rules or identity
goes to `bso-marketing` instead.

## Two things to know before editing

**`tools/` and `plugins/` are vendored third-party code.** Do not translate, reformat or "improve"
them. Where an upstream file has been edited (see `bootstrap-device/scoring-layer-2.md`), that edit
is recorded so it can be reconciled on the next upstream update.

**`bootstrap-device/plugins-claude-code.tsv` is generated.** Only the `pack` column is edited by
hand; `export-plugins.sh` preserves it and regenerates everything else. Rejections live in
`plugins-loai.tsv` so they are not re-litigated.

---

## 🔴 HARD RULE — every commit is in English

**This is a hard stop, enforced by the pre-commit hook. It is not a style preference.**

Everything committed to any of the three repos — `bso-marketing`, `bso-strategy`, `bso-power-kit` —
is written in **English**. That covers, without exception:

- document bodies, headings, tables, and frontmatter keys **and** values
- **code**: comments, docstrings, variable and function names, `echo` / `print` / log output,
  error and usage messages, `--help` text
- `.bat` / `.ps1` / `.sh` scripts, `.tsv` and `.txt` headers, JSON and YAML comments
- commit messages, branch names, PR titles and descriptions

### The only Vietnamese that may be committed

The carve-out is **final product content and regulator-facing wording**. It does not grow:

| Stays Vietnamese | Why |
|---|---|
| `assets/scripts/**` | Narration and on-screen copy for a Vietnamese audience |
| `assets/outlines/**` | The episode outlines those scripts come from |
| `core/claims-matrix/**` · `core/disclaimers.md` | Legally binding wording shown to a Vietnamese regulator |
| `core/rules/vn/nghi-dinh-vn/_ocr/**` | OCR of Vietnamese decrees — a primary source |
| `assets/skills/supplement-compliance/references/vn/**` | Vietnamese claim-language rules |
| `assets/skills/vietnamese-anti-slop/**` | Rules about writing Vietnamese prose; the examples are the content |
| Drive `output/**` · Drive `source/INPUT/**` | Finished product folders and the Vietnamese production material |

Anything in the carve-out keeps its **byte-for-byte** Vietnamese. Never "tidy up" an approved claim,
a disclaimer, or a decree quotation — rewording an approved claim creates a new claim, which is a
regulatory breach.

### Everything else that needs Vietnamese must declare it

A file outside the carve-out that genuinely needs Vietnamese — an on-screen copy example, a verbatim
quotation used as evidence, a regex that matches Vietnamese text — declares it with one line
anywhere in the file:

```
lang-exception: <the reason>
```

The pre-commit hook skips a file carrying that marker. Use it for a real reason, never to get a
commit through.

### How it is enforced

`assets/tools/git-hooks/pre-commit` reads the **added lines** of the staged diff and blocks the
commit when it finds Vietnamese diacritics outside the carve-out. Existing Vietnamese never blocks
an unrelated edit — only newly added Vietnamese does.

Install it once per machine, in every repo at the project root:

```bash
sh bso-marketing/assets/tools/git-hooks/install.sh
```

The hook is a safety net, not the rule. It catches diacritics; it cannot catch Vietnamese written
without them (`Cai dat`, `thu muc`, `khong`). **Write English in the first place.**

`git commit --no-verify` bypasses the hook. Using it to push Vietnamese is a violation, not a
workaround.
