"""Shared data contracts between the Lead (investigator/channels) and Evals lanes.

Owned by the Lead lane. The Evals lane imports from here; do not edit it there.
"""

from dataclasses import dataclass, field
from typing import Literal

Label = Literal["scam", "suspicious", "safe"]
Severity = Literal["red", "yellow", "green", "info"]
Confidence = Literal["low", "medium", "high"]


@dataclass
class IncomingMessage:
    message_id: str
    sender: str
    text: str
    space_id: str | None = None
    received_at: str | None = None


@dataclass
class Entities:
    urls: list[str] = field(default_factory=list)
    domains: list[str] = field(default_factory=list)
    phones: list[str] = field(default_factory=list)
    emails: list[str] = field(default_factory=list)
    payment_handles: list[str] = field(default_factory=list)
    crypto_addresses: list[str] = field(default_factory=list)
    amounts: list[str] = field(default_factory=list)
    claimed_brand: str | None = None


@dataclass
class Evidence:
    check: str  # e.g. "rdap_domain_age"
    finding: str  # human-readable, e.g. "Domain registered 2 days ago"
    severity: Severity
    ok: bool = True  # False if the check failed to run


@dataclass
class Verdict:
    label: Label
    confidence: Confidence
    scam_type: str | None
    evidence: list[Evidence]
    safe_verify: str
    reply_text: str
    screenshot_path: str | None = None
    debug: dict = field(default_factory=dict)


def clip(text: str, limit: int) -> str:
    """Shorten text to <= limit chars on a word boundary, with an ellipsis (never cuts mid-word)."""
    text = " ".join(text.split())
    if len(text) <= limit:
        return text
    cut = text[: limit - 1].rsplit(" ", 1)[0].rstrip(",;:-—")
    return cut + "…"


def investigate(msg: IncomingMessage, context: str | None = None) -> Verdict:
    """Full Tripwire investigation. Implemented in src/investigator/orchestrator.py."""
    from src.investigator.orchestrator import investigate as _investigate

    return _investigate(msg, context=context)


def baseline_classify(text: str) -> Label:
    """Single LLM call, for evals. Implemented by the Evals lane in src/llm.py."""
    from src.llm import baseline_classify as _baseline_classify

    return _baseline_classify(text)
