"""
cogs/moderation.py
Core moderation slash commands: warn, warnings, clear, timeout, untimeout,
kick, ban, unban, lock, unlock. Every sanction is persisted and logged.
"""
from __future__ import annotations

import datetime as dt
import logging

import discord
from discord import app_commands
from discord.ext import commands

from utils import checks, embeds, helpers, permissions

logger = logging.getLogger("afrocodeurs.cogs.moderation")


class ModerationCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    async def _log(self, guild: discord.Guild, embed: discord.Embed):
        config = await self.bot.db.get_guild_config(guild.id)
        if not config:
            return
        channel_id = config["moderation_channel"] or config["logs_channel"]
        channel = guild.get_channel(channel_id) if channel_id else None
        if channel:
            try:
                await channel.send(embed=embed)
            except discord.Forbidden:
                pass

    def _hierarchy_check(self, actor: discord.Member, target: discord.Member) -> str | None:
        if not permissions.is_hierarchy_safe(actor, target):
            return "❌ Vous ne pouvez pas agir sur un membre ayant un rôle égal ou supérieur au vôtre."
        if not permissions.bot_can_act_on(target.guild, target):
            return "❌ Mon rôle est trop bas dans la hiérarchie pour agir sur ce membre."
        return None

    # ---------------- warn ----------------

    @app_commands.command(name="warn", description="Avertir un membre.")
    @app_commands.describe(member="Le membre à avertir", reason="Raison de l'avertissement")
    @checks.has_staff_role()
    async def warn(self, interaction: discord.Interaction, member: discord.Member, reason: str):
        err = self._hierarchy_check(interaction.user, member)
        if err:
            return await interaction.response.send_message(err, ephemeral=True)

        db = self.bot.db
        await db.add_warning(interaction.guild.id, member.id, interaction.user.id, reason)
        await db.log_moderation_action(interaction.guild.id, member.id, interaction.user.id, "warn", reason)
        count = await db.count_warnings(interaction.guild.id, member.id)

        config = await db.get_guild_config(interaction.guild.id)
        auto_action = None
        if config:
            if count >= config["warn_major_threshold"]:
                auto_action = "major"
            elif count >= config["warn_timeout_threshold"]:
                auto_action = "timeout"

        await interaction.response.send_message(
            embed=embeds.success("Membre averti", f"{member.mention} a reçu un avertissement ({count} au total)."),
            ephemeral=True,
        )
        await self._log(interaction.guild, embeds.moderation_log("Avertissement", member, interaction.user, reason))

        if auto_action == "timeout" and permissions.bot_can_act_on(interaction.guild, member):
            try:
                await member.timeout(dt.timedelta(minutes=10), reason=f"Auto: {count} avertissements")
                await self._log(
                    interaction.guild,
                    embeds.moderation_log("Timeout automatique (10m)", member, interaction.client.user, f"{count} avertissements"),
                )
            except discord.Forbidden:
                pass
        elif auto_action == "major":
            await self._log(
                interaction.guild,
                embeds.warning(
                    "Seuil critique atteint",
                    f"{member.mention} a atteint {count} avertissements — une sanction manuelle plus importante est recommandée.",
                ),
            )

    @app_commands.command(name="warnings", description="Afficher l'historique des avertissements d'un membre.")
    @checks.has_staff_role()
    async def warnings_cmd(self, interaction: discord.Interaction, member: discord.Member):
        rows = await self.bot.db.get_warnings(interaction.guild.id, member.id)
        if not rows:
            return await interaction.response.send_message(
                embed=embeds.info("Aucun avertissement", f"{member.mention} n'a aucun avertissement."),
                ephemeral=True,
            )
        lines = [f"**{i+1}.** {r['reason']} — <@{r['moderator_id']}> ({r['created_at']})" for i, r in enumerate(rows)]
        await interaction.response.send_message(
            embed=embeds.info(f"Avertissements de {member.display_name} ({len(rows)})", "\n".join(lines[:15])),
            ephemeral=True,
        )

    # ---------------- clear ----------------

    @app_commands.command(name="clear", description="Supprimer un nombre de messages dans ce salon.")
    @app_commands.describe(amount="Nombre de messages à supprimer (1-100)")
    @checks.has_staff_role()
    async def clear(self, interaction: discord.Interaction, amount: app_commands.Range[int, 1, 100]):
        await interaction.response.defer(ephemeral=True)
        deleted = await interaction.channel.purge(limit=amount)
        await self.bot.db.log_moderation_action(
            interaction.guild.id, interaction.user.id, interaction.user.id, "clear", f"{len(deleted)} messages"
        )
        await interaction.followup.send(
            embed=embeds.success("Messages supprimés", f"{len(deleted)} message(s) supprimé(s)."), ephemeral=True
        )

    # ---------------- timeout / untimeout ----------------

    @app_commands.command(name="timeout", description="Mettre un membre en timeout.")
    @app_commands.describe(member="Membre", duration="Durée (ex: 10m, 1h, 1d)", reason="Raison")
    @checks.has_staff_role()
    async def timeout_cmd(self, interaction: discord.Interaction, member: discord.Member, duration: str, reason: str = "Non spécifiée"):
        err = self._hierarchy_check(interaction.user, member)
        if err:
            return await interaction.response.send_message(err, ephemeral=True)

        seconds = helpers.parse_duration(duration)
        if seconds is None or seconds > 28 * 86400:
            return await interaction.response.send_message(
                "❌ Durée invalide. Format : 10m, 2h, 1d (max 28 jours).", ephemeral=True
            )

        try:
            await member.timeout(dt.timedelta(seconds=seconds), reason=reason)
        except discord.Forbidden:
            return await interaction.response.send_message("❌ Permissions insuffisantes.", ephemeral=True)

        await self.bot.db.log_moderation_action(
            interaction.guild.id, member.id, interaction.user.id, "timeout", reason, seconds
        )
        await interaction.response.send_message(
            embed=embeds.success("Timeout appliqué", f"{member.mention} en timeout pour {helpers.format_duration(seconds)}."),
            ephemeral=True,
        )
        await self._log(
            interaction.guild,
            embeds.moderation_log("Timeout", member, interaction.user, reason, helpers.format_duration(seconds)),
        )

    @app_commands.command(name="untimeout", description="Retirer le timeout d'un membre.")
    @checks.has_staff_role()
    async def untimeout_cmd(self, interaction: discord.Interaction, member: discord.Member, reason: str = "Non spécifiée"):
        err = self._hierarchy_check(interaction.user, member)
        if err:
            return await interaction.response.send_message(err, ephemeral=True)
        try:
            await member.timeout(None, reason=reason)
        except discord.Forbidden:
            return await interaction.response.send_message("❌ Permissions insuffisantes.", ephemeral=True)

        await self.bot.db.log_moderation_action(interaction.guild.id, member.id, interaction.user.id, "untimeout", reason)
        await interaction.response.send_message(
            embed=embeds.success("Timeout retiré", f"{member.mention} n'est plus en timeout."), ephemeral=True
        )
        await self._log(interaction.guild, embeds.moderation_log("Timeout retiré", member, interaction.user, reason))

    # ---------------- kick / ban / unban ----------------

    @app_commands.command(name="kick", description="Expulser un membre du serveur.")
    @checks.has_staff_role()
    async def kick(self, interaction: discord.Interaction, member: discord.Member, reason: str = "Non spécifiée"):
        err = self._hierarchy_check(interaction.user, member)
        if err:
            return await interaction.response.send_message(err, ephemeral=True)
        try:
            await member.kick(reason=reason)
        except discord.Forbidden:
            return await interaction.response.send_message("❌ Permissions insuffisantes.", ephemeral=True)

        await self.bot.db.log_moderation_action(interaction.guild.id, member.id, interaction.user.id, "kick", reason)
        await interaction.response.send_message(
            embed=embeds.success("Membre expulsé", f"{member.mention} a été expulsé."), ephemeral=True
        )
        await self._log(interaction.guild, embeds.moderation_log("Expulsion", member, interaction.user, reason))

    @app_commands.command(name="ban", description="Bannir un membre du serveur.")
    @checks.has_staff_role()
    async def ban(self, interaction: discord.Interaction, member: discord.Member, reason: str = "Non spécifiée"):
        err = self._hierarchy_check(interaction.user, member)
        if err:
            return await interaction.response.send_message(err, ephemeral=True)
        try:
            await member.ban(reason=reason, delete_message_seconds=0)
        except discord.Forbidden:
            return await interaction.response.send_message("❌ Permissions insuffisantes.", ephemeral=True)

        await self.bot.db.log_moderation_action(interaction.guild.id, member.id, interaction.user.id, "ban", reason)
        await interaction.response.send_message(
            embed=embeds.success("Membre banni", f"{member.mention} a été banni."), ephemeral=True
        )
        await self._log(interaction.guild, embeds.moderation_log("Bannissement", member, interaction.user, reason))

    @app_commands.command(name="unban", description="Débannir un utilisateur via son ID.")
    @checks.has_staff_role()
    async def unban(self, interaction: discord.Interaction, user_id: str, reason: str = "Non spécifiée"):
        if not user_id.isdigit():
            return await interaction.response.send_message("❌ ID invalide.", ephemeral=True)
        try:
            user = discord.Object(id=int(user_id))
            await interaction.guild.unban(user, reason=reason)
        except discord.NotFound:
            return await interaction.response.send_message("❌ Cet utilisateur n'est pas banni.", ephemeral=True)
        except discord.Forbidden:
            return await interaction.response.send_message("❌ Permissions insuffisantes.", ephemeral=True)

        await self.bot.db.log_moderation_action(interaction.guild.id, int(user_id), interaction.user.id, "unban", reason)
        await interaction.response.send_message(embed=embeds.success("Utilisateur débanni", f"<@{user_id}> a été débanni."), ephemeral=True)
        await self._log(
            interaction.guild,
            embeds.info("Débannissement", f"<@{user_id}> débanni par {interaction.user.mention}. Raison : {reason}"),
        )

    # ---------------- lock / unlock ----------------

    @app_commands.command(name="lock", description="Verrouiller ce salon (les membres ne peuvent plus écrire).")
    @checks.has_staff_role()
    async def lock(self, interaction: discord.Interaction, reason: str = "Non spécifiée"):
        channel = interaction.channel
        try:
            await channel.set_permissions(interaction.guild.default_role, send_messages=False, reason=reason)
        except discord.Forbidden:
            return await interaction.response.send_message("❌ Permissions insuffisantes.", ephemeral=True)
        await self.bot.db.log_moderation_action(interaction.guild.id, interaction.user.id, interaction.user.id, "lock", reason)
        await interaction.response.send_message(embed=embeds.warning("Salon verrouillé", reason))

    @app_commands.command(name="unlock", description="Déverrouiller ce salon.")
    @checks.has_staff_role()
    async def unlock(self, interaction: discord.Interaction, reason: str = "Non spécifiée"):
        channel = interaction.channel
        try:
            await channel.set_permissions(interaction.guild.default_role, send_messages=None, reason=reason)
        except discord.Forbidden:
            return await interaction.response.send_message("❌ Permissions insuffisantes.", ephemeral=True)
        await self.bot.db.log_moderation_action(interaction.guild.id, interaction.user.id, interaction.user.id, "unlock", reason)
        await interaction.response.send_message(embed=embeds.success("Salon déverrouillé", reason))

    async def cog_app_command_error(self, interaction: discord.Interaction, error: app_commands.AppCommandError):
        if isinstance(error, (checks.InsufficientRole, checks.NotConfigured)):
            await interaction.response.send_message(f"❌ {error}", ephemeral=True)
        else:
            logger.exception("Erreur commande modération", exc_info=error)
            if not interaction.response.is_done():
                await interaction.response.send_message("❌ Une erreur est survenue.", ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(ModerationCog(bot))
