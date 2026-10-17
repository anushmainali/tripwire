import pytest

from src.investigator import orchestrator


@pytest.fixture(autouse=True)
def no_heavy_steps(monkeypatch):
    """Tests stay offline: never start Droid sessions or Chalk sandboxes."""
    monkeypatch.setattr(orchestrator, "ALL_STEPS", ())
