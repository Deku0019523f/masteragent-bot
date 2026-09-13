"""
views/ticket_view.py
Persistent views for the ticket system:
- TicketPanelView: the "Créer un ticket" button posted in #support
- TicketCategorySelect: dropdown to choose ticket category
- TicketControlView: buttons inside an open ticket (claim / close / delete)

All use fixed custom_ids and are re-registered in bot.py on startup so they
survive restarts.
"""
from __future__ import annotations

import logging

import discord

from utils import embeds, permissions

logger = logging.getLogger("masteragent.views.ticket")

TICKET_CATEGORIES = {
    "support": "🛠️ Support technique",
    "collaboration": "🤝 Collaboration",
    "signalement": "🚨 Signalement",
    "partenariat": "💼 Partenariat",
    "autre": "❓ Autre",
}


class TicketCategorySelect(discord.ui.Select):
    def __init__(self, bot):
        self.bot = bot
        options = [
            discord.SelectOption(label=label, value=key) for key, label in TICKET_CATEGORIES.items()
        ]
        super().__init__(
            placeholder="Choisissez une catégorie...",
            options=options,
            custom_id="masteragent:ticket_category_select",
            min_values=1,
            max_values=1,
        )

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True, thinking=True)
        category = self.values[0]
        guild = interaction.guild
        member = interaction.user
        db = self.bot.db

        config = await db.get_guild_config(guild.id)
        if config is None or not config["tickets_enabled"]:
            return await interaction.followup.send("❌ Le système de tickets est désactivé.", ephemeral=True)

        staff_role_ids = [rid for rid in (config["admin_role"], config["moderator_role"]) if rid]
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(view_channel=False),
            member: discord.PermissionOverwrite(view_channel=True, send_messages=True, read_message_history=True),
            guild.me: discord.PermissionOverwrite(view_channel=True, send_messages=True, manage_channels=True),
        }
        for rid in staff_role_ids:
            role = guild.get_role(rid)
            if role:
                overwrites[role] = discord.PermissionOverwrite(view_channel=True, send_messages=True)

        ticket_number = await db.next_ticket_number(guild.id)
        channel_name = f"ticket-{ticket_number:03d}"

        support_category_id = config["staff_category"]
        category_obj = guild.get_channel(support_category_id) if support_category_id else None
        parent = category_obj if isinstance(category_obj, discord.CategoryChannel) else None

        try:
            channel = await guild.create_text_channel(
                name=channel_name,
                overwrites=overwrites,
                category=parent,
                topic=f"Ticket ouvert par {member} ({member.id}) — {TICKET_CATEGORIES[category]}",
                reason=f"Ticket créé par {member}",
            )
        except discord.Forbidden:
            return await interaction.followup.send(
                "❌ Je n'ai pas la permission de créer des salons.", ephemeral=True
            )

        await db.create_ticket(guild.id, channel.id, member.id, category, ticket_number)

        embed = embeds.info(
            f"🎫 Ticket #{ticket_number:03d}",
            f"Catégorie : **{TICKET_CATEGORIES[category]}**\n"
            f"Ouvert par : {member.mention}\n\n"
            "Un membre du staff va vous répondre bientôt. Décrivez votre demande ci-dessous.",
        )
        await channel.send(content=member.mention, embed=embed, view=TicketControlView(self.bot))

        await interaction.followup.send(f"✅ Votre ticket a été créé : {channel.mention}", ephemeral=True)


class TicketCategoryView(discord.ui.View):
    def __init__(self, bot):
        super().__init__(timeout=None)
        self.add_item(TicketCategorySelect(bot))


class TicketPanelView(discord.ui.View):
    """Posted once in #support. Clicking opens an ephemeral category picker."""

    def __init__(self, bot):
        super().__init__(timeout=None)
        self.bot = bot

    @discord.ui.button(
        label="Créer un ticket",
        style=discord.ButtonStyle.primary,
        emoji="🎫",
        custom_id="masteragent:create_ticket",
    )
    async def create_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message(
            "Choisissez la catégorie de votre ticket :",
            view=TicketCategoryView(self.bot),
            ephemeral=True,
        )


class TicketControlView(discord.ui.View):
    """Posted inside each ticket channel: claim / close / delete."""

    def __init__(self, bot):
        super().__init__(timeout=None)
        self.bot = bot

    async def _is_staff(self, interaction: discord.Interaction) -> bool:
        guild = interaction.guild
        member = interaction.user
        if guild is None or not isinstance(member, discord.Member):
            return False
        if member.id == guild.owner_id or member.guild_permissions.administrator:
            return True
        config = await self.bot.db.get_guild_config(guild.id)
        if not config:
            return False
        staff_ids = {rid for rid in (config["admin_role"], config["moderator_role"]) if rid}
        return any(r.id in staff_ids for r in member.roles)

    @discord.ui.button(label="Prendre en charge", style=discord.ButtonStyle.secondary, emoji="🙋",
                        custom_id="masteragent:ticket_claim")
    async def claim(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not await self._is_staff(interaction):
            return await interaction.response.send_message("❌ Réservé au staff.", ephemeral=True)
        await self.bot.db.claim_ticket(interaction.channel_id, interaction.user.id)
        await interaction.response.send_message(
            embed=embeds.info("Ticket pris en charge", f"{interaction.user.mention} s'occupe de ce ticket.")
        )

    @discord.ui.button(label="Fermer", style=discord.ButtonStyle.danger, emoji="🔒",
                        custom_id="masteragent:ticket_close")
    async def close(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not await self._is_staff(interaction):
            return await interaction.response.send_message("❌ Réservé au staff.", ephemeral=True)

        db = self.bot.db
        await db.close_ticket(interaction.channel_id, interaction.user.id, "Fermé via bouton")
        ticket = await db.get_ticket_by_channel(interaction.channel_id)

        try:
            await interaction.channel.set_permissions(
                interaction.guild.get_member(ticket["opener_id"]), view_channel=False
            )
        except (discord.Forbidden, discord.HTTPException, AttributeError):
            pass

        await interaction.response.send_message(
            embed=embeds.warning("Ticket fermé", f"Fermé par {interaction.user.mention}.")
        )

        config = await db.get_guild_config(interaction.guild.id)
        logs_channel = interaction.guild.get_channel(config["logs_channel"]) if config and config["logs_channel"] else None
        if logs_channel:
            await logs_channel.send(
                embed=embeds.info(
                    "Ticket fermé",
                    f"Ticket #{ticket['ticket_number']:03d} fermé par {interaction.user.mention}.",
                )
            )

    @discord.ui.button(label="Supprimer", style=discord.ButtonStyle.secondary, emoji="🗑️",
                        custom_id="masteragent:ticket_delete")
    async def delete(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not await self._is_staff(interaction):
            return await interaction.response.send_message("❌ Réservé au staff.", ephemeral=True)
        await interaction.response.send_message("🗑️ Suppression du salon dans 5 secondes...")
        await interaction.channel.delete(reason=f"Ticket supprimé par {interaction.user}", delay=5)
