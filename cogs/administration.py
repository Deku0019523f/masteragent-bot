"""
cogs/administration.py
/role add|remove|info|list and /config — administrative controls.
Role assignment always respects hierarchy: a user can never assign a role
equal to or above their own top role.
"""
from __future__ import annotations

import discord
from discord import app_commands
from discord.ext import commands

from utils import checks, embeds, permissions


class AdministrationCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    role_group = app_commands.Group(name="role", description="Gestion des rôles.")

    @role_group.command(name="add", description="Attribuer un rôle à un membre.")
    @checks.has_staff_role()
    async def role_add(self, interaction: discord.Interaction, member: discord.Member, role: discord.Role):
        actor = interaction.user
        if not permissions.can_assign_role(actor, role):
            return await interaction.response.send_message(
                "❌ Vous ne pouvez pas attribuer un rôle égal ou supérieur au vôtre.", ephemeral=True
            )
        if not permissions.bot_can_act_on(interaction.guild, member) and role >= interaction.guild.me.top_role:
            return await interaction.response.send_message(
                "❌ Mon rôle est trop bas pour attribuer ce rôle.", ephemeral=True
            )
        try:
            await member.add_roles(role, reason=f"Ajouté par {actor}")
        except discord.Forbidden:
            return await interaction.response.send_message("❌ Permissions insuffisantes.", ephemeral=True)
        await interaction.response.send_message(
            embed=embeds.success("Rôle attribué", f"{role.mention} ajouté à {member.mention}."), ephemeral=True
        )

    @role_group.command(name="remove", description="Retirer un rôle d'un membre.")
    @checks.has_staff_role()
    async def role_remove(self, interaction: discord.Interaction, member: discord.Member, role: discord.Role):
        actor = interaction.user
        if not permissions.can_assign_role(actor, role):
            return await interaction.response.send_message(
                "❌ Vous ne pouvez pas retirer un rôle égal ou supérieur au vôtre.", ephemeral=True
            )
        try:
            await member.remove_roles(role, reason=f"Retiré par {actor}")
        except discord.Forbidden:
            return await interaction.response.send_message("❌ Permissions insuffisantes.", ephemeral=True)
        await interaction.response.send_message(
            embed=embeds.success("Rôle retiré", f"{role.mention} retiré de {member.mention}."), ephemeral=True
        )

    @role_group.command(name="info", description="Informations sur un rôle.")
    @checks.has_staff_role()
    async def role_info(self, interaction: discord.Interaction, role: discord.Role):
        embed = embeds.info(
            f"Rôle : {role.name}",
            f"ID : `{role.id}`\nMembres : {len(role.members)}\nPosition : {role.position}\n"
            f"Mentionnable : {'Oui' if role.mentionable else 'Non'}\nCouleur : {role.colour}",
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @role_group.command(name="list", description="Lister tous les rôles du serveur.")
    @checks.has_staff_role()
    async def role_list(self, interaction: discord.Interaction):
        roles = sorted(interaction.guild.roles, key=lambda r: r.position, reverse=True)
        lines = [f"{r.mention} — {len(r.members)} membre(s)" for r in roles if r.name != "@everyone"]
        await interaction.response.send_message(
            embed=embeds.info("Rôles du serveur", "\n".join(lines[:25])), ephemeral=True
        )

    # ---------------- /config ----------------

    @app_commands.command(name="config", description="Afficher ou modifier la configuration Master Agent.")
    @app_commands.describe(
        welcome_enabled="Activer/désactiver le système d'accueil",
        tickets_enabled="Activer/désactiver les tickets",
        projects_enabled="Activer/désactiver la présentation d'agents (/agent)",
        voice_enabled="Activer/désactiver les salons vocaux temporaires",
    )
    @checks.is_owner_or_admin()
    async def config_cmd(
        self,
        interaction: discord.Interaction,
        welcome_enabled: bool | None = None,
        tickets_enabled: bool | None = None,
        projects_enabled: bool | None = None,
        voice_enabled: bool | None = None,
    ):
        db = self.bot.db
        updates = {}
        if welcome_enabled is not None:
            updates["welcome_enabled"] = int(welcome_enabled)
        if tickets_enabled is not None:
            updates["tickets_enabled"] = int(tickets_enabled)
        if projects_enabled is not None:
            updates["projects_enabled"] = int(projects_enabled)
        if voice_enabled is not None:
            updates["voice_enabled"] = int(voice_enabled)

        if updates:
            await db.update_guild_config(interaction.guild.id, **updates)

        config = await db.get_guild_config(interaction.guild.id)
        if config is None:
            return await interaction.response.send_message(
                "⚠️ Le serveur n'est pas encore configuré. Utilisez /setup.", ephemeral=True
            )

        embed = embeds.info(
            "⚙️ Configuration Master Agent",
            f"Statut setup : `{config['setup_status']}`\n"
            f"Accueil : {'✅' if config['welcome_enabled'] else '❌'}\n"
            f"Tickets : {'✅' if config['tickets_enabled'] else '❌'}\n"
            f"Projets : {'✅' if config['projects_enabled'] else '❌'}\n"
            f"Vocaux temporaires : {'✅' if config['voice_enabled'] else '❌'}\n"
            f"Seuil timeout auto : {config['warn_timeout_threshold']} avertissements\n"
            f"Seuil sanction majeure : {config['warn_major_threshold']} avertissements",
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)


async def setup(bot: commands.Bot):
    # role_group is a class-level app_commands.Group attribute; discord.py
    # registers it automatically with the CommandTree via add_cog().
    await bot.add_cog(AdministrationCog(bot))
