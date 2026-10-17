from types import SimpleNamespace

from src import main
from src.channels.state import State
from src.contracts import Evidence, IncomingMessage, Verdict


class FakeChannel:
    def __init__(self, batches):
        self.batches = list(batches)
        self.cfg = SimpleNamespace(agent_handle="+10000000000", platform="imessage")
        self.texts, self.images, self.closed = [], [], False

    def poll(self):
        return self.batches.pop(0) if self.batches else []

    def send_text(self, target, text):
        self.texts.append((target, text))

    def send_image(self, target, path):
        self.images.append((target, path))
        return True

    def fetch_attachment(self, attachment_id):
        return None

    def close(self):
        self.closed = True


def test_live_loop_dedupes_and_replies(monkeypatch):
    def fake_investigate(msg, context=None):
        return Verdict("scam", "high", None, [Evidence("x", "bad", "red")], "go", "VERDICT", screenshot_path="/s.jpg")

    monkeypatch.setattr(main, "investigate", fake_investigate)
    m = IncomingMessage("m1", "+1555", "pay at https://usps-fee.top")
    ch = FakeChannel([[(m, "T1")], [(m, "T1")]])  # same message delivered twice
    main.run_live(channel=ch, state=State(":memory:"), max_polls=3, poll_s=0.01)
    assert [t for _, t in ch.texts] == ["Investigating… 🔍", "VERDICT"]
    assert ch.images == [("T1", "/s.jpg")] and ch.closed


def test_live_loop_reports_crash(monkeypatch):
    def boom(msg, context=None):
        raise RuntimeError("x")

    monkeypatch.setattr(main, "investigate", boom)
    ch = FakeChannel([[(IncomingMessage("m2", "+1", "check https://a.top"), "T")]])
    main.run_live(channel=ch, state=State(":memory:"), max_polls=2, poll_s=0.01)
    assert "something went wrong" in ch.texts[-1][1]
