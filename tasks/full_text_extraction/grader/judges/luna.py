"""gpt-6-luna through OpenAI's Decisions API (POST https://api.openai.com/v1/decisions) with the official SDK's
AsyncOpenAI.decisions.create. Key: OPENAI_API_KEY.

The state goes in as one user message holding an input_json part, wrapped as {"state": ...} so the prompt's
state.context, state.prediction and state.reference name the same fields they name for Jev and Clef. The question is
a `predicate`, whose `probability` is p(yes)."""
from __future__ import annotations

from typing import Any

import openai

from . import QUESTION, Reply, Transient, transient_status

MODEL = "gpt-6-luna"
# https://developers.openai.com/api/docs/guides/decisions, checked 2026-10-26: uncached input $0.10 per 1M tokens,
# output free. Cached reads are cheaper; pricing every input token at the uncached rate makes cost an upper bound.
USD_PER_INPUT_TOKEN = 0.10e-6


class LunaJudge:
    def __init__(self, http_client: Any = None) -> None:
        self.client = openai.AsyncOpenAI(max_retries=0, timeout=120.0, http_client=http_client)

    async def ask(self, state: dict[str, Any], prompt: str) -> Reply:
        try:
            decision = await self.client.decisions.create(
                model=MODEL,
                input=[{"role": "user", "content": [{"type": "input_json", "data": {"state": state}}]}],
                questions=[{"type": "predicate", "name": QUESTION, "instructions": prompt}],
            )
        except openai.APIStatusError as error:
            if transient_status(error.status_code):
                raise Transient(str(error)) from error
            raise
        except openai.APIConnectionError as error:  # includes timeouts
            raise Transient(str(error)) from error
        answer = next(a for a in decision.answers if a.name == QUESTION)
        usage = decision.usage
        return Reply(p_yes=answer.probability if answer.type == "predicate" else None, raw=decision.model_dump(mode="json"),
                     input_tokens=usage.input_tokens, output_tokens=usage.output_tokens, cost_usd=usage.input_tokens * USD_PER_INPUT_TOKEN)

    async def aclose(self) -> None:
        await self.client.close()
