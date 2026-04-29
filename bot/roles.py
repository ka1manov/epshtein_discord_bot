from __future__ import annotations

import logging
from typing import Optional

import discord

log = logging.getLogger(__name__)


def resolve_role_by_name(guild: discord.Guild, name: str) -> Optional[discord.Role]:
    """Return the first role on `guild` whose name matches `name`, else None.
    Logs a warning if multiple roles share the same name."""
    matches = [r for r in guild.roles if r.name == name]
    if not matches:
        return None
    if len(matches) > 1:
        log.warning("multiple roles named %r in guild %s; using the first", name, guild)
    return matches[0]


async def assign_roles(
    member: discord.Member, role_names: list[str]
) -> tuple[list[str], list[str]]:
    """Resolve and assign every role name that exists on the member's guild.

    Returns (assigned, skipped) — both are lists of role names.
    Re-raises discord.Forbidden if the bot lacks permission."""
    resolved: list[discord.Role] = []
    assigned: list[str] = []
    skipped: list[str] = []

    for name in role_names:
        role = resolve_role_by_name(member.guild, name)
        if role is None:
            log.warning("role not found: name=%r member_id=%s", name, member.id)
            skipped.append(name)
            continue
        resolved.append(role)
        assigned.append(name)

    if resolved:
        await member.add_roles(*resolved, reason="Onboarding game selection")

    return assigned, skipped
