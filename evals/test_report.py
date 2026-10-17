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
