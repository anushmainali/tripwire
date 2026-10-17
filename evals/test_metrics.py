import pytest

from evals.metrics import summarize
from evals.run import read_results


def row(label, prediction, error=None):
    return {"label": label, "prediction": prediction, "error": error, "latency_s": 2, "cost_usd": None}


def test_three_class_metrics_and_warning_fpr():
    result = summarize(
        [
            row("safe", "safe"),
            row("safe", "suspicious"),
            row("safe", "scam"),
            row("scam", "scam"),
            row("scam", "suspicious"),
            row("suspicious", "suspicious"),
        ]
    )
    assert result["accuracy"] == 0.5
    assert result["scam_precision"] == 0.5
    assert result["scam_recall"] == 0.5
    assert result["false_positive_rate"] == pytest.approx(1 / 3)
    assert result["warning_false_positive_rate"] == pytest.approx(2 / 3)
    assert result["mean_cost_usd"] is None
    assert result["confusion_matrix"]["safe"] == {"safe": 1, "suspicious": 1, "scam": 1}


def test_failures_cannot_count_as_correct_and_empty_denominators():
    result = summarize([row("suspicious", "suspicious", "timeout"), row("safe", "safe")])
    assert result["accuracy"] == 0.5
    assert result["successful_call_accuracy"] == 1
    assert result["error_count"] == 1
    assert result["scam_precision"] is None
    assert result["scam_recall"] is None
    assert summarize([])["accuracy"] is None
    with pytest.raises(ValueError):
        summarize([row("safe", "sure")])


def test_resume_truncates_only_incomplete_final_line(tmp_path):
    path = tmp_path / "predictions.jsonl"
    path.write_bytes(b'{"case_id":"a"}\n{"case')
    assert read_results(path) == [{"case_id": "a"}]
    assert path.read_bytes() == b'{"case_id":"a"}\n'
    path.write_bytes(b'bad\n{"case_id":"a"}\n')
    with pytest.raises(ValueError):
        read_results(path)
