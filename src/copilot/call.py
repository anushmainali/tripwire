"""EXPERIMENTAL live call co-pilot (SPEC.md moonshot). OFF unless TRIPWIRE_CALL_COPILOT=1.

Takes transcript chunks from a call (the voice transport is not wired up yet), runs only the offline script
checks over the running transcript, and returns a short whisper-style alert when a NEW red flag appears.
It never touches the text pipeline and makes no network calls.
"""

import os

from src.investigator.checks.script import check_script
from src.investigator.extract import extract

ALERTS = {
    "secrecy": "They're asking you to keep this secret. Real banks and agencies never do. Hang up.",
    "urgency": "They're rushing you. Slow down. A real caller will let you call back.",
    "scam_script": "This matches a known scam script. Don't send money or codes.",
    "gift_cards": "Gift cards or crypto as payment is a scam signal. Hang up.",
    "credentials": "They're asking for a code, PIN or password. Never give those out on a call.",
}


def enabled() -> bool:
    return os.environ.get("TRIPWIRE_CALL_COPILOT") == "1"


class CallCopilot:
    def __init__(self) -> None:
        self.transcript = ""
        self._alerted: set[str] = set()

    def feed(self, chunk: str) -> list[str]:
        """Add transcript text; return alerts for red/yellow checks not yet announced (empty if none or disabled)."""
        if not enabled():
            return []
        self.transcript = (self.transcript + " " + chunk).strip()[-6000:]
        result = check_script(self.transcript, extract(self.transcript))
        out = []
        for e in result.evidence:
            if e.severity in ("red", "yellow") and e.check not in self._alerted:
                self._alerted.add(e.check)
                out.append(ALERTS.get(e.check, e.finding))
        return out
