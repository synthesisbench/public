"""Judge adapters. Each asks one yes/no question (the prompt) about one state and returns p(yes) with usage.

Every adapter turns off its SDK's own retries and raises Transient for rate limits, 5xx and connection failures, so
the runner applies one retry policy to all three. Adapters import their SDKs lazily: running one judge needs only
that judge's dependencies."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol

NAMES = ("jev", "luna", "clef")
QUESTION = "same_result"  # the question's name in every request


@dataclass(frozen=True)
class Reply:
    p_yes: float | None  # None when the model declined to answer
    raw: Any
    input_tokens: int | None = None
    output_tokens: int | None = None
    cost_usd: float | None = None


class Transient(Exception):
    """A failure worth retrying (429, 5xx, timeout, connection)."""


class Judge(Protocol):
    async def ask(self, state: dict[str, Any], prompt: str) -> Reply: ...

    async def aclose(self) -> None: ...


def make(name: str) -> Judge:
    if name == "jev":
        from .jev import JevJudge

        return JevJudge()
    if name == "luna":
        from .luna import LunaJudge

        return LunaJudge()
    if name == "clef":
        from .clef import ClefJudge

        return ClefJudge()
    raise ValueError(f"unknown judge {name!r}; expected one of {NAMES}")


def transient_status(status: int) -> bool:
    return status in (408, 429) or status >= 500
