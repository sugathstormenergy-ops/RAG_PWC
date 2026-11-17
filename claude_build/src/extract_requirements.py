#!/usr/bin/env python3
"""
Task 5 — Extract requirements.

From one specification, extract every "shall" statement into a CSV file
with columns: requirement_id, text, type, section, page.

Approach: use Ollama's structured output (JSON schema via `format`),
validated with Pydantic. If the JSON is invalid, retry once, then log the
error and skip that chunk (per the task hint).

Usage:
    python src/extract_requirements.py data/synthetic/EQSPEC-RADAR-100_RevB.pdf
    python src/extract_requirements.py data/synthetic/EQSPEC-RADAR-100_RevB.pdf --out requirements.csv
"""
import argparse
import csv
import json
import os
import re
import sys

from pydantic import BaseModel, ValidationError, field_validator
from typing import Literal

sys.path.insert(0, os.path.dirname(__file__))
from ingest import ingest_pdf, ingest_docx
from ollama_client import generate_structured, DEFAULT_CHAT_MODEL, OllamaUnavailable

ROOT = os.path.join(os.path.dirname(__file__), "..")
ERROR_LOG = os.path.join(ROOT, "logs", "extract_errors.log")
os.makedirs(os.path.dirname(ERROR_LOG), exist_ok=True)

ReqType = Literal["performance", "environmental", "safety", "interface", "other"]


class Requirement(BaseModel):
    requirement_id: str
    text: str
    type: ReqType
    section: str = ""

    @field_validator("text")
    @classmethod
    def must_contain_shall(cls, v):
        if "shall" not in v.lower():
            raise ValueError("extracted text does not contain 'shall'")
        return v


class RequirementList(BaseModel):
    requirements: list[Requirement]


JSON_SCHEMA = {
    "type": "object",
    "properties": {
        "requirements": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "requirement_id": {"type": "string"},
                    "text": {"type": "string"},
                    "type": {"type": "string", "enum": ["performance", "environmental", "safety", "interface", "other"]},
                    "section": {"type": "string"},
                },
                "required": ["requirement_id", "text", "type", "section"],
            },
        }
    },
    "required": ["requirements"],
}

PROMPT_TEMPLATE = """You are extracting formal requirements from an engineering specification.

Below is one section of the document (section number: {section}, page: {page}).
Find every sentence that contains the word "shall" and is a requirement
statement. For each one, produce:
  - requirement_id: use the section number if the text has one (e.g. "3.2.1"),
    otherwise invent one like "{file_tag}-{{n}}"
  - text: the exact requirement sentence
  - type: one of performance, environmental, safety, interface, other
  - section: the section number this requirement belongs to (may be empty)

If there are no "shall" statements in this text, return an empty list.

Text:
---
{text}
---
"""


def extract_shall_sentences_fallback(text, section):
    """Regex-only fallback if Ollama is unavailable, so the tool still
    produces something useful offline without the LLM."""
    sentences = re.split(r"(?<=[.!?])\s+", text)
    out = []
    for i, s in enumerate(sentences):
        if re.search(r"\bshall\b", s, re.IGNORECASE):
            out.append({
                "requirement_id": section or f"R{i}",
                "text": s.strip(),
                "type": "other",
                "section": section,
            })
    return out


def extract_from_chunk(chunk, model, use_llm=True):
    text = chunk["text"]
    if "shall" not in text.lower():
        return []

    if not use_llm:
        return extract_shall_sentences_fallback(text, chunk.get("section", ""))

    prompt = PROMPT_TEMPLATE.format(
        section=chunk.get("section", ""), page=chunk["page"], text=text,
        file_tag=os.path.splitext(chunk["file"])[0][:8],
    )

    for attempt in range(2):  # try once, retry once on invalid JSON
        try:
            content, _stats = generate_structured(prompt, JSON_SCHEMA, model=model)
            data = json.loads(content)
            validated = RequirementList(**data)
            return [r.model_dump() for r in validated.requirements]
        except (json.JSONDecodeError, ValidationError) as e:
            if attempt == 0:
                continue  # retry once
            with open(ERROR_LOG, "a") as f:
                f.write(f"{chunk['file']} p.{chunk['page']} sec.{chunk.get('section')}: {e}\n")
            return extract_shall_sentences_fallback(text, chunk.get("section", ""))
        except OllamaUnavailable as e:
            print(f"ERROR: {e}", file=sys.stderr)
            print("Falling back to regex-only 'shall' extraction (no type classification).", file=sys.stderr)
            return extract_shall_sentences_fallback(text, chunk.get("section", ""))


def ingest_single_file(path):
    rev_hint = "Rev A" if "RevA" in path else ("Rev B" if "RevB" in path else "")
    if path.lower().endswith(".pdf"):
        return ingest_pdf(path, rev_hint)
    elif path.lower().endswith(".docx"):
        return ingest_docx(path, rev_hint)
    raise ValueError(f"Unsupported file type: {path}")


def run(spec_path, out_csv, model=DEFAULT_CHAT_MODEL, use_llm=True):
    chunks = ingest_single_file(spec_path)
    all_reqs = []
    for chunk in chunks:
        reqs = extract_from_chunk(chunk, model, use_llm=use_llm)
        for r in reqs:
            r["page"] = chunk["page"]
            r["source_file"] = chunk["file"]
            all_reqs.append(r)

    fieldnames = ["requirement_id", "text", "type", "section", "page", "source_file"]
    with open(out_csv, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for r in all_reqs:
            writer.writerow({k: r.get(k, "") for k in fieldnames})

    print(f"Extracted {len(all_reqs)} requirements -> {out_csv}")
    return all_reqs


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("spec_path", help="PDF or DOCX specification to extract from")
    ap.add_argument("--out", default=os.path.join(ROOT, "requirements.csv"))
    ap.add_argument("--model", default=DEFAULT_CHAT_MODEL)
    ap.add_argument("--no-llm", action="store_true", help="regex-only extraction (no Ollama needed, no type classification)")
    args = ap.parse_args()
    run(args.spec_path, args.out, model=args.model, use_llm=not args.no_llm)
