"""Load and validate settings from .env.

Secret values are never printed: errors name the missing variable only, and
`describe()` reports which settings are present without showing their values.
"""

import os
from dataclasses import dataclass, fields
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")

PHOTON_PLATFORMS = ("imessage", "email")


class ConfigError(RuntimeError):
    pass


def _get(name: str, required: bool = True) -> str | None:
    value = os.environ.get(name, "").strip() or None
    if required and value is None:
        raise ConfigError(f"Missing {name} in .env (see .env.example).")
    return value


@dataclass(frozen=True)
class FactoryConfig:
    # Optional: the SDK can use a signed-in `droid` CLI session instead.
    api_key: str | None


@dataclass(frozen=True)
class PhotonConfig:
    api_key: str
    project_id: str
    platform: str
    agent_handle: str
    test_sender: str


@dataclass(frozen=True)
class ChalkConfig:
    client_id: str
    client_secret: str
    environment: str | None
    api_server: str | None


@dataclass(frozen=True)
class ChalkRouterConfig:
    api_key: str
    env_id: str
    base_url: str = "https://api.chalk.ai/v1/router"


def factory() -> FactoryConfig:
    return FactoryConfig(api_key=_get("FACTORY_API_KEY", required=False))


def photon() -> PhotonConfig:
    project_id = _get("PHOTON_PROJECT_ID")
    if not project_id.startswith("pho_prj_"):
        raise ConfigError("PHOTON_PROJECT_ID should start with pho_prj_.")
    platform = _get("PHOTON_PLATFORM")
    if platform not in PHOTON_PLATFORMS:
        raise ConfigError(f"PHOTON_PLATFORM must be one of {PHOTON_PLATFORMS}.")
    return PhotonConfig(
        api_key=_get("PHOTON_API_KEY"),
        project_id=project_id,
        platform=platform,
        agent_handle=_get("PHOTON_AGENT_HANDLE"),
        test_sender=_get("PHOTON_TEST_SENDER"),
    )


def chalk() -> ChalkConfig:
    return ChalkConfig(
        client_id=_get("CHALK_CLIENT_ID"),
        client_secret=_get("CHALK_CLIENT_SECRET"),
        environment=_get("CHALK_ENVIRONMENT", required=False),
        api_server=_get("CHALK_API_SERVER", required=False),
    )


def chalk_router() -> ChalkRouterConfig:
    return ChalkRouterConfig(api_key=_get("CHALK_ROUTER_API_KEY"), env_id=_get("CHALK_ENV_ID"))


def shot_token() -> str | None:
    """Shared token for uploading screenshots to the demo/screenshot host."""
    return _get("TRIPWIRE_SHOT_TOKEN", required=False)


def demo_site_url() -> str | None:
    """Public URL of the Chalk-hosted demo site (env override, else written by `python -m demo_site.deploy`)."""
    url = _get("TRIPWIRE_DEMO_URL", required=False)
    if url:
        return url.rstrip("/")
    path = ROOT / "data" / "demo_site_url.txt"
    return path.read_text().strip().rstrip("/") if path.exists() else None


def describe() -> dict[str, dict[str, bool] | str]:
    """Which settings are present per service (True/False), never the values."""
    report: dict[str, dict[str, bool] | str] = {}
    for name, loader in (("factory", factory), ("photon", photon), ("chalk", chalk), ("chalk_router", chalk_router)):
        try:
            cfg = loader()
            report[name] = {f.name: getattr(cfg, f.name) is not None for f in fields(cfg)}
        except ConfigError as error:
            report[name] = str(error)
    return report


if __name__ == "__main__":
    for service, status in describe().items():
        print(f"{service}: {status}")
