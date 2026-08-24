"""
utils/permissions.py
Role-hierarchy and permission safety checks.
These MUST be used before any sensitive role/moderation operation so that:
- a moderator/admin can never act on someone with an equal or higher top role
- the bot never attempts an action above its own top role
"""
from __future__ import annotations

import discord

REQUIRED_BOT_PERMISSIONS = [
    "manage_roles",
    "manage_channels",
    "kick_members",
    "ban_members",
    "moderate_members",  # timeout
    "manage_messages",
    "view_channel",
    "send_messages",
    "embed_links",
    "read_message_history",
]


def missing_bot_permissions(guild: discord.Guild) -> list[str]:
    """Return the list of required permission names the bot lacks in this guild."""
    me = guild.me
    if me is None:
        return REQUIRED_BOT_PERMISSIONS
    perms = me.guild_permissions
    return [p for p in REQUIRED_BOT_PERMISSIONS if not getattr(perms, p, False)]


def is_hierarchy_safe(actor: discord.Member, target: discord.Member) -> bool:
    """
    True if `actor` is allowed to act on `target` based on role hierarchy.
    The guild owner always passes. Otherwise the actor's top role must be
    strictly higher than the target's top role.
    """
    if actor.guild.owner_id == actor.id:
        return True
    if actor.id == target.id:
        return False
    return actor.top_role > target.top_role


def bot_can_act_on(guild: discord.Guild, target: discord.Member) -> bool:
    """True if the bot's top role is higher than the target's — required for
    role changes, kicks, bans, and timeouts to succeed."""
    me = guild.me
    if me is None:
        return False
    return me.top_role > target.top_role


def can_assign_role(actor: discord.Member, role: discord.Role) -> bool:
    """A member can never assign a role equal to or above their own top role,
    unless they are the guild owner."""
    if actor.guild.owner_id == actor.id:
        return True
    return actor.top_role > role


def is_staff(member: discord.Member, staff_role_ids: set[int]) -> bool:
    if member.guild.owner_id == member.id:
        return True
    return any(role.id in staff_role_ids for role in member.roles)
