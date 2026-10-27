"""Do independent LLM judges make the same determination on extraction equivalence questions?

    agreement run QUESTIONS.jsonl --judge jev|luna|clef --prompt PROMPT.txt --runs 3 --out DIR
    agreement report DIR --out report.json

`run` asks every question (schema.Question, one JSON object per line) of one judge, `--runs` times, and writes
DIR/<judge>/run-<n>.jsonl (schema.Answer per line). A judge answers yes when its p(yes) reaches --threshold (0.8, the
cut the Cochrane extraction grader applies to Jev). Rerunning resumes: answered questions are kept and failed ones
asked again. The first run copies the questions and the prompt into DIR, and later runs refuse a different one, so DIR
describes itself. `report` reads DIR and writes pairwise Cohen's kappa and raw agreement, Fleiss' kappa, unanimity
(every judge, every run), run-to-run stability and each judge's errors against `expected`, per question set and
overall, plus the list of split questions; metrics.py says how a judge's answer is formed from its runs.

Every judge gets the same request content: the prompt text as the one yes/no question, about the state
{context, prediction, reference}. Run it outside any project environment (jev needs Python 3.14), from this task
directory so `grader` imports:

    uv run --no-project --python 3.14 --with typer --with openai --with httpx --with jev==0.3.0 \\
        python -m grader.agreement run ...

Keys come from the environment: TYPESAFE_API_KEY (jev), OPENAI_API_KEY (luna), CLOUDFLARE_API_KEY and
CLOUDFLARE_ACCOUNT_ID (clef)."""
from __future__ import annotations

import asyncio
import json
import random
import shutil
import sys
import time
from pathlib import Path
from typing import Annotated, Any

import typer

from . import metrics
from .judges import NAMES, Judge, Transient, make
from .schema import Answer, Question, read_answers, read_questions, write_jsonl

CONCURRENCY = 16
THRESHOLD = 0.8
ATTEMPTS = 6
MAX_DELAY = 60.0

app = typer.Typer(add_completion=False, no_args_is_help=True, help=__doc__.split("\n\n")[0])


async def ask(judge: Judge, question: Question, prompt: str, threshold: float, sleep=asyncio.sleep) -> Answer:
    """One question, retried with jittered exponential backoff while the failure is transient. Never raises: a failure
    is an Answer with `error` set, so one bad question can't sink a run."""
    for attempt in range(1, ATTEMPTS + 1):
        started = time.monotonic()
        try:
            reply = await judge.ask(question.state(), prompt)
        except Transient as error:
            if attempt == ATTEMPTS:
                return Answer(qid=question.qid, answer=None, latency_s=time.monotonic() - started, attempts=attempt, error=f"transient, gave up: {error}")
            await sleep(min(MAX_DELAY, 2 ** (attempt - 1)) * random.uniform(0.5, 1.5))
            continue
        except Exception as error:  # a bad request, auth or response: retrying won't help
            return Answer(qid=question.qid, answer=None, latency_s=time.monotonic() - started, attempts=attempt, error=f"{type(error).__name__}: {error}")
        label = None if reply.p_yes is None else "yes" if reply.p_yes >= threshold else "no"
        return Answer(qid=question.qid, answer=label, p_yes=reply.p_yes, raw=reply.raw, latency_s=round(time.monotonic() - started, 3),
                      attempts=attempt, input_tokens=reply.input_tokens, output_tokens=reply.output_tokens, cost_usd=reply.cost_usd,
                      error="refused" if label is None else None)
    raise AssertionError("unreachable")


async def run_judge(judge: Judge, name: str, questions: list[Question], prompt: str, runs: int, out: Path,
                    threshold: float = THRESHOLD, concurrency: int = CONCURRENCY) -> list[Path]:
    """Every unanswered (run, question) pair through one concurrency limit; each answer is appended as it lands, and
    each run file is rewritten in question order at the end."""
    paths = [out / name / f"run-{n}.jsonl" for n in range(1, runs + 1)]
    kept = [{a.qid: a for a in read_answers(path) if a.error is None} for path in paths]
    limit = asyncio.Semaphore(concurrency)
    for path in paths:
        path.parent.mkdir(parents=True, exist_ok=True)

    async def one(run: int, question: Question) -> None:
        async with limit:
            answer = await ask(judge, question, prompt, threshold)
        with paths[run].open("a", encoding="utf-8") as handle:
            handle.write(answer.model_dump_json() + "\n")
        if answer.error is None:
            kept[run][question.qid] = answer
        else:
            print(f"{name} run-{run + 1} {question.qid}: {answer.error}", file=sys.stderr)

    try:
        await asyncio.gather(*(one(run, q) for run in range(runs) for q in questions if q.qid not in kept[run]))
    finally:
        await judge.aclose()
    for run, path in enumerate(paths):
        # Failed answers stay in the file only when no later attempt succeeded, so a report can count them.
        failed = {a.qid: a for a in read_answers(path) if a.error is not None}
        write_jsonl(path, [kept[run].get(q.qid) or failed[q.qid] for q in questions if q.qid in kept[run] or q.qid in failed])
    return paths


def pin(source: Path, target: Path) -> None:
    """Copy source to target, or check that target already holds the same bytes."""
    if target.exists():
        if target.read_bytes() != source.read_bytes():
            raise typer.BadParameter(f"{target} differs from {source}: use a new --out")
        return
    target.parent.mkdir(parents=True, exist_ok=True)
    if source.resolve() != target.resolve():
        shutil.copyfile(source, target)


@app.command()
def run(questions: Path, judge: Annotated[str, typer.Option(help=f"one of {', '.join(NAMES)}")],
        prompt: Annotated[Path, typer.Option(help="text of the yes/no question every judge is asked")],
        out: Annotated[Path, typer.Option(help="run directory")], runs: int = 3, threshold: float = THRESHOLD,
        concurrency: int = CONCURRENCY) -> None:
    """Ask every question of one judge, --runs times."""
    if judge not in NAMES:
        raise typer.BadParameter(f"--judge must be one of {', '.join(NAMES)}")
    parsed = read_questions(questions)
    pin(questions, out / "questions.jsonl")
    pin(prompt, out / "prompt.txt")
    started = time.monotonic()
    paths = asyncio.run(run_judge(make(judge), judge, parsed, prompt.read_text(encoding="utf-8").strip(), runs, out, threshold, concurrency))
    answered = [sum(a.error is None for a in read_answers(path)) for path in paths]
    print(f"{judge}: {answered} of {len(parsed)} answered per run in {time.monotonic() - started:.0f}s")


def load(run_dir: Path, threshold: float | None) -> tuple[list[Question], dict[str, list[list[Answer]]]]:
    questions = read_questions(run_dir / "questions.jsonl")
    answers = {}
    for judge_dir in sorted(p for p in run_dir.iterdir() if p.is_dir() and any(p.glob("run-*.jsonl"))):
        runs = sorted(judge_dir.glob("run-*.jsonl"), key=lambda p: int(p.stem.removeprefix("run-")))
        answers[judge_dir.name] = [read_answers(path) for path in runs]
    if threshold is not None:
        for runs in answers.values():
            for records in runs:
                for a in records:
                    if a.p_yes is not None:
                        a.answer = "yes" if a.p_yes >= threshold else "no"
    return questions, answers


def usage(answers: dict[str, list[list[Answer]]]) -> dict[str, Any]:
    out = {}
    for judge, runs in answers.items():
        records = [a for run in runs for a in run]
        out[judge] = {"runs": len(runs), "answers": sum(a.error is None for a in records), "errors": sum(a.error is not None for a in records),
                      "input_tokens": sum(a.input_tokens or 0 for a in records), "cost_usd": round(sum(a.cost_usd or 0 for a in records), 4),
                      "call_seconds": round(sum(a.latency_s for a in records), 1),
                      "median_latency_s": sorted(a.latency_s for a in records)[len(records) // 2] if records else None}
    return out


def cell(stat: dict[str, Any]) -> str:
    return f"{stat['count']}/{stat['of']}"


def number(value: float | None) -> str:
    return "—" if value is None else f"{value:.3f}"


def render(summary: dict[str, Any], judges: list[str]) -> str:
    """A compact Markdown view of report.json."""
    lines = []
    pairs = list(next(iter(summary.values()))["pairwise"]) if summary else []
    header = ["set", "n", *(f"κ {p}" for p in pairs), "Fleiss κ", "unanimous", *(f"{j} FE" for j in judges), *(f"{j} FNE" for j in judges)]
    lines += ["| " + " | ".join(header) + " |", "|" + "---|" * len(header)]
    for name, group in summary.items():
        row = [name, str(group["n"]), *(f"{number(group['pairwise'][p]['kappa'])} ({number(group['pairwise'][p]['agreement'])})" for p in pairs),
               number(group["fleiss"]["kappa"]), cell(group["unanimity"]),
               *(cell(group["errors"][j]["majority"]["false_equivalent"]) for j in judges),
               *(cell(group["errors"][j]["majority"]["false_not_equivalent"]) for j in judges)]
        lines.append("| " + " | ".join(row) + " |")
    return "\n".join(lines)


@app.command()
def report(run_dir: Path, out: Annotated[Path, typer.Option(help="report.json to write")],
           threshold: Annotated[float | None, typer.Option(help="re-derive every answer from p(yes) at this cut")] = None) -> None:
    """Agreement, stability and label errors over every judge's runs in RUN_DIR."""
    questions, answers = load(run_dir, threshold)
    labels = {judge: [{a.qid: a.answer for a in run} for run in runs] for judge, runs in answers.items()}
    summary = metrics.summarize(questions, labels)
    p_yes = {judge: [{a.qid: a.p_yes for a in run} for run in runs] for judge, runs in answers.items()}
    for group in summary.values():
        for item in group["split"]:
            item["p_yes"] = {judge: [run.get(item["qid"]) for run in runs] for judge, runs in p_yes.items()}
    document = {"run_dir": str(run_dir), "threshold": threshold, "judges": list(answers), "usage": usage(answers), "sets": summary}
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(document, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    print(render(summary, list(answers)))
    print(f"\n{out}")


if __name__ == "__main__":
    app()
