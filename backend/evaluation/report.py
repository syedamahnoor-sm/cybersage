"""Render recorded observations and a separately authored manual review."""

import json
import argparse
from hashlib import sha256
from pathlib import Path

from evaluation.dataset import load_dataset
from evaluation.grading import metrics


def render(dataset, report, reviews):
    rows = {result["question_id"]: result for result in report["results"]}
    summary = metrics(dataset, report["results"], reviews)
    lines = ["# CyberSage: recorded 10-question evaluation", "",
        f"Run status: **{report['overall_status']}**. Dataset: **8 answerable / 2 unanswerable**.", "",
        "These are recorded responses, not model examples. Manual grades are separate from lexical signals.", "",
        "| ID | Expected | Observed status | Capability | Seconds | Manual grade |", "|---|---|---|---|---:|---|"]
    for q in dataset.questions:
        result = rows[q.id]
        response = result.get("response") or {}
        review = reviews.get(q.id, {})
        lines.append(f"| {q.id} | {'answerable' if q.answerable else 'unanswerable'} | "
                     f"{response.get('status', result['execution'])} | {response.get('capability','—')} | "
                     f"{result.get('duration_seconds','—')} | {review.get('grade','pending')} |")
    lines += ["", "## Metrics", "", "```json", json.dumps(summary, indent=2), "```", "",
        "Metadata validity and source-filename matches do not prove factual support or completeness.", "",
        "## Question-by-question observations", ""]
    for q in dataset.questions:
        result = rows[q.id]
        response = result.get("response") or {}
        review = reviews.get(q.id,{})
        lines += [f"### {q.id}: {q.question}", "",
            f"Expected source/pages: `{q.expected_source}` / {q.expected_pages or 'none'}. {q.rationale}", "",
            "Expected criteria:", *[f"- {c.id}: {c.description} (PDF p. {c.page})" for c in q.criteria], "",
            "Actual answer:", "", *[("> " + line).rstrip() for line in (response.get("answer") or "[No answer returned]").splitlines()], "",
            f"Observed failure signal: `{result.get('failure_classification')}`; error: `{result.get('error')}`.", "",
            "Citations:", *[f"- {c.get('label')} — `{c.get('evidence_id')}`, chunk index {c.get('chunk_index')}"
                              for c in response.get("citations",[])], "",
            "Manual review: " + review.get("notes", "Pending human review."), ""]
    return "\n".join(lines)


def write_report(results_path, review_path, destination):
    dataset = load_dataset()
    report = json.loads(Path(results_path).read_text(encoding="utf-8"))
    reviews = json.loads(Path(review_path).read_text(encoding="utf-8"))["reviews"]
    for result in report["results"]:
        review = reviews.get(result["question_id"])
        if review and review.get("response_sha256") != response_hash(result.get("response")):
            raise ValueError("Review does not match recorded response")
    text = render(dataset, report, reviews)
    Path(destination).write_text(text, encoding="utf-8")
    return metrics(dataset, report["results"], reviews)


def response_hash(response):
    return sha256(json.dumps(response, sort_keys=True, ensure_ascii=True).encode()).hexdigest()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--results", type=Path, default=Path("evaluation/results/milestone9.json"))
    parser.add_argument("--reviews", type=Path, default=Path("evaluation/reviews.json"))
    parser.add_argument("--output", type=Path, default=Path("../docs/milestone9-results.md"))
    args = parser.parse_args()
    print(json.dumps(write_report(args.results, args.reviews, args.output), indent=2))
