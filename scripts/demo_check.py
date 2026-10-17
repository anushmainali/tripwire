"""Demo reliability check: run the exact DEMO.md scam message through the live pipeline (no Photon send).

  .venv/bin/python -m scripts.demo_check          # full run + asserts
  .venv/bin/python -m scripts.demo_check --warm   # just wake the demo site + a sandbox before judging

Needs the demo site up (`cat data/demo_site_url.txt`) and a Chalk login. Costs one Droid session + one sandbox.
"""

import re
import sys
import time
from pathlib import Path

import httpx

from src import config
from src.contracts import IncomingMessage

DEMO_MD = Path(__file__).resolve().parent.parent / "DEMO.md"


def demo_message() -> str:
    """The first fenced block under the scam demo message in DEMO.md."""
    text = DEMO_MD.read_text()
    block = re.search(r"\*\*1\. Scam.*?```\n(.*?)\n```", text, re.S)
    if not block:
        raise SystemExit("could not find demo message 1 in DEMO.md")
    return block.group(1).strip()


def step(name: str, ok: bool, detail: str = "") -> bool:
    print(f"[{'PASS' if ok else 'FAIL'}] {name} {detail}".rstrip())
    return ok


def warm() -> bool:
    base = config.demo_site_url()
    t = time.monotonic()
    try:
        ok = httpx.get(f"{base}/health", timeout=30).status_code == 200
    except Exception as error:  # noqa: BLE001
        return step("demo site", False, f"({type(error).__name__}) run: .venv/bin/python -m demo_site.deploy")
    step("demo site", ok, f"{time.monotonic() - t:.1f}s")
    from src.detonation.sandbox import detonate

    t = time.monotonic()
    r = detonate(f"{base}/redeliver", 70)
    return step("sandbox", r.ok, f"{time.monotonic() - t:.1f}s {r.error or ''}") and ok


def full() -> bool:
    from src.channels.shots import report_meta, upload_screenshot
    from src.detonation.sandbox import valid_screenshot
    from src.investigator.orchestrator import investigate

    t = time.monotonic()
    v = investigate(IncomingMessage("demo-check", "demo-check", demo_message()))
    elapsed = time.monotonic() - t
    print(v.reply_text, "\n")
    results = [
        step("verdict is scam/suspicious", v.label in ("scam", "suspicious"), f"({v.label}/{v.confidence})"),
        step("pipeline time < 85s", elapsed < 85, f"({elapsed:.1f}s)"),
    ]
    shot_ok = bool(v.screenshot_path) and valid_screenshot(v.screenshot_path)
    results.append(step("screenshot valid", shot_ok, f"({v.screenshot_path})"))
    if shot_ok:
        url = upload_screenshot(v.screenshot_path, report_meta(v))
        results.append(step("hosted link uploaded", bool(url), f"({url})"))
        if url:
            page = httpx.get(url, timeout=20)
            results.append(
                step("report page 200 html", page.status_code == 200 and "html" in page.headers["content-type"])
            )
            img = httpx.get(url + ".jpg", timeout=20)
            results.append(
                step("image 200 image/jpeg", img.status_code == 200 and img.headers["content-type"] == "image/jpeg")
            )
    return all(results)


if __name__ == "__main__":
    sys.exit(0 if (warm() if "--warm" in sys.argv else full()) else 1)
