#!/bin/bash
# Verifier. Copied to /tests/test.sh and run from the working directory.
# Deterministic, no network: just checks the agent produced the expected file.

EXPECTED='smoke-ok'
ACTUAL="$(cat /app/answer.txt 2>/dev/null || true)"

mkdir -p /logs/verifier

if [ "$ACTUAL" = "$EXPECTED" ]; then
  echo "PASS: /app/answer.txt matches expected content"
  echo 1 > /logs/verifier/reward.txt
else
  echo "FAIL: expected '$EXPECTED', got '$ACTUAL'"
  echo 0 > /logs/verifier/reward.txt
fi
