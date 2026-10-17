"""Domain age via RDAP (rdap.org bootstrap -> the registry). Never contacts the suspicious site itself."""

import logging
from datetime import UTC, datetime

import httpx

from src import config
from src.contracts import Evidence
from src.investigator.checks.link import is_official
from src.investigator.extract import registrable_domain

log = logging.getLogger(__name__)
_chalk_client = None
RDAP_URL = "https://rdap.org/domain/{domain}"
TIMEOUT_S = 6.0


def registration_date(domain: str, client: httpx.Client | None = None) -> datetime | None:
    owns = client is None
    client = client or httpx.Client(timeout=TIMEOUT_S, follow_redirects=True)
    try:
        resp = client.get(RDAP_URL.format(domain=domain), headers={"Accept": "application/rdap+json"})
        if resp.status_code == 404:
            return None  # registry has no record (unregistered or unsupported TLD)
        resp.raise_for_status()  # other HTTP errors mean the check failed, not "no record"
        for event in resp.json().get("events", []):
            if event.get("eventAction") == "registration" and event.get("eventDate"):
                return datetime.fromisoformat(event["eventDate"].replace("Z", "+00:00"))
        return None
    finally:
        if owns:
            client.close()


def chalk_age_days(domain: str) -> int | None:
    """Domain age served by the Chalk feature engine (chalk_features/domain_features.py). None = unavailable/unknown,
    in which case the caller falls back to a direct RDAP lookup."""
    if not config.chalk_features_enabled():
        return None
    try:
        from chalk.client import ChalkClient

        global _chalk_client
        if _chalk_client is None:
            _chalk_client = ChalkClient(default_request_timeout=4.0)
        result = _chalk_client.query(input={"domain.id": domain}, output=["domain.registered_days_ago"])
        if result.errors:
            return None
        value = result.get_feature_value("domain.registered_days_ago")
        return int(value) if value is not None else None
    except Exception as error:  # noqa: BLE001 — Chalk is an accelerator here, not a dependency
        log.info("chalk feature query failed: %s", type(error).__name__)
        return None


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
        days = chalk_age_days(reg)  # Chalk feature engine first (Domain.registered_days_ago)
        if days is None:
            try:
                created = registration_date(reg)
            except (httpx.HTTPError, ValueError) as error:
                msg = f"Couldn't look up {reg}'s age ({type(error).__name__})"
                out.append(Evidence("rdap_domain_age", msg, "info", ok=False))
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
