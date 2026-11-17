# Offline Engineering-Docs Assistant (Ollama RAG) — Claude build

Self-contained build for the PwC "Offline Engineering-Docs Assistant"
assignment, kept in its own `claude_build/` subfolder so it doesn't mix
with the earlier implementation one level up (`../RAG_ask.py`,
`../build_index.py`, `../evaluation.py`, which has its own real, executed
Ollama run in `../output/evaluation_results.csv`). Run all commands below
from inside `claude_build/` — every relative path (`src/`, `data/`,
`tests/`, `docs/`, `ui/`) resolves against this folder.

## What's actually been tested, and where

This folder was built and tested in two different environments, and it's
worth being precise about which parts were proven where:

1. **A sandboxed cloud container** with Python but no access to
   `ollama.com`, real document hosts, or this computer's files. Used to
   write and syntax/logic-check all the code, and to validate the
   retrieval pipeline with a mock embedder.
2. **This computer**, via a constrained bridge shell (same OS family as
   this repo, but a separate scratch filesystem bind-mounting your
   `PwC_AI_Assignment` folder — not a full terminal on your actual desktop
   session). Used to:
   - Copy the 10 real documents your other build already collected
     (`../docs/public/*.pdf`) into `data/real/`, alongside this build's
     12 synthetic documents in `data/synthetic/` — **22 documents total**,
     inside the assignment's 15–25 range.
   - Actually run `src/ingest.py --rebuild` against all 22 real documents
     (not a mock) — **722 chunks produced in 41 seconds**, with correct
     file/page/section/revision/marking metadata (see "What I found while
     testing" below for one real bug this caught and fixed).
   - Actually build the hybrid BM25 + Chroma vector index and run all 20
     test questions through real retrieval against this real 722-chunk
     corpus (still with a mock embedder in place of Ollama's real
     embedding model, since this bridge shell has no path to
     `ollama.com`/a running Ollama server either) — confirms retrieval
     correctly surfaces the right document for the RADAR-100 spec
     questions even mixed in with 700+ chunks of real, unrelated technical
     manuals.

**What's still untested: anything that needs a real LLM call.** Neither
environment I had access to could reach a running Ollama server. The
`../output/evaluation_results.csv` run in the parent folder's build is the
one real Ollama execution that exists for this assignment so far — Task
4/6 evidence should come from there (or from you running
`python src/ask.py "..."` yourself in a real terminal on this machine,
where Ollama is already installed).

## What I found while testing (and fixed)

- **`AC_60-22.pdf` is a 34-page scan with no text layer on any page**, and
  Tesseract OCR genuinely works here but costs ~10-15 seconds *per page*.
  A naive "OCR every blank page" approach would have taken 8+ minutes on
  this one file alone (worse on the 71-page `mil_std_810a.pdf`). Fixed in
  `src/ingest.py`: OCR is now capped at `OCR_PAGE_LIMIT = 3` pages per file
  by default (demonstrates the capability without ballooning runtime), with
  a `--full-ocr` flag to remove the cap when you have time to let it run,
  and chunk writes now happen incrementally after each file (not only at
  the end), so an interrupted run resumes instead of losing all progress.
- **Chroma's SQLite backend failed with a "disk I/O error"** when built
  directly inside the OneDrive-synced folder through the bridge shell
  (`chromadb.errors.InternalError: ... disk I/O error`) — this looks like
  a file-locking incompatibility between SQLite and that particular
  mounted filesystem, not a flaw in the index design (the original build's
  own `data/chroma/` elsewhere in this project proves Chroma works fine
  directly on this machine's real NTFS). Worked around it by building the
  index on local scratch disk and copying the resulting JSON artifacts
  back. **If you hit the same "disk I/O error" building the index
  yourself:** build it on a local (non-cloud-synced) path first, or simply
  run from a plain terminal on this machine instead of through a bridge —
  that's almost certainly not a problem for your normal setup.

## Quick start

```bash
cd claude_build
pip install -r requirements.txt
ollama pull llama3.2:3b          # or pass --model llama3.1:8b to match the other build
ollama pull nomic-embed-text

python src/ingest.py --rebuild          # ~40s for all 22 documents (real+synthetic)
python src/search_index.py --build      # builds data/real + data/synthetic into one index

python src/ask.py "What is the vibration test duration for the RADAR-100?"
streamlit run ui/app.py                 # optional UI, 127.0.0.1 only
```

## Documents (22 total — real + synthetic)

| Folder | Contents |
|---|---|
| `data/real/` | 10 real documents, copied from `../docs/public/`: FAA Advisory Circulars (`AC_21.17-3.pdf`, `AC_60-22.pdf` — the scanned one), a defence-science-style review paper, a MIL-STD-810 copy (`mil_std_810a.pdf`), a TUF-2000 ultrasonic flow meter manual, Bove/Walrus gateway guides, plus two test-report PDFs. |
| `data/synthetic/` | 12 documents from `scripts/generate_synthetic_docs.py`: `EQSPEC-RADAR-100_RevA/RevB.pdf` (spec, two revisions, 21 "shall" requirements each), two test reports, two ECNs, a cross-referenced power-supply spec, a CONFIDENTIAL marked document, a maintenance manual (.docx), and three `SYN-*.pdf` placeholders (clearly labeled inside as synthetic stand-ins, originally created before real documents were available in this build). |

Re-run `python scripts/fetch_real_docs.py` any time to pull in more real
public documents (MIL-STD-882E/461G, NASA SE Handbook, more FAA ACs, a
DRDO paper, an archive.org scanned manual) — see that script for sources.

## Tasks and where they live

| Task | File(s) |
|---|---|
| 1. Ollama setup & model choice | `src/ollama_client.py` (chat + embed wrappers, tok/s from `eval_count`/`eval_duration`) |
| 2. Ingest documents | `src/ingest.py` (PyMuPDF/python-docx, section-aware chunking, file-hash skip, Tesseract OCR with a page cap — see above) |
| 3. Search index | `src/search_index.py` (Chroma vector DB + BM25 keyword index with stopword filtering, reciprocal-rank fusion, absolute-score not-found gate) |
| 4. Q&A with citations | `src/ask.py`, logs every answer to `logs/qa_log.jsonl` |
| 5. Requirement extraction | `src/extract_requirements.py` (Ollama structured output + Pydantic, retry-once, regex fallback), sample output in `requirements.csv` (21 requirements extracted from `EQSPEC-RADAR-100_RevB.pdf`) |
| 6. Model tuning | `src/tune_models.py`, results template in `docs/task6_results.md` |
| 7. Offline packaging | `scripts/package_offline.sh`, `install.sh` / `install.bat` |
| 8. UI & user guide | `ui/app.py` (Streamlit, 127.0.0.1 only), `docs/user_guide.md` |

## Test results

- **Ingestion** (`python src/ingest.py --rebuild`): all 22 real+synthetic
  documents processed successfully, 722 chunks, 41 seconds, correct
  file/page/section/revision/marking metadata on every chunk.
- **Retrieval** (`python tests/run_self_test.py`, mock embedder):
  surfaced the correct source document for 14/20 test questions on the
  original 12-synthetic-document corpus; re-verified against the full
  722-chunk real+synthetic corpus that the RADAR-100-specific questions
  still correctly retrieve `EQSPEC-RADAR-100_Rev*.pdf` even mixed in with
  700+ unrelated chunks. See `tests/self_test_results.json`.
- **Still to run, with real Ollama** (the original build in the parent
  folder already did a real Task-4 run — `../output/evaluation_results.csv`
  — use that as your primary evidence, or re-run `src/ask.py` yourself):
  live Task 1 model timing, a fair-scored Task 4 run of this build's
  `ask.py`, the Task 6 tuning table, and the Wi-Fi-off screen recording.

## Known limitations

- Answers only from the ingested documents — says "Not found in the
  documents" rather than guessing.
- OCR is capped at 3 pages/file by default for speed; pass `--full-ocr` to
  `src/ingest.py` for complete OCR coverage of large scanned documents.
- Document "marking" (CONFIDENTIAL/RESTRICTED) is tracked as metadata only
  — this tool does not enforce access control.
