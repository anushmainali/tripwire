from src.contracts import IncomingMessage, Verdict, investigate


def test_investigate_returns_verdict():
    v = investigate(IncomingMessage(message_id="m1", sender="+15550000000", text="hi"))
    assert isinstance(v, Verdict)
    assert v.label in ("scam", "suspicious", "safe")
