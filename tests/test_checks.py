from datetime import UTC, datetime

import httpx

from src.investigator.checks import payment, rdap
from src.investigator.checks.link import check_links, lookalike_brand
from src.investigator.checks.script import check_script
from src.investigator.extract import extract


def checks(ev):
    return {e.check for e in ev}


def test_lookalikes():
    assert lookalike_brand("usps-redeliver.co") == "usps"
    assert lookalike_brand("paypa1.com") == "paypal"
    assert lookalike_brand("arnazon.com") == "amazon"
    assert lookalike_brand("www.paypal.com") is None
    assert lookalike_brand("example.org") is None


def test_link_checks_scam():
    ev = check_links(extract("USPS: pay at https://usps-redeliver.top/x"))
    assert {"lookalike_domain", "suspicious_tld"} <= checks(ev)


def test_link_checks_official():
    ev = check_links(extract("Your USPS package: https://tools.usps.com/go/TrackConfirmAction?tLabels=9400"))
    assert checks(ev) == {"official_domain"}


def test_brand_mismatch():
    ev = check_links(extract("Chase alert: verify at https://secure-verify-login.net"))
    assert "brand_domain_mismatch" in checks(ev)


def test_script_landlord():
    text = "Hi this is the landlord, I'm out of the country. Send the $1200 deposit via Zelle today and I'll mail keys"
    r = check_script(text, extract(text))
    assert r.scam_type == "fake_landlord_rental"
    assert {"irreversible_payment", "urgency"} <= checks(r.evidence)


def test_script_otp_is_green():
    text = "Your verification code is 482913. Don't share it with anyone. We will never ask for it."
    r = check_script(text, extract(text))
    assert "credential_request" not in checks(r.evidence)


def test_script_benign():
    r = check_script("see you at dinner tonight!", extract("see you at dinner tonight!"))
    assert r.scam_type is None and r.evidence == []


def _mock_client(handler):
    return httpx.Client(transport=httpx.MockTransport(handler))


def test_rdap_age(monkeypatch):
    def handler(request):
        return httpx.Response(
            200, json={"events": [{"eventAction": "registration", "eventDate": "2026-10-15T00:00:00Z"}]}
        )

    real = rdap.registration_date

    def fake(domain, client=None):
        return real(domain, _mock_client(handler))

    monkeypatch.setattr(rdap, "registration_date", fake)
    ev = rdap.check_domain_age(["usps-redeliver.co"], now=datetime(2026, 10, 17, tzinfo=UTC))
    assert ev[0].severity == "red" and "2 days ago" in ev[0].finding


def test_rdap_failure(monkeypatch):
    def boom(domain, client=None):
        raise httpx.ConnectTimeout("t")

    monkeypatch.setattr(rdap, "registration_date", boom)
    ev = rdap.check_domain_age(["evil.top"])
    assert ev[0].ok is False


def test_payment_crypto(monkeypatch):
    def handler(request):
        return httpx.Response(200, json={"n_tx": 0, "total_received": 0})

    real_client = httpx.Client
    monkeypatch.setattr(payment.httpx, "Client", lambda **kw: real_client(transport=httpx.MockTransport(handler)))
    ev = payment.check_payment(extract("send 500 USDT to 0x52908400098527886E0F7030069857D2E4169EE7"))
    assert "crypto_request" in checks(ev)
    assert any("brand new" in e.finding for e in ev)


def test_script_job_scam():
    text = "Recruiter here: remote data-entry job, $350/day. Deposit 120 USDT to activate your account."
    assert check_script(text, extract(text)).scam_type == "job_or_check_scam"
