"""Scam-script signals: urgency, secrecy, irreversible payment, authority impersonation, known script patterns."""

import re
from dataclasses import dataclass

from src.contracts import Entities, Evidence

SCAM_TYPES: dict[str, list[str]] = {
    "fake_delivery": [
        r"\b(package|parcel|shipment|delivery)\b.*\b(hold|failed|unable|redeliver|pending|address)",
        r"redeliver",
        r"customs fee",
    ],
    "toll_or_fine": [r"\btoll\b.*\b(unpaid|balance|outstanding|due)", r"\b(unpaid|outstanding)\b.*\btoll"],
    "bank_impersonation": [
        r"\b(bank|account|card)\b.*\b(suspend|lock|restrict|unusual|unauthori[sz]ed|frozen|compromised)",
        r"\bfraud (department|alert|team)\b",
        r"verify your (identity|account)",
    ],
    "government_impersonation": [
        r"\b(irs|social security|ssa|tax refund|warrant|arrest|court)\b",
        r"\bdmv\b.*\b(suspend|fine|penalt)",
    ],
    "fake_landlord_rental": [
        r"\b(deposit|rent|lease|apartment|landlord|keys?)\b.*\b(zelle|venmo|cash ?app|wire|send|before)",
        r"\bout of (the )?(country|town)\b.*\b(keys|apartment|house)",
    ],
    "job_or_check_scam": [
        r"\b(job|position|hiring|remote work|work from home|recruit\w*|data[- ]entry)\b"
        r".*(\$\d|\bper (day|hour|week)\b|/day|\bearn)",
        r"\b(deposit|cash) (the|this) check\b",
        r"\bsend (back|the rest|the difference)\b",
    ],
    "investment_romance": [
        r"\b(crypto|bitcoin|usdt|trading platform|investment|guaranteed (return|profit))\b",
        r"\bwrong number\b",
    ],
    "family_emergency": [
        r"\b(grandma|grandpa|mom|dad|it'?s me|new number)\b.*\b(jail|bail|accident|hospital|trouble|lost my phone)",
        r"\bdon'?t tell (mom|dad|anyone)\b",
    ],
    "tech_support": [r"\b(virus|infected|hacked|microsoft|apple support|geek squad|norton|mcafee)\b.*\b(call|renew)"],
    "prize_lottery": [r"\b(won|winner|prize|lottery|sweepstakes|gift card|reward)\b.*\b(claim|collect|fee)"],
    "account_locked": [r"\b(account|apple id|password)\b.*\b(locked|disabled|expire|suspended)"],
}
URGENCY = r"\b(urgent|immediately|within \d+ ?(hours?|hrs?|minutes?|mins?)|today|final (notice|warning)|act now|asap|expires?|last chance|24 ?h)\b"  # noqa: E501
SECRECY = r"\b(don'?t tell|keep (this|it) (between|secret|private)|confidential|do not share)\b"
IRREVERSIBLE = r"\b(gift ?cards?|wire transfer|western union|moneygram|zelle|crypto|bitcoin|btc|usdt|bitcoin atm|cash ?app|venmo)\b"  # noqa: E501
CREDENTIALS = r"\b(password|ssn|social security number|pin|verification code|one[- ]time code|card number|cvv|login)\b"
OTP_LEGIT = (
    r"\b(your|the) (verification|security|one[- ]time) code is\b|\bcode:? ?\d{4,8}\b.*\b(don'?t share|never ask)"
)


@dataclass
class ScriptResult:
    scam_type: str | None
    evidence: list[Evidence]


def _has(pattern: str, text: str) -> bool:
    return re.search(pattern, text, re.IGNORECASE | re.DOTALL) is not None


def check_script(text: str, entities: Entities) -> ScriptResult:
    t = text.lower()
    out: list[Evidence] = []
    hits = {kind: sum(_has(p, t) for p in pats) for kind, pats in SCAM_TYPES.items()}
    matched = sorted((k for k, n in hits.items() if n), key=lambda k: -hits[k])  # stable: ties keep table order
    scam_type = matched[0] if matched else None
    if scam_type:
        out.append(Evidence("scam_script", f"Matches a known '{scam_type.replace('_', ' ')}' scam pattern", "yellow"))
    if _has(URGENCY, t):
        out.append(Evidence("urgency", "Pressures you to act fast — a classic scam tactic", "yellow"))
    if _has(SECRECY, t):
        out.append(Evidence("secrecy", "Asks you to keep it secret", "red"))
    rails = sorted({m.group(0).lower() for m in re.finditer(IRREVERSIBLE, t, re.I)})
    if rails and (entities.amounts or _has(r"\b(pay|send|transfer|deposit|buy)\b", t)):
        out.append(
            Evidence(
                "irreversible_payment",
                f"Asks for payment via {', '.join(rails)} — hard or impossible to reverse",
                "red",
            )
        )
    if _has(CREDENTIALS, t) and _has(r"\b(enter|confirm|verify|send|provide|update|reply with)\b", t):
        if _has(OTP_LEGIT, t):
            out.append(
                Evidence("otp_notice", "Looks like a standard one-time-code notice that warns not to share it", "green")
            )
        else:
            out.append(Evidence("credential_request", "Asks for a password, code, or card details", "red"))
    return ScriptResult(scam_type=scam_type, evidence=out)
