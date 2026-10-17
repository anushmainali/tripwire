"""Decide how to answer each incoming message: help, "why", added context, or a new investigation.

Pure logic: I/O is injected (`send`, `send_image`, `investigate`) so it's testable offline.
"""

import logging
from collections.abc import Callable

from src.channels.state import State
from src.contracts import IncomingMessage, Verdict
from src.investigator.checks.script import check_script
from src.investigator.extract import extract

log = logging.getLogger(__name__)

HELP = (
    "I'm Tripwire 🛡️ — text me before you pay. Forward any suspicious text, link, or payment request and I'll "
    "investigate it: check where links really go (I open them in a sealed sandbox so you don't have to), how old "
    "the website is, whether a wallet or payment request looks risky, and whether the story matches known scams. "
    "Then I'll tell you what I found and how to double-check through an official channel."
)
ACK = "Investigating… 🔍"
HELP_WORDS = {"help", "hi", "hello", "hey", "start", "?", "what is this", "what do you do", "info"}
WHY_WORDS = {"why", "why?", "details", "more", "explain", "full", "full report"}
ICON = {"red": "🔴", "yellow": "🟡", "green": "🟢", "info": "⚪️"}

Send = Callable[[str], None]


def format_why(verdict: Verdict) -> str:
    lines = [f"Full investigation — verdict: {verdict.label.upper()} ({verdict.confidence} confidence)"]
    if verdict.scam_type:
        lines.append(f"Pattern: {verdict.scam_type.replace('_', ' ')}")
    lines.append("")
    ran = [e for e in verdict.evidence if e.ok]
    failed = [e for e in verdict.evidence if not e.ok]
    for e in ran:
        lines.append(f"{ICON.get(e.severity, '•')} [{e.check}] {e.finding}")
    if not ran:
        lines.append("No findings from the checks.")
    if failed:
        lines += ["", "Checks that couldn't run:"] + [f"• [{e.check}] {e.finding}" for e in failed]
    lines += ["", f"Safe check: {verdict.safe_verify}"]
    return "\n".join(lines)


def looks_like_context(text: str) -> bool:
    """A short reply with no links/payments/scam signals, sent after a verdict, is context about the last case."""
    if len(text) > 220:
        return False
    ents = extract(text)
    if ents.urls or ents.crypto_addresses or ents.payment_handles or ents.phones or ents.emails:
        return False
    return check_script(text, ents).scam_type is None


def handle(
    msg: IncomingMessage,
    state: State,
    send: Send,
    investigate: Callable[[IncomingMessage, str | None], Verdict],
    send_image: Callable[[str], bool] | None = None,
) -> Verdict | None:
    text = (msg.text or "").strip()
    norm = text.lower().strip(" .!")
    if not text:
        send("Forward me the suspicious message as text (copy & paste works best) and I'll check it.")
        return None
    if norm in HELP_WORDS:
        send(HELP)
        return None
    last = state.last_case(msg.sender)
    if norm in WHY_WORDS:
        send(format_why(last[2]) if last else "I don't have a recent investigation for you. Forward me a message!")
        return None
    context = None
    target_text = text
    if last and looks_like_context(text):
        target_text, prev_context = last[0], last[1]
        context = f"{prev_context}\n{text}" if prev_context else text
        send("Got it — re-checking with that in mind… 🔍")
    else:
        send(ACK)
    case = IncomingMessage(msg.message_id, msg.sender, target_text, msg.space_id, msg.received_at)
    verdict = investigate(case, context)
    send(verdict.reply_text)
    if verdict.screenshot_path and send_image is not None:
        try:
            send_image(verdict.screenshot_path)
        except Exception as error:  # noqa: BLE001 — the text verdict already went out
            log.warning("screenshot send failed: %s", error)
    state.save_case(msg.sender, target_text, verdict, context)
    return verdict
