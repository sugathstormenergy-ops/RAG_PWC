"""
Test-only mock of the Ollama API, used to validate the ingestion / indexing /
retrieval / CLI pipeline in environments without Ollama installed (such as
the sandboxed build environment this project was first assembled in, which
has no network access to ollama.com to install Ollama or pull models).

This is NOT part of the delivered product. ask.py and the other tools always
talk to the real Ollama HTTP API (src/ollama_client.py); this module is only
imported by tests/run_self_test.py.

- `mock_embed(texts)` produces a deterministic bag-of-hashed-words vector
  per text, so texts sharing vocabulary get cosine-similar vectors. This is
  good enough to validate the retrieval plumbing (does the right chunk come
  back), though far weaker than a real embedding model -- the BM25 keyword
  index does the real work for exact-term questions in this test mode.

- `MockChatModel.answer(question, context_chunks)` is a simple extractive
  "answerer": if the question's keywords appear in a context chunk, it
  returns that chunk's most relevant sentence(s) plus a citation; otherwise
  it returns the "not found" fallback. It stands in for a real LLM only for
  self-testing the retrieval -> citation -> answer wiring end to end.
"""
import hashlib
import math
import re

VEC_DIM = 256
TOKEN_RE = re.compile(r"[A-Za-z0-9/_.\-]+")


def _tokenize(text):
    return [t.lower() for t in TOKEN_RE.findall(text)]


def _hash_bucket(token, dim=VEC_DIM):
    h = hashlib.md5(token.encode("utf-8")).hexdigest()
    return int(h, 16) % dim


def mock_embed(texts):
    out = []
    for text in texts:
        vec = [0.0] * VEC_DIM
        for tok in _tokenize(text):
            vec[_hash_bucket(tok)] += 1.0
        norm = math.sqrt(sum(v * v for v in vec)) or 1.0
        out.append([v / norm for v in vec])
    return out


class MockChatModel:
    """Extractive stand-in for an LLM, used only by the self-test harness."""

    def answer(self, question, context_chunks):
        q_tokens = set(_tokenize(question)) - {
            "what", "is", "the", "a", "an", "for", "of", "in", "on", "to", "does"
        }
        best = None
        best_overlap = 0
        for c in context_chunks:
            c_tokens = set(_tokenize(c["text"]))
            overlap = len(q_tokens & c_tokens)
            if overlap > best_overlap:
                best_overlap = overlap
                best = c
        if best is None or best_overlap == 0:
            return "Not found in the documents."
        # crude sentence pick: first sentence containing the most overlap tokens
        sentences = re.split(r"(?<=[.!?])\s+", best["text"])
        sentence = max(
            sentences,
            key=lambda s: len(q_tokens & set(_tokenize(s))),
            default=best["text"][:200],
        )
        cite = f"[{best['file']}, p.{best['page']}]"
        return f"{sentence.strip()} {cite}"
