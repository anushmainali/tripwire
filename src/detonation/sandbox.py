"""Link detonation in a Chalk sandbox (stub until the sandbox runner lands)."""

from src.detonation.report import DetonationResult


def detonate(url: str, timeout_s: float = 60.0) -> DetonationResult:
    return DetonationResult(url=url, ok=False, error="detonation not available yet")
