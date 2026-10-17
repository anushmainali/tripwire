"""Domain age via RDAP (rdap.org bootstrap -> the registry). Never contacts the suspicious site itself."""

from datetime import UTC, datetime

import httpx

from src.contracts import Evidence
from src.investigator.checks.link import is_official
from src.investigator.extract import registrable_domain

RDAP_URL = "https://rdap.org/domain/{domain}"
TIMEOUT_S = 6.0


def registration_date(domain: str, client: httpx.Client | None = None) -> datetime | None:
    owns = client is None
    client = client or httpx.Client(timeout=TIMEOUT_S, follow_redirects=True)
    try:
        resp = client.get(RDAP_URL.format(domain=domain), headers={"Accept": "application/rdap+json"})
        if resp.status_code != 200:
            return None
        for event in resp.json().get("events", []):
            if event.get("eventAction") == "registration" and event.get("eventDate"):
                return datetime.fromisoformat(event["eventDate"].replace("Z", "+00:00"))
        return None
    finally:
        if owns:
            client.close()


def describe_age(days: int) -> str:
    if days < 1:
        return "today"
    if days < 60:
        return f"{days} day{'s' if days != 1 else ''} ago"
    if days < 730:
        return f"{days // 30} months ago"
    return f"{days // 365} years ago"


def check_domain_age(domains: list[str], now: datetime | None = None) -> list[Evidence]:
    now = now or datetime.now(UTC)
    out: list[Evidence] = []
    seen: set[str] = set()
    for host in domains:
        reg = registrable_domain(host)
        if reg in seen or is_official(host):
            continue
        seen.add(reg)
        if len(seen) > 3:
            break
        try:
            created = registration_date(reg)
        except (httpx.HTTPError, ValueError) as error:
            out.append(
                Evidence("rdap_domain_age", f"Couldn't look up {reg}'s age ({type(error).__name__})", "info", ok=False)
            )
            continue
        if created is None:
            out.append(Evidence("rdap_domain_age", f"No registration record found for {reg}", "yellow"))
            continue
        days = (now - created).days
        when = describe_age(days)
        if days < 30:
            out.append(Evidence("rdap_domain_age", f"{reg} was registered {when}", "red"))
        elif days < 365:
            out.append(Evidence("rdap_domain_age", f"{reg} was registered {when} — fairly new", "yellow"))
        else:
            out.append(Evidence("rdap_domain_age", f"{reg} was registered {when}", "info"))
    return out
