"""
views/welcome_view.py
Persistent view for the #reglement message: "✅ J'accepte le règlement" button.
Must use a fixed custom_id and be re-registered on bot startup (bot.py) so it
keeps working across restarts.
"""
from __future__ import annotations

import logging

import discord

from utils import embeds

logger = logging.getLogger("afrocodeurs.views.welcome")


class RulesAcceptView(discord.ui.View):
    """Persistent (timeout=None) view attached to the rules message."""

    def __init__(self, bot):
        super().__init__(timeout=None)
        self.bot = bot

    @discord.ui.button(
        label="J'accepte le règlement",
        style=discord.ButtonStyle.success,
        emoji="✅",
        custom_id="afrocodeurs:accept_rules",
    )
    async def accept_rules(self, interaction: discord.Interaction, button: discord.ui.Button):
        guild = interaction.guild
        member = interaction.user
        if guild is None or not isinstance(member, discord.Member):
            return await interaction.response.send_message(
                "Cette action doit être faite depuis le serveur.", ephemeral=True
            )

        db = self.bot.db
        config = await db.get_guild_config(guild.id)
        if config is None:
            return await interaction.response.send_message(
                "⚠️ Le serveur n'est pas encore configuré.", ephemeral=True
            )

        new_member_role = guild.get_role(config["new_member_role"]) if config["new_member_role"] else None
        verified_role = guild.get_role(config["member_role"]) if config["member_role"] else None

        try:
            if verified_role and verified_role not in member.roles:
                await member.add_roles(verified_role, reason="Règlement accepté")
            if new_member_role and new_member_role in member.roles:
                await member.remove_roles(new_member_role, reason="Règlement accepté")
        except discord.Forbidden:
            logger.warning("Permissions insuffisantes pour changer les rôles de %s dans %s", member.id, guild.id)
            return await interaction.response.send_message(
                "❌ Je n'ai pas la permission de mettre à jour vos rôles. Contactez un administrateur.",
                ephemeral=True,
            )

        await db.set_member_verified(guild.id, member.id, True)

        logs_channel = guild.get_channel(config["logs_channel"]) if config["logs_channel"] else None
        if logs_channel:
            try:
                await logs_channel.send(
                    embed=embeds.info("Règlement accepté", f"{member.mention} a accepté le règlement.")
                )
            except discord.Forbidden:
                pass

        await interaction.response.send_message(
            "✅ Merci d'avoir accepté le règlement ! Vous avez maintenant accès au serveur.",
            ephemeral=True,
        )
