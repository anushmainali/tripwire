from src.copilot.call import CallCopilot


def test_disabled_by_default(monkeypatch):
    monkeypatch.delenv("TRIPWIRE_CALL_COPILOT", raising=False)
    assert CallCopilot().feed("don't tell anyone, buy gift cards now") == []


def test_alerts_once(monkeypatch):
    monkeypatch.setenv("TRIPWIRE_CALL_COPILOT", "1")
    c = CallCopilot()
    first = c.feed("This is your bank. Please don't tell anyone about this call.")
    assert first and any("secret" in a for a in first)
    assert c.feed("Remember, don't tell anyone.") == []
