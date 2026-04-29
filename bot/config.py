from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Final, Optional

from dotenv import load_dotenv

_REQUIRED_ENV: Final[tuple[str, ...]] = (
    "DISCORD_BOT_TOKEN",
    "DISCORD_GUILD_ID",
    "ONBOARDING_CHANNEL_ID",
)

_MAX_GAMES = 25
_MAX_LABEL_LEN = 100


@dataclass(frozen=True, slots=True)
class AppConfig:
    bot_token: str
    guild_id: int
    onboarding_channel_id: int
    log_level: str


def load_env() -> AppConfig:
    """Load and validate environment variables. Reads `.env` if present."""
    load_dotenv()

    missing = [v for v in _REQUIRED_ENV if not os.environ.get(v)]
    if missing:
        raise RuntimeError(f"Missing required env var(s): {', '.join(missing)}")

    try:
        guild_id = int(os.environ["DISCORD_GUILD_ID"])
    except ValueError as e:
        raise RuntimeError(
            f"DISCORD_GUILD_ID must be an integer (got {os.environ['DISCORD_GUILD_ID']!r})"
        ) from e
    try:
        channel_id = int(os.environ["ONBOARDING_CHANNEL_ID"])
    except ValueError as e:
        raise RuntimeError(
            f"ONBOARDING_CHANNEL_ID must be an integer (got {os.environ['ONBOARDING_CHANNEL_ID']!r})"
        ) from e

    return AppConfig(
        bot_token=os.environ["DISCORD_BOT_TOKEN"],
        guild_id=guild_id,
        onboarding_channel_id=channel_id,
        log_level=os.environ.get("LOG_LEVEL", "INFO").upper(),
    )


@dataclass(frozen=True, slots=True)
class GameEntry:
    label: str
    role_name: str
    emoji: Optional[str] = None


@dataclass(frozen=True, slots=True)
class GamesConfig:
    games: tuple[GameEntry, ...]


def _get_str_field(item: dict, key: str, i: int) -> str:
    """Return the stripped string value for `key`, or '' if missing/None.
    Raises RuntimeError if present but not a string."""
    val = item.get(key)
    if val is None:
        return ""
    if not isinstance(val, str):
        raise RuntimeError(
            f"games[{i}] field {key!r} must be a string, got {type(val).__name__}"
        )
    return val.strip()


def _get_optional_str_field(item: dict, key: str, i: int) -> Optional[str]:
    """Return the (un-stripped) string value for `key`, or None if missing/None/empty.
    Raises RuntimeError if present but not a string."""
    val = item.get(key)
    if val is None or val == "":
        return None
    if not isinstance(val, str):
        raise RuntimeError(
            f"games[{i}] field {key!r} must be a string or null, got {type(val).__name__}"
        )
    return val


def load_games(path: Path) -> GamesConfig:
    """Load and validate the games config file."""
    if not path.exists():
        raise RuntimeError(f"games config not found at {path}")

    try:
        raw = json.loads(path.read_text())
    except json.JSONDecodeError as e:
        raise RuntimeError(f"failed to parse games config: {e}") from e

    games_raw = raw.get("games") if isinstance(raw, dict) else None
    if not isinstance(games_raw, list):
        raise RuntimeError("games config must be an object with a 'games' list")
    if len(games_raw) < 1:
        raise RuntimeError("games config must contain at least 1 game")
    if len(games_raw) > _MAX_GAMES:
        raise RuntimeError(f"games config exceeds Discord limit of {_MAX_GAMES} entries")

    seen_labels: set[str] = set()
    entries: list[GameEntry] = []
    for i, item in enumerate(games_raw):
        if not isinstance(item, dict):
            raise RuntimeError(f"games[{i}] is not an object")
        label = _get_str_field(item, "label", i)
        role_name = _get_str_field(item, "role_name", i)
        emoji = _get_optional_str_field(item, "emoji", i)
        if not label:
            raise RuntimeError(f"games[{i}] has empty label")
        if len(label) > _MAX_LABEL_LEN:
            raise RuntimeError(f"games[{i}] label exceeds {_MAX_LABEL_LEN} chars")
        if not role_name:
            raise RuntimeError(f"games[{i}] has empty role_name")
        if label in seen_labels:
            raise RuntimeError(f"games config has duplicate label: {label!r}")
        seen_labels.add(label)
        entries.append(GameEntry(label=label, role_name=role_name, emoji=emoji))

    return GamesConfig(games=tuple(entries))
