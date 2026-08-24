"""
cogs/staff.py
/staff list|add|remove|promote|demote — tracks staff membership and actions
separately from raw Discord roles, so the team has a clear roster and history.
"""
from __future__ import annotations

import discord
from discord import app_commands
from discord.ext import commands

from utils import checks, embeds, permissions


class StaffCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    staff_group = app_commands.Group(name="staff", description="Gestion de l'équipe staff.")

    @staff_group.command(name="list", description="Lister les membres du staff.")
    @checks.has_staff_role()
    async def staff_list(self, interaction: discord.Interaction):
        rows = await self.bot.db.list_staff(interaction.guild.id)
        if not rows:
            return await interaction.response.send_message(
                embed=embeds.info("Équipe staff", "Aucun membre staff enregistré."), ephemeral=True
            )
        lines = [
            f"<@{r['user_id']}> — {r['role_label']} • {r['actions_count']} action(s) • depuis {r['joined_staff_at'][:10]}"
            for r in rows
        ]
        await interaction.response.send_message(
            embed=embeds.info(f"🛡️ Équipe staff ({len(rows)})", "\n".join(lines[:25])), ephemeral=True
        )

    @staff_group.command(name="add", description="Ajouter un membre à l'équipe staff.")
    @app_commands.describe(role_label="Étiquette du rôle staff (ex: Modérateur)")
    @checks.is_owner_or_admin()
    async def staff_add(self, interaction: discord.Interaction, member: discord.Member, role_label: str):
        await self.bot.db.add_staff_member(interaction.guild.id, member.id, role_label, interaction.user.id)
        await interaction.response.send_message(
            embed=embeds.success("Staff ajouté", f"{member.mention} ajouté à l'équipe en tant que **{role_label}**."),
            ephemeral=True,
        )

    @staff_group.command(name="remove", description="Retirer un membre de l'équipe staff.")
    @checks.is_owner_or_admin()
    async def staff_remove(self, interaction: discord.Interaction, member: discord.Member):
        await self.bot.db.remove_staff_member(interaction.guild.id, member.id, interaction.user.id)
        await interaction.response.send_message(
            embed=embeds.success("Staff retiré", f"{member.mention} retiré de l'équipe."), ephemeral=True
        )

    @staff_group.command(name="promote", description="Promouvoir un membre du staff vers un rôle Discord supérieur.")
    @checks.is_owner_or_admin()
    async def staff_promote(self, interaction: discord.Interaction, member: discord.Member, new_role: discord.Role):
        if not permissions.can_assign_role(interaction.user, new_role):
            return await interaction.response.send_message(
                "❌ Vous ne pouvez pas attribuer un rôle égal ou supérieur au vôtre.", ephemeral=True
            )
        try:
            await member.add_roles(new_role, reason=f"Promotion par {interaction.user}")
        except discord.Forbidden:
            return await interaction.response.send_message("❌ Permissions insuffisantes.", ephemeral=True)

        await self.bot.db.log_staff_action(interaction.guild.id, member.id, interaction.user.id, "promoted", new_role.name)
        await interaction.response.send_message(
            embed=embeds.success("Membre promu", f"{member.mention} a été promu à {new_role.mention}."), ephemeral=True
        )

    @staff_group.command(name="demote", description="Rétrograder un membre du staff (retirer un rôle).")
    @checks.is_owner_or_admin()
    async def staff_demote(self, interaction: discord.Interaction, member: discord.Member, role_to_remove: discord.Role):
        if not permissions.can_assign_role(interaction.user, role_to_remove):
            return await interaction.response.send_message(
                "❌ Vous ne pouvez pas retirer un rôle égal ou supérieur au vôtre.", ephemeral=True
            )
        try:
            await member.remove_roles(role_to_remove, reason=f"Rétrogradation par {interaction.user}")
        except discord.Forbidden:
            return await interaction.response.send_message("❌ Permissions insuffisantes.", ephemeral=True)

        await self.bot.db.log_staff_action(interaction.guild.id, member.id, interaction.user.id, "demoted", role_to_remove.name)
        await interaction.response.send_message(
            embed=embeds.success("Membre rétrogradé", f"{role_to_remove.mention} retiré à {member.mention}."), ephemeral=True
        )


async def setup(bot: commands.Bot):
    # staff_group is a class-level app_commands.Group attribute; discord.py
    # registers it automatically with the CommandTree via add_cog().
    await bot.add_cog(StaffCog(bot))
