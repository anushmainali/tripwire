"""Link detonation in a sealed Chalk sandbox (gVisor-isolated, destroyed after every use).

The suspicious URL is only ever opened inside the sandbox. The host uploads `browser_script.py`, runs it, reads back
the JSON facts, screenshot and HTML, then terminates the sandbox. Egress to cloud metadata and private networks is
denied by network policy.
"""

import json
import logging
import time
import uuid
from pathlib import Path

from src.detonation.report import DetonationResult

log = logging.getLogger(__name__)

SCRIPT = Path(__file__).with_name("browser_script.py")
ARTIFACTS = Path("/tmp/tripwire-detonations")
PLAYWRIGHT = "playwright==1.55.0"
REMOTE_DIR = "/tmp/det"
DENIED = ["169.254.169.254/32", "10.0.0.0/8", "172.16.0.0/12", "192.168.0.0/16", "100.64.0.0/10"]


def image():
    from chalkcompute import Image

    return (
        Image.debian_slim("3.12")
        .pip_install([PLAYWRIGHT])
        .run_commands("python -m playwright install --with-deps chromium")
    )


def _sandbox():
    from chalkcompute import NetworkPolicy, Sandbox

    return Sandbox(
        name=f"tripwire-det-{uuid.uuid4().hex[:10]}",
        image=image(),
        cpu="1",
        memory="2Gi",
        lifetime="300s",
        # Public internet only: a denied_routes-only policy blocks DNS, so allow 0.0.0.0/0 and deny private ranges.
        network_policy=NetworkPolicy(allowed_routes=[NetworkPolicy.Route("0.0.0.0/0")], denied_routes=DENIED),
        tags={"app": "tripwire", "purpose": "link-detonation"},
    )


def detonate(url: str, timeout_s: float = 60.0) -> DetonationResult:
    if not url.lower().startswith(("http://", "https://")):
        url = "http://" + url
    started = time.monotonic()
    out_dir = ARTIFACTS / uuid.uuid4().hex[:12]
    out_dir.mkdir(parents=True, exist_ok=True)
    sandbox = None
    try:
        sandbox = _sandbox().run(timeout=min(timeout_s, 120))
        sandbox.exec("mkdir", "-p", REMOTE_DIR, timeout_secs=15)
        sandbox.fs.write_bytes(f"{REMOTE_DIR}/browser_script.py", SCRIPT.read_bytes())
        left = max(25, int(timeout_s - (time.monotonic() - started)))
        res = sandbox.exec("python3", f"{REMOTE_DIR}/browser_script.py", url, REMOTE_DIR, timeout_secs=left)
        stdout = res.stdout.decode(errors="replace")
        line = next((ln for ln in stdout.splitlines() if ln.startswith("TRIPWIRE_RESULT ")), None)
        if line is None:
            err = res.stderr.decode(errors="replace")[-300:]
            return DetonationResult(url=url, error=f"browser exited {res.exit_code}: {err}")
        data = json.loads(line.removeprefix("TRIPWIRE_RESULT "))
        result = DetonationResult(**{k: v for k, v in data.items() if k in DetonationResult.__dataclass_fields__})
        for remote, local, attr in (
            ("shot.jpg", "shot.jpg", "screenshot_path"),
            ("page.html", "page.html", "html_path"),
        ):
            try:
                (out_dir / local).write_bytes(sandbox.fs.read_bytes(f"{REMOTE_DIR}/{remote}", timeout_secs=20))
                setattr(result, attr, str(out_dir / local))
            except Exception as error:  # noqa: BLE001
                log.info("no %s from sandbox: %s", remote, type(error).__name__)
        result.duration_s = round(time.monotonic() - started, 2)
        return result
    except Exception as error:  # noqa: BLE001
        log.warning("detonation failed: %s", error)
        return DetonationResult(url=url, error=f"{type(error).__name__}")
    finally:
        if sandbox is not None:
            try:
                sandbox.terminate(grace_period_seconds=0)
            except Exception as error:  # noqa: BLE001
                log.warning("sandbox terminate failed: %s", error)


if __name__ == "__main__":
    import sys

    logging.basicConfig(level=logging.INFO)
    r = detonate(sys.argv[1])
    print(json.dumps({k: v for k, v in r.__dict__.items() if k != "text_excerpt"}, indent=1))
