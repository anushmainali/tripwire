import pytest

from src.investigator import intel
from src.investigator.extract import extract


@pytest.fixture(autouse=True)
def mem_db():
    intel.reset(":memory:")
    yield
    intel.reset(":memory:")


def test_history_counts_other_reporters():
    e = extract("Pay at https://usps-fee.top/x or Zelle $LandlordMike")
    intel.record(e, "+1111", "scam")
    intel.record(e, "+2222", "scam")
    intel.record(e, "+3333", "safe")
    ev = intel.history(e, "+4444")
    assert {x.severity for x in ev} == {"red"} and len(ev) == 2
    assert "2 other people" in ev[0].finding


def test_own_reports_and_official_domains_ignored():
    e = extract("track at https://tools.usps.com/x and https://usps-fee.top")
    intel.record(e, "+1111", "scam")
    assert intel.history(e, "+1111") == []
    assert ("domain", "usps.com") not in intel.indicators(e)


def test_orchestrator_intel_off_by_default():
    from src.contracts import IncomingMessage
    from src.investigator import orchestrator

    e = extract("pay at https://usps-fee.top")
    intel.record(e, "+1", "scam")
    intel.record(e, "+2", "scam")
    msg = IncomingMessage("m", "+9", "pay at https://usps-fee.top")
    off = orchestrator.investigate(msg, use_llm=False, steps=())
    assert all(x.check != "tripwire_history" for x in off.evidence)
    on = orchestrator.investigate(msg, use_llm=False, steps=(), intel=True)
    assert any(x.check == "tripwire_history" for x in on.evidence)
