"""Screenshot link fallback: upload a JPEG to the Chalk-hosted demo site and return a public URL."""

from pathlib import Path

import httpx

from src import config


def upload_screenshot(path: str, timeout: float = 15.0) -> str | None:
    base, token = config.demo_site_url(), config.shot_token()
    data = Path(path).read_bytes()
    if not base or not token or not data.startswith(b"\xff\xd8"):
        return None
    resp = httpx.post(f"{base}/upload", content=data, headers={"X-Tripwire-Token": token}, timeout=timeout)
    resp.raise_for_status()
    return base + resp.text.strip()
