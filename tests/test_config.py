import json
from pathlib import Path

import pytest

from bot.config import AppConfig, GameEntry, GamesConfig, load_env, load_games


def test_load_env_returns_appconfig(monkeypatch):
    monkeypatch.setenv("DISCORD_BOT_TOKEN", "tok")
    monkeypatch.setenv("DISCORD_GUILD_ID", "123")
    monkeypatch.setenv("ONBOARDING_CHANNEL_ID", "456")
    monkeypatch.setenv("LOG_LEVEL", "DEBUG")

    cfg = load_env()

    assert isinstance(cfg, AppConfig)
    assert cfg.bot_token == "tok"
    assert cfg.guild_id == 123
    assert cfg.onboarding_channel_id == 456
    assert cfg.log_level == "DEBUG"


def test_load_env_default_log_level(monkeypatch):
    monkeypatch.setenv("DISCORD_BOT_TOKEN", "tok")
    monkeypatch.setenv("DISCORD_GUILD_ID", "1")
    monkeypatch.setenv("ONBOARDING_CHANNEL_ID", "2")
    monkeypatch.delenv("LOG_LEVEL", raising=False)

    cfg = load_env()

    assert cfg.log_level == "INFO"


@pytest.mark.parametrize("missing", ["DISCORD_BOT_TOKEN", "DISCORD_GUILD_ID", "ONBOARDING_CHANNEL_ID"])
def test_load_env_missing_required(monkeypatch, missing):
    for v in ("DISCORD_BOT_TOKEN", "DISCORD_GUILD_ID", "ONBOARDING_CHANNEL_ID"):
        monkeypatch.setenv(v, "1" if v != "DISCORD_BOT_TOKEN" else "tok")
    monkeypatch.delenv(missing, raising=False)

    with pytest.raises(RuntimeError, match=missing):
        load_env()


@pytest.mark.parametrize("var", ["DISCORD_GUILD_ID", "ONBOARDING_CHANNEL_ID"])
def test_load_env_non_numeric_id(monkeypatch, var):
    monkeypatch.setenv("DISCORD_BOT_TOKEN", "tok")
    monkeypatch.setenv("DISCORD_GUILD_ID", "1")
    monkeypatch.setenv("ONBOARDING_CHANNEL_ID", "2")
    monkeypatch.setenv(var, "not-a-number")

    with pytest.raises(RuntimeError, match=var):
        load_env()


def write_games(tmp_path: Path, payload: dict) -> Path:
    p = tmp_path / "games.config.json"
    p.write_text(json.dumps(payload))
    return p


def test_load_games_valid(tmp_path):
    p = write_games(tmp_path, {
        "games": [
            {"label": "Valorant", "role_name": "Valorant", "emoji": "🎯"},
            {"label": "Dota 2", "role_name": "Dota 2"},
        ]
    })

    cfg = load_games(p)

    assert isinstance(cfg, GamesConfig)
    assert len(cfg.games) == 2
    assert cfg.games[0] == GameEntry(label="Valorant", role_name="Valorant", emoji="🎯")
    assert cfg.games[1] == GameEntry(label="Dota 2", role_name="Dota 2", emoji=None)


def test_load_games_missing_file(tmp_path):
    with pytest.raises(RuntimeError, match="not found"):
        load_games(tmp_path / "nope.json")


def test_load_games_malformed_json(tmp_path):
    p = tmp_path / "games.config.json"
    p.write_text("{not valid json")
    with pytest.raises(RuntimeError, match="parse"):
        load_games(p)


def test_load_games_empty_list(tmp_path):
    p = write_games(tmp_path, {"games": []})
    with pytest.raises(RuntimeError, match="at least 1"):
        load_games(p)


def test_load_games_too_many(tmp_path):
    p = write_games(tmp_path, {
        "games": [{"label": f"g{i}", "role_name": f"r{i}"} for i in range(26)]
    })
    with pytest.raises(RuntimeError, match="25"):
        load_games(p)


def test_load_games_duplicate_labels(tmp_path):
    p = write_games(tmp_path, {
        "games": [
            {"label": "Same", "role_name": "A"},
            {"label": "Same", "role_name": "B"},
        ]
    })
    with pytest.raises(RuntimeError, match="duplicate"):
        load_games(p)


def test_load_games_missing_role_name(tmp_path):
    p = write_games(tmp_path, {"games": [{"label": "Valorant", "role_name": ""}]})
    with pytest.raises(RuntimeError, match="role_name"):
        load_games(p)


def test_load_games_missing_label(tmp_path):
    p = write_games(tmp_path, {"games": [{"label": "", "role_name": "Valorant"}]})
    with pytest.raises(RuntimeError, match="label"):
        load_games(p)


def test_load_games_label_too_long(tmp_path):
    p = write_games(tmp_path, {"games": [{"label": "x" * 101, "role_name": "r"}]})
    with pytest.raises(RuntimeError, match="100"):
        load_games(p)


def test_load_games_non_string_label(tmp_path):
    p = write_games(tmp_path, {"games": [{"label": 5, "role_name": "r"}]})
    with pytest.raises(RuntimeError, match="must be a string"):
        load_games(p)


def test_load_games_non_string_role_name(tmp_path):
    p = write_games(tmp_path, {"games": [{"label": "Valorant", "role_name": 7}]})
    with pytest.raises(RuntimeError, match="must be a string"):
        load_games(p)


def test_load_games_non_string_emoji(tmp_path):
    p = write_games(tmp_path, {"games": [{"label": "Valorant", "role_name": "Valorant", "emoji": []}]})
    with pytest.raises(RuntimeError, match="emoji"):
        load_games(p)


def test_load_games_null_emoji(tmp_path):
    p = write_games(tmp_path, {"games": [{"label": "Valorant", "role_name": "Valorant", "emoji": None}]})
    cfg = load_games(p)
    assert cfg.games[0].emoji is None


def test_load_games_empty_emoji_normalized_to_none(tmp_path):
    p = write_games(tmp_path, {"games": [{"label": "Valorant", "role_name": "Valorant", "emoji": ""}]})
    cfg = load_games(p)
    assert cfg.games[0].emoji is None


def test_load_games_non_dict_entry(tmp_path):
    p = write_games(tmp_path, {"games": ["just a string"]})
    with pytest.raises(RuntimeError, match="not an object"):
        load_games(p)
