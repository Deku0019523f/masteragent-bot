"""
cogs/utility.py
General utility commands: /ping, /help, /about, /rules, /stats.
"""
from __future__ import annotations

import time

import discord
from discord import app_commands
from discord.ext import commands

from utils import embeds

STAFF_COMMANDS = {
    "warn", "warnings", "clear", "timeout", "untimeout", "kick", "ban", "unban",
    "lock", "unlock", "role", "config", "staff", "setup", "reset",
}


class UtilityCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.start_time = time.monotonic()

    @app_commands.command(name="ping", description="Vérifier la latence du bot.")
    async def ping(self, interaction: discord.Interaction):
        latency_ms = round(self.bot.latency * 1000)
        await interaction.response.send_message(embed=embeds.info("🏓 Pong !", f"Latence : `{latency_ms}ms`"))

    @app_commands.command(name="about", description="À propos du bot Master Agent.")
    async def about(self, interaction: discord.Interaction):
        embed = embeds.info(
            "🤖 Master Agent",
            "Communauté officielle de **Master Agent**, la plateforme de création d'agents IA "
            "pour l'automatisation WhatsApp. Échangez avec d'autres créateurs d'agents, partagez vos "
            "cas d'usage et obtenez de l'aide.\n\n"
            "Ce bot administre automatiquement la structure du serveur, la modération, les tickets, "
            "les profils et les présentations d'agents.",
        )
        embed.add_field(name="Serveurs", value=str(len(self.bot.guilds)), inline=True)
        embed.add_field(name="Latence", value=f"{round(self.bot.latency*1000)}ms", inline=True)
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="rules", description="Afficher le lien vers le règlement.")
    async def rules(self, interaction: discord.Interaction):
        config = await self.bot.db.get_guild_config(interaction.guild.id)
        rules_channel = interaction.guild.get_channel(config["rules_channel"]) if config and config["rules_channel"] else None
        if rules_channel:
            await interaction.response.send_message(f"📜 Consultez le règlement ici : {rules_channel.mention}", ephemeral=True)
        else:
            await interaction.response.send_message("⚠️ Le salon règlement n'est pas encore configuré.", ephemeral=True)

    @app_commands.command(name="stats", description="Statistiques du serveur Master Agent.")
    async def stats(self, interaction: discord.Interaction):
        db = self.bot.db
        guild_id = interaction.guild.id
        tickets_open = await db.fetchall("SELECT id FROM tickets WHERE guild_id=? AND status!='closed'", (guild_id,))
        projects = await db.fetchall("SELECT id FROM projects WHERE guild_id=?", (guild_id,))
        warnings_total = await db.fetchall("SELECT id FROM warnings WHERE guild_id=?", (guild_id,))

        embed = embeds.info(
            "📊 Statistiques Master Agent",
            f"Membres : {interaction.guild.member_count}\n"
            f"Tickets ouverts : {len(tickets_open)}\n"
            f"Projets partagés : {len(projects)}\n"
            f"Avertissements enregistrés : {len(warnings_total)}",
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="help", description="Afficher les commandes disponibles.")
    async def help_cmd(self, interaction: discord.Interaction):
        member = interaction.user
        is_staff = False
        if isinstance(member, discord.Member):
            if member.id == interaction.guild.owner_id or member.guild_permissions.administrator:
                is_staff = True
            else:
                config = await self.bot.db.get_guild_config(interaction.guild.id)
                if config:
                    staff_ids = {rid for rid in (config["admin_role"], config["moderator_role"], config["founder_role"]) if rid}
                    is_staff = any(r.id in staff_ids for r in member.roles)

        general = [
            "/profile", "/userinfo", "/serverinfo", "/agent", "/ping", "/about", "/rules", "/stats", "/help", "/members",
            "/reglement voir", "/bienvenue voir",
        ]
        staff_cmds = [
            "/setup", "/config", "/warn", "/warnings", "/clear", "/timeout", "/untimeout",
            "/kick", "/ban", "/unban", "/lock", "/unlock", "/role add|remove|info|list",
            "/staff list|add|remove|promote|demote", "/reset config|masteragent",
            "/reglement definir|reinitialiser", "/bienvenue definir|reinitialiser",
        ]

        description = "**Commandes générales**\n" + " • ".join(general)
        if is_staff:
            description += "\n\n**Commandes staff**\n" + " • ".join(staff_cmds)

        await interaction.response.send_message(embed=embeds.info("📖 Aide Master Agent", description), ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(UtilityCog(bot))
