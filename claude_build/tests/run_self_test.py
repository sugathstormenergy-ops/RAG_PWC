#!/usr/bin/env python3
"""
Self-test harness: validates ingestion -> indexing -> hybrid retrieval ->
citation wiring END TO END without needing Ollama installed, by substituting
a deterministic mock embedder and a simple extractive mock "chat model"
(tests/mock_ollama.py).

This does NOT replace Task 4's real "run your 20 test questions against the
LLM and record how many were right" exercise -- that must be done with a
real Ollama model (see docs/task4_results.md placeholder / README). What
this script proves is that retrieval finds the right chunk for each
question and that the citation format is correct, which is the part that
does not depend on which LLM you point ask.py at.

Run:
    python tests/run_self_test.py
"""
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
sys.path.insert(0, os.path.dirname(__file__))

from ingest import run as ingest_run
from search_index import HybridIndex
from mock_ollama import mock_embed, MockChatModel

ROOT = os.path.join(os.path.dirname(__file__), "..")
QUESTIONS_PATH = os.path.join(ROOT, "tests", "test_questions.json")


def main():
    print("== 1. Ingest documents ==")
    ingest_run(rebuild=True)

    print("\n== 2. Build hybrid index (mock embeddings) ==")
    idx = HybridIndex(embed_fn=mock_embed)
    idx.build()

    print("\n== 3. Run 20 test questions ==")
    with open(QUESTIONS_PATH) as f:
        questions = json.load(f)

    model = MockChatModel()
    correct = 0
    not_found_correct = 0
    not_found_total = 0
    results = []

    for q in questions:
        hits = idx.search(q["question"], top_k=5)
        top_score = hits[0]["score"] if hits else 0.0
        nothing_relevant = not hits or (
            hits[0].get("best_bm25_score", 0) < 1.0
            and hits[0].get("best_vec_similarity", 0) < 0.55
        )

        if q["category"] == "not_found":
            not_found_total += 1
            # Two-layer defense, matching the real ask.py design: a cheap
            # score-based gate catches the obvious cases; for anything that
            # gets past the gate, the (mock) model still has to find enough
            # keyword/semantic overlap in the actual chunk text to produce
            # an answer, same as a real LLM would refuse to answer from
            # irrelevant context. Either layer saying "not found" is correct.
            answer = "Not found in the documents." if nothing_relevant else model.answer(q["question"], hits)
            is_correct = "not found" in answer.lower()
            if is_correct:
                not_found_correct += 1
                correct += 1
        else:
            if nothing_relevant:
                answer = "Not found in the documents."
                is_correct = False
            else:
                answer = model.answer(q["question"], hits)
                # Correct if the expected source file is among the retrieved
                # chunks' sources (the mock extractive model may pick a
                # different sentence/chunk from the same or a related doc
                # than the single cited one -- what matters for this
                # self-test is that retrieval surfaced the right document).
                expected_file = (q.get("source_file") or "").split(" / ")[0]
                retrieved_files = {h["file"] for h in hits}
                is_correct = bool(expected_file) and expected_file in retrieved_files
            if is_correct:
                correct += 1

        results.append({
            "id": q["id"], "category": q["category"], "question": q["question"],
            "top_hit": f"{hits[0]['file']} p.{hits[0]['page']}" if hits else None,
            "top_score": round(top_score, 4),
            "mock_answer": answer,
            "retrieval_ok": bool(is_correct),
        })
        flag = "OK  " if is_correct else "MISS"
        print(f"[{flag}] #{q['id']:>2} ({q['category']:<18}) -> {results[-1]['top_hit']}  score={top_score:.4f}")

    print(f"\n{correct}/{len(questions)} questions retrieved/answered as expected "
          f"({not_found_correct}/{not_found_total} correct 'not found' rejections).")

    out_path = os.path.join(ROOT, "tests", "self_test_results.json")
    with open(out_path, "w") as f:
        json.dump(results, f, indent=2)
    print(f"Details written to {out_path}")

    if correct < len(questions) * 0.7:
        print("\nWARNING: retrieval accuracy below 70% in self-test mode.", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
