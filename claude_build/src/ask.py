#!/usr/bin/env python3
"""
Task 4 — Question answering with citations.

    python src/ask.py "What is the vibration test duration for RADAR-100?"

Retrieves the top chunks from the hybrid index (search_index.HybridIndex),
sends them to the Ollama chat model with a prompt that forces the model to
answer only from the given context, and prints an answer ending with
citations like [EQSPEC-RADAR-100_RevB.pdf, p.3].

If retrieval scores are all low (nothing relevant found), the model call is
skipped entirely and "Not found in the documents." is returned directly, per
the assignment hint -- this also means a "not found" answer costs zero LLM
tokens.

Every question is logged to logs/qa_log.jsonl with timestamp, sources used,
and model name (Task 8 traceability requirement).
"""
import argparse
import datetime
import json
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
from search_index import HybridIndex
from ollama_client import chat, DEFAULT_CHAT_MODEL, OllamaUnavailable

ROOT = os.path.join(os.path.dirname(__file__), "..")
LOG_PATH = os.path.join(ROOT, "logs", "qa_log.jsonl")
os.makedirs(os.path.dirname(LOG_PATH), exist_ok=True)

# "Nothing relevant found" gate. Reciprocal-rank-fusion scores reflect rank
# position, not absolute relevance (a weak top-1 hit scores almost the same
# as a strong one), so the not-found decision uses the two underlying
# absolute-magnitude signals instead: best raw BM25 score and best vector
# cosine similarity. If BOTH are low, nothing in the corpus is a good match
# for the question and we skip the LLM call entirely.
MIN_BM25_SCORE = 1.0
MIN_VEC_SIMILARITY = 0.55

SYSTEM_PROMPT = (
    "You are an engineering-documentation assistant for a defense "
    "engineering company. Answer the user's question using ONLY the "
    "context excerpts provided below. Each excerpt is labeled with its "
    "source document and page number.\n"
    "Rules:\n"
    "1. If the context does not contain the answer, reply exactly: "
    "\"Not found in the documents.\" Do not guess or use outside knowledge.\n"
    "2. If multiple excerpts give conflicting values (e.g. two revisions of "
    "the same spec), prefer the most recent revision and say so explicitly.\n"
    "3. Always end your answer with the source(s) you used, in the form "
    "[DOCUMENT_NAME, p.PAGE]. Use one citation per distinct fact.\n"
    "4. Be concise -- a few sentences, not a report.\n"
)


def format_context(chunks):
    blocks = []
    for c in chunks:
        header = f"[{c['file']}, p.{c['page']}" + (f", sec.{c['section']}" if c.get("section") else "") + "]"
        if c.get("marking"):
            header += f" (marking: {c['marking']})"
        blocks.append(f"{header}\n{c['text']}")
    return "\n\n---\n\n".join(blocks)


def ask(question, index=None, chat_model=DEFAULT_CHAT_MODEL, top_k=5, verbose=False):
    index = index or HybridIndex()
    hits = index.search(question, top_k=top_k)

    nothing_relevant = not hits or (
        hits[0].get("best_bm25_score", 0) < MIN_BM25_SCORE
        and hits[0].get("best_vec_similarity", 0) < MIN_VEC_SIMILARITY
    )
    if nothing_relevant:
        answer = "Not found in the documents."
        _log(question, answer, [], chat_model, skipped_llm=True)
        return answer, hits

    context = format_context(hits)
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": f"Context:\n\n{context}\n\nQuestion: {question}"},
    ]
    try:
        content, stats = chat(messages, model=chat_model)
    except OllamaUnavailable as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)

    if verbose:
        print(f"  (model stats: {stats['tokens_per_second']} tok/s, "
              f"{stats['eval_count']} tokens, {stats['total_duration_s']}s total)",
              file=sys.stderr)

    _log(question, content, hits, chat_model, skipped_llm=False)
    return content, hits


def _log(question, answer, hits, model, skipped_llm):
    entry = {
        "timestamp": datetime.datetime.now().isoformat(timespec="seconds"),
        "question": question,
        "answer": answer,
        "model": model,
        "skipped_llm": skipped_llm,
        "sources": [{"file": h["file"], "page": h["page"], "score": h["score"]} for h in hits],
    }
    with open(LOG_PATH, "a") as f:
        f.write(json.dumps(entry) + "\n")


def main():
    ap = argparse.ArgumentParser(description="Ask a question of the engineering documents.")
    ap.add_argument("question", nargs="+", help="the question to ask")
    ap.add_argument("--model", default=DEFAULT_CHAT_MODEL)
    ap.add_argument("--top-k", type=int, default=5)
    ap.add_argument("-v", "--verbose", action="store_true")
    args = ap.parse_args()
    question = " ".join(args.question)

    answer, hits = ask(question, chat_model=args.model, top_k=args.top_k, verbose=args.verbose)
    print(answer)
    if args.verbose:
        print("\nRetrieved chunks:", file=sys.stderr)
        for h in hits:
            print(f"  [{h['score']}] {h['file']} p.{h['page']}", file=sys.stderr)


if __name__ == "__main__":
    main()
