"""Each adapter against a fake transport: the request it sends, the p(yes) and usage it reads back, and which failures
it marks for retry. Plus the runner's retry and resume behavior with a scripted judge. Skips an adapter whose SDK is
not installed (see agreement.py's docstring for the run environment)."""
import asyncio
import json

import pytest

pytest.importorskip("typer")  # the CLI's dependency; the public lock carries only pydantic and pytest

from grader import agreement  # noqa: E402
from grader.judges import QUESTION, Reply, Transient  # noqa: E402
from grader.schema import Question, read_answers  # noqa: E402

STATE = {"context": "Adults with a fictional condition.", "prediction": {"study_id": "Fixture 2099"}, "reference": {"study_id": "Fixture 2099"}}
PROMPT = "Do the prediction and the reference describe the same result?"


def run(coroutine):
    return asyncio.run(coroutine)


def test_clef_posts_a_system_one_body_and_reads_the_workers_ai_envelope(monkeypatch):
    httpx = pytest.importorskip("httpx")
    from grader.judges.clef import ClefJudge

    monkeypatch.setenv("CLOUDFLARE_API_KEY", "test-token")
    monkeypatch.setenv("CLOUDFLARE_ACCOUNT_ID", "acct")
    seen = []

    def handler(request):
        seen.append(request)
        result = {"model": "clef", "answers": {QUESTION: {"type": "noul", "noul": 0.9}}, "usage": {"input_tokens": 1000, "output_tokens": 1}}
        return httpx.Response(200, json={"result": result, "success": True, "errors": [], "messages": []})

    judge = ClefJudge(transport=httpx.MockTransport(handler))
    reply = run(judge.ask(STATE, PROMPT))
    assert reply.p_yes == 0.9 and reply.input_tokens == 1000 and reply.cost_usd == pytest.approx(0.00024)
    assert str(seen[0].url) == "https://api.cloudflare.com/client/v4/accounts/acct/ai/run/@cf/cloudflare/clef"
    assert seen[0].headers["authorization"] == "Bearer test-token"
    assert json.loads(seen[0].content) == {"model": "clef", "state": STATE, "questions": {QUESTION: {"type": "noul", "instructions": PROMPT}}}

    for status, kind in ((429, Transient), (503, Transient), (400, httpx.HTTPStatusError)):
        judge = ClefJudge(transport=httpx.MockTransport(lambda request, status=status: httpx.Response(status, json={"success": False})))
        with pytest.raises(kind):
            run(judge.ask(STATE, PROMPT))


def test_luna_sends_the_state_as_json_and_a_predicate_question(monkeypatch):
    httpx2 = pytest.importorskip("httpx2")
    pytest.importorskip("openai")
    from grader.judges.luna import LunaJudge

    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    seen = []
    usage = {"input_tokens": 2000, "input_tokens_details": {"cached_tokens": 0, "cache_write_tokens": 0}, "output_tokens": 0,
             "output_tokens_details": {"reasoning_tokens": 0}, "total_tokens": 2000}

    def handler(request):
        seen.append(request)
        return httpx2.Response(200, json={"model": "gpt-6-luna", "answers": [{"type": "predicate", "name": QUESTION, "probability": 0.3}], "usage": usage})

    judge = LunaJudge(http_client=httpx2.AsyncClient(transport=httpx2.MockTransport(handler)))
    reply = run(judge.ask(STATE, PROMPT))
    assert reply.p_yes == 0.3 and reply.input_tokens == 2000 and reply.cost_usd == pytest.approx(0.0002)
    assert seen[0].url.path == "/v1/decisions"
    assert json.loads(seen[0].content) == {"model": "gpt-6-luna", "input": [{"role": "user", "content": [{"type": "input_json", "data": {"state": STATE}}]}],
                                           "questions": [{"type": "predicate", "name": QUESTION, "instructions": PROMPT}]}

    refusal = LunaJudge(http_client=httpx2.AsyncClient(transport=httpx2.MockTransport(
        lambda request: httpx2.Response(200, json={"model": "gpt-6-luna", "answers": [{"type": "refusal", "name": QUESTION}], "usage": usage}))))
    assert run(refusal.ask(STATE, PROMPT)).p_yes is None
    limited = LunaJudge(http_client=httpx2.AsyncClient(transport=httpx2.MockTransport(lambda request: httpx2.Response(429, json={"error": {"message": "slow down"}}))))
    with pytest.raises(Transient):
        run(limited.ask(STATE, PROMPT))


def test_jev_sends_the_graders_system_one_question(monkeypatch):
    httpx2 = pytest.importorskip("httpx2")
    pytest.importorskip("jev")
    from grader.judges.jev import JevJudge

    monkeypatch.setenv("TYPESAFE_API_KEY", "test-key")
    seen = []

    def handler(request):
        seen.append(request)
        return httpx2.Response(200, json={"model": "jev-1.14.0", "answers": {QUESTION: {"type": "noul", "noul": 0.85}}, "usage": {"input_tokens": 100, "output_tokens": 1}})

    reply = run(JevJudge(transport=httpx2.MockTransport(handler)).ask(STATE, PROMPT))
    assert reply.p_yes == 0.85 and reply.input_tokens == 100 and reply.cost_usd == pytest.approx(0.0000042)
    body = json.loads(seen[0].content)
    assert seen[0].url.path == "/v1/systemone" and body["model"] == "jev-1.14.0" and body["state"] == STATE
    assert body["questions"] == {QUESTION: {"type": "noul", "instructions": PROMPT}}

    with pytest.raises(Transient):
        run(JevJudge(transport=httpx2.MockTransport(lambda request: httpx2.Response(502, json={"detail": "bad gateway"}))).ask(STATE, PROMPT))


class Scripted:
    """A judge that replays a script per question: a float is p(yes), an exception is raised."""

    def __init__(self, script):
        self.script, self.calls = {qid: list(steps) for qid, steps in script.items()}, []

    async def ask(self, state, prompt):
        qid = state["prediction"]["qid"]
        self.calls.append(qid)
        step = self.script[qid].pop(0)
        if isinstance(step, Exception):
            raise step
        return Reply(p_yes=step, raw={"p": step}, input_tokens=10, cost_usd=0.001)

    async def aclose(self):
        pass


def question(qid):
    return Question(qid=qid, set="fixture", context="ctx", prediction={"qid": qid}, reference={"qid": qid})


def test_ask_retries_transient_failures_and_applies_the_threshold():
    judge = Scripted({"q1": [Transient("429"), Transient("503"), 0.8]})
    answer = run(agreement.ask(judge, question("q1"), PROMPT, 0.8, sleep=lambda seconds: asyncio.sleep(0)))
    assert (answer.answer, answer.p_yes, answer.attempts, answer.error) == ("yes", 0.8, 3, None)


def test_ask_records_a_permanent_failure_without_retrying():
    judge = Scripted({"q1": [ValueError("bad request"), 0.9]})
    answer = run(agreement.ask(judge, question("q1"), PROMPT, 0.8))
    assert answer.answer is None and answer.attempts == 1 and answer.error == "ValueError: bad request" and judge.calls == ["q1"]


def test_a_rerun_asks_only_what_failed_and_writes_runs_in_question_order(tmp_path):
    questions = [question("q1"), question("q2")]
    first = Scripted({"q1": [0.9, 0.2], "q2": [ValueError("boom"), 0.95]})
    run(agreement.run_judge(first, "fake", questions, PROMPT, 2, tmp_path))
    assert [(a.qid, a.answer, a.error) for a in read_answers(tmp_path / "fake/run-1.jsonl")] == [("q1", "yes", None), ("q2", None, "ValueError: boom")]

    second = Scripted({"q2": [0.1]})
    run(agreement.run_judge(second, "fake", questions, PROMPT, 2, tmp_path))
    assert second.calls == ["q2"]
    assert [(a.qid, a.answer) for a in read_answers(tmp_path / "fake/run-1.jsonl")] == [("q1", "yes"), ("q2", "no")]
    assert [(a.qid, a.answer) for a in read_answers(tmp_path / "fake/run-2.jsonl")] == [("q1", "no"), ("q2", "yes")]
