#!/usr/bin/env python3
"""
Task 6 — Tune the model.

Runs the 20 test questions (tests/test_questions.json) through two or more
Ollama chat models / quantization levels / settings, and reports a table:
model, memory used (via `ollama ps`), speed (tok/s from ollama_client.chat
stats), and a correctness count (scored against the expected_answer field
by simple substring/keyword overlap -- good enough for a quick tuning pass;
spot-check manually for the final README table).

Usage:
    python src/tune_models.py --models llama3.2:3b qwen2.5:7b
    python src/tune_models.py --models llama3.2:3b --num-ctx 2048 4096
    python src/tune_models.py --models llama3.2:3b --parallel 1 4
"""
import argparse
import json
import os
import re
import subprocess
import sys

sys.path.insert(0, os.path.dirname(__file__))
from search_index import HybridIndex
from ollama_client import chat, OllamaUnavailable
import ask as ask_module

ROOT = os.path.join(os.path.dirname(__file__), "..")
QUESTIONS_PATH = os.path.join(ROOT, "tests", "test_questions.json")
TUNE_RESULTS_PATH = os.path.join(ROOT, "docs", "task6_results.json")


def get_ollama_mem_usage(model):
    """Parse `ollama ps` output for the SIZE column of the given model."""
    try:
        out = subprocess.run(["ollama", "ps"], capture_output=True, text=True, timeout=10).stdout
    except Exception:
        return "n/a"
    for line in out.splitlines()[1:]:
        if model.split(":")[0] in line:
            m = re.search(r"(\d+(\.\d+)?\s*(GB|MB))", line)
            if m:
                return m.group(1)
    return "n/a"


def score_answer(answer, expected):
    if expected is None or expected.strip().lower().startswith("not found"):
        return "not found" in answer.lower()
    # crude keyword-overlap score: count distinctive expected tokens present
    expected_tokens = set(re.findall(r"[A-Za-z0-9.\-]+", expected.lower()))
    expected_tokens = {t for t in expected_tokens if len(t) > 2}
    answer_tokens = set(re.findall(r"[A-Za-z0-9.\-]+", answer.lower()))
    if not expected_tokens:
        return False
    overlap = len(expected_tokens & answer_tokens) / len(expected_tokens)
    return overlap >= 0.4


def run_one_config(model, num_ctx=None, questions=None, index=None):
    options = {}
    if num_ctx:
        options["num_ctx"] = num_ctx

    index = index or HybridIndex()
    correct = 0
    speeds = []
    for q in questions:
        hits = index.search(q["question"], top_k=5)
        nothing_relevant = not hits or (
            hits[0].get("best_bm25_score", 0) < ask_module.MIN_BM25_SCORE
            and hits[0].get("best_vec_similarity", 0) < ask_module.MIN_VEC_SIMILARITY
        )
        if nothing_relevant:
            answer = "Not found in the documents."
        else:
            context = ask_module.format_context(hits)
            messages = [
                {"role": "system", "content": ask_module.SYSTEM_PROMPT},
                {"role": "user", "content": f"Context:\n\n{context}\n\nQuestion: {q['question']}"},
            ]
            try:
                answer, stats = chat(messages, model=model, options=options or None)
                speeds.append(stats["tokens_per_second"])
            except OllamaUnavailable as e:
                print(f"ERROR: {e}", file=sys.stderr)
                sys.exit(1)

        if score_answer(answer, q.get("expected_answer")):
            correct += 1

    avg_speed = round(sum(speeds) / len(speeds), 2) if speeds else 0.0
    mem = get_ollama_mem_usage(model)
    return {
        "model": model,
        "num_ctx": num_ctx or "default",
        "avg_tokens_per_second": avg_speed,
        "memory": mem,
        "correct": correct,
        "total": len(questions),
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--models", nargs="+", required=True, help="e.g. llama3.2:3b qwen2.5:7b")
    ap.add_argument("--num-ctx", nargs="+", type=int, default=[None])
    args = ap.parse_args()

    with open(QUESTIONS_PATH) as f:
        questions = json.load(f)
    index = HybridIndex()  # expects an index already built with `python src/search_index.py --build`

    results = []
    for model in args.models:
        for ctx in args.num_ctx:
            print(f"\n== {model}  num_ctx={ctx or 'default'} ==")
            r = run_one_config(model, num_ctx=ctx, questions=questions, index=index)
            print(r)
            results.append(r)

    os.makedirs(os.path.dirname(TUNE_RESULTS_PATH), exist_ok=True)
    with open(TUNE_RESULTS_PATH, "w") as f:
        json.dump(results, f, indent=2)

    print("\n| Model | num_ctx | Memory | Speed (tok/s) | Correct |")
    print("|---|---|---|---|---|")
    for r in results:
        print(f"| {r['model']} | {r['num_ctx']} | {r['memory']} | {r['avg_tokens_per_second']} | {r['correct']}/{r['total']} |")


if __name__ == "__main__":
    main()
