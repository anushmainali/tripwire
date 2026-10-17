"""Deploy the demo site to a Chalk ScalingGroup and print its URL.

Run: .venv/bin/python -m demo_site.deploy
Needs TRIPWIRE_SHOT_TOKEN in .env (any long random string; shared by the uploader and the site).
Writes the public URL to data/demo_site_url.txt (gitignored) for the app to read.
"""

import chalkcompute

from src import config
from src.config import ROOT

NAME = "tripwire-demo"


def main() -> None:
    token = config.shot_token()
    if not token:
        raise SystemExit("Set TRIPWIRE_SHOT_TOKEN in .env first.")
    img = (
        chalkcompute.Image.debian_slim("3.12")
        .add_local_file(str(ROOT / "demo_site" / "app.py"), "/app/app.py", strategy="copy")
        .entrypoint(["python", "/app/app.py"])
    )
    sg = chalkcompute.ScalingGroup(
        image=img,
        name=NAME,
        port=8080,
        min_replicas=1,
        max_replicas=1,
        secrets=[chalkcompute.Secret.from_local_env("TRIPWIRE_SHOT_TOKEN")],
        startup_probe=chalkcompute.StartupProbe.http("/health"),
        tags={"app": "tripwire"},
    ).deploy()
    url = sg.web_url.rstrip("/")
    (ROOT / "data").mkdir(exist_ok=True)
    (ROOT / "data" / "demo_site_url.txt").write_text(url)
    print(url)


if __name__ == "__main__":
    main()
