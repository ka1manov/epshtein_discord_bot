from __future__ import annotations

import logging

import discord

from bot.config import AppConfig, GamesConfig
from bot.views import OnboardingView

log = logging.getLogger(__name__)

_PROMPT = "👋 Welcome! Pick the games you play and hit Confirm."


async def handle_member_join(
    member: discord.Member, app_config: AppConfig, games: GamesConfig
) -> None:
    """Send the onboarding welcome message to the configured channel.

    No-op if the member is a bot, the channel is missing, or it isn't a text channel.
    Logs and swallows discord.Forbidden / discord.HTTPException — never raises."""
    if member.bot:
        return

    channel = member.guild.get_channel(app_config.onboarding_channel_id)
    if channel is None:
        log.error(
            "onboarding channel id=%s not found in guild=%s",
            app_config.onboarding_channel_id, member.guild.id,
        )
        return
    if not isinstance(channel, discord.TextChannel):
        log.error(
            "onboarding channel id=%s is not a text channel (got %s)",
            app_config.onboarding_channel_id, type(channel).__name__,
        )
        return

    view = OnboardingView(games=games)
    content = f"{member.mention} {_PROMPT}"

    try:
        await channel.send(content=content, view=view)
    except discord.Forbidden:
        log.error(
            "missing permission to send in #%s for member_id=%s",
            channel.name, member.id,
        )
    except discord.HTTPException:
        log.exception(
            "HTTP error sending onboarding message in #%s for member_id=%s",
            channel.name, member.id,
        )
