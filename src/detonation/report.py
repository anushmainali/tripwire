"""Detonation result (captured inside a Chalk sandbox) and the evidence it supports."""

from dataclasses import dataclass, field

from src.contracts import Evidence
from src.investigator.checks.link import is_official, lookalike_brand
from src.investigator.extract import BRANDS, host_of, registrable_domain


@dataclass
class DetonationResult:
    url: str
    ok: bool = False
    error: str | None = None
    final_url: str | None = None
    redirect_chain: list[str] = field(default_factory=list)
    status: int | None = None
    title: str | None = None
    has_password_field: bool = False
    has_card_field: bool = False
    has_ssn_field: bool = False
    form_count: int = 0
    input_names: list[str] = field(default_factory=list)
    brand_mentions: list[str] = field(default_factory=list)
    text_excerpt: str = ""
    screenshot_path: str | None = None
    html_path: str | None = None
    duration_s: float | None = None


def detonation_evidence(r: DetonationResult, claimed_brand: str | None) -> list[Evidence]:
    if not r.ok:
        return [
            Evidence("detonation", f"Couldn't open the link safely ({r.error or 'unknown error'})", "info", ok=False)
        ]
    out: list[Evidence] = []
    start_reg = registrable_domain(host_of(r.url))
    final_host = host_of(r.final_url or r.url)
    final_reg = registrable_domain(final_host)
    if final_reg and final_reg != start_reg:
        hops = len(r.redirect_chain)
        sev = "green" if is_official(final_host) else "yellow"
        out.append(Evidence("detonation_redirect", f"The link redirects ({hops} hops) to {final_reg}", sev))
    fields = []
    if r.has_card_field:
        fields.append("card number")
    if r.has_password_field:
        fields.append("password")
    if r.has_ssn_field:
        fields.append("SSN")
    official = is_official(final_host)
    if fields and not official:
        out.append(Evidence("detonation_page_fields", f"The page asks for your {' and '.join(fields)}", "red"))
    elif fields:
        out.append(Evidence("detonation_page_fields", f"Official {official} login/payment page", "green"))
    imitated = lookalike_brand(final_host) or next(
        (b for b in r.brand_mentions if b in BRANDS and not official and b == claimed_brand), None
    )
    if imitated and not official:
        out.append(
            Evidence(
                "detonation_brand",
                f"The page shows {imitated.upper()} branding but isn't on {BRANDS[imitated][0]}",
                "red",
            )
        )
    if not out:
        title = (r.title or "untitled page")[:80]
        out.append(Evidence("detonation", f"Opened in a sandbox: lands on {final_reg} ('{title}')", "info"))
    return out
