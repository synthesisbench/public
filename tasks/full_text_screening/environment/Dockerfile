FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim

RUN apt-get update \
  && apt-get install -y --no-install-recommends ca-certificates curl ripgrep poppler-utils \
  && rm -rf /var/lib/apt/lists/*

WORKDIR /task
