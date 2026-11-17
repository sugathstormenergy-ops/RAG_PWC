from pathlib import Path
import fitz

folder = Path("docs/public")
pdf_files = sorted(folder.glob("*.pdf"))

print("Engineering Document Verification")
print("---------------------------------")

if not pdf_files:
    print("No PDF files found.")
else:
    for pdf_path in pdf_files:
        try:
            with fitz.open(pdf_path) as doc:
                page_count = len(doc)
                text = doc[0].get_text() if page_count else ""

                print(f"\nDocument: {pdf_path.name}")
                print(f"Pages: {page_count}")
                print(f"First-page characters: {len(text)}")
                print(f"Preview: {text[:200]!r}")

                if len(text.strip()) < 50:
                    print("Warning: May require OCR.")
        except Exception as error:
            print(f"Error reading {pdf_path.name}: {error}")

print("\nVerification complete.")