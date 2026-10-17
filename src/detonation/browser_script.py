"""Runs INSIDE the Chalk sandbox only (never on the host). Opens one URL in headless Chromium as an iPhone,
records redirects and page facts, saves a screenshot + HTML, and prints one JSON line.

Never types, clicks, submits forms or downloads anything.
Usage (in sandbox): python3 browser_script.py <url> <out_dir>
"""

import json
import re
import sys
import time

from playwright.sync_api import sync_playwright

NAV_TIMEOUT_MS = 20000
BRANDS = [
    "usps", "ups", "fedex", "dhl", "paypal", "chase", "wells fargo", "bank of america", "citi", "capital one",
    "amazon", "apple", "icloud", "microsoft", "netflix", "irs", "social security", "venmo", "zelle", "cash app",
    "coinbase", "binance", "e-zpass", "ezpass", "dmv", "geico", "verizon", "t-mobile", "postalplus",
]  # fmt: skip
PROBE = """() => {
  const inputs = [...document.querySelectorAll('input, select, textarea')];
  const desc = el => [el.type, el.name, el.id, el.placeholder, el.autocomplete, el.getAttribute('aria-label'),
    (el.labels && el.labels[0] ? el.labels[0].innerText : '')].filter(Boolean).join(' ').toLowerCase();
  const d = inputs.map(desc);
  return {
    inputs: d.slice(0, 40),
    forms: document.forms.length,
    form_actions: [...document.forms].map(f => f.action).slice(0, 5),
    text: (document.body ? document.body.innerText : '').slice(0, 4000),
  };
}"""


def main(url: str, out_dir: str) -> None:
    started = time.time()
    result: dict = {"url": url, "ok": False, "redirect_chain": []}
    with sync_playwright() as p:
        browser = p.chromium.launch(args=["--no-sandbox", "--disable-dev-shm-usage"])
        context = browser.new_context(
            **p.devices["iPhone 13"], accept_downloads=False, java_script_enabled=True, ignore_https_errors=True
        )
        page = context.new_page()
        page.on("dialog", lambda d: d.dismiss())
        chain: list[str] = []

        def on_response(resp):
            if resp.request.is_navigation_request() and resp.request.frame == page.main_frame:
                chain.append(f"{resp.status} {resp.url}")

        page.on("response", on_response)
        try:
            resp = page.goto(url, wait_until="domcontentloaded", timeout=NAV_TIMEOUT_MS)
            try:
                page.wait_for_load_state("networkidle", timeout=5000)
            except Exception:  # noqa: BLE001 — busy pages never go idle; facts so far are enough
                pass
            page.wait_for_timeout(800)  # let late paints/JS render before probing and capturing
            facts = page.evaluate(PROBE)
            inputs = facts["inputs"]
            text = facts["text"].lower()
            joined = " ".join(inputs)
            result.update(
                ok=True,
                status=resp.status if resp else None,
                final_url=page.url,
                title=page.title()[:200],
                redirect_chain=chain[:10],
                form_count=facts["forms"],
                input_names=inputs[:20],
                has_password_field="password" in joined,
                has_card_field=bool(re.search(r"card|cc-num|cvv|cvc|expir|cc-exp", joined)),
                has_ssn_field=bool(re.search(r"ssn|social security", joined)),
                brand_mentions=[b.replace(" ", "") for b in BRANDS if re.search(rf"\b{re.escape(b)}\b", text)][:5],
                text_excerpt=facts["text"][:1500],
            )
            page.screenshot(path=f"{out_dir}/shot.jpg", type="jpeg", quality=70, full_page=False)
            with open(f"{out_dir}/page.html", "w") as f:
                f.write(page.content()[:500000])
        except Exception as error:  # noqa: BLE001
            result.update(error=f"{type(error).__name__}: {str(error)[:200]}", redirect_chain=chain[:10])
            try:
                page.screenshot(path=f"{out_dir}/shot.jpg", type="jpeg", quality=70)
            except Exception:  # noqa: BLE001
                pass
        finally:
            browser.close()
    result["duration_s"] = round(time.time() - started, 2)
    print("TRIPWIRE_RESULT " + json.dumps(result))


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
