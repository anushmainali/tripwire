"""Regression tests for the dev-only false-alarm set (deterministic path, no network, no LLM)."""

import json

import pytest

from src.contracts import IncomingMessage
from src.investigator.orchestrator import investigate

ROWS = [json.loads(line) for line in open("evals/fixtures/dev_false_alarms.jsonl")]


@pytest.mark.parametrize("row", ROWS, ids=[r["id"] for r in ROWS])
def test_dev_set(row):
    v = investigate(IncomingMessage(row["id"], "dev", row["text"]), use_llm=False, steps=())
    assert (v.label == "safe") == (row["expected"] == "safe"), (row["text"], v.label)
