#!/usr/bin/env python3
"""
Task 3 — Build the search index.

Combines:
  - a local Chroma vector database (semantic search, embeddings from Ollama)
  - a BM25 keyword index (rank_bm25) for exact terms: part numbers, section
    numbers, method names like "Method 514.8" that embeddings often miss

build_index() reads index_store/chunks.jsonl (written by ingest.py) and
persists the Chroma collection under index_store/chroma/.

search() runs both and fuses the result lists (reciprocal rank fusion).
"""
import json
import os
import re
import sys

import chromadb
from rank_bm25 import BM25Okapi

ROOT = os.path.join(os.path.dirname(__file__), "..")
INDEX_STORE = os.path.join(ROOT, "index_store")
CHUNKS_PATH = os.path.join(INDEX_STORE, "chunks.jsonl")
CHROMA_DIR = os.path.join(INDEX_STORE, "chroma")
BM25_CORPUS_PATH = os.path.join(INDEX_STORE, "bm25_corpus.json")
COLLECTION_NAME = "engineering_docs"

TOKEN_RE = re.compile(r"[A-Za-z0-9/_.\-]+")

STOPWORDS = {
    "a", "an", "the", "is", "are", "was", "were", "be", "been", "being",
    "of", "in", "on", "at", "to", "for", "and", "or", "but", "with", "by",
    "what", "which", "who", "whom", "this", "that", "these", "those", "it",
    "its", "does", "do", "did", "has", "have", "had", "will", "would",
    "should", "can", "could", "may", "might", "must", "not",
}


def tokenize(text, drop_stopwords=True):
    toks = [t.lower() for t in TOKEN_RE.findall(text)]
    if drop_stopwords:
        toks = [t for t in toks if t not in STOPWORDS]
    return toks


def load_chunks():
    if not os.path.exists(CHUNKS_PATH):
        raise FileNotFoundError(
            f"{CHUNKS_PATH} not found. Run `python src/ingest.py` first.")
    with open(CHUNKS_PATH) as f:
        return [json.loads(line) for line in f if line.strip()]


def chunk_id(i, chunk):
    return f"{chunk['file']}::p{chunk['page']}::{i}"


class HybridIndex:
    def __init__(self, embed_fn=None):
        """embed_fn(list[str]) -> list[list[float]]. Defaults to the real
        Ollama embedding model via src.ollama_client.embed. Tests can inject
        a mock embed_fn (see tests/mock_embeddings.py) to validate the
        pipeline without Ollama installed."""
        self.embed_fn = embed_fn
        self.client = chromadb.PersistentClient(path=CHROMA_DIR)
        self.collection = None
        self.bm25 = None
        self.bm25_chunks = None

    def _get_embed_fn(self):
        if self.embed_fn is None:
            from ollama_client import embed as ollama_embed
            self.embed_fn = ollama_embed
        return self.embed_fn

    def build(self, chunks=None):
        chunks = chunks if chunks is not None else load_chunks()
        try:
            self.client.delete_collection(COLLECTION_NAME)
        except Exception:
            pass
        self.collection = self.client.create_collection(
            COLLECTION_NAME, metadata={"hnsw:space": "cosine"})

        embed_fn = self._get_embed_fn()
        texts = [c["text"] for c in chunks]
        ids = [chunk_id(i, c) for i, c in enumerate(chunks)]
        metadatas = [{
            "file": c["file"], "page": c["page"], "section": c.get("section", ""),
            "revision": c.get("revision", ""), "marking": c.get("marking", ""),
        } for c in chunks]

        BATCH = 64
        for start in range(0, len(texts), BATCH):
            batch_texts = texts[start:start + BATCH]
            embeddings = embed_fn(batch_texts)
            self.collection.add(
                ids=ids[start:start + BATCH],
                embeddings=embeddings,
                documents=batch_texts,
                metadatas=metadatas[start:start + BATCH],
            )
            print(f"  embedded {start + len(batch_texts)}/{len(texts)} chunks")

        # BM25 keyword index
        tokenized = [tokenize(c["text"]) for c in chunks]
        self.bm25 = BM25Okapi(tokenized)
        self.bm25_chunks = chunks
        with open(BM25_CORPUS_PATH, "w") as f:
            json.dump(chunks, f)

        print(f"Indexed {len(chunks)} chunks into Chroma + BM25.")

    def _ensure_loaded(self):
        if self.collection is None:
            self.collection = self.client.get_collection(COLLECTION_NAME)
        if self.bm25 is None:
            if not os.path.exists(BM25_CORPUS_PATH):
                raise FileNotFoundError("BM25 corpus missing. Run build() first.")
            with open(BM25_CORPUS_PATH) as f:
                self.bm25_chunks = json.load(f)
            self.bm25 = BM25Okapi([tokenize(c["text"]) for c in self.bm25_chunks])

    def search(self, query, top_k=5, vector_k=10, bm25_k=10):
        """Hybrid search with reciprocal-rank fusion. Returns up to top_k
        chunk dicts (with 'text','file','page','section','revision',
        'marking','score') ranked best-first."""
        self._ensure_loaded()

        # --- vector search ---
        embed_fn = self._get_embed_fn()
        q_emb = embed_fn([query])[0]
        vec_res = self.collection.query(query_embeddings=[q_emb], n_results=vector_k)
        vec_hits = []
        best_vec_sim = 0.0
        if vec_res["ids"] and vec_res["ids"][0]:
            for doc, meta, dist in zip(vec_res["documents"][0], vec_res["metadatas"][0], vec_res["distances"][0]):
                sim = 1.0 - dist  # cosine distance -> similarity
                best_vec_sim = max(best_vec_sim, sim)
                vec_hits.append({"text": doc, **meta, "_vec_dist": dist})

        # --- bm25 search ---
        scores = self.bm25.get_scores(tokenize(query))
        max_possible = max(scores) if len(scores) and max(scores) > 0 else 1.0
        order = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)[:bm25_k]
        bm25_hits = [{**self.bm25_chunks[i], "_bm25_score": scores[i]} for i in order if scores[i] > 0]
        best_bm25_score = scores[order[0]] if order else 0.0

        # --- reciprocal rank fusion ---
        def key(h):
            return (h["file"], h["page"], h["text"][:40])

        rrf_scores = {}
        combined = {}
        K = 60
        for rank, h in enumerate(vec_hits):
            k = key(h)
            rrf_scores[k] = rrf_scores.get(k, 0) + 1.0 / (K + rank + 1)
            combined.setdefault(k, h)
        for rank, h in enumerate(bm25_hits):
            k = key(h)
            rrf_scores[k] = rrf_scores.get(k, 0) + 1.0 / (K + rank + 1)
            combined.setdefault(k, h)

        ranked_keys = sorted(rrf_scores, key=lambda k: rrf_scores[k], reverse=True)
        results = []
        for k in ranked_keys[:top_k]:
            h = dict(combined[k])
            h["score"] = round(rrf_scores[k], 5)
            # Absolute-magnitude signal (not rank-based) for "is anything
            # actually relevant" decisions -- see ask.py's not-found gate.
            h["best_vec_similarity"] = round(best_vec_sim, 4)
            h["best_bm25_score"] = round(best_bm25_score, 4)
            results.append(h)
        return results


if __name__ == "__main__":
    idx = HybridIndex()
    if "--build" in sys.argv:
        idx.build()
    else:
        q = " ".join(a for a in sys.argv[1:] if a != "--build") or "vibration test duration"
        for r in idx.search(q):
            print(f"[{r['score']}] {r['file']} p.{r['page']} sec.{r.get('section','')}: {r['text'][:100]!r}")
