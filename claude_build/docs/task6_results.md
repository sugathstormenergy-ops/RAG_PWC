# Task 6 — Model Tuning Results

Fill this in by running, on a machine with Ollama installed:

```bash
python src/search_index.py --build          # if not already built
python src/tune_models.py --models llama3.2:3b qwen2.5:7b
# or compare quantizations of one model, e.g.:
python src/tune_models.py --models llama3.2:3b:q4_K_M llama3.2:3b:q8_0
# or try different context sizes:
python src/tune_models.py --models llama3.2:3b --num-ctx 2048 4096 8192
```

Paste the printed table below:

| Model | num_ctx | Memory | Speed (tok/s) | Correct / 20 |
|---|---|---|---|---|
| | | | | |
| | | | | |

## Recommendation

_(3-4 lines: which model/quantization/num_ctx/OLLAMA_NUM_PARALLEL setup
would you recommend for a client GPU server, and why? Consider the
trade-off between answer speed and correctness on the exact-term and
revision-comparison questions, and how many concurrent engineers the
server needs to support.)_
