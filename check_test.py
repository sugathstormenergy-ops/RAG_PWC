import csv
from pathlib import Path

OUTPUT = Path("tests/test_questions.csv")
OUTPUT.parent.mkdir(parents=True, exist_ok=True)

categories = (
    ["fact"] * 8
    + ["table"] * 4
    + ["exact_term"] * 3
    + ["revision"] * 2
    + ["not_found"] * 3
)

rows = []

for number, category in enumerate(categories, start=1):
    rows.append({
        "id": number,
        "category": category,
        "question": "",
        "expected_answer": (
            "Not found in the documents"
            if category == "not_found" else ""
        ),
        "source_file": "",
        "source_page": "",
        "actual_answer": "",
        "result": ""
    })

with OUTPUT.open("w", newline="", encoding="utf-8-sig") as f:
    writer = csv.DictWriter(f, fieldnames=rows[0].keys())
    writer.writeheader()
    writer.writerows(rows)

print(f"Created: {OUTPUT}")
print(f"Total questions: {len(rows)}")