"""Cloudflare Workers AI Clef (@cf/cloudflare/clef) through the REST endpoint
POST https://api.cloudflare.com/client/v4/accounts/{CLOUDFLARE_ACCOUNT_ID}/ai/run/@cf/cloudflare/clef with
CLOUDFLARE_API_KEY as a bearer token.

Clef takes the System One body Jev takes (state plus a `noul` question), but the Typesafe client can't call it: that
client appends /v1/systemone to its base URL, and Workers AI wraps the answer in its {"result": ...} envelope."""
from __future__ import annotations

import os
from typing import Any

import httpx

from . import QUESTION, Reply, Transient, transient_status

MODEL = "clef"
URL = "https://api.cloudflare.com/client/v4/accounts/{account}/ai/run/@cf/cloudflare/clef"
# https://developers.cloudflare.com/workers-ai/models/clef/, checked 2026-10-26: $0.24 per 1M input tokens, output free.
USD_PER_INPUT_TOKEN = 0.24e-6


class ClefJudge:
    def __init__(self, transport: httpx.AsyncBaseTransport | None = None) -> None:
        token, account = os.environ.get("CLOUDFLARE_API_KEY"), os.environ.get("CLOUDFLARE_ACCOUNT_ID")
        if not token or not account:
            raise RuntimeError("CLOUDFLARE_API_KEY and CLOUDFLARE_ACCOUNT_ID must be set")
        self.url = URL.format(account=account)
        self.client = httpx.AsyncClient(headers={"Authorization": f"Bearer {token}"}, timeout=120.0, transport=transport)

    async def ask(self, state: dict[str, Any], prompt: str) -> Reply:
        body = {"model": MODEL, "state": state, "questions": {QUESTION: {"type": "noul", "instructions": prompt}}}
        try:
            response = await self.client.post(self.url, json=body)
        except httpx.TransportError as error:
            raise Transient(f"{type(error).__name__}: {error}") from error
        if transient_status(response.status_code):
            raise Transient(f"HTTP {response.status_code}: {response.text[:500]}")
        response.raise_for_status()
        payload = response.json()
        result = payload["result"]
        usage = result["usage"]
        return Reply(p_yes=result["answers"][QUESTION]["noul"], raw=payload, input_tokens=usage["input_tokens"],
                     output_tokens=usage["output_tokens"], cost_usd=usage["input_tokens"] * USD_PER_INPUT_TOKEN)

    async def aclose(self) -> None:
        await self.client.aclose()
