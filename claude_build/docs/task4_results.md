# Task 4 — Q&A Accuracy Results

Fill this in by running, on a machine with Ollama installed:

```bash
python src/search_index.py --build
python -c "
import json, sys
sys.path.insert(0, 'src')
from ask import ask
from search_index import HybridIndex
idx = HybridIndex()
qs = json.load(open('tests/test_questions.json'))
correct = 0
for q in qs:
    answer, hits = idx, None
    answer, hits = ask(q['question'], index=idx)
    print(q['id'], '->', answer)
"
```

(or simply call `python src/ask.py "<question>"` for each of the 20
questions in `tests/test_questions.json` and compare manually against the
`expected_answer` field.)

| # | Category | Question | Correct? | Notes |
|---|---|---|---|---|
| 1-20 | | | | |

**Score: __ / 20**

This project's self-test (`tests/run_self_test.py`), run in the sandboxed
build environment with a mock embedder in place of Ollama, validated that
retrieval (not the LLM's wording) surfaces the right source document for
14/20 questions -- see `tests/self_test_results.json` and the README's
"What's tested vs. what you still need to run" section for why the other 6
need a real LLM to resolve (multi-chunk revision comparisons) or a real
embedding model to discriminate cleanly (borderline not-found cases).
