from pathlib import Path
import hashlib
import json
import re

import pymupdf
import chromadb
from ollama import embed

DOCS = Path("docs")
DATA = Path("data")
DATA.mkdir(exist_ok=True)

DB_PATH = str(DATA / "chroma")
MANIFEST = DATA / "manifest.json"
EMBED_MODEL = "nomic-embed-text"

client = chromadb.PersistentClient(path=DB_PATH)
collection = client.get_or_create_collection(
    name="engineering_documents",
    metadata={"hnsw:space": "cosine"}
)


def file_hash(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def split_text(text, size=1200, overlap=150):
    """Split text into overlapping chunks."""
    text = re.sub(r"\s+", " ", text).strip()

    if not text:
        return []

    chunks = []
    start = 0

    while start < len(text):
        end = min(start + size, len(text))
        chunks.append(text[start:end])

        if end == len(text):
            break

        start = end - overlap

    return chunks


def detect_revision(filename):
    match = re.search(
        r"rev[_\s-]*([A-Z0-9]+)",
        filename,
        re.IGNORECASE
    )
    return match.group(1).upper() if match else "Unknown"


def detect_marking(text):
    header = text[:500].upper()

    for marking in ("RESTRICTED", "CONFIDENTIAL"):
        if marking in header:
            return marking

    return "Unmarked"


def load_manifest():
    if MANIFEST.exists():
        return json.loads(MANIFEST.read_text(encoding="utf-8"))
    return {}


def main():
    manifest = load_manifest()
    total = 0

    pdf_files = sorted(DOCS.rglob("*.pdf"))

    if not pdf_files:
        print("No PDF documents found.")
        return

    for path in pdf_files:
        relative = path.relative_to(DOCS).as_posix()
        digest = file_hash(path)

        if manifest.get(relative) == digest:
            print(f"Skipping unchanged: {relative}")
            continue

        print(f"\nProcessing: {relative}")

        # Remove previous chunks for this document.
        collection.delete(where={"source": relative})

        ids = []
        documents = []
        metadatas = []

        with pymupdf.open(path) as pdf:
            for page_number, page in enumerate(pdf, start=1):
                text = page.get_text(sort=True)

                if not text.strip():
                    print(f"Page {page_number}: no text (OCR needed)")
                    continue

                marking = detect_marking(text)
                revision = detect_revision(path.stem)

                for index, chunk in enumerate(split_text(text)):
                    section = re.search(
                        r"\b\d+(?:\.\d+){1,4}\b", chunk
                    )

                    chunk_id = hashlib.sha256(
                        f"{relative}:{page_number}:{index}".encode()
                    ).hexdigest()

                    ids.append(chunk_id)
                    documents.append(chunk)
                    metadatas.append({
                        "source": relative,
                        "filename": path.name,
                        "page": page_number,
                        "section": section.group(0) if section else "",
                        "revision": revision,
                        "marking": marking
                    })

        for start in range(0, len(ids), 20):
            end = start + 20
            batch_texts = documents[start:end]

            vectors = embed(
                model=EMBED_MODEL,
                input=batch_texts
            ).embeddings

            collection.upsert(
                ids=ids[start:end],
                documents=batch_texts,
                metadatas=metadatas[start:end],
                embeddings=vectors
            )

        manifest[relative] = digest
        MANIFEST.write_text(
            json.dumps(manifest, indent=2),
            encoding="utf-8"
        )

        total += len(ids)
        print(f"Indexed {len(ids)} chunks.")

    print(f"\nNew chunks indexed: {total}")
    print(f"Total chunks in database: {collection.count()}")


if __name__ == "__main__":
    main()