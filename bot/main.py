from __future__ import annotations

import logging
from pathlib import Path

import discord
from discord.ext import commands

from bot.config import AppConfig, GamesConfig, load_env, load_games
from bot.logging_setup import configure as configure_logging
from bot.onboarding import handle_member_join
from bot.views import OnboardingView

GAMES_CONFIG_PATH = Path(__file__).resolve().parent.parent / "games.config.json"


def build_bot(app_config: AppConfig, games: GamesConfig) -> commands.Bot:
    intents = discord.Intents.none()
    intents.guilds = True
    intents.members = True  # privileged intent

    bot = commands.Bot(command_prefix="!", intents=intents)
    log = logging.getLogger(__name__)

    @bot.event
    async def on_ready() -> None:
        # Re-register the persistent view so old messages keep working after restart.
        bot.add_view(OnboardingView(games=games))
        log.info("logged in as %s; persistent OnboardingView registered", bot.user)

    @bot.event
    async def on_member_join(member: discord.Member) -> None:
        await handle_member_join(member, app_config, games)

    return bot


def main() -> None:
    # Load env first so LOG_LEVEL set only in `.env` is honored when configuring logging.
    app_config = load_env()
    configure_logging(level=app_config.log_level)
    games = load_games(GAMES_CONFIG_PATH)
    bot = build_bot(app_config, games)
    bot.run(app_config.bot_token, log_handler=None)


if __name__ == "__main__":
    main()
