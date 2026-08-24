"""
cogs/welcome.py
Handles new member arrival: assigns "Nouveau membre" role, posts a welcome
message in #bienvenue, and points them to the rules.
"""
from __future__ import annotations

import logging

import discord
from discord.ext import commands

from utils import embeds

logger = logging.getLogger("afrocodeurs.cogs.welcome")


class WelcomeCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        guild = member.guild
        db = self.bot.db
        config = await db.get_guild_config(guild.id)
        if config is None or config["setup_status"] != "completed" or not config["welcome_enabled"]:
            return

        await db.upsert_member(guild.id, member.id)

        new_member_role = guild.get_role(config["new_member_role"]) if config["new_member_role"] else None
        if new_member_role:
            try:
                await member.add_roles(new_member_role, reason="Arrivée sur le serveur")
            except discord.Forbidden:
                logger.warning("Impossible d'attribuer le rôle Nouveau membre à %s", member.id)

        welcome_channel = guild.get_channel(config["welcome_channel"]) if config["welcome_channel"] else None
        rules_channel = guild.get_channel(config["rules_channel"]) if config["rules_channel"] else None

        if welcome_channel:
            rules_mention = rules_channel.mention if rules_channel else "#reglement"
            embed = embeds.info(
                f"Bienvenue {member.display_name} ! 👋",
                f"Ravi de t'accueillir sur **AfroCodeurs**, {member.mention} !\n\n"
                f"Pour commencer :\n"
                f"1️⃣ Lis le règlement dans {rules_mention} et clique sur *J'accepte le règlement*\n"
                f"2️⃣ Présente-toi dans le salon dédié\n"
                f"3️⃣ Explore les salons VibeCoding et rejoins la communauté 🚀",
            )
            if member.display_avatar:
                embed.set_thumbnail(url=member.display_avatar.url)
            try:
                await welcome_channel.send(content=member.mention, embed=embed)
            except discord.Forbidden:
                logger.warning("Impossible d'envoyer le message de bienvenue dans %s", guild.id)

        logs_channel = guild.get_channel(config["logs_channel"]) if config["logs_channel"] else None
        if logs_channel:
            try:
                await logs_channel.send(embed=embeds.info("Membre rejoint", f"{member.mention} ({member.id})"))
            except discord.Forbidden:
                pass

    @commands.Cog.listener()
    async def on_member_remove(self, member: discord.Member):
        guild = member.guild
        db = self.bot.db
        config = await db.get_guild_config(guild.id)
        if config is None:
            return
        logs_channel = guild.get_channel(config["logs_channel"]) if config["logs_channel"] else None
        if logs_channel:
            try:
                await logs_channel.send(embed=embeds.warning("Membre a quitté", f"{member} ({member.id})"))
            except discord.Forbidden:
                pass


async def setup(bot: commands.Bot):
    await bot.add_cog(WelcomeCog(bot))
