FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim

RUN uv pip install --system pydantic litellm

WORKDIR /task
COPY . /tests
