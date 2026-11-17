#!/usr/bin/env python3
"""
Thin wrapper around the local Ollama HTTP API (http://localhost:11434).

Task 1 requirements covered here:
  - call a chat model and an embedding model from Python
  - compute tokens/second from Ollama's timing fields (eval_count, eval_duration)

Set OLLAMA_HOST to override the default endpoint (e.g. for a remote Ollama
server on a client's GPU box). All functions raise OllamaUnavailable with a
clear message if Ollama is not reachable, so callers (ask.py, etc.) can give
the user a helpful error instead of a raw connection traceback.
"""
import json
import os
import time
import requests

OLLAMA_HOST = os.environ.get("OLLAMA_HOST", "http://localhost:11434")
DEFAULT_CHAT_MODEL = os.environ.get("CHAT_MODEL", "llama3.2:3b")
DEFAULT_EMBED_MODEL = os.environ.get("EMBED_MODEL", "nomic-embed-text")


class OllamaUnavailable(RuntimeError):
    pass


def _post(path, payload, timeout=120):
    url = f"{OLLAMA_HOST}{path}"
    try:
        resp = requests.post(url, json=payload, timeout=timeout)
        resp.raise_for_status()
        return resp.json()
    except requests.exceptions.ConnectionError as e:
        raise OllamaUnavailable(
            f"Could not reach Ollama at {OLLAMA_HOST}. Is it running? "
            f"Try: ollama serve  (and `ollama pull {payload.get('model', '')}` "
            f"if the model isn't pulled yet). Underlying error: {e}"
        )
    except requests.exceptions.HTTPError as e:
        raise OllamaUnavailable(f"Ollama returned an error for {path}: {e} -- {resp.text}")


def embed(texts, model=DEFAULT_EMBED_MODEL):
    """Return a list of embedding vectors for a list of input strings."""
    if isinstance(texts, str):
        texts = [texts]
    data = _post("/api/embed", {"model": model, "input": texts})
    return data["embeddings"]


def chat(messages, model=DEFAULT_CHAT_MODEL, options=None, json_schema=None, stream=False):
    """Call the chat endpoint. Returns (content:str, stats:dict).

    stats includes: eval_count, eval_duration_s, tokens_per_second,
    prompt_eval_count, total_duration_s.
    If json_schema is given, Ollama's structured-output mode is used
    (passed as `format`) and `content` will be a JSON string matching it.
    """
    payload = {"model": model, "messages": messages, "stream": stream}
    if options:
        payload["options"] = options
    if json_schema:
        payload["format"] = json_schema

    t0 = time.time()
    data = _post("/api/chat", payload, timeout=180)
    wall_s = time.time() - t0

    content = data.get("message", {}).get("content", "")
    eval_count = data.get("eval_count", 0)
    eval_duration_ns = data.get("eval_duration", 0)
    eval_duration_s = eval_duration_ns / 1e9 if eval_duration_ns else wall_s
    tps = (eval_count / eval_duration_s) if eval_duration_s > 0 else 0.0

    stats = {
        "model": model,
        "wall_seconds": round(wall_s, 3),
        "eval_count": eval_count,
        "eval_duration_s": round(eval_duration_s, 3),
        "tokens_per_second": round(tps, 2),
        "prompt_eval_count": data.get("prompt_eval_count", 0),
        "total_duration_s": round(data.get("total_duration", 0) / 1e9, 3),
    }
    return content, stats


def generate_structured(prompt, json_schema, model=DEFAULT_CHAT_MODEL, options=None):
    """Convenience wrapper for Task 5: one-shot structured JSON generation."""
    messages = [{"role": "user", "content": prompt}]
    content, stats = chat(messages, model=model, options=options, json_schema=json_schema)
    return content, stats


def ping():
    """Quick reachability check. Returns True/False."""
    try:
        requests.get(f"{OLLAMA_HOST}/api/tags", timeout=5)
        return True
    except Exception:
        return False


if __name__ == "__main__":
    print(f"Ollama host: {OLLAMA_HOST}")
    print(f"Reachable: {ping()}")
    if ping():
        content, stats = chat([{"role": "user", "content": "Say OK."}])
        print("Response:", content)
        print("Stats:", json.dumps(stats, indent=2))
