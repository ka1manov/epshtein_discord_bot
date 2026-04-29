import logging
from unittest.mock import MagicMock

from bot.roles import resolve_role_by_name


def make_role(name: str):
    r = MagicMock()
    r.name = name
    return r


def test_resolve_found():
    guild = MagicMock()
    role = make_role("Valorant")
    guild.roles = [make_role("Other"), role]

    assert resolve_role_by_name(guild, "Valorant") is role


def test_resolve_not_found():
    guild = MagicMock()
    guild.roles = [make_role("Other")]

    assert resolve_role_by_name(guild, "Valorant") is None


def test_resolve_multiple_returns_first_and_warns(caplog):
    guild = MagicMock()
    first = make_role("Dup")
    second = make_role("Dup")
    guild.roles = [first, second]

    with caplog.at_level(logging.WARNING):
        result = resolve_role_by_name(guild, "Dup")

    assert result is first
    assert any("multiple" in r.message.lower() for r in caplog.records)


import pytest
from unittest.mock import AsyncMock

import discord

from bot.roles import assign_roles


def make_member_with_guild(role_names: list[str]):
    """Build a Mock member whose guild has roles with the given names."""
    member = MagicMock()
    member.id = 42
    member.add_roles = AsyncMock()
    member.guild = MagicMock()
    member.guild.roles = [make_role(n) for n in role_names]
    return member


@pytest.mark.asyncio
async def test_assign_roles_returns_assigned_and_skipped():
    member = make_member_with_guild(["Valorant", "Dota 2"])

    assigned, skipped = await assign_roles(member, ["Valorant", "DoesNotExist", "Dota 2"])

    assert assigned == ["Valorant", "Dota 2"]
    assert skipped == ["DoesNotExist"]


@pytest.mark.asyncio
async def test_assign_roles_calls_add_roles_with_resolved():
    member = make_member_with_guild(["Valorant"])

    await assign_roles(member, ["Valorant", "Missing"])

    member.add_roles.assert_awaited_once()
    args, _ = member.add_roles.call_args
    assert len(args) == 1
    assert args[0].name == "Valorant"


@pytest.mark.asyncio
async def test_assign_roles_skips_add_roles_when_all_missing():
    member = make_member_with_guild([])

    assigned, skipped = await assign_roles(member, ["Missing"])

    assert assigned == []
    assert skipped == ["Missing"]
    member.add_roles.assert_not_awaited()


@pytest.mark.asyncio
async def test_assign_roles_propagates_forbidden():
    member = make_member_with_guild(["Valorant"])
    member.add_roles.side_effect = discord.Forbidden(MagicMock(status=403), "no perm")

    with pytest.raises(discord.Forbidden):
        await assign_roles(member, ["Valorant"])
