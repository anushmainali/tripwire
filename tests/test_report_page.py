import base64
import json

from demo_site.app import render_report
from src.channels.shots import report_meta
from src.contracts import Evidence, Verdict


def test_report_page_escapes_and_lists_flags():
    meta = {
        "final_url": "http://evil.test/<script>alert(1)</script>",
        "chain": ["http://a.test/x", "http://evil.test/y"],
        "flags": [{"t": "The page asks for your card number", "s": "red"}],
    }
    page = render_report("abc", meta)
    assert "<script>alert" not in page
    assert "/s/abc.jpg" in page and "card number" in page and "evil.test/y" in page


def test_report_page_without_meta():
    assert "/s/abc.jpg" in render_report("abc", {})


def test_report_meta_from_verdict():
    v = Verdict("scam", "high", None, [Evidence("a", "bad", "red"), Evidence("b", "ok", "green")], "", "")
    v.debug["detonation"] = {"final_url": "http://x.test", "redirect_chain": ["http://x.test"]}
    meta = report_meta(v)
    assert meta["flags"] == [{"t": "bad", "s": "red"}] and meta["final_url"] == "http://x.test"
    json.dumps(meta)
    base64.b64encode(json.dumps(meta).encode())


def test_clip_never_cuts_mid_word():
    from src.contracts import clip

    out = clip("The linked page asks for your full card number and CVV to pay a tiny fee right now", 40)
    assert (
        out.endswith("…") and out[:-1].split()[-1] in "The linked page asks for your full card number and CVV".split()
    )
