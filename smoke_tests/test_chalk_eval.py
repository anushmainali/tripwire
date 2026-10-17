"""Chalk Evaluations smoke test: the evaluation quick start, verbatim.

Source: https://docs.chalk.ai/docs/evaluations/quick-start
Auth: your `chalk login` session and active environment (`chalk user` to check).
Expected output: EvaluationRunStatus.SUCCEEDED, then 0.75.

Run from the repo root: .venv/bin/python smoke_tests/test_chalk_eval.py
Chalk imports this file inside every function it deploys, so it must stay
self-contained (no imports from this repo) with the run code under __main__.
"""

import chalkcompute
import pyarrow.compute as pc

@chalkcompute.function
def triage(message: str) -> str:
    import json, re
    text = message.lower()
    if "refund" in text or "money back" in text:
        intent = "refund"
    elif "cancel" in text or "close my account" in text:
        intent = "cancel"
    elif "invoice" in text or "billed" in text or "card" in text:
        intent = "billing"
    elif "where is" in text or "waiting" in text or "arrived" in text:
        intent = "status"
    else:
        return "unclassified"
    amount = re.search(r"\d+(?:\.\d+)?", message)
    return json.dumps({"intent": intent, "amount": float(amount.group()) if amount else 0.0})

valid_json = chalkcompute.scorers.json_valid(name="valid-json")

if __name__ == "__main__":
    dataset = chalkcompute.DatasetClient().upload("support-triage", [
        {"message": "I was charged twice for order 1182 ($49.99), please refund",
         "expected": '{"intent": "refund", "amount": 49.99}', "expected_intent": "refund"},
        {"message": "Where is my order? It was due Tuesday.",
         "expected": '{"intent": "status", "amount": 0.0}', "expected_intent": "status"},
        {"message": "Please close my account and refund the last $12 charge",
         "expected": '{"intent": "cancel", "amount": 12.0}', "expected_intent": "cancel"},
        {"message": "Following up on my last email",
         "expected": '{"intent": "status", "amount": 0.0}', "expected_intent": "status"},
    ])

    evaluation = chalkcompute.Evaluation.create(
        "support-triage",
        dataset=dataset,
        task=triage,
        scorers=[valid_json],
    )

    run = evaluation.run(metadata={"git_sha": "abc123"}).wait()
    print(run.status)

    table = chalkcompute.DatasetClient().read(run.result_dataset)
    print(pc.mean(table["valid-json_value"]).as_py())
