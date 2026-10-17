import json

import pytest

from evals.audit_artifacts import analyze, collect


def test_audit_parses_without_executing_and_flags_network_or_dynamic_execution():
    assert analyze("import json\nprint(json.loads('{}'))") == []
    assert "review_import:urllib.request" in analyze("import urllib.request")
    assert "review_call:exec" in analyze("exec('raise Exception()')")
    assert analyze("invalid(") == ["parse_error"]


def test_artifact_path_escape_rejected(tmp_path):
    row = {"system": "tripwire", "debug": {"droid": {"case_dir": str(tmp_path)}}}
    (tmp_path / "predictions.jsonl").write_text(json.dumps(row) + "\n")
    with pytest.raises(ValueError, match="outside approved"):
        collect(tmp_path)
