from src.investigator.extract import extract, registrable_domain


def test_usps_smish():
    e = extract("USPS: Your package is on hold. Pay $1.99 redelivery fee at https://usps-redeliver.co/track?id=9 now")
    assert e.urls == ["https://usps-redeliver.co/track?id=9"]
    assert e.domains == ["usps-redeliver.co"]
    assert e.amounts == ["$1.99"]
    assert e.claimed_brand == "usps"


def test_bare_domain_and_defang():
    e = extract("verify at chase-secure-login[.]com/verify or call (800) 555-0199")
    assert "chase-secure-login.com" in e.domains
    assert e.phones == ["8005550199"]
    assert e.claimed_brand == "chase"


def test_payment_handles_and_crypto():
    e = extract(
        "Send the deposit via Zelle to @landlord-mike or $RentMike. "
        "Or USDT to 0x52908400098527886E0F7030069857D2E4169EE7 and BTC bc1qar0srrr7xfkvy5l643lydnw9re59gtzzwf5mdq"
    )
    assert "$RentMike" in e.payment_handles
    assert "@landlord-mike" in e.payment_handles
    assert "0x52908400098527886E0F7030069857D2E4169EE7" in e.crypto_addresses
    assert "bc1qar0srrr7xfkvy5l643lydnw9re59gtzzwf5mdq" in e.crypto_addresses
    assert e.claimed_brand == "zelle"


def test_email_not_a_url():
    e = extract("Contact support@paypal-help.net about your account")
    assert e.emails == ["support@paypal-help.net"]
    assert e.urls == []


def test_plain_message():
    e = extract("hey are we still on for dinner at 7?")
    assert e.urls == [] and e.crypto_addresses == [] and e.claimed_brand is None


def test_registrable_domain():
    assert registrable_domain("secure.login.paypal.com") == "paypal.com"
    assert registrable_domain("www.amazon.co.uk") == "amazon.co.uk"


def test_brand_ignores_freemail_and_prefers_earliest():
    e = extract("I'm Jessica, recruiter at Coinbase. Contact jess.hiring@gmail.com")
    assert e.claimed_brand == "coinbase"
    assert extract("Join our groups today").claimed_brand is None
