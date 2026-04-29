import logging
from unittest.mock import AsyncMock, MagicMock, patch

import discord
import pytest

from bot.config import AppConfig, GameEntry, GamesConfig
from bot.onboarding import handle_member_join


def make_app_config(channel_id: int = 100) -> AppConfig:
    return AppConfig(
        bot_token="tok", guild_id=1, onboarding_channel_id=channel_id, log_level="INFO"
    )


def make_games() -> GamesConfig:
    return GamesConfig(games=(GameEntry(label="Valorant", role_name="Valorant"),))


def make_member(*, is_bot: bool = False, member_id: int = 42, channel=None):
    member = MagicMock()
    member.id = member_id
    member.bot = is_bot
    member.mention = f"<@{member_id}>"
    member.guild = MagicMock()
    member.guild.get_channel.return_value = channel
    return member


def make_text_channel(name: str = "pick-your-roles"):
    channel = MagicMock(spec=discord.TextChannel)
    channel.name = name
    channel.send = AsyncMock()
    return channel


@pytest.mark.asyncio
async def test_skip_when_member_is_bot():
    member = make_member(is_bot=True)

    await handle_member_join(member, make_app_config(), make_games())

    member.guild.get_channel.assert_not_called()


@pytest.mark.asyncio
async def test_logs_and_returns_when_channel_not_found(caplog):
    member = make_member(channel=None)

    with caplog.at_level(logging.ERROR):
        await handle_member_join(member, make_app_config(), make_games())

    assert any("channel" in r.message.lower() for r in caplog.records)


@pytest.mark.asyncio
async def test_logs_and_returns_when_channel_is_not_text(caplog):
    not_text = MagicMock()  # not a TextChannel
    member = make_member(channel=not_text)

    with caplog.at_level(logging.ERROR):
        await handle_member_join(member, make_app_config(), make_games())

    assert any("channel" in r.message.lower() for r in caplog.records)


@pytest.mark.asyncio
async def test_sends_welcome_message_with_view():
    channel = make_text_channel()
    member = make_member(channel=channel)

    await handle_member_join(member, make_app_config(), make_games())

    channel.send.assert_awaited_once()
    _, kwargs = channel.send.call_args
    assert "<@42>" in kwargs["content"]
    assert kwargs["view"] is not None


@pytest.mark.asyncio
async def test_logs_when_send_forbidden(caplog):
    channel = make_text_channel()
    channel.send.side_effect = discord.Forbidden(MagicMock(status=403), "nope")
    member = make_member(channel=channel)

    with caplog.at_level(logging.ERROR):
        await handle_member_join(member, make_app_config(), make_games())

    assert any("permission" in r.message.lower() or "forbidden" in r.message.lower()
               for r in caplog.records)


@pytest.mark.asyncio
async def test_logs_when_send_http_error(caplog):
    channel = make_text_channel()
    channel.send.side_effect = discord.HTTPException(MagicMock(status=500), "boom")
    member = make_member(channel=channel)

    with caplog.at_level(logging.ERROR):
        await handle_member_join(member, make_app_config(), make_games())

    assert any(r.levelno >= logging.ERROR for r in caplog.records)
