from pathlib import Path
import pymupdf
from ollama import chat

PDF_FOLDER = Path("docs/public")
MODEL = "llama3.1:8b"

def load_pdf():
    pages = []

    for pdf_path in sorted(PDF_FOLDER.glob("*.pdf")):
        with pymupdf.open(pdf_path) as doc:
            for page_number, page in enumerate(doc, start=1):
                text = page.get_text().strip()

                if text:
                    pages.append({
                        "filename": pdf_path.name,
                        "page": page_number,
                        "text": text
                    })

    return pages


def ask_question(pages, question):
    # Small initial test: use the first few pages.
    selected = pages[:3]

    context = "\n\n".join(
        f"Document: {p['filename']}, Page: {p['page']}\n"
        f"{p['text'][:3500]}"
        for p in selected
    )

    prompt = f"""
You are an engineering document assistant.

Answer ONLY using the document text below.
If the answer is absent, say:
"Not found in the documents."

Include the document name and page number.

DOCUMENT TEXT:
{context}

QUESTION:
{question}
"""

    response = chat(
        model=MODEL,
        messages=[
            {"role": "user", "content": prompt}
        ],
        options={"temperature": 0}
    )

    return response.message.content


def main():
    pages = load_pdf()

    print(f"Loaded {len(pages)} PDF pages.")

    if not pages:
        print("No readable PDF text found.")
        return

    while True:
        question = input("\nAsk a question (exit to quit): ")

        if question.lower() == "exit":
            break

        answer = ask_question(pages, question)
        print("\nAI ANSWER:\n")
        print(answer)


if __name__ == "__main__":
    main()