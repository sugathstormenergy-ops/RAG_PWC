
import csv
import json
import re
from pathlib import Path

import fitz
import ollama
from docx import Document
from typing import Literal
from pydantic import BaseModel, Field


MODEL = "llama3.1:8b"

DOCUMENTS = Path("docs/public")
OUTPUT = Path("requirements.csv")

MAX_CHARS = 3000


class Requirement(BaseModel):
    source_text: str
    requirement: str
    category: Literal[
        "functional",
        "performance",
        "interface",
        "safety",
        "other"
    ]
    priority: Literal[
        "mandatory",
        "recommended",
        "unspecified"
    ]


class RequirementList(BaseModel):
    requirements: list[Requirement] = Field(
        default_factory=list
    )


def normalize(text):
    return re.sub(r"\s+", " ", text).strip()


def split_text(text, max_chars=MAX_CHARS):
    paragraphs = [
        p.strip()
        for p in re.split(r"\n\s*\n", text)
        if p.strip()
    ]

    chunks = []
    current = ""

    for paragraph in paragraphs:
        if len(paragraph) > max_chars:
            if current:
                chunks.append(current)
                current = ""

            for start in range(
                0, len(paragraph), max_chars
            ):
                chunks.append(
                    paragraph[start:start + max_chars]
                )

        elif len(current) + len(paragraph) + 2 <= max_chars:
            current += "\n\n" + paragraph

        else:
            if current:
                chunks.append(current)

            current = paragraph

    if current:
        chunks.append(current)

    return chunks


def extract_requirements(text):
    prompt = f"""
You are an engineering requirements extraction assistant.

Extract ONLY requirements explicitly supported by
the supplied engineering document.

A requirement must state an obligation, prohibition,
or objectively testable technical constraint.

Examples of possible indicators:
shall, must, required, mandatory, should,
shall not, must not, cannot, at least, no more than.

IMPORTANT:
These words are indicators, not sufficient proof.

RULES:

1. Never invent requirements.
2. Never convert a command example into an obligation.
3. Never convert a table of contents into requirements.
4. Never invent priority.
5. Preserve numerical values and units exactly.
6. Extract the exact original supporting text
   into source_text.
7. source_text must appear verbatim in the input.
8. A requirement may be rewritten for clarity,
   but its meaning must not change.
9. Exclude descriptions that do not impose a
   requirement or technical constraint.
10. Exclude headings, revision history and examples.
11. If there are no requirements, return an empty list.

PRIORITY:

mandatory:
Explicitly required or prohibited.

recommended:
Explicitly recommended, typically using "should".

unspecified:
A technical constraint whose priority is not stated.

Return only the required structured JSON.

DOCUMENT TEXT:

{text}
"""

    response = ollama.chat(
        model=MODEL,
        messages=[
            {"role": "user", "content": prompt}
        ],
        format=RequirementList.model_json_schema(),
        options={"temperature": 0},
    )

    data = json.loads(response["message"]["content"])

    return RequirementList.model_validate(
        data
    ).requirements


def read_documents():
    for path in sorted(DOCUMENTS.rglob("*")):
        suffix = path.suffix.lower()

        if suffix == ".pdf":
            with fitz.open(path) as pdf:
                for page_no, page in enumerate(
                    pdf, start=1
                ):
                    text = page.get_text("text").strip()

                    if text:
                        yield path.name, page_no, text

        elif suffix == ".docx":
            doc = Document(path)

            paragraphs = [
                p.text.strip()
                for p in doc.paragraphs
                if p.text.strip()
            ]

            for table in doc.tables:
                for row in table.rows:
                    cells = [
                        cell.text.strip()
                        for cell in row.cells
                    ]
                    paragraphs.append(" | ".join(cells))

            text = "\n".join(paragraphs)

            if text:
                # DOCX page numbers are not reliably
                # available without rendering.
                yield path.name, "", text


def main():
    if not DOCUMENTS.exists():
        raise FileNotFoundError(
            f"Document folder not found: {DOCUMENTS}"
        )

    rows = []
    seen = set()

    documents_seen = set()
    chunks_processed = 0
    rejected = 0

    for filename, page_no, text in read_documents():
        documents_seen.add(filename)

        print(
            f"Processing: {filename}, "
            f"page {page_no or 'N/A'}",
            flush=True
        )

        for chunk in split_text(text):
            chunks_processed += 1

            try:
                requirements = extract_requirements(
                    chunk
                )

                for req in requirements:
                    original = normalize(req.source_text)

                    # Reject invented or altered evidence.
                    if not original or original not in normalize(chunk):
                        rejected += 1
                        continue

                    requirement = normalize(
                        req.requirement
                    )

                    if not requirement:
                        rejected += 1
                        continue

                    key = (
                        filename.lower(),
                        requirement.lower()
                    )

                    if key in seen:
                        continue

                    seen.add(key)

                    rows.append({
                        "source_file": filename,
                        "page": page_no,
                        "source_text": req.source_text,
                        "requirement": requirement,
                        "category": req.category,
                        "priority": req.priority,
                    })

            except Exception as error:
                print(
                    f"Error: {filename}, "
                    f"page {page_no}: {error}"
                )

    with OUTPUT.open(
        "w",
        newline="",
        encoding="utf-8-sig"
    ) as file:

        fieldnames = [
            "source_file",
            "page",
            "source_text",
            "requirement",
            "category",
            "priority",
        ]

        writer = csv.DictWriter(
            file,
            fieldnames=fieldnames
        )

        writer.writeheader()
        writer.writerows(rows)

    print("\nEXTRACTION SUMMARY")
    print("-------------------")
    print("Documents:", len(documents_seen))
    print("Chunks processed:", chunks_processed)
    print("Requirements:", len(rows))
    print("Rejected evidence:", rejected)
    print("Saved to:", OUTPUT.resolve())


if __name__ == "__main__":
    main()
