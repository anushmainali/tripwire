from src.detonation.report import DetonationResult, detonation_evidence


def checks(ev):
    return {e.check: e for e in ev}


def test_phishing_page():
    r = DetonationResult(
        url="https://usps-redeliver.co/x",
        ok=True,
        final_url="https://usps-pay-secure.top/card",
        redirect_chain=["302 https://usps-redeliver.co/x", "200 https://usps-pay-secure.top/card"],
        has_card_field=True,
        brand_mentions=["usps"],
    )
    ev = checks(detonation_evidence(r, "usps"))
    assert ev["detonation_page_fields"].severity == "red" and "card number" in ev["detonation_page_fields"].finding
    assert ev["detonation_redirect"].severity == "yellow"
    assert ev["detonation_brand"].severity == "red"


def test_official_login_is_green():
    r = DetonationResult(url="https://www.paypal.com/signin", ok=True, final_url="https://www.paypal.com/signin",
                         has_password_field=True, brand_mentions=["paypal"])  # fmt: skip
    ev = checks(detonation_evidence(r, "paypal"))
    assert ev["detonation_page_fields"].severity == "green" and "detonation_brand" not in ev


def test_failed_detonation():
    ev = detonation_evidence(DetonationResult(url="http://x.top", error="Timeout"), None)
    assert ev[0].ok is False
