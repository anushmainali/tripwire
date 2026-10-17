import json

from src.contracts import IncomingMessage
from src.investigator import droid_agent
from src.investigator.extract import extract


def test_prepare_case_writes_untrusted_files_and_sandbox(tmp_path, monkeypatch):
    monkeypatch.setattr(droid_agent, "CASES_ROOT", tmp_path)
    msg = IncomingMessage("../../etc/passwd", "+1", "pay at https://usps-fee.top")
    case = droid_agent.prepare_case(msg, extract(msg.text), [])
    assert case.parent == tmp_path  # id sanitized, no path traversal
    assert (case / "message.txt").read_text() == msg.text
    settings = json.loads((case / ".factory" / "settings.json").read_text())
    assert settings["sandbox"]["enabled"] is True
    assert settings["sandbox"]["network"]["allowedDomains"] == ["localhost", "127.0.0.1"]
