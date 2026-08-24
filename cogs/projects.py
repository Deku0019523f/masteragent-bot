"""
cogs/projects.py
/projet — opens a modal form and publishes a formatted project embed.
"""
from __future__ import annotations

import discord
from discord import app_commands
from discord.ext import commands

from utils import embeds
from views.project_view import ProjectModal


class ProjectsCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="projet", description="Présenter un projet à la communauté.")
    async def projet(self, interaction: discord.Interaction):
        db = self.bot.db
        config = await db.get_guild_config(interaction.guild.id)
        if config is None or not config["projects_enabled"]:
            return await interaction.response.send_message(
                "❌ Le système de projets est désactivé sur ce serveur.", ephemeral=True
            )

        target_channel_id = await db.get_resource(interaction.guild.id, "channel", "🚀・projets")
        target_channel = interaction.guild.get_channel(target_channel_id) if target_channel_id else interaction.channel
        if target_channel is None:
            target_channel = interaction.channel

        await interaction.response.send_modal(ProjectModal(self.bot, target_channel))


async def setup(bot: commands.Bot):
    await bot.add_cog(ProjectsCog(bot))
