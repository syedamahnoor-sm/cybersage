"""Transparent lexical signals plus explicit manual support/coverage review."""

from statistics import mean


def lexical_coverage(question, response):
    text = " ".join(response.get("answer", "").split()).casefold() if response.get("answer") else ""
    return {item.id: all(any(term.casefold() in text for term in group) for group in item.groups)
            for item in question.criteria}


def classify_failure(question, response, citation_checks, coverage, error=None):
    if error:
        return "provider_or_transport_error"
    if response.get("capability") != "knowledge":
        return "routing_failure"
    status = response.get("status")
    if status == "insufficient_evidence":
        return "incorrect_abstention" if question.answerable else None
    if status != "answered":
        return "unexpected_status"
    if not question.answerable:
        return "unsupported_answer"
    if not citation_checks or not all(c.get("provenance_valid") for c in citation_checks):
        return "citation_mismatch"
    if not all(c.get("source_relevant") for c in citation_checks):
        return "irrelevant_source"
    if not all(coverage.values()):
        return "incomplete_answer"
    return None


def metrics(dataset, results, reviews=None):
    reviews = reviews or {}
    by_id = {result["question_id"]: result for result in results}
    answered = correct_abstentions = incorrect_abstentions = unsupported = 0
    checked = valid = relevant = provenance = 0
    durations = []
    covered = total = 0
    human_covered = human_total = reviewed = 0
    failures = {}
    for question in dataset.questions:
        result = by_id.get(question.id, {})
        response = result.get("response") or {}
        status = response.get("status") if not result.get("error") and result.get("execution") == "executed" else None
        answered += status == "answered"
        correct_abstentions += not question.answerable and status == "insufficient_evidence" and not response.get("citations")
        incorrect_abstentions += question.answerable and status == "insufficient_evidence"
        review = reviews.get(question.id)
        unsupported += status == "answered" and (not question.answerable or bool(review and review.get("support") == "unsupported"))
        if result.get("execution") == "executed" and result.get("duration_seconds") is not None:
            durations.append(result["duration_seconds"])
        for check in result.get("citation_checks", []):
            checked += 1
            valid += bool(check.get("metadata_valid"))
            provenance += bool(check.get("provenance_valid"))
            relevant += bool(check.get("source_relevant"))
        signals = result.get("lexical_coverage", {})
        if question.answerable:
            total += len(question.criteria)
            covered += sum(bool(signals.get(c.id)) for c in question.criteria)
            if review:
                if set(review["criteria_met"]) != {c.id for c in question.criteria}:
                    raise ValueError("Manual review criteria mismatch")
                reviewed += 1
                human_total += len(question.criteria)
                human_covered += sum(review["criteria_met"].values())
        failure = result.get("failure_classification")
        if failure:
            failures[failure] = failures.get(failure, 0) + 1
    return {"dataset_questions": 10, "executed_count": len(durations), "answered_count": answered,
        "correct_abstention_count": correct_abstentions, "incorrect_abstention_count": incorrect_abstentions,
        "unsupported_answer_count": unsupported, "unsupported_count_scope": "unanswerable answers + manually unsupported answers",
        "citations_checked": checked, "citation_metadata_valid_count": valid,
        "citation_metadata_valid_rate": valid / checked if checked else None,
        "citation_provenance_valid_count": provenance,
        "citation_provenance_valid_rate": provenance / checked if checked else None,
        "citation_source_relevant_count": relevant, "citation_source_relevant_rate": relevant / checked if checked else None,
        "lexical_criteria_met": covered, "criteria_total": total,
        "lexical_coverage_rate": covered / total if total else None,
        "manually_reviewed_answerable_questions": reviewed,
        "manual_criteria_met": human_covered, "manual_criteria_total": human_total,
        "manual_coverage_rate": human_covered / human_total if human_total else None,
        "average_response_latency_seconds": mean(durations) if durations else None,
        "failure_counts": failures}
