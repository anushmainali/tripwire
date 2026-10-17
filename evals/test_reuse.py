import json
from pathlib import Path

import pytest

from evals.reuse import load_tripwire


def fixture(tmp_path):
    origin = Path(__file__).parent / "runs" / "dev-checks-v2"
    for name in ("manifest.json", "inputs.json", "predictions.jsonl"):
        (tmp_path / name).write_bytes((origin / name).read_bytes())
    manifest = json.loads((tmp_path / "manifest.json").read_text())
    manifest.update(full_run=True, mode="full")
    (tmp_path / "manifest.json").write_text(json.dumps(manifest))
    (tmp_path / "investigator_sources.json").write_text(json.dumps({"src/test.py": "pinned"}))
    return json.loads((tmp_path / "inputs.json").read_text())


def test_reuse_preserves_exact_predictions_and_provenance(tmp_path):
    rows = fixture(tmp_path)
    predictions, metadata = load_tripwire(tmp_path, rows, {"src/test.py": "pinned"})
    originals = [json.loads(line) for line in (tmp_path / "predictions.jsonl").read_text().splitlines()]
    assert predictions == [r for r in originals if r["system"] == "tripwire"]
    assert metadata["reused_tripwire_cases"] == 8
    assert len(metadata["source_predictions_sha256"]) == 64


def test_reuse_rejects_changed_source_inputs_or_incomplete_run(tmp_path):
    rows = fixture(tmp_path)
    with pytest.raises(ValueError, match="source changed"):
        load_tripwire(tmp_path, rows, {"src/test.py": "different"})
    with pytest.raises(ValueError, match="input rows differ"):
        load_tripwire(tmp_path, rows[:-1], {"src/test.py": "pinned"})
    path = tmp_path / "predictions.jsonl"
    path.write_text("\n".join(path.read_text().splitlines()[:-1]) + "\n")
    with pytest.raises(ValueError, match="complete paired"):
        load_tripwire(tmp_path, rows, {"src/test.py": "pinned"})
