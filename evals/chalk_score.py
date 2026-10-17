"""Replay saved predictions as real Chalk tasks and score remotely (no new LLM calls).

Self-contained module: Chalk imports it in the deployed Function. All local repo
imports and dataset IO stay under main. Docs: docs.chalk.ai/docs/evaluations/quick-start
and docs.chalk.ai/docs/evaluations/scorers. Uses existing Chalk CLI login.
"""

import chalkcompute


@chalkcompute.function(name="tripwire-replay-prediction", call_timeout=30, retries=0)
def replay(prediction: str) -> str:
    return prediction


SCORERS = [
    chalkcompute.scorers.sql("correct", "CASE WHEN inference_error = '' AND output = expected THEN 1.0 ELSE 0.0 END"),
    chalkcompute.scorers.sql("safe_case", "CASE WHEN expected = 'safe' THEN 1.0 ELSE 0.0 END"),
    chalkcompute.scorers.sql("scam_case", "CASE WHEN expected = 'scam' THEN 1.0 ELSE 0.0 END"),
    chalkcompute.scorers.sql("scam_prediction", "CASE WHEN output = 'scam' THEN 1.0 ELSE 0.0 END"),
    chalkcompute.scorers.sql(
        "scam_tp", "CASE WHEN inference_error = '' AND expected = 'scam' AND output = 'scam' THEN 1.0 ELSE 0.0 END"
    ),
    chalkcompute.scorers.sql("false_positive", "CASE WHEN expected = 'safe' AND output = 'scam' THEN 1.0 ELSE 0.0 END"),
    chalkcompute.scorers.sql("warning_fp", "CASE WHEN expected = 'safe' AND output <> 'safe' THEN 1.0 ELSE 0.0 END"),
    chalkcompute.scorers.sql("inference_failed", "CASE WHEN inference_error <> '' THEN 1.0 ELSE 0.0 END"),
]


def main():
    import argparse
    import json
    from pathlib import Path

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("run_dir", type=Path)
    args = parser.parse_args()
    manifest = json.loads((args.run_dir / "manifest.json").read_text())
    predictions = [json.loads(line) for line in (args.run_dir / "predictions.jsonl").read_text().splitlines()]
    if len(predictions) != 2 * manifest["cases"]:
        parser.error("Only complete paired runs can be published")
    records = [
        {
            "case_id": r["case_id"],
            "system": r["system"],
            "prediction": r["prediction"],
            "expected": r["label"],
            "source": r["source"],
            "inference_error": r.get("error") or "",
            "latency_s": r["latency_s"],
        }
        for r in predictions
    ]
    client = chalkcompute.DatasetClient()
    dataset = client.upload("tripwire-" + args.run_dir.name, records, timeout=120)
    evaluation = chalkcompute.Evaluation.create(
        "tripwire-" + args.run_dir.name,
        dataset=dataset,
        task=replay,
        scorers=SCORERS,
        metadata={"purpose": "saved-prediction replay; no fresh inference", **manifest},
    )
    run = evaluation.run(metadata={"git_sha": manifest["git_sha"], "mode": manifest["mode"]})
    receipt_path = args.run_dir / "chalk_receipt.json"
    receipt = {
        "evaluation_id": evaluation.id,
        "run_id": run.id,
        "status": str(run.status),
        "environment_id": run.environment_id,
        "method": "local inference; remote replay task and SQL scorers",
    }
    receipt_path.write_text(json.dumps(receipt, indent=2) + "\n")
    print(json.dumps(receipt), flush=True)
    run = run.wait(timeout=600, poll_interval=3)
    table = client.read(run.result_dataset)
    receipt.update(
        status=str(run.status),
        result_dataset_id=run.result_dataset_id,
        result_dataset_revision_id=run.result_dataset_revision_id,
        rows=table.num_rows,
    )
    remote = table.to_pylist()
    error_cols = [name for name in table.column_names if name.endswith("_error") and name != "inference_error"]
    errors = sum(any(row.get(name) for name in error_cols) for row in remote)
    receipt["row_errors"] = errors
    receipt["columns"] = table.column_names
    # Validate remote task output and every scorer against local predictions.
    keyed = {(r["case_id"], r["system"]): r for r in records}
    if table.num_rows != len(records) or errors:
        receipt["verified"] = False
    else:
        seen = set()
        verified = True
        for row in remote:
            key = (row["case_id"], row["system"])
            seen.add(key)
            expected = keyed[key]
            actual = row["output"]
            checks = {
                "correct": not expected["inference_error"] and actual == expected["expected"],
                "safe_case": expected["expected"] == "safe",
                "scam_case": expected["expected"] == "scam",
                "scam_prediction": actual == "scam",
                "scam_tp": not expected["inference_error"] and actual == expected["expected"] == "scam",
                "false_positive": expected["expected"] == "safe" and actual == "scam",
                "warning_fp": expected["expected"] == "safe" and actual != "safe",
                "inference_failed": bool(expected["inference_error"]),
            }
            verified &= actual == expected["prediction"] and all(
                row.get(name + "_value") == float(value) for name, value in checks.items()
            )
        receipt["verified"] = verified and len(seen) == len(records)
    receipt_path.write_text(json.dumps(receipt, indent=2) + "\n")
    (args.run_dir / "chalk_rows.json").write_text(json.dumps(remote, indent=2, default=str) + "\n")
    print(json.dumps(receipt, indent=2))
    if not receipt["verified"]:
        raise SystemExit("Remote scoring failed row-count/error/value verification; inspect saved receipt.")


if __name__ == "__main__":
    main()
