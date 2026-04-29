import logging

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

import discord
from discord import ui

from bot.config import GameEntry, GamesConfig
from bot.views import OnboardingView, extract_owner_id, is_owner


def test_extract_owner_id_plain_mention():
    assert extract_owner_id("<@123456789> welcome") == 123456789


def test_extract_owner_id_nickname_mention():
    assert extract_owner_id("<@!987654321> welcome") == 987654321


def test_extract_owner_id_no_mention():
    assert extract_owner_id("welcome friend") is None


def test_extract_owner_id_mention_in_middle():
    # Must be at the start — owner is always the first mention
    assert extract_owner_id("hi <@123>") is None


@pytest.mark.asyncio
async def test_is_owner_accepts_correct_user():
    interaction = MagicMock()
    interaction.message.content = "<@42> welcome"
    interaction.user.id = 42
    interaction.response.send_message = AsyncMock()

    assert await is_owner(interaction) is True
    interaction.response.send_message.assert_not_awaited()


@pytest.mark.asyncio
async def test_is_owner_rejects_other_user_with_ephemeral():
    interaction = MagicMock()
    interaction.message.content = "<@42> welcome"
    interaction.user.id = 99
    interaction.response.send_message = AsyncMock()

    assert await is_owner(interaction) is False
    interaction.response.send_message.assert_awaited_once()
    _, kwargs = interaction.response.send_message.call_args
    assert kwargs.get("ephemeral") is True


@pytest.mark.asyncio
async def test_is_owner_rejects_when_no_mention():
    interaction = MagicMock()
    interaction.message.content = "no mention here"
    interaction.user.id = 42
    interaction.response.send_message = AsyncMock()

    assert await is_owner(interaction) is False
    interaction.response.send_message.assert_awaited_once()


def make_games() -> GamesConfig:
    return GamesConfig(games=(
        GameEntry(label="Valorant", role_name="Valorant", emoji="🎯"),
        GameEntry(label="Dota 2", role_name="Dota 2"),
    ))


def test_view_builds_select_with_options_from_config():
    view = OnboardingView(games=make_games())

    select = next(c for c in view.children if isinstance(c, ui.Select))
    assert select.placeholder == "Pick your games"
    assert select.min_values == 0
    assert select.max_values == 2
    labels = [opt.label for opt in select.options]
    assert labels == ["Valorant", "Dota 2"]


def test_view_select_max_values_capped_to_games_count():
    games = GamesConfig(games=(GameEntry(label="Solo", role_name="Solo"),))
    view = OnboardingView(games=games)

    select = next(c for c in view.children if isinstance(c, ui.Select))
    assert select.max_values == 1


@pytest.mark.asyncio
async def test_select_callback_stores_selection_for_owner():
    view = OnboardingView(games=make_games())

    interaction = MagicMock()
    interaction.message.content = "<@42> welcome"
    interaction.user.id = 42
    interaction.response.defer = AsyncMock()
    interaction.response.send_message = AsyncMock()

    select = next(c for c in view.children if isinstance(c, ui.Select))
    select._values = ["Valorant", "Dota 2"]

    await select.callback(interaction)

    assert view.selection[42] == ["Valorant", "Dota 2"]
    interaction.response.defer.assert_awaited_once()


@pytest.mark.asyncio
async def test_select_callback_rejects_non_owner():
    view = OnboardingView(games=make_games())

    interaction = MagicMock()
    interaction.message.content = "<@42> welcome"
    interaction.user.id = 99
    interaction.response.defer = AsyncMock()
    interaction.response.send_message = AsyncMock()

    select = next(c for c in view.children if isinstance(c, ui.Select))
    select._values = ["Valorant"]

    await select.callback(interaction)

    assert 99 not in view.selection
    interaction.response.send_message.assert_awaited_once()


def test_view_is_persistent():
    view = OnboardingView(games=make_games())

    select = next(c for c in view.children if isinstance(c, ui.Select))

    assert view.timeout is None
    assert view.is_persistent()
    assert select.custom_id == "onboarding:select"


def test_children_do_not_shadow_framework_parent_attribute():
    """discord.py's `Item._parent` is set by the framework and used internally
    (Item._run_checks recurses through it). If our subclasses store their own
    `self._parent`, they shadow the framework's attribute and interactions
    crash with `AttributeError: 'OnboardingView' object has no attribute
    '_run_checks'`. Lock this down with a structural test."""
    view = OnboardingView(games=make_games())

    for child in view.children:
        # The framework's _parent (when set) must expose _run_checks. If our
        # own assignment shadows it with the View, the View won't have that
        # method and we regress the v2.7+ bug.
        framework_parent = getattr(child, "_parent", None)
        if framework_parent is not None:
            assert hasattr(framework_parent, "_run_checks"), (
                f"{type(child).__name__}._parent shadows the framework attribute "
                f"(got {type(framework_parent).__name__})"
            )


def make_confirm_interaction(user_id: int = 42, member=None):
    interaction = MagicMock()
    interaction.message.content = "<@42> welcome"
    interaction.user.id = user_id
    interaction.user = member if member else MagicMock(id=user_id)
    interaction.response.send_message = AsyncMock()
    interaction.response.edit_message = AsyncMock()
    interaction.followup.send = AsyncMock()
    return interaction


def get_confirm(view: OnboardingView):
    return next(c for c in view.children if isinstance(c, ui.Button))


@pytest.mark.asyncio
async def test_confirm_rejects_non_owner():
    view = OnboardingView(games=make_games())
    interaction = make_confirm_interaction(user_id=99)

    await get_confirm(view).callback(interaction)

    interaction.response.send_message.assert_awaited_once()
    interaction.response.edit_message.assert_not_awaited()


@pytest.mark.asyncio
async def test_confirm_empty_selection_edits_message_and_removes_view():
    view = OnboardingView(games=make_games())
    interaction = make_confirm_interaction(user_id=42)
    # selection is empty by default

    await get_confirm(view).callback(interaction)

    interaction.response.edit_message.assert_awaited_once()
    _, kwargs = interaction.response.edit_message.call_args
    assert "No games selected" in kwargs["content"]
    assert kwargs["view"] is None


@pytest.mark.asyncio
async def test_confirm_success_assigns_roles_and_lists_them():
    view = OnboardingView(games=make_games())
    view.selection[42] = ["Valorant", "Dota 2"]

    member = MagicMock()
    member.id = 42
    interaction = make_confirm_interaction(user_id=42, member=member)

    with patch("bot.views.assign_roles", new=AsyncMock(return_value=(["Valorant", "Dota 2"], []))) as mock_assign:
        await get_confirm(view).callback(interaction)

    mock_assign.assert_awaited_once()
    assert mock_assign.call_args.args[1] == ["Valorant", "Dota 2"]

    interaction.response.edit_message.assert_awaited_once()
    _, kwargs = interaction.response.edit_message.call_args
    assert "Roles assigned" in kwargs["content"]
    assert "Valorant" in kwargs["content"]
    assert "Dota 2" in kwargs["content"]
    assert kwargs["view"] is None


@pytest.mark.asyncio
async def test_confirm_success_only_lists_assigned_not_skipped():
    view = OnboardingView(games=make_games())
    view.selection[42] = ["Valorant", "Missing"]

    member = MagicMock()
    member.id = 42
    interaction = make_confirm_interaction(user_id=42, member=member)

    with patch("bot.views.assign_roles", new=AsyncMock(return_value=(["Valorant"], ["Missing"]))):
        await get_confirm(view).callback(interaction)

    _, kwargs = interaction.response.edit_message.call_args
    assert "Valorant" in kwargs["content"]
    assert "Missing" not in kwargs["content"]


@pytest.mark.asyncio
async def test_confirm_handles_forbidden_with_generic_error(caplog):
    view = OnboardingView(games=make_games())
    view.selection[42] = ["Valorant"]

    member = MagicMock()
    member.id = 42
    interaction = make_confirm_interaction(user_id=42, member=member)

    err = discord.Forbidden(MagicMock(status=403), "no perm")
    with patch("bot.views.assign_roles", new=AsyncMock(side_effect=err)):
        with caplog.at_level(logging.ERROR):
            await get_confirm(view).callback(interaction)

    interaction.response.edit_message.assert_awaited_once()
    _, kwargs = interaction.response.edit_message.call_args
    assert "Something went wrong" in kwargs["content"]
    assert kwargs["view"] is None
    assert any("forbidden" in r.message.lower() or "permission" in r.message.lower()
               for r in caplog.records)


@pytest.mark.asyncio
async def test_confirm_no_matching_roles_uses_fallback_message():
    view = OnboardingView(games=make_games())
    view.selection[42] = ["Valorant"]

    member = MagicMock()
    member.id = 42
    interaction = make_confirm_interaction(user_id=42, member=member)

    with patch("bot.views.assign_roles", new=AsyncMock(return_value=([], ["Valorant"]))):
        await get_confirm(view).callback(interaction)

    interaction.response.edit_message.assert_awaited_once()
    _, kwargs = interaction.response.edit_message.call_args
    assert "No matching roles" in kwargs["content"]
    assert "contact a server admin" in kwargs["content"]
    assert kwargs["view"] is None
