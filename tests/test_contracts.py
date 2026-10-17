from src.contracts import IncomingMessage, Verdict, investigate
from src.investigator import gateway


def test_investigate_returns_verdict(monkeypatch):
    def offline(*a, **k):
        raise TimeoutError

    monkeypatch.setattr(gateway, "chat_json", offline)
    v = investigate(IncomingMessage(message_id="m1", sender="+15550000000", text="hi"))
    assert isinstance(v, Verdict)
    assert v.label in ("scam", "suspicious", "safe")
