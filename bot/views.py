from __future__ import annotations

import logging
import re
from typing import Optional

import discord
from discord import ui

from bot.config import GamesConfig
from bot.roles import assign_roles

log = logging.getLogger(__name__)

_MENTION_RE = re.compile(r"^<@!?(\d+)>")


def extract_owner_id(message_content: str) -> Optional[int]:
    """Parse the leading mention from a message and return the user ID, or None."""
    match = _MENTION_RE.match(message_content)
    return int(match.group(1)) if match else None


async def is_owner(interaction: discord.Interaction) -> bool:
    """Return True if `interaction.user` owns the message; otherwise reply ephemerally."""
    owner_id = extract_owner_id(interaction.message.content) if interaction.message else None
    if owner_id is not None and interaction.user.id == owner_id:
        return True
    await interaction.response.send_message(
        "This onboarding message isn't for you.", ephemeral=True
    )
    return False


_SELECT_CUSTOM_ID = "onboarding:select"
_CONFIRM_CUSTOM_ID = "onboarding:confirm"


class OnboardingView(ui.View):
    """Persistent view: a multi-select dropdown of games + a Confirm button."""

    def __init__(self, games: GamesConfig) -> None:
        super().__init__(timeout=None)
        self.games: GamesConfig = games
        self.selection: dict[int, list[str]] = {}
        self.add_item(GameSelect(games=games, parent=self))
        self.add_item(ConfirmButton(parent=self))


class GameSelect(ui.Select):
    def __init__(self, games: GamesConfig, parent: OnboardingView) -> None:
        options = [
            discord.SelectOption(label=g.label, value=g.label, emoji=g.emoji)
            for g in games.games
        ]
        super().__init__(
            custom_id=_SELECT_CUSTOM_ID,
            placeholder="Pick your games",
            min_values=0,
            max_values=len(options),
            options=options,
            row=0,
        )
        self._owner_view = parent

    async def callback(self, interaction: discord.Interaction) -> None:
        if not await is_owner(interaction):
            return
        self._owner_view.selection[interaction.user.id] = list(self.values)
        await interaction.response.defer()


class ConfirmButton(ui.Button):
    def __init__(self, parent: OnboardingView) -> None:
        super().__init__(
            custom_id=_CONFIRM_CUSTOM_ID,
            label="Confirm",
            emoji="✅",
            style=discord.ButtonStyle.primary,
            row=1,
        )
        self._owner_view = parent

    async def callback(self, interaction: discord.Interaction) -> None:
        if not await is_owner(interaction):
            return

        selection = self._owner_view.selection.get(interaction.user.id, [])
        if not selection:
            await interaction.response.edit_message(
                content="No games selected — you can pick a role anytime.",
                view=None,
            )
            return

        # Map labels back to role_names (config is the source of truth).
        label_to_role = {g.label: g.role_name for g in self._owner_view.games.games}
        role_names = [label_to_role[label] for label in selection if label in label_to_role]

        try:
            assigned, _skipped = await assign_roles(interaction.user, role_names)
        except discord.Forbidden:
            log.exception(
                "Forbidden when assigning roles for member_id=%s — bot may lack Manage Roles "
                "or its highest role is below a target role",
                interaction.user.id,
            )
            await interaction.response.edit_message(
                content="Something went wrong while assigning roles. Please contact a server admin.",
                view=None,
            )
            return
        except Exception:
            log.exception("unexpected error in confirm handler for member_id=%s", interaction.user.id)
            await interaction.response.edit_message(
                content="Something went wrong, try again later.",
                view=None,
            )
            return

        # Pop the user's selection so the dict doesn't grow unboundedly across the bot's uptime.
        self._owner_view.selection.pop(interaction.user.id, None)

        if assigned:
            content = "✅ Roles assigned: " + ", ".join(assigned)
        else:
            content = "No matching roles existed on this server. Please contact a server admin."
        await interaction.response.edit_message(content=content, view=None)
