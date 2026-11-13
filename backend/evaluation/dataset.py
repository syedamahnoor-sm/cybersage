import hashlib
import json
from pathlib import Path
import re

import pymupdf
from pydantic import BaseModel, ConfigDict, Field, model_validator

ROOT = Path(__file__).resolve().parents[2]
DATASET_PATH = Path(__file__).with_name("dataset.json")


def normalize(text):
    return " ".join(text.split())


class Criterion(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str
    description: str
    page: int = Field(ge=1)
    source_excerpt: str = Field(min_length=10)
    groups: list[list[str]] = Field(min_length=1)


class Question(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str
    question: str = Field(min_length=1, max_length=2000)
    answerable: bool
    expected_source: str | None
    expected_pages: list[int]
    criteria: list[Criterion]
    rationale: str

    @model_validator(mode="after")
    def valid_ground_truth(self):
        if self.answerable:
            if not self.expected_source or Path(self.expected_source).name != self.expected_source:
                raise ValueError("Answerable items require a safe source filename")
            if not self.criteria or not self.expected_pages:
                raise ValueError("Answerable items require verified criteria/pages")
            if any(item.page not in self.expected_pages for item in self.criteria):
                raise ValueError("Criterion pages must be in expected pages")
            if len({item.id for item in self.criteria}) != len(self.criteria):
                raise ValueError("Criterion IDs must be unique")
        elif self.expected_source or self.expected_pages or self.criteria:
            raise ValueError("Unanswerable items cannot invent supporting sources")
        return self


class Dataset(BaseModel):
    model_config = ConfigDict(extra="forbid")
    version: int
    top_k: int = Field(ge=1, le=20)
    questions: list[Question]

    @model_validator(mode="after")
    def exact_split(self):
        if len(self.questions) != 10 or sum(q.answerable for q in self.questions) != 8:
            raise ValueError("Dataset must contain exactly 8 answerable and 2 unanswerable questions")
        if len({q.id for q in self.questions}) != 10:
            raise ValueError("Question IDs must be unique")
        if len({q.expected_source for q in self.questions if q.answerable}) != 3:
            raise ValueError("Answerable questions must cover three sources")
        return self


def load_dataset(path=DATASET_PATH):
    return Dataset.model_validate_json(Path(path).read_text(encoding="utf-8"))


def verify_ground_truth(dataset, raw_directory=ROOT / "data" / "raw"):
    pages = {}
    manifest = {}
    for filename in sorted({q.expected_source for q in dataset.questions if q.answerable}):
        path = raw_directory / filename
        with pymupdf.open(path) as pdf:
            pages[filename] = [normalize(page.get_text()) for page in pdf]
        manifest[filename] = {"sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                              "page_count": len(pages[filename])}
    for question in dataset.questions:
        for criterion in question.criteria:
            if normalize(criterion.source_excerpt) not in pages[question.expected_source][criterion.page - 1]:
                raise ValueError(f"Unverified ground-truth excerpt: {question.id}/{criterion.id}")
    if any(re.search(r"\bmars\b", page, re.I) for source in pages.values() for page in source):
        raise ValueError("Recheck the Mars unanswerability assumption")
    casebook = pages["CyberSage_Security_Incident_Casebook_RAG_v2.pdf"][2]
    if re.search(r"\b[a-fA-F0-9]{64}\b", casebook):
        raise ValueError("Recheck CS-INC-002 hash unanswerability")
    return manifest
