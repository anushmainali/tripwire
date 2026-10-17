"""Tripwire domain-risk features served by the Chalk feature engine.

`Domain.id` is a registrable domain (e.g. "usps-redeliver.co"). String features are Chalk expressions (compiled to
native code); `registered_days_ago` comes from an online resolver that calls the RDAP registry (never the domain).
"""

from datetime import UTC, datetime

import chalk.functions as F
from chalk import online
from chalk.features import _, features

BRAND_TOKENS = (
    "usps|paypal|chase|wellsfargo|bankofamerica|amazon|apple|icloud|microsoft|netflix|irs|venmo|zelle|cashapp|"
    "coinbase|binance|ezpass|fedex|dhl|postalplus"
)
RISKY_TLDS = (
    "xyz|top|click|link|live|shop|online|site|icu|buzz|tk|ml|ga|cf|gq|cc|ws|vip|club|support|help|services|win|bid|"
    "loan|work|rest|cyou|sbs|lol|mobi|su|pw|fun|space|website|info|ru|cn|zip|mov|co"
)


@features(owner="tripwire", tags=["group:link-risk"])
class Domain:
    id: str
    hyphen_count: int = F.length(_.id) - F.length(F.replace(_.id, "-", ""))
    has_brand_token: bool = F.regexp_like(_.id, BRAND_TOKENS)
    risky_tld: bool = F.regexp_like(_.id, "\\.(" + RISKY_TLDS + ")$")
    registered_days_ago: int | None
    risk_points: int = (
        F.if_then_else(_.has_brand_token, 2, 0)
        + F.if_then_else(_.risky_tld, 1, 0)
        + F.if_then_else(_.hyphen_count >= 2, 1, 0)
    )


@online
def rdap_age(domain_id: Domain.id) -> Domain.registered_days_ago:
    import httpx

    try:
        resp = httpx.get(f"https://rdap.org/domain/{domain_id}", timeout=5.0, follow_redirects=True)
        if resp.status_code != 200:
            return None
        for event in resp.json().get("events", []):
            if event.get("eventAction") == "registration":
                created = datetime.fromisoformat(event["eventDate"].replace("Z", "+00:00"))
                return (datetime.now(UTC) - created).days
    except Exception:
        return None
    return None
