from copy import deepcopy
import json
from pathlib import Path
from uuid import uuid4

from pydantic import ValidationError
import pytest

from evaluation.dataset import Dataset, ROOT, load_dataset, verify_ground_truth
from evaluation.grading import classify_failure, lexical_coverage, metrics
from evaluation.report import render
from evaluation.runner import redact, run


def test_dataset_exact_split_and_sources():
    data = load_dataset()
    assert len(data.questions) == 10
    assert sum(q.answerable for q in data.questions) == 8
    assert len({q.id for q in data.questions}) == 10
    assert len({q.expected_source for q in data.questions if q.answerable}) == 3
    assert all(q.rationale and q.criteria for q in data.questions if q.answerable)


@pytest.mark.parametrize("mutation", ["count", "split", "ids", "path", "page"])
def test_invalid_datasets_rejected(mutation):
    data = load_dataset().model_dump()
    if mutation == "count": data["questions"].pop()
    elif mutation == "split": data["questions"][-1]["answerable"] = True
    elif mutation == "ids": data["questions"][1]["id"] = data["questions"][0]["id"]
    elif mutation == "path": data["questions"][0]["expected_source"] = "../secret.pdf"
    elif mutation == "page": data["questions"][0]["expected_pages"] = [1]
    with pytest.raises(ValidationError):
        Dataset.model_validate(data)


@pytest.mark.skipif(not (ROOT / "data/raw/NIST.CSWP.29.pdf").is_file(), reason="Local source PDFs not available")
def test_ground_truth_excerpts_match_actual_pdf_pages():
    manifest = verify_ground_truth(load_dataset())
    assert sum(item["page_count"] for item in manifest.values()) == 75
    data = load_dataset()
    data.questions[0].criteria[0].source_excerpt = "Invented reference not in the source PDF."
    with pytest.raises(ValueError, match="Unverified"):
        verify_ground_truth(data)


def responses(dataset):
    by_question = {q.question:q for q in dataset.questions}
    def caller(base, path, payload):
        if path.endswith("/search"):
            return 200, {"results": []}
        q = by_question[payload["message"]]
        return 200, {"capability":"knowledge", "status":"answered" if q.answerable else "insufficient_evidence",
            "answer":" ".join(c.source_excerpt for c in q.criteria), "context_used":False,
            "conversation_id":str(uuid4()), "request_id":str(uuid4()),
            "citations":[{"filename":q.expected_source}] if q.answerable else []}
    return caller


def valid_check(citation, question):
    return {"metadata_valid":True, "provenance_valid":True, "source_relevant":True}


def test_runner_records_all_questions_independently_and_metrics(tmp_path):
    data = load_dataset()
    pauses = []
    report = run(data, tmp_path / "results.json", "http://localhost", valid_check,
                 caller=responses(data), sleeper=pauses.append)
    assert report["overall_status"] == "complete" and len(report["results"]) == 10
    assert len(pauses) == 9 and all(value == 65 for value in pauses)
    assert report["metrics"]["answered_count"] == 8
    assert report["metrics"]["correct_abstention_count"] == 2
    assert report["metrics"]["lexical_coverage_rate"] == 1
    assert report["results"][0]["response"]["conversation_id"] == "[PRIVATE]"
    with pytest.raises(ValueError, match="exists"):
        run(data, tmp_path / "results.json", "http://localhost", valid_check)


def test_missing_credentials_marks_evaluation_incomplete(tmp_path):
    report = run(load_dataset(), tmp_path / "missing.json", "http://localhost", valid_check,
                 credential_available=False)
    assert report["overall_status"] == "incomplete"
    assert all(r["execution"] == "not_run" for r in report["results"])
    assert report["metrics"]["answered_count"] == 0


def test_runner_errors_do_not_log_raw_exceptions_or_secrets(tmp_path):
    def caller(*args): raise TimeoutError("sensitive configured-key body")
    report = run(load_dataset(), tmp_path / "errors.json", "http://localhost", valid_check,
                 caller=caller, sleeper=lambda _:None)
    assert report["overall_status"] == "incomplete"
    assert all(r["error"] == "TimeoutError" for r in report["results"])
    assert "sensitive" not in (tmp_path / "errors.json").read_text()


def test_http_failure_is_recorded_not_abstention(tmp_path):
    report = run(load_dataset(), tmp_path / "http.json", "http://localhost", valid_check,
        caller=lambda base,path,payload:(503,{"detail":"unavailable"}), sleeper=lambda _:None)
    assert report["overall_status"] == "incomplete"
    assert report["metrics"]["correct_abstention_count"] == 0
    assert report["results"][0]["error"] == "http_503"


def test_redacts_recursive_secrets_and_access_ids():
    value = {"answer":"prefix actual-secret suffix gsk_"+"a"*32,
             "nested":[{"conversation_id":"private-cid", "request_id":"private-rid"}]}
    output = json.dumps(redact(value,["actual-secret"]))
    assert "actual-secret" not in output and "gsk_" not in output
    assert "private-cid" not in output and "private-rid" not in output


@pytest.mark.parametrize("status,answerable,checks,coverage,error,expected", [
    ("insufficient_evidence",True,[],{},None,"incorrect_abstention"),
    ("insufficient_evidence",False,[],{},None,None),
    ("answered",False,[],{},None,"unsupported_answer"),
    ("answered",True,[],{},None,"citation_mismatch"),
    ("answered",True,[{"provenance_valid":True,"source_relevant":False}],{},None,"irrelevant_source"),
    ("answered",True,[{"provenance_valid":True,"source_relevant":True}],{"criterion":False},None,"incomplete_answer"),
    ("error",True,[],{},"http_503","provider_or_transport_error"),
])
def test_failure_classification(status,answerable,checks,coverage,error,expected):
    question = load_dataset().questions[0].model_copy(update={"answerable":answerable})
    assert classify_failure(question,{"capability":"knowledge","status":status},checks,coverage,error)==expected


def test_metrics_separate_support_coverage_and_provenance():
    data = load_dataset()
    results = [
        {"question_id":"P01","execution":"executed","duration_seconds":1,
         "response":{"status":"answered"},"lexical_coverage":{"sovereignty":True,"response":False},
         "citation_checks":[{"metadata_valid":True,"source_relevant":True}]},
        {"question_id":"P02","execution":"executed","duration_seconds":2,"response":{"status":"insufficient_evidence"}},
        {"question_id":"U01","execution":"executed","duration_seconds":3,"response":{"status":"insufficient_evidence","citations":[]}},
        {"question_id":"U02","execution":"executed","duration_seconds":4,"response":{"status":"answered"}},
    ]
    review={"P01":{"support":"supported","criteria_met":{"sovereignty":True,"response":False}}}
    summary=metrics(data,results,review)
    assert summary["answered_count"]==2 and summary["correct_abstention_count"]==1
    assert summary["incorrect_abstention_count"]==1 and summary["unsupported_answer_count"]==1
    assert summary["citation_metadata_valid_rate"]==1 and summary["manual_coverage_rate"]==0.5
    assert summary["average_response_latency_seconds"]==2.5


def test_report_marks_missing_observations_and_manual_review_pending():
    data=load_dataset()
    text=render(data,{"overall_status":"incomplete","results":[{"question_id":q.id,"execution":"not_run"} for q in data.questions]}, {})
    assert "incomplete" in text and "Pending human review" in text
    assert all(q.id in text for q in data.questions)


def test_resume_preserves_recorded_results_and_only_runs_missing(tmp_path):
    data=load_dataset()
    output=tmp_path/"resume.json"
    report=run(data,output,"http://localhost",valid_check,credential_available=False)
    report=run(data,output,"http://localhost",valid_check,resume=True,caller=responses(data),sleeper=lambda _:None)
    assert report["overall_status"]=="complete" and "incomplete_reason" not in report
    def forbidden(*args): raise AssertionError("Completed questions must not run again")
    resumed=run(data,output,"http://localhost",valid_check,resume=True,caller=forbidden,sleeper=lambda _:None)
    assert resumed["results"]==report["results"]


def test_base_urls_cannot_embed_credentials(tmp_path):
    with pytest.raises(ValueError,match="without credentials"):
        run(load_dataset(),tmp_path/"bad.json","http://user:password@localhost",valid_check)


def test_provider_errors_cannot_count_as_correct_abstentions():
    result={"question_id":"U01","execution":"executed","error":"http_503", "response":{"status":"insufficient_evidence"}}
    assert metrics(load_dataset(),[result])["correct_abstention_count"]==0
