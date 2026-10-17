"""Run the DEV-ONLY false-alarm set (evals/fixtures/dev_false_alarms.jsonl). Not the frozen benchmark."""

import json
import sys

from src.contracts import IncomingMessage
from src.investigator.orchestrator import investigate


def main(use_llm: bool = True) -> int:
    bad = 0
    for line in open("evals/fixtures/dev_false_alarms.jsonl"):
        row = json.loads(line)
        v = investigate(IncomingMessage(row["id"], "dev", row["text"]), use_llm=use_llm, steps=())
        ok = v.label == "safe" if row["expected"] == "safe" else v.label != "safe"
        bad += not ok
        print(f"{'OK ' if ok else 'BAD'} {row['id']} {v.label}/{v.confidence}  {row['text'][:60]}")
    print(f"mistakes: {bad}")
    return bad


if __name__ == "__main__":
    main(use_llm="--no-llm" not in sys.argv)
