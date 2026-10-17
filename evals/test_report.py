import csv
import json
from pathlib import Path
from unittest.mock import patch

import pytest

from evals.report import report


def fixture(tmp_path):
    source = Path(__file__).parent / "runs" / "dev-checks-v2"
    for name in ("manifest.json", "inputs.json", "predictions.jsonl"):
        (tmp_path / name).write_bytes((source / name).read_bytes())
    return tmp_path


def test_report_does_not_present_development_as_benchmark_or_unknown_cost_as_zero(tmp_path):
    run = fixture(tmp_path)
    destination = tmp_path / "report"
    with patch("evals.report.chart"):
        report(run, destination)
    text = (destination / "RESULTS.md").read_text()
    assert "DEVELOPMENT SMOKE — NOT THE BENCHMARK" in text
    assert "| Mean USD / case | unknown | unknown |" in text
    with (destination / "results.csv").open() as f:
        rows = list(csv.DictReader(f))
    assert len(rows) == 16
    assert all(r["cost_usd"] == "" for r in rows)


def test_report_rejects_changed_labels_even_if_pair_counts_match(tmp_path):
    run = fixture(tmp_path)
    path = run / "predictions.jsonl"
    rows = [json.loads(line) for line in path.read_text().splitlines()]
    rows[0]["label"] = "safe"
    path.write_text("".join(json.dumps(r) + "\n" for r in rows))
    with pytest.raises(ValueError, match="metadata"):
        report(run, tmp_path / "report")


def test_full_report_discloses_limited_sandbox_coverage(tmp_path):
    run = fixture(tmp_path)
    manifest_path = run / "manifest.json"
    manifest = json.loads(manifest_path.read_text())
    manifest.update(full_run=True, mode="full", detonation_cases=["dev-1"])
    manifest_path.write_text(json.dumps(manifest))
    predictions = run / "predictions.jsonl"
    rows = [json.loads(line) for line in predictions.read_text().splitlines()]
    for row in rows:
        if row["case_id"] == "dev-1" and row["system"] == "tripwire":
            row.update(detonation_requested=True, screenshot_path="/tmp/tripwire-test.png")
    predictions.write_text("".join(json.dumps(row) + "\n" for row in rows))
    with patch("evals.report.chart"):
        report(run, tmp_path / "report")
    text = (tmp_path / "report" / "RESULTS.md").read_text()
    assert "1/8 cases requested detonation" in text
    assert "1 returned screenshot paths" in text
    assert "Droid may be skipped" in text
