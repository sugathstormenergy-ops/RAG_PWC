import csv
import subprocess
import sys
import re
from pathlib import Path

INPUT = Path("tests/test_questions.csv")
OUTPUT = Path("output/evaluation_results.csv")


def normalize(text):
    return re.sub(r"\s+", " ", text.lower()).strip()


def run_rag(question):
    result = subprocess.run(
        [sys.executable, "rag_ask.py", question],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace"
    )

    if result.returncode != 0:
        raise RuntimeError(result.stderr)

    output = result.stdout

    if "ANSWER:" not in output:
        raise RuntimeError("No answer found in RAG output")

    answer_section = output.split("ANSWER:", 1)[1]

    if "RETRIEVED SOURCES:" in answer_section:
        answer, sources = answer_section.split(
            "RETRIEVED SOURCES:", 1
        )
    else:
        answer = answer_section
        sources = ""

    return answer.strip(), sources.strip()


def evaluate(expected, actual, category):
    expected = normalize(expected)
    actual = normalize(actual)

    if not expected:
        return "NEEDS_REVIEW"

    if category == "not_found":
        return (
            "PASS"
            if "not found in the documents" in actual
            else "FAIL"
        )

    if expected == actual:
        return "PASS"

    return "NEEDS_REVIEW"


def main():
    OUTPUT.parent.mkdir(exist_ok=True)

    with INPUT.open(
        "r", encoding="utf-8-sig", newline=""
    ) as file:
        questions = list(csv.DictReader(file))

    if not questions:
        print("No questions found.")
        return

    results = []

    for index, row in enumerate(questions, start=1):
        question = row["question"].strip()

        if not question:
            print(f"Skipping empty question {index}")
            continue

        print(f"\n[{index}/{len(questions)}] {question}")

        try:
            answer, sources = run_rag(question)
            status = evaluate(
                row.get("expected_answer", ""),
                answer,
                row.get("category", "")
            )
        except Exception as error:
            answer = f"ERROR: {error}"
            sources = ""
            status = "ERROR"

        result = dict(row)
        result["actual_answer"] = answer
        result["retrieved_sources"] = sources
        result["result"] = status

        results.append(result)
        print(f"Result: {status}")

    fieldnames = list(
        dict.fromkeys(
            list(questions[0].keys())
            + ["actual_answer", "retrieved_sources", "result"]
        )
    )

    with OUTPUT.open(
        "w", encoding="utf-8-sig", newline=""
    ) as file:
        writer = csv.DictWriter(
            file, fieldnames=fieldnames
        )
        writer.writeheader()
        writer.writerows(results)

    passed = sum(r["result"] == "PASS" for r in results)
    reviewed = sum(
        r["result"] == "NEEDS_REVIEW" for r in results
    )
    failed = sum(r["result"] == "FAIL" for r in results)
    errors = sum(r["result"] == "ERROR" for r in results)

    print("\n--- EVALUATION SUMMARY ---")
    print(f"Questions evaluated: {len(results)}")
    print(f"Automatic passes: {passed}")
    print(f"Needs manual review: {reviewed}")
    print(f"Failed: {failed}")
    print(f"Errors: {errors}")
    print(f"Report saved: {OUTPUT}")


if __name__ == "__main__":
    main()