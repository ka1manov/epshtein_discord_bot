import pytest


@pytest.fixture(autouse=True)
def _stub_load_dotenv(monkeypatch):
    """Neutralize python-dotenv during tests so a developer-local `.env`
    cannot leak into test environments and override `monkeypatch.setenv` /
    `monkeypatch.delenv`."""
    monkeypatch.setattr("bot.config.load_dotenv", lambda *args, **kwargs: None)
