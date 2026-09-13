"""
views/customization_view.py
Modals utilisés pour personnaliser le règlement (#reglement) et le message
de bienvenue envoyé aux nouveaux membres. Invoqués depuis cogs/customization.py
via /reglement definir et /bienvenue definir.
"""
from __future__ import annotations

import discord

from utils import embeds, rules_message


class RulesEditModal(discord.ui.Modal, title="📜 Modifier le règlement"):
    def __init__(self, bot, current_text: str):
        super().__init__()
        self.bot = bot
        self.rules_input = discord.ui.TextInput(
            label="Texte du règlement (Markdown supporté)",
            style=discord.TextStyle.paragraph,
            max_length=4000,
            required=True,
            default=current_text,
        )
        self.add_item(self.rules_input)

    async def on_submit(self, interaction: discord.Interaction):
        guild = interaction.guild
        db = self.bot.db
        new_text = self.rules_input.value
        await db.update_guild_config(guild.id, rules_text=new_text)

        config = await db.get_guild_config(guild.id)
        rules_channel = guild.get_channel(config["rules_channel"]) if config and config["rules_channel"] else None
        if rules_channel:
            await rules_message.sync_rules_panel(self.bot, guild, rules_channel, new_text)
            description = "Le nouveau texte est maintenant affiché dans le salon règlement."
        else:
            description = "Le texte a été enregistré, mais le salon règlement est introuvable (relancez /setup pour l'afficher)."

        await interaction.response.send_message(
            embed=embeds.success("Règlement mis à jour", description), ephemeral=True
        )


class WelcomeEditModal(discord.ui.Modal, title="👋 Modifier le message de bienvenue"):
    def __init__(self, bot, current_text: str):
        super().__init__()
        self.bot = bot
        self.welcome_input = discord.ui.TextInput(
            label="Message de bienvenue",
            style=discord.TextStyle.paragraph,
            max_length=2000,
            required=True,
            default=current_text,
            placeholder="Variables : {member_mention} {member_name} {server_name} {rules_channel}",
        )
        self.add_item(self.welcome_input)

    async def on_submit(self, interaction: discord.Interaction):
        db = self.bot.db
        await db.update_guild_config(interaction.guild.id, welcome_message=self.welcome_input.value)
        await interaction.response.send_message(
            embed=embeds.success(
                "Message de bienvenue mis à jour",
                "Il sera utilisé pour le prochain membre qui rejoint. Testez le rendu avec /bienvenue voir.",
            ),
            ephemeral=True,
        )
