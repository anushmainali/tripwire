"""Validate saved Tripwire predictions before a baseline-only correction run."""

import hashlib
import json
from pathlib import Path


def source_fingerprints(root: Path) -> dict[str, str]:
    return {
        str(path.relative_to(root)): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in sorted((root / "src").rglob("*.py"))
        if path != root / "src" / "llm.py"
    }


def load_tripwire(source: Path, rows: list[dict], current_sources: dict[str, str]) -> tuple[list[dict], dict]:
    from evals.run import validate_saved

    manifest = json.loads((source / "manifest.json").read_text())
    if not manifest["full_run"] or manifest["mode"] != "full":
        raise ValueError("Reuse requires a real full-system benchmark")
    inputs = json.loads((source / "inputs.json").read_text())
    if inputs != rows:
        raise ValueError("Reuse input rows differ from the frozen benchmark")
    pinned = json.loads((source / "investigator_sources.json").read_text())
    if pinned != current_sources:
        raise ValueError("Investigator source changed; cannot reuse its predictions")
    raw = (source / "predictions.jsonl").read_bytes()
    predictions = [json.loads(line) for line in raw.splitlines()]
    validate_saved(predictions, rows)
    if len(predictions) != 2 * len(rows):
        raise ValueError("Reuse requires complete paired predictions")
    tripwire = [r for r in predictions if r["system"] == "tripwire"]
    metadata = {
        "source_run": str(source),
        "source_git_sha": manifest["git_sha"],
        "source_predictions_sha256": hashlib.sha256(raw).hexdigest(),
        "reused_tripwire_cases": len(tripwire),
        "reason": (
            "Baseline-only token-budget correction; unchanged Tripwire predictions reused exactly, "
            "no new investigation calls."
        ),
    }
    return tripwire, metadata
