"""
cogs/customization.py
Personnalisation du règlement et du message de bienvenue :
  /reglement definir | voir | reinitialiser
  /bienvenue definir | voir | reinitialiser

"definir" et "reinitialiser" sont réservés au propriétaire/administrateur.
"voir" est accessible à tout le monde pour prévisualiser la configuration
actuelle (utile pour vérifier le rendu des variables du message de bienvenue).
"""
from __future__ import annotations

import discord
from discord import app_commands
from discord.ext import commands

from config import settings
from utils import checks, embeds, rules_message
from utils.welcome_message import render_welcome_message
from views.customization_view import RulesEditModal, WelcomeEditModal


class CustomizationCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    reglement_group = app_commands.Group(name="reglement", description="Gérer le règlement personnalisé du serveur.")
    bienvenue_group = app_commands.Group(name="bienvenue", description="Gérer le message de bienvenue personnalisé.")

    # ---------------- /reglement ----------------

    @reglement_group.command(name="definir", description="Modifier le texte du règlement affiché dans le salon règlement.")
    @checks.is_owner_or_admin()
    async def reglement_definir(self, interaction: discord.Interaction):
        config = await self.bot.db.get_guild_config(interaction.guild.id)
        if config is None:
            return await interaction.response.send_message(
                embed=embeds.warning("Serveur non configuré", "Utilisez /setup avant de personnaliser le règlement."),
                ephemeral=True,
            )
        current = config["rules_text"] or settings.DEFAULT_RULES_TEXT
        await interaction.response.send_modal(RulesEditModal(self.bot, current))

    @reglement_group.command(name="voir", description="Afficher le texte actuel du règlement.")
    async def reglement_voir(self, interaction: discord.Interaction):
        config = await self.bot.db.get_guild_config(interaction.guild.id)
        text = config["rules_text"] if config and config["rules_text"] else settings.DEFAULT_RULES_TEXT
        await interaction.response.send_message(embed=embeds.info("📜 Règlement actuel", text), ephemeral=True)

    @reglement_group.command(name="reinitialiser", description="Revenir au règlement par défaut.")
    @checks.is_owner_or_admin()
    async def reglement_reinitialiser(self, interaction: discord.Interaction):
        db = self.bot.db
        await db.update_guild_config(interaction.guild.id, rules_text=None)

        config = await db.get_guild_config(interaction.guild.id)
        rules_channel = (
            interaction.guild.get_channel(config["rules_channel"]) if config and config["rules_channel"] else None
        )
        if rules_channel:
            await rules_message.sync_rules_panel(self.bot, interaction.guild, rules_channel, settings.DEFAULT_RULES_TEXT)

        await interaction.response.send_message(
            embed=embeds.success("Règlement réinitialisé", "Le règlement par défaut a été restauré."), ephemeral=True
        )

    # ---------------- /bienvenue ----------------

    @bienvenue_group.command(name="definir", description="Modifier le message envoyé aux nouveaux membres.")
    @checks.is_owner_or_admin()
    async def bienvenue_definir(self, interaction: discord.Interaction):
        config = await self.bot.db.get_guild_config(interaction.guild.id)
        if config is None:
            return await interaction.response.send_message(
                embed=embeds.warning(
                    "Serveur non configuré", "Utilisez /setup avant de personnaliser le message de bienvenue."
                ),
                ephemeral=True,
            )
        current = config["welcome_message"] or settings.DEFAULT_WELCOME_MESSAGE
        await interaction.response.send_modal(WelcomeEditModal(self.bot, current))

    @bienvenue_group.command(name="voir", description="Prévisualiser le message de bienvenue actuel.")
    async def bienvenue_voir(self, interaction: discord.Interaction):
        config = await self.bot.db.get_guild_config(interaction.guild.id)
        template = config["welcome_message"] if config and config["welcome_message"] else settings.DEFAULT_WELCOME_MESSAGE
        rules_channel = (
            interaction.guild.get_channel(config["rules_channel"]) if config and config["rules_channel"] else None
        )
        preview = render_welcome_message(template, interaction.user, rules_channel)
        await interaction.response.send_message(
            embed=embeds.info("👋 Aperçu du message de bienvenue", preview), ephemeral=True
        )

    @bienvenue_group.command(name="reinitialiser", description="Revenir au message de bienvenue par défaut.")
    @checks.is_owner_or_admin()
    async def bienvenue_reinitialiser(self, interaction: discord.Interaction):
        await self.bot.db.update_guild_config(interaction.guild.id, welcome_message=None)
        await interaction.response.send_message(
            embed=embeds.success("Message de bienvenue réinitialisé", "Le message par défaut a été restauré."),
            ephemeral=True,
        )


async def setup(bot: commands.Bot):
    # reglement_group et bienvenue_group sont des attributs de classe
    # app_commands.Group ; discord.py les enregistre automatiquement dans le
    # CommandTree via add_cog() — pas besoin de tree.add_command manuel.
    await bot.add_cog(CustomizationCog(bot))
