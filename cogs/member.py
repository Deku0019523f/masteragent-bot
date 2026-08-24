"""
cogs/member.py
Member-facing commands: /profile, /userinfo, /member, /members.
"""
from __future__ import annotations

import discord
from discord import app_commands
from discord.ext import commands

from utils import embeds


class ProfileModal(discord.ui.Modal, title="👤 Configurer mon profil"):
    domain = discord.ui.TextInput(label="Domaine", placeholder="Développement web, IA, design...", required=False, max_length=100)
    skills = discord.ui.TextInput(label="Compétences", style=discord.TextStyle.paragraph, required=False, max_length=300)
    technologies = discord.ui.TextInput(label="Technologies", placeholder="Python, React, Docker...", required=False, max_length=200)
    bio = discord.ui.TextInput(label="Bio", style=discord.TextStyle.paragraph, required=False, max_length=500)
    links = discord.ui.TextInput(
        label="GitHub, Portfolio, Réseaux (virgule)", required=False, max_length=300,
        placeholder="https://github.com/..., https://portfolio.dev, @twitter",
    )

    def __init__(self, bot):
        super().__init__()
        self.bot = bot

    async def on_submit(self, interaction: discord.Interaction):
        github, portfolio, socials = "", "", ""
        if self.links.value:
            parts = [p.strip() for p in self.links.value.split(",")]
            github = parts[0] if len(parts) > 0 else ""
            portfolio = parts[1] if len(parts) > 1 else ""
            socials = ", ".join(parts[2:]) if len(parts) > 2 else ""

        await self.bot.db.upsert_profile(
            interaction.guild.id,
            interaction.user.id,
            display_name=interaction.user.display_name,
            domain=self.domain.value,
            skills=self.skills.value,
            technologies=self.technologies.value,
            bio=self.bio.value,
            github=github,
            portfolio=portfolio,
            socials=socials,
        )
        await interaction.response.send_message("✅ Profil mis à jour !", ephemeral=True)


class MemberCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="profile", description="Configurer ou afficher un profil membre.")
    @app_commands.describe(member="Laisser vide pour configurer votre propre profil, ou choisir un membre pour le voir")
    async def profile(self, interaction: discord.Interaction, member: discord.Member | None = None):
        if member is None:
            return await interaction.response.send_modal(ProfileModal(self.bot))
        row = await self.bot.db.get_profile(interaction.guild.id, member.id)
        await interaction.response.send_message(embed=embeds.profile_embed(member, row), ephemeral=True)

    @app_commands.command(name="userinfo", description="Afficher les informations d'un membre.")
    async def userinfo(self, interaction: discord.Interaction, member: discord.Member | None = None):
        member = member or interaction.user
        warnings_count = await self.bot.db.count_warnings(interaction.guild.id, member.id)
        roles = ", ".join(r.mention for r in reversed(member.roles) if r.name != "@everyone") or "Aucun"

        embed = embeds.info(f"👤 {member.display_name}")
        if member.display_avatar:
            embed.set_thumbnail(url=member.display_avatar.url)
        embed.add_field(name="ID", value=str(member.id), inline=True)
        embed.add_field(name="Compte créé le", value=discord.utils.format_dt(member.created_at, "D"), inline=True)
        embed.add_field(name="A rejoint le", value=discord.utils.format_dt(member.joined_at, "D") if member.joined_at else "Inconnu", inline=True)
        embed.add_field(name="Statut", value=str(member.status).capitalize(), inline=True)
        embed.add_field(name="Avertissements", value=str(warnings_count), inline=True)
        embed.add_field(name="Rôles", value=roles[:1024], inline=False)
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="serverinfo", description="Afficher les informations du serveur.")
    async def serverinfo(self, interaction: discord.Interaction):
        guild = interaction.guild
        embed = embeds.info(f"🏠 {guild.name}")
        if guild.icon:
            embed.set_thumbnail(url=guild.icon.url)
        embed.add_field(name="Membres", value=str(guild.member_count), inline=True)
        embed.add_field(name="Rôles", value=str(len(guild.roles)), inline=True)
        embed.add_field(name="Salons", value=str(len(guild.channels)), inline=True)
        embed.add_field(name="Créé le", value=discord.utils.format_dt(guild.created_at, "D"), inline=True)
        embed.add_field(name="Propriétaire", value=f"<@{guild.owner_id}>", inline=True)
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="members", description="Voir le nombre de membres par rôle principal.")
    async def members(self, interaction: discord.Interaction):
        db = self.bot.db
        config = await db.get_guild_config(interaction.guild.id)
        if not config:
            return await interaction.response.send_message("⚠️ Serveur non configuré.", ephemeral=True)

        guild = interaction.guild
        lines = []
        for label, rid in [
            ("👑 Fondateur", config["founder_role"]),
            ("🛡️ Administrateur", config["admin_role"]),
            ("🔨 Modérateur", config["moderator_role"]),
            ("⭐ Membre vérifié", config["member_role"]),
            ("🌱 Nouveau membre", config["new_member_role"]),
        ]:
            role = guild.get_role(rid) if rid else None
            lines.append(f"{label} : {len(role.members) if role else 0}")
        await interaction.response.send_message(
            embed=embeds.info("👥 Répartition des membres", "\n".join(lines)), ephemeral=True
        )


async def setup(bot: commands.Bot):
    await bot.add_cog(MemberCog(bot))
