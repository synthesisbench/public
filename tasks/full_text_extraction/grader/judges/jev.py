"""Jev through the `jev` package's Typesafe client: the System One request the Cochrane extraction grader sends
(one `noul` question over the state), POST https://api.typesafe.ai/v1/systemone. Key: TYPESAFE_API_KEY.

This module's name shadows nothing: it is grader.judges.jev, and `import jev` below is absolute."""
from __future__ import annotations

from typing import Any

import jev
from typesafe_sdk import RetryPolicy, TypeSafeAPIConnectionError, TypeSafeAPIError

from . import QUESTION, Reply, Transient, transient_status

MODEL = "jev-1.14.0"  # the grader's pinned model
USD_PER_INPUT_TOKEN = 0.042e-6  # https://docs.typesafe.ai/models, checked 2026-10-26; output is free


class JevJudge:
    def __init__(self, transport: Any = None) -> None:
        self.client = jev.AsyncTypeSafeClient(retry=RetryPolicy(max_retries=0), transport=transport, timeout=120.0)

    async def ask(self, state: dict[str, Any], prompt: str) -> Reply:
        try:
            response = await self.client.system_one(state=state, questions={QUESTION: jev.Noul(instructions=prompt)}, model=MODEL)
        except TypeSafeAPIError as error:
            if transient_status(error.status):
                raise Transient(str(error)) from error
            raise
        except TypeSafeAPIConnectionError as error:
            raise Transient(str(error)) from error
        usage = response.usage
        return Reply(p_yes=response.nouls[QUESTION].noul, raw=response.model_dump(mode="json"), input_tokens=usage.input_tokens,
                     output_tokens=usage.output_tokens, cost_usd=usage.input_tokens * USD_PER_INPUT_TOKEN)

    async def aclose(self) -> None:
        await self.client.aclose()
