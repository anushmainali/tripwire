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
from src.contracts import IncomingMessage, investigate

POLL_S = 2.5
log = logging.getLogger("tripwire")


def run_live() -> None:
    from photon_api import ApiError

    from src.channels.photon import PhotonChannel

    channel = PhotonChannel()
    state = State()
    pool = ThreadPoolExecutor(max_workers=4)
    stopping = False

    def stop(*_):
        nonlocal stopping
        stopping = True

    signal.signal(signal.SIGINT, stop)
    signal.signal(signal.SIGTERM, stop)
    log.info("Tripwire live on %s (%s). Polling every %.1fs.", channel.cfg.agent_handle, channel.cfg.platform, POLL_S)

    def work(msg: IncomingMessage, target) -> None:
        try:
            router.handle(
                msg,
                state,
                send=lambda text: channel.send_text(target, text),
                investigate=lambda m, ctx: investigate(m, context=ctx),
                send_image=lambda path: channel.send_image(target, path),
            )
        except Exception:
            log.exception("failed handling %s", msg.message_id)
            try:
                channel.send_text(target, "Sorry — something went wrong checking that. Please try again in a minute.")
            except Exception:  # noqa: BLE001
                log.exception("failed to send error notice")

    backoff = POLL_S
    while not stopping:
        try:
            for msg, target in channel.poll():
                if state.mark_seen(msg.message_id):
                    log.info("new message %s from %s…", msg.message_id, msg.sender[-4:])
                    pool.submit(work, msg, target)
            backoff = POLL_S
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
