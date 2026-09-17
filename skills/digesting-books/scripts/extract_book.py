#!/usr/bin/env python3
"""extract_book.py - split a book or long document into one text file per chapter.

Claude reads the chapter files once and writes notes per chapter (see ../SKILL.md).
Later work reads the notes, not the book.

Formats: .pdf (needs pypdf)  .epub  .docx  .txt  .md
Not supported: .mobi (convert it to .epub with Calibre), scanned PDFs (run OCR first).

How a book is split, first match wins:
    1. PDF bookmarks, at chapter level (a Part is opened into its chapters,
       a chapter keeps its sections inside it)
    2. "Chapter N" / "Part N" headings in the text (also Vietnamese Chuong, Phan, Bai)
    3. every 3000 words

Output, per input file:
    <out>/<book-slug>/00-contents.md      parts, word counts, warnings
    <out>/<book-slug>/NN-<chapter>.md     one file per chapter

The text extraction comes from bso-marketing/tools/video-pipeline/_system/ingest_book.py,
without its video-series files. A bug fixed in one copy must be fixed in the other.

    python3 extract_book.py BOOK_OR_FOLDER [BOOK_OR_FOLDER ...] --out DIR
    python3 extract_book.py --self-check
"""

import argparse
import datetime
import html as html_mod
import json
import os
import re
import sys
import unicodedata
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET

# English and Vietnamese chapter headings, with or without diacritics:
# Chapter, Part, Chuong, Phan, Bai. Escapes keep the source file ASCII.
CHAPTER_RE = re.compile(
    r"^\s*(?:CH(?:UONG|\u01af\u01a0NG)|Ch(?:uong|\u01b0\u01a1ng)|CHAPTER|Chapter"
    r"|PH(?:AN|\u1ea6N)|Ph(?:an|\u1ea7n)|PART|Part|B(?:AI|\xc0I)|B(?:ai|\xe0i))"
    r"\s+(?:\d+|[IVXLC]+)\b.*$",
    re.MULTILINE,
)
FALLBACK_WORDS = 3000     # no chapter headings found -> cut every ~3000 words
MIN_PART_WORDS = 300      # smaller parts (cover, title page, Part divider) join the next part
MAX_PART_WORDS = 20000    # larger parts get a warning: the split probably missed chapters
MIN_CHAPTER_PAGES = 5     # a bookmark level with a shorter median length is sections, not chapters
D_STROKE = (("\u0111", "d"), ("\u0110", "D"))  # the one letter NFD cannot decompose


def slugify(text, maxlen=50):
    text = unicodedata.normalize("NFD", text)
    text = "".join(c for c in text if unicodedata.category(c) != "Mn")
    for a, b in D_STROKE:
        text = text.replace(a, b)
    text = re.sub(r"[^a-zA-Z0-9]+", "-", text).strip("-").lower()
    return text[:maxlen].rstrip("-") or "part"


# ---------- text extraction per format ----------
# Each extractor returns (text, chapters). chapters is None unless the file itself
# says where chapters start (PDF bookmarks).

def extract_txt(path):
    for enc in ("utf-8-sig", "utf-8", "cp1258", "latin-1"):
        try:
            return path.read_text(encoding=enc), None
        except (UnicodeDecodeError, LookupError):
            continue
    return path.read_text(encoding="utf-8", errors="replace"), None


def outline_starts(reader, n_pages):
    """Return [(title, first_page)] for the chapter-level PDF bookmarks, or [].

    Books nest bookmarks two ways: Part > Chapter, or Chapter > Section. Level 1 is
    used when its median length is chapter-sized, otherwise level 0. Level 1 keeps
    the level-0 entries too, so front matter and Part dividers are not lost.
    """
    flat = []

    def walk(items, depth):
        for it in items:
            if isinstance(it, list):  # pypdf puts the children right after their parent
                if depth < 1:
                    walk(it, depth + 1)
                continue
            try:
                page = reader.get_destination_page_number(it)
            except Exception:
                continue
            if page is not None:  # some publishers pad titles with NUL characters
                title = " ".join(re.sub(r"[\x00-\x1f\x7f]", " ", str(it.title)).split())
                flat.append((depth, title, page))

    walk(reader.outline, 0)

    def starts_at(level):  # stable sort: a parent stays before a child on the same page
        return sorted(((t, p) for d, t, p in flat if d <= level), key=lambda s: s[1])

    def median_span(starts):
        pages = [p for _, p in starts] + [n_pages]
        spans = sorted(b - a for a, b in zip(pages, pages[1:]))
        return spans[len(spans) // 2] if spans else 0

    deep = starts_at(1)
    if any(d == 1 for d, _, _ in flat) and median_span(deep) >= MIN_CHAPTER_PAGES:
        return deep
    return starts_at(0)


def extract_pdf(path):
    try:
        from pypdf import PdfReader
    except ImportError:
        sys.exit("[ERROR] pypdf is missing. Run: python3 -m pip install pypdf")
    reader = PdfReader(str(path))
    pages = []
    for i, page in enumerate(reader.pages):
        try:
            pages.append(page.extract_text() or "")
        except Exception:
            pages.append("")
        if (i + 1) % 50 == 0:
            print(f"    ... {i + 1}/{len(reader.pages)} pages")
    text = "\n".join(pages)
    try:
        starts = outline_starts(reader, len(pages))
    except Exception:
        starts = []
    if len(starts) < 2:
        return text, None
    chapters = [("Front matter", "\n".join(pages[:starts[0][1]]))]
    for i, (title, start) in enumerate(starts):
        end = starts[i + 1][1] if i + 1 < len(starts) else len(pages)
        chapters.append((title, "\n".join(pages[start:end])))
    return text, [(t, b.strip()) for t, b in chapters if b.strip()]


def _html_to_text(html):
    html = re.sub(r"(?is)<(script|style)[^>]*>.*?</\1>", " ", html)
    # a heading gets its own line so CHAPTER_RE can see it
    html = re.sub(r"(?is)<h([1-3])[^>]*>(.*?)</h\1>", r"\n\n\2\n\n", html)
    html = re.sub(r"(?i)</(p|div|h[1-6]|li|tr|blockquote|section|article)>", "\n", html)
    html = re.sub(r"(?i)<(br|hr)\s*/?>", "\n", html)
    text = html_mod.unescape(re.sub(r"(?s)<[^>]+>", " ", html))
    text = re.sub(r"[ \t]+", " ", text)
    return re.sub(r"\n\s*\n\s*\n+", "\n\n", text).strip()


def extract_epub(path):
    with zipfile.ZipFile(path) as z:
        names = z.namelist()
        # read the spine in the OPF file to get the real reading order
        spine_files = []
        try:
            container = z.read("META-INF/container.xml").decode("utf-8", "replace")
            opf_path = re.search(r'full-path="([^"]+)"', container).group(1)
            opf_dir = os.path.dirname(opf_path)
            opf = z.read(opf_path).decode("utf-8", "replace")
            root = ET.fromstring(re.sub(r'xmlns="[^"]+"', "", opf, count=1))
            manifest = {i.get("id"): i.get("href") for i in root.iter("item")}
            for itemref in root.iter("itemref"):
                href = manifest.get(itemref.get("idref"))
                if href:
                    full = os.path.normpath(os.path.join(opf_dir, href)).replace("\\", "/")
                    if full in names:
                        spine_files.append(full)
        except Exception:
            pass
        if not spine_files:  # fallback: every html file, by name
            spine_files = sorted(n for n in names
                                 if n.lower().endswith((".xhtml", ".html", ".htm")))
        parts = []
        for name in spine_files:
            try:
                parts.append(_html_to_text(z.read(name).decode("utf-8", "replace")))
            except Exception:
                continue
        return "\n\n".join(p for p in parts if p), None


def extract_docx(path):
    with zipfile.ZipFile(path) as z:
        xml = z.read("word/document.xml").decode("utf-8", "replace")
    text = re.sub(r"(?s)<[^>]+>", "", re.sub(r"</w:p>", "\n", xml))
    return html_mod.unescape(text), None


EXTRACTORS = {
    ".txt": extract_txt, ".md": extract_txt,
    ".pdf": extract_pdf, ".epub": extract_epub, ".docx": extract_docx,
}


# ---------- chapter splitting ----------

def split_chapters(text):
    """Return (method, [(title, body)]) from headings in the text, or by word count."""
    matches = list(CHAPTER_RE.finditer(text))
    if len(matches) >= 2:
        chapters = []
        for i, m in enumerate(matches):
            end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
            body = text[m.end():end].strip()
            if body:
                chapters.append((" ".join(m.group(0).split()), body))
        intro = text[: matches[0].start()].strip()
        if len(intro.split()) > 100:
            chapters.insert(0, ("Front matter", intro))
        return "chapter headings in the text", chapters
    words = text.split()
    return f"every {FALLBACK_WORDS} words (no chapter headings found)", [
        (f"Part {i // FALLBACK_WORDS + 1}", " ".join(words[i:i + FALLBACK_WORDS]))
        for i in range(0, len(words), FALLBACK_WORDS)]


def merge_small(chapters):
    """Join runs of parts under MIN_PART_WORDS into the part that follows them."""
    out, titles, bodies = [], [], []
    for title, body in chapters:
        titles.append(title)
        bodies.append(body)
        if len(" ".join(bodies).split()) >= MIN_PART_WORDS:
            name = titles[0] if len(titles) == 1 else f"{titles[0]} ... {titles[-1]}"
            out.append((name, "\n\n".join(bodies)))
            titles, bodies = [], []
    if bodies and out:
        out[-1] = (out[-1][0], out[-1][1] + "\n\n" + "\n\n".join(bodies))
    elif bodies:
        out.append((titles[0], "\n\n".join(bodies)))
    return out


def check_chapters(chapters):
    """Return warnings about parts that look wrongly split.

    A cross-reference in body text ("... see Chapter 33 ...") can land at the start
    of a line after PDF extraction, match CHAPTER_RE, and split the book in the wrong
    place. Real chapter numbers are unique and ascending, so a repeat or a backward
    jump is the sign. Report it and let a person decide: guessing which match is real
    can silently drop a chapter. Roman numerals carry no digit and are not checked.
    A very large part means the split missed chapter starts, so it is reported too.
    """
    warnings, seen, highest = [], {}, 0
    for i, (title, body) in enumerate(chapters, 1):
        n_words = len(body.split())
        if n_words > MAX_PART_WORDS:
            warnings.append(f"part {i:02d} has {n_words} words -- the split probably "
                            f"missed chapter starts inside it -- {title!r}")
        m = re.search(r"\b(\d+)\b", title)
        if not m:
            continue
        num = int(m.group(1))
        if num in seen:
            warnings.append(f"part {i:02d} repeats number {num} "
                            f"(already used by part {seen[num]:02d}) -- {title!r}")
        else:
            seen[num] = i
        if num < highest:
            warnings.append(f"part {i:02d} jumps back to {num} after {highest} -- {title!r}")
        highest = max(highest, num)
    return warnings


# ---------- output ----------

def frontmatter(title, description):
    """Minimal OKF-style frontmatter. Harmless outside an OKF bundle, required inside one."""
    now = datetime.datetime.now().astimezone().isoformat(timespec="seconds")
    return ("---\ntype: Source Material\n"
            f"title: {json.dumps(title, ensure_ascii=False)}\n"
            f"description: {json.dumps(description, ensure_ascii=False)}\n"
            f'generated: {{ by: process:extract_book, at: "{now}" }}\n---\n\n')


def extract_one(path, out_root):
    """Write the chapter files for one book. Return the number of parts, or 0."""
    text, chapters = EXTRACTORS[path.suffix.lower()](path)
    text = re.sub(r"\n{3,}", "\n\n", text).strip()
    n_words = len(text.split())
    if n_words < 50:
        print(f"  [WARN] Only {n_words} words extracted -- probably a scanned PDF. Run OCR first.")
        return 0
    if chapters:
        method = "PDF bookmarks"
    else:
        method, chapters = split_chapters(text)
    chapters = merge_small(chapters)
    book_dir = out_root / slugify(path.stem, 60)
    book_dir.mkdir(parents=True, exist_ok=True)

    written = {"00-contents.md"}
    lines = [f"# Contents: {path.name}", "",
             f"{len(chapters)} parts, {n_words} words. Split by {method}.", ""]
    for i, (title, body) in enumerate(chapters, 1):
        name = f"{i:02d}-{slugify(title)}.md"
        (book_dir / name).write_text(
            frontmatter(f"{path.stem} - part {i:02d}", f"Part {i:02d} of {path.name}: {title}.")
            + f"# {title}\n\n(Source: {path.name})\n\n{body}\n", encoding="utf-8")
        written.add(name)
        lines.append(f"- `{name}` - {title} ({len(body.split())} words)")

    warnings = check_chapters(chapters)
    if warnings:
        lines += ["", "## Split warnings", "",
                  "Check these parts before writing notes. A repeated or backward number is",
                  "usually a cross-reference cut as a new chapter.", ""]
        lines += [f"- {w}" for w in warnings]
    # A rerun that makes fewer parts leaves old files behind, and they would be read as the book.
    stale = sorted(f.name for f in book_dir.glob("*.md") if f.name not in written)
    if stale:
        lines += ["", "## Files not written by this run", "",
                  "Left over from an earlier run. Move them out before reading this folder.", ""]
        lines += [f"- `{s}`" for s in stale]
    (book_dir / "00-contents.md").write_text(
        frontmatter(f"{path.stem} - contents", f"Parts and word counts extracted from {path.name}.")
        + "\n".join(lines) + "\n", encoding="utf-8")

    print(f"  -> {book_dir}: {len(chapters)} parts by {method}, {n_words} words"
          + (f", {len(warnings)} warning(s)" if warnings else "")
          + (f", {len(stale)} leftover file(s)" if stale else ""))
    return len(chapters)


def collect(inputs):
    files = []
    for item in inputs:
        p = Path(item)
        if p.is_dir():
            files += sorted(f for f in p.iterdir() if f.is_file() and not f.name.startswith("."))
        elif p.is_file():
            files.append(p)
        else:
            sys.exit(f"[ERROR] Not found: {p}")
    return files


def main_run(inputs, out):
    out_root = Path(out)
    total = 0
    for f in collect(inputs):
        ext = f.suffix.lower()
        if ext == ".mobi":
            print(f"[SKIP] {f.name}: convert .mobi to .epub with Calibre, then rerun.")
            continue
        if ext not in EXTRACTORS:
            print(f"[SKIP] {f.name}: unsupported extension {ext or '(none)'}")
            continue
        print(f"[READ] {f.name}")
        total += extract_one(f, out_root)
    if total == 0:
        sys.exit("[ERROR] Nothing could be extracted.")
    print(f"DONE: {total} parts under {out_root}. Open each 00-contents.md first.")


def self_check():
    """Fails loudly if the bookmark level, the splits, the warnings or the leftover report break."""
    import tempfile

    class Mark:
        def __init__(self, title, page):
            self.title, self.page = title, page

    class Reader:
        def __init__(self, outline):
            self.outline = outline

        def get_destination_page_number(self, mark):
            return mark.page

    # Part > Chapter: open the Parts into chapters
    parts = Reader([Mark("Cover\x00\x00", 0), Mark("Part I", 2), [Mark("1. A", 2), Mark("2. B", 12)],
                    Mark("Part II", 22), [Mark("3. C", 22), Mark("4. D", 32)]])
    assert [t for t, _ in outline_starts(parts, 42)] == [
        "Cover", "Part I", "1. A", "2. B", "Part II", "3. C", "4. D"]
    # Chapter > Section: keep the sections inside their chapter
    sections = Reader([Mark("1: A", 0), [Mark("1.1", 0), Mark("1.2", 2), Mark("1.3", 4)],
                       Mark("2: B", 20), [Mark("2.1", 20), Mark("2.2", 22)]])
    assert outline_starts(sections, 40) == [("1: A", 0), ("2: B", 20)]

    text = ("front matter line\n" * 60 + "\nChapter 1\n" + "body one\n" * 200
            + "\nChapter 2\n" + "body two\n" * 200)
    method, chapters = split_chapters(text)
    assert method.startswith("chapter headings")
    assert [t for t, _ in chapters] == ["Front matter", "Chapter 1", "Chapter 2"]
    assert split_chapters("word " * 7000)[1][-1][0] == "Part 3"
    assert [t for t, _ in merge_small([("Cover", "x"), ("Part I", "y " * 5), ("1. A", "z " * 400),
                                       ("Index", "w")])] == ["Cover ... 1. A"]
    assert check_chapters([("Chapter 1", ""), ("Chapter 33", ""), ("Chapter 2", "")])[0].count("jumps back")
    assert check_chapters([("Chapter 1", ""), ("Chapter 1", "")])[0].count("repeats")
    assert check_chapters([("Part V", "w " * (MAX_PART_WORDS + 1))])[0].count("missed chapter")
    assert slugify("Ch\u01b0\u01a1ng 3: \u0110\u00f4ng l\u1ea1nh") == "chuong-3-dong-lanh"

    with tempfile.TemporaryDirectory() as tmp:
        book = Path(tmp) / "My Book.txt"
        book.write_text(text, encoding="utf-8")
        out = Path(tmp) / "extracted"
        assert extract_one(book, out) == 2  # 60-word front matter joins chapter 1
        book_dir = out / "my-book"
        assert sorted(f.name for f in book_dir.iterdir()) == [
            "00-contents.md", "01-front-matter-chapter-1.md", "02-chapter-2.md"]
        assert (book_dir / "02-chapter-2.md").read_text(encoding="utf-8").startswith("---\ntype: ")
        book.write_text("only one part " * 400, encoding="utf-8")
        assert extract_one(book, out) == 1
        contents = (book_dir / "00-contents.md").read_text(encoding="utf-8")
        assert "`02-chapter-2.md`" in contents and "Files not written" in contents, contents
    print("self-check OK")


def main():
    ap = argparse.ArgumentParser(description="Split books into one text file per chapter.")
    ap.add_argument("inputs", nargs="*", help="book files, or folders of book files")
    ap.add_argument("--out", help="output folder; one subfolder per book")
    ap.add_argument("--self-check", action="store_true", help="run the built-in checks and exit")
    args = ap.parse_args()
    if args.self_check:
        return self_check()
    if not args.inputs or not args.out:
        ap.error("give at least one book and --out")
    main_run(args.inputs, args.out)


if __name__ == "__main__":
    main()
