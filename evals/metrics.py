"""Predeclared three-class metrics; failures never inflate exact accuracy."""

from collections import Counter
from statistics import median

LABELS = ("safe", "suspicious", "scam")


def ratio(numerator, denominator):
    return numerator / denominator if denominator else None


def summarize(rows: list[dict]) -> dict:
    if any(r["label"] not in LABELS or r["prediction"] not in LABELS for r in rows):
        raise ValueError("Unknown label")
    n = len(rows)
    good = [r for r in rows if not r.get("error")]
    safe = [r for r in rows if r["label"] == "safe"]
    actual_scam = sum(r["label"] == "scam" for r in rows)
    predicted_scam = sum(r["prediction"] == "scam" for r in rows)
    tp = sum(r["prediction"] == r["label"] == "scam" and not r.get("error") for r in rows)
    latencies = [r["latency_s"] for r in rows]
    costs = [r["cost_usd"] for r in rows if r.get("cost_usd") is not None]
    return {
        "n": n,
        "labels": dict(Counter(r["label"] for r in rows)),
        "accuracy": ratio(sum(r["prediction"] == r["label"] for r in good), n),
        "successful_call_accuracy": ratio(sum(r["prediction"] == r["label"] for r in good), len(good)),
        "scam_precision": ratio(tp, predicted_scam),
        "scam_recall": ratio(tp, actual_scam),
        "false_positive_rate": ratio(sum(r["prediction"] == "scam" for r in safe), len(safe)),
        "warning_false_positive_rate": ratio(sum(r["prediction"] != "safe" for r in safe), len(safe)),
        "error_count": n - len(good),
        "errors": dict(Counter(r["error"] for r in rows if r.get("error"))),
        "median_latency_s": median(latencies) if latencies else None,
        "mean_cost_usd": sum(costs) / n if n and len(costs) == n else None,
        "cost_known_cases": len(costs),
        "failed_check_count": sum(sum(not e.get("ok", True) for e in r.get("evidence", [])) for r in rows),
        "confusion_matrix": {
            label: {p: sum(r["label"] == label and r["prediction"] == p for r in rows) for p in LABELS}
            for label in LABELS
        },
    }


def grouped(rows: list[dict]) -> dict:
    return {
        system: summarize([r for r in rows if r["system"] == system]) for system in sorted({r["system"] for r in rows})
    }
