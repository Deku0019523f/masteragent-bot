"""
utils/checks.py
Reusable app_commands checks for gating slash commands by permission/role.
"""
from __future__ import annotations

import discord
from discord import app_commands


class NotConfigured(app_commands.CheckFailure):
    """Raised when /setup has not been run yet for this guild."""


class InsufficientRole(app_commands.CheckFailure):
    """Raised when the user lacks the required staff/admin role."""


def is_owner_or_admin():
    async def predicate(interaction: discord.Interaction) -> bool:
        if interaction.guild is None:
            raise app_commands.NoPrivateMessage()
        if interaction.user.id == interaction.guild.owner_id:
            return True
        if isinstance(interaction.user, discord.Member) and interaction.user.guild_permissions.administrator:
            return True
        raise app_commands.MissingPermissions(["administrator"])

    return app_commands.check(predicate)


def has_staff_role():
    """Requires the member to hold the configured moderator/admin/founder role,
    have Administrator, or be the guild owner."""

    async def predicate(interaction: discord.Interaction) -> bool:
        if interaction.guild is None or not isinstance(interaction.user, discord.Member):
            raise app_commands.NoPrivateMessage()

        member: discord.Member = interaction.user
        if member.id == interaction.guild.owner_id:
            return True
        if member.guild_permissions.administrator:
            return True

        bot = interaction.client
        db = getattr(bot, "db", None)
        if db is None:
            raise InsufficientRole("Base de données indisponible.")

        config = await db.get_guild_config(interaction.guild.id)
        if config is None:
            raise NotConfigured("Le serveur n'a pas encore été configuré. Utilisez /setup.")

        staff_role_ids = {
            rid for rid in (config["admin_role"], config["moderator_role"], config["founder_role"]) if rid
        }
        if any(role.id in staff_role_ids for role in member.roles):
            return True

        raise InsufficientRole("Vous n'avez pas le rôle requis pour cette commande.")

    return app_commands.check(predicate)


def guild_configured():
    async def predicate(interaction: discord.Interaction) -> bool:
        if interaction.guild is None:
            raise app_commands.NoPrivateMessage()
        bot = interaction.client
        db = getattr(bot, "db", None)
        config = await db.get_guild_config(interaction.guild.id) if db else None
        if config is None or config["setup_status"] != "completed":
            raise NotConfigured("Le serveur n'a pas encore été configuré. Utilisez /setup d'abord.")
        return True

    return app_commands.check(predicate)
