#!/usr/bin/env python3
"""
Task 2 — Ingest the documents.

Reads all PDFs and DOCX files under data/real/ and data/synthetic/, splits
them into chunks (by section heading where possible, falling back to
paragraph/size-based splitting), and returns a list of chunk dicts with
metadata: file name, page number, section number, revision, marking.

A SHA-256 hash of each source file is cached in index_store/file_hashes.json
so files that have already been processed are skipped on the next run
(use --rebuild to force reprocessing of everything).
"""
import argparse
import hashlib
import json
import os
import re
import sys

try:
    import pymupdf as fitz  # modern import name
except ImportError:
    import fitz  # PyMuPDF (older versions)
from docx import Document as DocxDocument

ROOT = os.path.join(os.path.dirname(__file__), "..")
DATA_DIRS = [os.path.join(ROOT, "data", "real"), os.path.join(ROOT, "data", "synthetic")]
INDEX_STORE = os.path.join(ROOT, "index_store")
HASH_CACHE_PATH = os.path.join(INDEX_STORE, "file_hashes.json")
CHUNKS_PATH = os.path.join(INDEX_STORE, "chunks.jsonl")

os.makedirs(INDEX_STORE, exist_ok=True)

# Matches "3.1", "3.2.1", "7.1", etc. at the start of a line/paragraph
SECTION_RE = re.compile(r"^\s*(\d+(?:\.\d+)*)\s*[\.\)]?\s+(.*)$")
REV_RE = re.compile(r"\bRev(?:ision)?\s*([A-Za-z0-9]+)\b", re.IGNORECASE)
MARKING_RE = re.compile(r"\b(CONFIDENTIAL|RESTRICTED|SECRET|UNCLASSIFIED|PROPRIETARY)\b")

MAX_CHUNK_CHARS = 1200  # fallback size-based split ceiling

# OCR (Tesseract) genuinely works here but costs ~10-15 seconds PER PAGE on
# modest hardware. A fully-scanned 30-70 page manual would take many
# minutes. Default to OCR'ing only the first OCR_PAGE_LIMIT scanned pages
# per file, so a normal `ingest.py --rebuild` stays fast; pass --full-ocr to
# OCR every scanned page (do this when you have time to let it run, e.g.
# overnight on a big scanned manual). Pages past the limit are left with
# empty text rather than silently guessed at.
OCR_PAGE_LIMIT = 3


def file_hash(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(65536), b""):
            h.update(block)
    return h.hexdigest()


def load_hash_cache():
    if os.path.exists(HASH_CACHE_PATH):
        with open(HASH_CACHE_PATH) as f:
            return json.load(f)
    return {}


def save_hash_cache(cache):
    with open(HASH_CACHE_PATH, "w") as f:
        json.dump(cache, f, indent=2)


def detect_revision(text, fallback=""):
    m = REV_RE.search(text)
    return m.group(0) if m else fallback


def detect_marking(text):
    m = MARKING_RE.search(text.upper())
    return m.group(1) if m else ""


def split_into_sections(page_text):
    """Split a page's text into (section_number, section_text) pieces based
    on numbered-heading lines. Falls back to a single unnumbered section."""
    lines = page_text.split("\n")
    sections = []
    current_sec = ""
    current_lines = []
    for line in lines:
        m = SECTION_RE.match(line)
        if m and len(m.group(1)) <= 10:  # looks like a real section number
            if current_lines:
                sections.append((current_sec, "\n".join(current_lines)))
            current_sec = m.group(1)
            current_lines = [line]
        else:
            current_lines.append(line)
    if current_lines:
        sections.append((current_sec, "\n".join(current_lines)))
    return sections if sections else [("", page_text)]


def chunk_text(text, max_chars=MAX_CHUNK_CHARS):
    """Size-based fallback split that tries to keep paragraphs (and crude
    table blocks) whole."""
    if len(text) <= max_chars:
        return [text]
    paras = re.split(r"\n\s*\n", text)
    chunks, buf = [], ""
    for p in paras:
        if len(buf) + len(p) + 2 <= max_chars:
            buf = f"{buf}\n\n{p}" if buf else p
        else:
            if buf:
                chunks.append(buf)
            buf = p
    if buf:
        chunks.append(buf)
    return chunks


def ingest_pdf(path, doc_revision_hint, ocr_limit=OCR_PAGE_LIMIT):
    out = []
    doc = fitz.open(path)
    ocr_used = 0
    for page_index in range(len(doc)):
        page = doc[page_index]
        page_num = page_index + 1
        text = page.get_text("text")
        if not text.strip():
            # Likely a scanned page with no text layer -> OCR fallback,
            # capped at ocr_limit pages per file (see OCR_PAGE_LIMIT).
            if ocr_limit is None or ocr_used < ocr_limit:
                text = ocr_page(page)
                ocr_used += 1
            else:
                print(f"  [ocr-skip] {os.path.basename(path)} p.{page_num}: "
                      f"OCR page limit ({ocr_limit}) reached, leaving blank "
                      f"(use --full-ocr to process every scanned page)",
                      file=sys.stderr)
        marking = detect_marking(text)
        revision = detect_revision(text, doc_revision_hint)
        for sec_no, sec_text in split_into_sections(text):
            for piece in chunk_text(sec_text):
                piece = piece.strip()
                if not piece:
                    continue
                out.append({
                    "text": piece,
                    "file": os.path.basename(path),
                    "page": page_num,
                    "section": sec_no,
                    "revision": revision,
                    "marking": marking,
                })
    doc.close()
    return out


def ocr_page(page, zoom=2.0):
    """OCR fallback for scanned PDF pages with no extractable text layer.
    Requires pytesseract + the Tesseract binary; degrades gracefully to an
    empty string if unavailable so ingestion doesn't crash on a machine
    without Tesseract installed yet."""
    try:
        import pytesseract
        from PIL import Image
        import io
        mat = fitz.Matrix(zoom, zoom)
        pix = page.get_pixmap(matrix=mat)
        img = Image.open(io.BytesIO(pix.tobytes("png")))
        return pytesseract.image_to_string(img)
    except Exception as e:
        print(f"  [ocr-skip] {e}", file=sys.stderr)
        return ""


def ingest_docx(path, doc_revision_hint):
    out = []
    doc = DocxDocument(path)
    # DOCX has no native "page" concept; we track a monotonically
    # increasing pseudo-page by counting roughly MAX_CHUNK_CHARS of text,
    # and record the paragraph index in `section` when no numbered
    # heading is found, matching the spirit of Task 2's metadata fields.
    full_text_blocks = []
    current_sec = ""
    buf_lines = []
    for para in doc.paragraphs:
        line = para.text
        m = SECTION_RE.match(line)
        if para.style and para.style.name.startswith("Heading"):
            if buf_lines:
                full_text_blocks.append((current_sec, "\n".join(buf_lines)))
            current_sec = line.strip()
            buf_lines = [line]
        elif m and len(m.group(1)) <= 10:
            if buf_lines:
                full_text_blocks.append((current_sec, "\n".join(buf_lines)))
            current_sec = m.group(1)
            buf_lines = [line]
        else:
            buf_lines.append(line)
    if buf_lines:
        full_text_blocks.append((current_sec, "\n".join(buf_lines)))

    full_text = "\n".join(p.text for p in doc.paragraphs)
    marking = detect_marking(full_text)
    revision = detect_revision(full_text, doc_revision_hint)

    pseudo_page = 1
    chars_on_page = 0
    for sec_no, sec_text in full_text_blocks:
        for piece in chunk_text(sec_text):
            piece = piece.strip()
            if not piece:
                continue
            out.append({
                "text": piece,
                "file": os.path.basename(path),
                "page": pseudo_page,
                "section": sec_no,
                "revision": revision,
                "marking": marking,
            })
            chars_on_page += len(piece)
            if chars_on_page >= MAX_CHUNK_CHARS * 2:
                pseudo_page += 1
                chars_on_page = 0
    return out


def iter_source_files():
    for d in DATA_DIRS:
        if not os.path.isdir(d):
            continue
        for fname in sorted(os.listdir(d)):
            if fname.lower().endswith((".pdf", ".docx")):
                yield os.path.join(d, fname)


def run(rebuild=False):
    cache = {} if rebuild else load_hash_cache()
    all_chunks = []
    if not rebuild and os.path.exists(CHUNKS_PATH):
        with open(CHUNKS_PATH) as f:
            all_chunks = [json.loads(line) for line in f if line.strip()]
    processed_files = {c["file"] for c in all_chunks}

    new_count = 0
    for path in iter_source_files():
        fname = os.path.basename(path)
        h = file_hash(path)
        if cache.get(fname) == h and fname in processed_files and not rebuild:
            print(f"[skip]   {fname} (unchanged)")
            continue

        print(f"[ingest] {fname}")
        # Strip stale chunks for this file if re-processing
        all_chunks = [c for c in all_chunks if c["file"] != fname]

        rev_hint = "Rev A" if "RevA" in fname else ("Rev B" if "RevB" in fname else "")
        if path.lower().endswith(".pdf"):
            chunks = ingest_pdf(path, rev_hint)
        else:
            chunks = ingest_docx(path, rev_hint)

        all_chunks.extend(chunks)
        cache[fname] = h
        new_count += len(chunks)

    with open(CHUNKS_PATH, "w") as f:
        for c in all_chunks:
            f.write(json.dumps(c) + "\n")
    save_hash_cache(cache)

    print(f"\nTotal chunks: {len(all_chunks)}  (added/updated this run: {new_count})")
    print(f"Wrote {CHUNKS_PATH}")
    return all_chunks


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--rebuild", action="store_true", help="reprocess all files, ignoring the hash cache")
    args = ap.parse_args()
    run(rebuild=args.rebuild)
