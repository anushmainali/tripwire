import pytest

from src.contracts import Evidence
from src.investigator import orchestrator
from src.investigator.checks import payment, rdap


@pytest.fixture(autouse=True)
def no_heavy_steps(monkeypatch):
    """Tests stay offline: never start Droid sessions or Chalk sandboxes."""
    monkeypatch.setattr(orchestrator, "ALL_STEPS", ())


@pytest.fixture(autouse=True)
def offline_lookups(request, monkeypatch):
    """No Chalk / RDAP / explorer network calls (test_checks patches the HTTP clients itself)."""
    monkeypatch.setattr(rdap, "chalk_age_days", lambda d: None)
    if request.module.__name__.endswith("test_checks"):
        return
    monkeypatch.setattr(rdap, "registration_date", lambda d, client=None: None)
    monkeypatch.setattr(payment, "_btc", lambda a, c: Evidence("crypto_explorer", "x", "yellow"))
    monkeypatch.setattr(payment, "_eth", lambda a, c: Evidence("crypto_explorer", "x", "yellow"))
