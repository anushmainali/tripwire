"""Investigation orchestrator (stub; real pipeline lands in later commits)."""

from src.contracts import IncomingMessage, Verdict


def investigate(msg: IncomingMessage, context: str | None = None) -> Verdict:
    return Verdict(
        label="suspicious",
        confidence="low",
        scam_type=None,
        evidence=[],
        safe_verify="Contact the company through its official website or the number on your card.",
        reply_text="⚠️ Suspicious (Low confidence)\n\nTripwire's investigator is not wired up yet.",
    )
