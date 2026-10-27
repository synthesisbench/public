"""The two file formats: questions in (one JSON object per line) and judge answers out (one per question per run)."""
from __future__ import annotations

from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict

Label = Literal["yes", "no"]


class Question(BaseModel):
    """One equivalence question: is `prediction` the same extracted result as `reference`, read under `context`?

    `expected` is the intended label when the question set has one; `meta` is free-form provenance (review, item,
    category) that judges never see."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    qid: str
    set: str
    context: str
    prediction: dict[str, Any]
    reference: dict[str, Any]
    expected: Label | None = None
    meta: dict[str, Any] = {}

    def state(self) -> dict[str, Any]:
        """What every judge is asked about: the prompt refers to these fields as state.context, state.prediction and
        state.reference."""
        return {"context": self.context, "prediction": self.prediction, "reference": self.reference}


class Answer(BaseModel):
    """One judge's answer to one question in one run. `answer` is None when the judge gave no usable answer (`error`
    says why); `p_yes` is None when the judge returns no probability, or refused."""

    model_config = ConfigDict(extra="forbid")

    qid: str
    answer: Label | None
    p_yes: float | None = None
    raw: Any = None
    latency_s: float
    attempts: int = 1
    input_tokens: int | None = None
    output_tokens: int | None = None
    cost_usd: float | None = None
    error: str | None = None


def read_questions(path: Path) -> list[Question]:
    questions = [Question.model_validate_json(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    duplicate = len(questions) - len({q.qid for q in questions})
    if duplicate:
        raise ValueError(f"{path}: {duplicate} duplicate qids")
    return questions


def read_answers(path: Path) -> list[Answer]:
    if not path.is_file():
        return []
    return [Answer.model_validate_json(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def write_jsonl(path: Path, records: list[BaseModel]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(record.model_dump_json() + "\n" for record in records), encoding="utf-8")
