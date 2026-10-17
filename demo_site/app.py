"""Tripwire demo site, hosted on a Chalk ScalingGroup.

1. A harmless imitation of a delivery-fee scam for a FICTIONAL brand ("PostalPlus"), so the live demo never depends
   on a real criminal site. /track -> 302 -> /redeliver, which shows a card form. The form submits nowhere and
   nothing typed is ever sent or stored.
2. Screenshot hosting fallback: POST /upload (token-protected) stores a JPEG in memory; GET /s/<id>.jpg serves it.

Standard library only. Binds 0.0.0.0:8080.
"""

import base64
import hmac
import html
import json
import os
import secrets
from collections import OrderedDict
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlsplit

TOKEN = os.environ.get("TRIPWIRE_SHOT_TOKEN", "")
MAX_SHOTS = 300
MAX_BYTES = 3_000_000
SHOTS: OrderedDict[str, bytes] = OrderedDict()
METAS: dict[str, dict] = {}

STYLE = """<style>
body{font-family:-apple-system,Helvetica,Arial,sans-serif;margin:0;background:#f4f4f6;color:#1d1d1f}
header{background:#3b2a8f;color:#fff;padding:18px 20px;font-weight:700;font-size:22px;letter-spacing:.3px}
header span{color:#ffcc00}
.card{background:#fff;margin:16px;padding:20px;border-radius:12px;box-shadow:0 1px 4px rgba(0,0,0,.1)}
.warn{background:#fff4e5;border-left:4px solid #ff9500;padding:12px;margin-bottom:14px;font-size:15px}
label{display:block;font-size:13px;color:#555;margin:12px 0 4px}
input{width:100%;box-sizing:border-box;padding:12px;font-size:16px;border:1px solid #ccc;border-radius:8px}
button{margin-top:18px;width:100%;padding:14px;border:0;border-radius:8px;background:#3b2a8f;color:#fff;font-size:17px}
.fee{font-size:28px;font-weight:700;margin:6px 0}
footer{font-size:10px;color:#aaa;text-align:center;padding:16px}
</style>"""

REDELIVER = f"""<!doctype html><html><head><meta name="viewport" content="width=device-width,initial-scale=1">
<title>PostalPlus - Redelivery Payment</title>{STYLE}</head><body>
<header>Postal<span>Plus</span> Delivery</header>
<div class="card">
<div class="warn">⚠️ Your parcel <b>PP-4471-2209-US</b> is on hold due to an unpaid redelivery fee.
Pay within <b>12 hours</b> or it will be returned to sender.</div>
<div>Redelivery fee</div><div class="fee">$1.99</div>
<form onsubmit="return false" autocomplete="off">
<label for="name">Full name</label><input id="name" name="name">
<label for="cc-number">Card number</label><input id="cc-number" name="cardnumber" autocomplete="cc-number"
 placeholder="1234 5678 9012 3456">
<label for="cc-exp">Expiry (MM/YY)</label><input id="cc-exp" name="exp" autocomplete="cc-exp">
<label for="cvv">CVV</label><input id="cvv" name="cvv">
<button type="submit">Pay $1.99 now</button>
</form></div>
<footer>Fictional brand · Tripwire HackHarvard demo page · form submits nowhere</footer>
</body></html>"""

REPORT_STYLE = """<style>
body{font-family:-apple-system,Helvetica,Arial,sans-serif;margin:0;background:#0f1115;color:#eee}
header{padding:16px 18px;font-weight:800;font-size:20px;border-bottom:1px solid #2a2d35}
header span{color:#ff4d4f}
.tag{padding:14px 18px;font-size:15px;color:#bbb}
.card{background:#181b21;margin:12px;padding:14px 16px;border-radius:12px}
h3{margin:0 0 8px;font-size:13px;letter-spacing:.8px;text-transform:uppercase;color:#8b93a1}
img{width:100%;border-radius:8px;border:1px solid #333;display:block}
code{word-break:break-all;font-size:13px;color:#9cdcfe}
li{margin:6px 0;font-size:15px;line-height:1.35}
.red{color:#ff6b6b}.yellow{color:#ffcc00}.green{color:#52c41a}
footer{font-size:11px;color:#666;text-align:center;padding:16px}
</style>"""


def render_report(shot_id: str, meta: dict) -> str:
    esc = lambda v: html.escape(str(v)[:300])  # noqa: E731
    chain = meta.get("chain") or []
    flags = meta.get("flags") or []
    parts = [
        '<!doctype html><html><head><meta name="viewport" content="width=device-width,initial-scale=1">',
        f"<title>Tripwire opened this link</title>{REPORT_STYLE}</head><body>",
        "<header>Trip<span>wire</span> 🪤</header>",
        '<div class="tag">Tripwire opened this link in a sealed sandbox so you didn\'t have to.</div>',
        f'<div class="card"><h3>What the page looks like</h3><img src="/s/{shot_id}.jpg" alt="Screenshot"></div>',
    ]
    if meta.get("final_url"):
        hops = "".join(f"<li><code>{esc(u)}</code></li>" for u in chain[:8])
        parts.append(
            f'<div class="card"><h3>Where it really goes</h3><code>{esc(meta["final_url"])}</code>'
            + (f"<ul>{hops}</ul>" if hops else "")
            + "</div>"
        )
    if flags:
        items = "".join(f'<li class="{esc(f.get("s", "yellow"))}">{esc(f.get("t", ""))}</li>' for f in flags[:8])
        parts.append(f'<div class="card"><h3>Red flags found</h3><ul>{items}</ul></div>')
    parts.append("<footer>Nothing was typed or submitted. Screenshot kept temporarily.</footer></body></html>")
    return "".join(parts)


HOME = """<!doctype html><html><head><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Tripwire demo</title></head><body style="font-family:sans-serif;padding:24px">
<h2>Tripwire demo host</h2><p>Hosts a harmless fictional scam page for the Tripwire HackHarvard demo and
investigation screenshots.</p></body></html>"""


class Handler(BaseHTTPRequestHandler):
    server_version = "nginx"
    sys_version = ""

    def _send(self, code: int, body: bytes, ctype: str = "text/html; charset=utf-8", extra: dict | None = None):
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        for k, v in (extra or {}).items():
            self.send_header(k, v)
        self.end_headers()
        if self.command != "HEAD":
            self.wfile.write(body)

    def do_HEAD(self):  # noqa: N802
        self.do_GET()

    def do_GET(self):  # noqa: N802
        path = urlsplit(self.path).path
        if path in ("/track", "/t", "/pp"):
            self._send(302, b"", extra={"Location": "/redeliver?ref=sms"})
        elif path == "/redeliver":
            self._send(200, REDELIVER.encode())
        elif path.startswith("/s/") and path.endswith(".jpg"):
            data = SHOTS.get(path[3:-4])
            self._send(200, data, "image/jpeg") if data else self._send(404, b"not found", "text/plain")
        elif path.startswith("/s/") and SHOTS.get(path[3:]):
            self._send(200, render_report(path[3:], METAS.get(path[3:], {})).encode())
        elif path in ("/", "/health"):
            self._send(200, HOME.encode())
        else:
            self._send(404, b"not found", "text/plain")

    def do_POST(self):  # noqa: N802
        if urlsplit(self.path).path != "/upload":
            return self._send(404, b"not found", "text/plain")
        given = self.headers.get("X-Tripwire-Token", "")
        if not TOKEN or not hmac.compare_digest(given, TOKEN):
            return self._send(403, b"forbidden", "text/plain")
        length = int(self.headers.get("Content-Length", "0"))
        if not 0 < length <= MAX_BYTES:
            return self._send(413, b"too large", "text/plain")
        data = self.rfile.read(length)
        if not data.startswith(b"\xff\xd8"):
            return self._send(415, b"jpeg only", "text/plain")
        shot_id = secrets.token_urlsafe(12)
        SHOTS[shot_id] = data
        try:
            meta = json.loads(base64.b64decode(self.headers.get("X-Tripwire-Meta", "")) or b"{}")
            METAS[shot_id] = meta if isinstance(meta, dict) else {}
        except Exception:  # noqa: BLE001
            METAS[shot_id] = {}
        while len(SHOTS) > MAX_SHOTS:
            METAS.pop(SHOTS.popitem(last=False)[0], None)
        self._send(200, f"/s/{shot_id}".encode(), "text/plain")

    def log_message(self, fmt, *args):
        pass


if __name__ == "__main__":
    port = int(os.environ.get("PORT", "8080"))
    ThreadingHTTPServer(("0.0.0.0", port), Handler).serve_forever()
