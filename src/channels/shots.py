"""Screenshot link fallback: upload a JPEG to the Chalk-hosted demo site and return a public URL."""

import base64
import json
from pathlib import Path

import httpx

from src import config


def upload_screenshot(path: str, meta: dict | None = None, timeout: float = 15.0) -> str | None:
    """Upload a JPEG (+ optional {final_url, chain, flags}) and return the public mobile report page URL."""
    base, token = config.demo_site_url(), config.shot_token()
    data = Path(path).read_bytes()
    if not base or not token or not data.startswith(b"\xff\xd8"):
        return None
    headers = {"X-Tripwire-Token": token}
    if meta:
        headers["X-Tripwire-Meta"] = base64.b64encode(json.dumps(meta).encode()).decode()
    resp = httpx.post(f"{base}/upload", content=data, headers=headers, timeout=timeout)
    resp.raise_for_status()
    return base + resp.text.strip()


def report_meta(verdict) -> dict:
    """Page details for the hosted report: final URL, redirect chain, and the red/yellow findings."""
    det = verdict.debug.get("detonation") or {}
    flags = [{"t": e.finding, "s": e.severity} for e in verdict.evidence if e.ok and e.severity in ("red", "yellow")]
    return {"final_url": det.get("final_url"), "chain": det.get("redirect_chain") or [], "flags": flags}
