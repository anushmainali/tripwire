"""Tripwire demo site, hosted on a Chalk ScalingGroup.

1. A harmless imitation of a delivery-fee scam for a FICTIONAL brand ("PostalPlus"), so the live demo never depends
   on a real criminal site. /track -> 302 -> /redeliver, which shows a card form. The form submits nowhere and
   nothing typed is ever sent or stored.
2. Screenshot hosting fallback: POST /upload (token-protected) stores a JPEG in memory; GET /s/<id>.jpg serves it.

Standard library only. Binds 0.0.0.0:8080.
"""

import hmac
import os
import secrets
from collections import OrderedDict
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlsplit

TOKEN = os.environ.get("TRIPWIRE_SHOT_TOKEN", "")
MAX_SHOTS = 300
MAX_BYTES = 3_000_000
SHOTS: OrderedDict[str, bytes] = OrderedDict()

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
        while len(SHOTS) > MAX_SHOTS:
            SHOTS.popitem(last=False)
        self._send(200, f"/s/{shot_id}.jpg".encode(), "text/plain")

    def log_message(self, fmt, *args):
        pass


if __name__ == "__main__":
    port = int(os.environ.get("PORT", "8080"))
    ThreadingHTTPServer(("0.0.0.0", port), Handler).serve_forever()
