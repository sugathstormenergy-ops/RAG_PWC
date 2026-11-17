import re
import sys

import chromadb
from ollama import chat, embed
from rank_bm25 import BM25Okapi
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(
        encoding="utf-8",
        errors="replace"
    )

if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(
        encoding="utf-8",
        errors="replace"
    )
DB_PATH = "data/chroma"
CHAT_MODEL = "llama3.1:8b"
EMBED_MODEL = "nomic-embed-text"

client = chromadb.PersistentClient(path=DB_PATH)
collection = client.get_collection("engineering_documents")



def tokenize(text):
    text = text.lower()

    # Keep complete engineering identifiers.
    tokens = re.findall(
        r"[a-z0-9]+(?:[+._=/:-][a-z0-9]+)*",
        text
    )

    # Also index their individual components.
    parts = re.findall(r"[a-z0-9]+", text)

    return tokens + parts


def search(question, top_k=8):
    all_data = collection.get(
        include=["documents", "metadatas"]
    )

    ids = all_data["ids"]
    documents = all_data["documents"]
    metadata = all_data["metadatas"]

    if not documents:
        return []

    # BM25 keyword search
    bm25 = BM25Okapi([tokenize(d) for d in documents])
    keyword_scores = bm25.get_scores(tokenize(question))

    keyword_order = sorted(
        range(len(documents)),
        key=lambda i: keyword_scores[i],
        reverse=True
    )[:20]

    # Semantic vector search
    question_vector = embed(
        model=EMBED_MODEL,
        input=question
    ).embeddings[0]

    vector_results = collection.query(
        query_embeddings=[question_vector],
        n_results=min(20, len(documents))
    )

    # Reciprocal Rank Fusion
    combined = {}

    for rank, index in enumerate(keyword_order):
        if keyword_scores[index] > 0:
            chunk_id = ids[index]
            combined[chunk_id] = (
                combined.get(chunk_id, 0) + 1 / (60 + rank + 1)
            )

    for rank, chunk_id in enumerate(vector_results["ids"][0]):
        combined[chunk_id] = (
            combined.get(chunk_id, 0) + 1 / (60 + rank + 1)
        )

    index_by_id = {chunk_id: i for i, chunk_id in enumerate(ids)}

    ranked = sorted(
        combined,
        key=lambda chunk_id: combined[chunk_id],
        reverse=True
    )[:top_k]

    return [
        {
            "text": documents[index_by_id[chunk_id]],
            "meta": metadata[index_by_id[chunk_id]]
        }
        for chunk_id in ranked
    ]


def answer_question(question):
    results = search(question)

    if not results:
        print("Not found in the documents.")
        return

    context = "\n\n".join(
        f"[Source {i}] {item['meta']['filename']}, "
        f"page {item['meta']['page']}\n{item['text']}"
        for i, item in enumerate(results, start=1)
    )

    prompt = f"""
You are a technical engineering document assistant.

Your job is to answer questions using ONLY the
retrieved engineering document passages.

RULES:

1. Read all retrieved passages carefully.

2. Answer using information explicitly stated
   in the passages.

3. Engineering commands may be written in
   different formats.

   Example:
   "AT+RDMETER" followed by "UL"
   represents "AT+RDMETER=UL".

4. Treat equivalent technical expressions as
   matching when the document clearly supports
   the equivalence.

5. If the answer is present, give a short,
   technically accurate explanation.

6. Cite the supporting source using [Source N].

7. If the answer is genuinely absent from
   ALL supplied passages, respond exactly:

   Not found in the documents.

8. Never invent technical specifications,
   commands, values or citations.

DOCUMENT PASSAGES:

{context}

QUESTION:

{question}

ANSWER:
"""

    response = chat(
        model=CHAT_MODEL,
        messages=[{"role": "user", "content": prompt}],
        options={"temperature": 0, "num_ctx": 8192}
    )

    print("\nANSWER:\n")
    print(response.message.content)


    print("\nRETRIEVED SOURCES:")

    for i, item in enumerate(results, start=1):
        meta = item["meta"]

        print(
            f"\n[Source {i}] "
            f"{meta['filename']}, "
            f"p.{meta['page']}"
        )

        print("PASSAGE:")
        print(item["text"][:1000])
        print("-" * 50)



if __name__ == "__main__":
    if len(sys.argv) > 1:
        answer_question(" ".join(sys.argv[1:]))
    else:
        question = input("Enter your question: ").strip()
        if question:
            answer_question(question)