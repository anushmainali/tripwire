"""Tripwire app: the single live Photon poller.

Run: .venv/bin/python -m src.main            (live iMessage via Photon)
     .venv/bin/python -m src.main --cli      (local REPL, no Photon; type messages as if texting Tripwire)
Only ONE process may run the live poller (duplicate replies otherwise).
"""

import argparse
import logging
import signal
import sys
import time
from concurrent.futures import ThreadPoolExecutor

from src.channels import router
from src.channels.state import State
from src.contracts import IncomingMessage
from src.investigator.orchestrator import investigate as _investigate


def investigate(msg: IncomingMessage, context: str | None = None):
    """Live investigations also use and feed the community intel memory."""
    return _investigate(msg, context=context, intel=True)


POLL_S = 2.5
log = logging.getLogger("tripwire")


def cleanup_tmp(max_age_s: float = 86400) -> None:
    """Delete case/detonation artifacts older than a day (they hold untrusted page HTML and screenshots)."""
    import shutil
    from pathlib import Path

    now = time.time()
    for root in (Path("/tmp/tripwire-cases"), Path("/tmp/tripwire-detonations")):
        for d in root.glob("*") if root.exists() else []:
            if d.is_dir() and now - d.stat().st_mtime > max_age_s:
                shutil.rmtree(d, ignore_errors=True)


def run_live(channel=None, state: State | None = None, max_polls: int | None = None, poll_s: float = POLL_S) -> None:
    """The live poller. `channel`/`state`/`max_polls` are injectable for offline tests."""
    from photon_api import ApiError

    if channel is None:
        from src.channels.photon import PhotonChannel

        channel = PhotonChannel()
    state = state or State()
    if max_polls is None:
        cleanup_tmp()
    pool = ThreadPoolExecutor(max_workers=4)
    stopping = False

    def stop(*_):
        nonlocal stopping
        stopping = True

    if max_polls is None:
        signal.signal(signal.SIGINT, stop)
        signal.signal(signal.SIGTERM, stop)
    log.info("Tripwire live on %s (%s). Polling every %.1fs.", channel.cfg.agent_handle, channel.cfg.platform, POLL_S)

    last_verdict: dict[str, object] = {}

    def remember(target, verdict):
        last_verdict[str(target)] = verdict
        return verdict

    def send_image(target, path: str) -> bool:
        """Screenshot as an iMessage attachment; if Photon rejects it, send a hosted link instead."""
        try:
            if channel.send_image(target, path):
                return True
        except Exception as error:  # noqa: BLE001
            log.warning(
                "attachment send failed (%s status=%s body=%.200s); falling back to link",
                type(error).__name__,
                getattr(error, "status", None),
                str(getattr(error, "body", ""))[:200],
            )
        from src.channels.shots import report_meta, upload_screenshot

        v = last_verdict.get(str(target))
        url = upload_screenshot(path, report_meta(v) if v else None)
        if url:
            channel.send_text(target, f"📸 Where the link really leads (opened safely in our sandbox): {url}")
            return True
        return False

    def read_images(ids: list[str]) -> str | None:
        from src.investigator.gateway import transcribe_image

        texts = []
        for attachment_id in ids[:2]:
            got = channel.fetch_attachment(attachment_id)
            if got:
                text = transcribe_image(*got)
                if text:
                    texts.append(text)
        return "\n\n".join(texts) or None

    def work(msg: IncomingMessage, target) -> None:
        try:
            router.handle(
                msg,
                state,
                send=lambda text: channel.send_text(target, text),
                investigate=lambda m, ctx: remember(target, investigate(m, context=ctx)),
                send_image=lambda path: send_image(target, path),
                read_images=read_images,
            )
        except Exception:
            log.exception("failed handling %s", msg.message_id)
            try:
                channel.send_text(target, "Sorry — something went wrong checking that. Please try again in a minute.")
            except Exception:  # noqa: BLE001
                log.exception("failed to send error notice")

    backoff = poll_s
    polls = 0
    while not stopping and (max_polls is None or polls < max_polls):
        polls += 1
        try:
            for msg, target in channel.poll():
                if state.mark_seen(msg.message_id):
                    log.info("new message %s from %s…", msg.message_id, msg.sender[-4:])
                    pool.submit(work, msg, target)
            backoff = poll_s
        except ApiError as error:
            log.warning("Photon API error %s (request %s)", error.status, error.request_id)
            backoff = min(backoff * 2, 30)
            if error.status == 429:
                backoff = max(backoff, float(error.headers.get("retry-after", 5) or 5))
        except Exception as error:  # noqa: BLE001 — keep the poller alive
            log.warning("poll failed: %s", type(error).__name__)
            backoff = min(backoff * 2, 30)
        time.sleep(backoff)
    pool.shutdown(wait=True)
    channel.close()


def run_cli() -> None:
    state = State(":memory:")
    print('Tripwire local REPL. Type a message (or "why", "help"); Ctrl-D to quit.')
    n = 0
    for line in sys.stdin:
        n += 1
        msg = IncomingMessage(message_id=f"cli-{n}", sender="cli-user", text=line.strip().replace("\\n", "\n"))
        v = router.handle(
            msg, state, send=lambda t: print(f"\n[Tripwire] {t}\n"), investigate=lambda m, c: investigate(m, context=c)
        )
        if v and v.screenshot_path:
            print(f"[screenshot: {v.screenshot_path}]")


def main() -> None:
    parser = argparse.ArgumentParser(description="Tripwire iMessage scam checker")
    parser.add_argument("--cli", action="store_true", help="local REPL instead of the live Photon poller")
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    logging.getLogger("httpx").setLevel(logging.WARNING)
    run_cli() if args.cli else run_live()


if __name__ == "__main__":
    main()
