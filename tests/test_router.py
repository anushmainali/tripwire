from src.channels import router
from src.channels.state import State
from src.contracts import Evidence, IncomingMessage, Verdict


def fake_investigate(calls):
    def inv(msg, ctx):
        calls.append((msg.text, ctx))
        label = "suspicious" if ctx else "scam"
        return Verdict(
            label, "high", "fake_delivery", [Evidence("lookalike_domain", "bad domain", "red")], "go", "VERDICT"
        )

    return inv


def run(state, text, calls, n=[0]):  # noqa: B006 — counter for unique ids
    n[0] += 1
    sent = []
    v = router.handle(IncomingMessage(f"m{n[0]}", "+1555", text), state, sent.append, fake_investigate(calls))
    return sent, v


def test_flow_help_investigate_why_context():
    state, calls = State(":memory:"), []
    sent, _ = run(state, "help", calls)
    assert sent == [router.HELP]
    sent, v = run(state, "USPS: pay fee at https://usps-redeliver.co", calls)
    assert sent == [router.ACK, "VERDICT"] and v.label == "scam"
    sent, _ = run(state, "why", calls)
    assert "bad domain" in sent[0] and "lookalike_domain" in sent[0]
    sent, v = run(state, "I actually ordered something from USPS today", calls)
    assert calls[-1] == ("USPS: pay fee at https://usps-redeliver.co", "I actually ordered something from USPS today")
    assert v.label == "suspicious"


def test_new_forward_is_new_case():
    state, calls = State(":memory:"), []
    run(state, "USPS: pay fee at https://usps-redeliver.co", calls)
    run(state, "Send $500 via Zelle to $LandlordMike for the deposit", calls)
    assert calls[-1][1] is None


def test_why_without_case():
    sent, _ = run(State(":memory:"), "why", [])
    assert "don't have" in sent[0]


def test_dedupe():
    s = State(":memory:")
    assert s.mark_seen("a") and not s.mark_seen("a")


def test_rate_limit():
    s = State(":memory:")
    assert all(s.allow("x", limit=3) for _ in range(3))
    assert not s.allow("x", limit=3) and s.allow("y", limit=3)


def test_progress_message(monkeypatch):
    import time as _t

    monkeypatch.setattr(router, "PROGRESS_AFTER_S", 0.05)
    sent = []

    def slow(msg, ctx):
        _t.sleep(0.2)
        return Verdict("safe", "low", None, [], "x", "VERDICT")

    router.handle(IncomingMessage("p1", "+1", "check https://a.top"), State(":memory:"), sent.append, slow)
    assert sent == [router.ACK, router.PROGRESS_LINK, "VERDICT"]


def test_detonation_target_prefers_lookalike():
    from src.investigator.extract import extract
    from src.investigator.orchestrator import _detonation_target

    e = extract("see https://www.usps.com and pay at https://usps-fee.top/x or https://random-site.net")
    assert _detonation_target(e) == "https://usps-fee.top/x"


def test_why_shows_droid_work():
    state = State(":memory:")
    droid = {"analyses_run": ["parsed page.html"], "scripts_written": ["analyze_page.py"]}
    v = Verdict("scam", "high", None, [Evidence("x", "bad", "red")], "go", "V", debug={"droid": droid})
    state.save_case("+1", "text", v)
    out = router.format_why(state.last_case("+1")[2])
    assert "parsed page.html" in out and "analyze_page.py" in out
