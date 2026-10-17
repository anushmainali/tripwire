import json
from unittest.mock import patch

import pytest
from PIL import Image

from evals.audit_screenshots import collect


def test_screenshot_audit_distinguishes_blank_and_missing(tmp_path):
    capture = tmp_path / "capture"
    capture.mkdir()
    image_path = capture / "blank.png"
    Image.new("RGB", (10, 10), "white").save(image_path)
    rows = [
        {"case_id": "blank", "system": "tripwire", "detonation_requested": True, "screenshot_path": str(image_path)},
        {"case_id": "missing", "system": "tripwire", "detonation_requested": True, "screenshot_path": None},
    ]
    (tmp_path / "predictions.jsonl").write_text("".join(json.dumps(row) + "\n" for row in rows))
    with patch("evals.audit_screenshots.ROOT", capture):
        results = collect(tmp_path)
    assert results[0]["uniform_image"] is True
    assert results[0]["capture_ok"] is False
    assert (tmp_path / results[0]["file"]).read_bytes() == image_path.read_bytes()
    assert results[1]["image_error"] == "no_image_path"


def test_screenshot_audit_rejects_paths_outside_capture_root(tmp_path):
    row = {"case_id": "x", "system": "tripwire", "detonation_requested": True, "screenshot_path": "/etc/passwd"}
    (tmp_path / "predictions.jsonl").write_text(json.dumps(row) + "\n")
    with pytest.raises(ValueError, match="Unapproved"):
        collect(tmp_path)
